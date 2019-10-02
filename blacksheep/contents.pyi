import json
import uuid
from typing import AsyncGenerator, Any, Callable, Optional, List, Dict


class Content:

    def __init__(self,
                 content_type: bytes,
                 data: bytes):
        self.type = content_type
        self.body = data
        self.length = len(data)

    async def read(self) -> bytes:
        return self.body


class StreamedContent(Content):

    def __init__(self,
                 content_type: bytes,
                 data_provider: AsyncGenerator[bytes]):
        self.type = content_type
        self.body = None
        self.length = -1
        self.generator = data_provider

    async def get_parts(self) -> AsyncGenerator[bytes]: ...


class ASGIContent(Content):

    def __init__(self, receive: Callable[[], bytes]):
        self.type = None
        self.body = None
        self.length = -1
        self.receive = receive

    def dispose(self): ...

    async def stream(self) -> AsyncGenerator[bytes]: ...

    async def read(self) -> bytes: ...


class TextContent(Content):

    def __init__(self, text: str):
        super().__init__(b'text/plain; charset=utf-8', text.encode('utf8'))


class HtmlContent(Content):

    def __init__(self, html: str):
        super().__init__(b'text/html; charset=utf-8', html.encode('utf8'))


class JsonContent(Content):

    def __init__(self, data: object, dumps: Callable[[Any], str] = json.dumps):
        super().__init__(b'application/json', dumps(data).encode('utf8'))


class FormContent(Content):

    def __init__(self, data: dict):
        super().__init__(b'application/x-www-form-urlencoded', write_www_form_urlencoded(data))


class FormPart:

    def __init__(self,
                 name: bytes,
                 data: bytes,
                 content_type: Optional[bytes]=None,
                 file_name: Optional[bytes]=None,
                 charset: Optional[bytes] = None):
        self.name = name
        self.data = data
        self.file_name = file_name
        self.content_type = content_type
        self.charset = charset

    def __repr__(self):
        return f'<FormPart {self.name} - at {id(self)}>'


class MultiPartFormData(Content):

    def __init__(self, parts: List[FormPart]):
        self.parts = parts
        self.boundary = b'------' + str(uuid.uuid4()).replace('-', '').encode()
        super().__init__(b'multipart/form-data; boundary=' + self.boundary, ...)


def parse_www_form(content: str) -> Dict[str, List[str]]:
    """Parses application/x-www-form-urlencoded content"""