"""Cache immutable public image encoding, invalidating when a file changes."""
from base64 import b64encode
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=32)
def _data_url(path: str, modified: int, size: int) -> str:
    content = Path(path).read_bytes()
    mime = 'image/avif' if content[4:8] == b'ftyp' else 'image/png'
    return f'data:{mime};base64,{b64encode(content).decode("ascii")}'


def image_data_url(path: Path) -> str:
    stat = path.stat()
    return _data_url(str(path), stat.st_mtime_ns, stat.st_size)
