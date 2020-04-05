import pathlib
import pytest

from blacksheep.common.asyncfs import FilesHandler


@pytest.fixture()
def files_folder():
    return pathlib.Path(__file__).parent.absolute() / 'files'


@pytest.mark.asyncio
@pytest.mark.parametrize('file_name', [
    'example.txt',
    'pexels-photo-126407.jpeg',
    'README.md'
])
async def test_files_handler_read_file(
    files_folder: pathlib.Path,
    file_name: str
):
    handler = FilesHandler()
    full_file_path = str(files_folder / file_name)

    contents = await handler.read(full_file_path)

    with open(full_file_path, mode='rb') as f:
        expected_contents = f.read()

    assert contents == expected_contents


@pytest.mark.asyncio
@pytest.mark.parametrize('file_name', [
    'example.txt',
    'pexels-photo-126407.jpeg',
    'README.md'
])
async def test_files_handler_read_file_with_open(
    files_folder: pathlib.Path,
    file_name: str
):
    handler = FilesHandler()

    full_file_path = str(files_folder / file_name)
    async with handler.open(full_file_path) as file_context:
        contents = await file_context.read()

    with open(full_file_path, mode='rb') as file:
        expected_contents = file.read()

    assert contents == expected_contents


@pytest.mark.asyncio
@pytest.mark.parametrize('file_name,index,size', [
    ['example.txt', 0, 10],
    ['example.txt', 10, 10],
    ['example.txt', 5, 15],
    ['README.md', 0, 10],
    ['README.md', 10, 10],
    ['README.md', 5, 15],
])
async def test_files_handler_seek_and_read_chunk(
    files_folder: pathlib.Path,
    file_name: str,
    index: int,
    size: int
):
    handler = FilesHandler()

    full_file_path = str(files_folder / file_name)
    async with handler.open(full_file_path) as file_context:
        await file_context.seek(index)
        chunk_read_async = await file_context.read(size)

    with open(full_file_path, mode='rb') as file:
        file.seek(index)
        chunk_read = file.read(size)

    assert chunk_read_async == chunk_read


@pytest.mark.asyncio
@pytest.mark.parametrize('file_name', [
    'example.txt',
    'pexels-photo-126407.jpeg',
    'README.md'
])
async def test_files_handler_read_file_chunks(
    files_folder: pathlib.Path,
    file_name: str
):
    handler = FilesHandler()
    full_file_path = str(files_folder / file_name)

    chunk: bytes
    chunk_size = 1024
    contents = b''
    expected_contents = b''

    async with handler.open(full_file_path) as file_context:
        async for chunk in file_context.chunks(chunk_size):
            assert chunk is not None
            contents += chunk

    with open(full_file_path, mode='rb') as f:
        while True:
            chunk = f.read(chunk_size)

            if not chunk:
                break
            expected_contents += chunk

    assert contents == expected_contents