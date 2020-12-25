import re
from typing import Any, Awaitable, Callable, Iterable, Optional, FrozenSet

from blacksheep.messages import Request, Response
from .responses import text, ok


class CORSException(Exception):
    pass


class DisallowedOriginCORSException(CORSException):
    def __init__(self) -> None:
        super().__init__("The request origin is not allowed.")


class DisallowedMethodCORSException(CORSException):
    def __init__(self) -> None:
        super().__init__("The request method is not allowed.")


class DisallowedHeaderCORSException(CORSException):
    def __init__(self, header_name: str) -> None:
        super().__init__(
            f"The request includes an header that is not allowed: {header_name}."
        )


class CORSPolicy:
    def __init__(
        self,
        *,
        allow_methods: Optional[Iterable[str]] = None,
        allow_headers: Optional[Iterable[str]] = None,
        allow_origins: Optional[Iterable[str]] = None,
        allow_credentials: bool = False,
        max_age: int = 5,
        expose_headers: Optional[Iterable[str]] = None,
    ) -> None:
        if expose_headers is None:
            expose_headers = self.default_expose_headers()
        self._max_age: int = 300
        self._allow_methods: FrozenSet[str]
        self._allow_headers: FrozenSet[str]
        self._allow_origins: FrozenSet[str]
        self._expose_headers: FrozenSet[str]
        self.allow_methods = allow_methods or []
        self.allow_headers = allow_headers or []
        self.allow_origins = allow_origins or []
        self.allow_credentials = bool(allow_credentials)
        self.expose_headers = expose_headers
        self.max_age = max_age

    def default_expose_headers(self) -> FrozenSet[str]:
        return frozenset(
            value.lower()
            for value in {
                "Transfer-Encoding",
                "Content-Encoding",
                "Vary",
                "Request-Context",
                "Set-Cookie",
                "Server",
                "Date",
            }
        )

    def _normalize_set(
        self, value: Iterable[str], ci_function: Callable[[str], str]
    ) -> FrozenSet[str]:
        if isinstance(value, str):
            value = re.split(r"\s|,\s?|;\s?", value)
        return frozenset(map(ci_function, value))

    @property
    def allow_methods(self) -> FrozenSet[str]:
        return self._allow_methods

    @allow_methods.setter
    def allow_methods(self, value: Iterable[str]) -> None:
        self._allow_methods = self._normalize_set(value, str.upper)

    @property
    def allow_headers(self) -> FrozenSet[str]:
        return self._allow_headers

    @allow_headers.setter
    def allow_headers(self, value: Iterable[str]) -> None:
        self._allow_headers = self._normalize_set(value, str.lower)

    @property
    def allow_origins(self) -> FrozenSet[str]:
        return self._allow_origins

    @allow_origins.setter
    def allow_origins(self, value: Iterable[str]) -> None:
        self._allow_origins = self._normalize_set(value, str.lower)

    @property
    def max_age(self) -> int:
        return self._max_age

    @max_age.setter
    def max_age(self, value) -> None:
        int_value = int(value)
        if int_value < 0:
            raise ValueError("max_age must be a positive number")
        self._max_age = int_value

    @property
    def expose_headers(self) -> FrozenSet[str]:
        return self._expose_headers

    @expose_headers.setter
    def expose_headers(self, value: Iterable[str]) -> None:
        self._expose_headers = self._normalize_set(value, str.lower)

    def allow_any_header(self) -> "CORSPolicy":
        self.allow_headers = frozenset("*")
        return self

    def allow_any_method(self) -> "CORSPolicy":
        self.allow_methods = frozenset("*")
        return self

    def allow_any_origin(self) -> "CORSPolicy":
        self.allow_origins = frozenset("*")
        return self


class CORSStrategy:
    # TODO: support a number of policies
    def __init__(self, default_policy: CORSPolicy) -> None:
        self.default_policy = default_policy


def _get_invalid_origin_response() -> Response:
    return text("The origin of the request is not enabled by CORS rules.", 400)


def _get_invalid_method_response() -> Response:
    return text("The method of the request is not enabled by CORS rules.", 400)


def _get_invalid_header_response(header_name: str) -> Response:
    return text(f"The request header {header_name} is not enabled by CORS rules.", 400)


def get_cors_middleware(
    strategy: CORSStrategy,
) -> Callable[[Request, Callable[..., Any]], Awaitable[Response]]:
    # TODO: use a policy by request method and path

    # TODO: how to support METHOD and PATH based rules?
    # requires a dictionary of METHOD-PATH: CORS POLICY NAME
    policy = strategy.default_policy
    allowed_origins = ", ".join(policy.allow_origins).encode()
    allowed_methods = ", ".join(policy.allow_methods).encode()
    expose_headers = ", ".join(policy.expose_headers).encode()
    max_age = str(policy.max_age).encode()

    async def cors_middleware(request, handler):
        origin = request.get_first_header(b"Origin")

        if not origin:
            # not a CORS request
            return await handler(request)

        if "*" not in policy.allow_origins and origin not in policy.allow_origins:
            return _get_invalid_origin_response()

        next_request_method = request.get_first_header(b"Access-Control-Request-Method")

        if next_request_method:
            # This is a preflight request;
            if (
                "*" not in policy.allow_methods
                and next_request_method not in policy.allow_methods
            ):
                return _get_invalid_method_response()

            next_request_headers = request.get_first_header(
                b"Access-Control-Request-Headers"
            )

            if next_request_headers:
                for value in next_request_headers.split(b","):
                    str_value = value.strip().decode()
                    if str_value.lower() not in policy.allow_headers:
                        return _get_invalid_header_response(str_value)

            response = ok()
            response.set_header(b"Access-Control-Allow-Methods", allowed_methods)
            response.set_header(b"Access-Control-Allow-Origin", allowed_origins)

            if next_request_headers:
                response.set_header(
                    b"Access-Control-Allow-Headers", next_request_headers
                )

            response.set_header(b"Access-Control-Max-Age", max_age)
            return response

        # regular (non-preflight) CORS request
        if "*" not in policy.allow_origins and origin not in policy.allow_origins:
            return _get_invalid_origin_response()

        if (
            "*" not in policy.allow_methods
            and request.method not in policy.allow_methods
        ):
            return _get_invalid_method_response()

        response = await handler(request)
        response.set_header(b"Access-Control-Allow-Origin", allowed_origins)
        response.set_header(b"Access-Control-Expose-Headers", expose_headers)
        # TODO: handle credentials
        return response

    return cors_middleware
