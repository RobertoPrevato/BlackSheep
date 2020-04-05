import asyncio
from asyncio import BaseEventLoop, AbstractEventLoop
from typing import AsyncIterable, Optional
from concurrent.futures.thread import ThreadPoolExecutor


class PoolClient:

    def __init__(
        self,
        loop: Optional[BaseEventLoop] = None,
        executor: Optional[ThreadPoolExecutor] = None
    ):
        self._loop = loop or asyncio.get_event_loop()
        self._executor = executor

    @property
    def loop(self) -> AbstractEventLoop:
        return self._loop

    async def run(self, func, *args):
        return await self._loop.run_in_executor(self._executor, func, *args)


class FileContext(PoolClient):

    def __init__(
        self,
        file_path: str,
        *,
        loop: Optional[BaseEventLoop] = None,
        mode: str = 'rb'
    ):
        super().__init__(loop)
        self._file_path = file_path
        self._file = None
        self._mode = mode

    @property
    def mode(self) -> str:
        return self.mode

    @property
    def file(self):
        return self._file

    async def seek(self, offset: int, whence: int = 0) -> None:
        await self.run(self._file.seek, offset, whence)

    async def read(self, chunk_size: Optional[int] = None) -> bytes:
        return await self.run(self.file.read, chunk_size)

    async def chunks(
        self,
        chunk_size: int = 1024 * 64
    ) -> AsyncIterable[bytes]:
        while True:
            chunk = await self.run(self.file.read, chunk_size)

            if not chunk:
                break

            yield chunk
        yield b''

    async def __aenter__(self):
        self._file = await self.run(open, self._file_path, self._mode)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            await self.run(self._file.close)
        finally:
            self._file = None


class FilesHandler(PoolClient):
    """Provides methods to handle files asynchronously."""

    def __init__(self, loop: Optional[BaseEventLoop] = None):
        super().__init__(loop)

    def open(self, file_path: str, mode: str = 'rb') -> FileContext:
        return FileContext(file_path, mode=mode, loop=self.loop)

    async def read(
        self,
        file_path: str,
        size: Optional[int] = None
    ) -> bytes:
        async with FileContext(file_path) as file:
            return await file.read(size)

    async def chunks(
        self,
        file_path: str,
        chunk_size: int = 1024 * 64
    ) -> AsyncIterable[bytes]:
        async with FileContext(file_path) as file:
            async for chunk in file.chunks(chunk_size):
                yield chunk