"""Local content-addressed storage for development and single-node deployments."""
from hashlib import sha256
from pathlib import Path
from shutil import copyfileobj
from tempfile import NamedTemporaryFile
from typing import BinaryIO

from .base import Storage, StoredObject


class LocalStorage(Storage):
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, stream: BinaryIO, key: str, content_type: str, max_bytes: int) -> StoredObject:
        digest = sha256()
        size = 0
        with NamedTemporaryFile(dir=self.root, delete=False) as temporary:
            while chunk := stream.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    temporary.close()
                    Path(temporary.name).unlink(missing_ok=True)
                    raise ValueError("material exceeds maximum size")
                digest.update(chunk)
                temporary.write(chunk)
            temporary_path = Path(temporary.name)
        target = self.root / digest.hexdigest()[:2] / digest.hexdigest()
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            temporary_path.replace(target)
        else:
            temporary_path.unlink(missing_ok=True)
        return StoredObject(f"file://{target}", digest.hexdigest(), size, content_type)

    def open(self, uri: str) -> BinaryIO:
        if not uri.startswith("file://"):
            raise ValueError("local storage only supports file:// URIs")
        path = Path(uri.removeprefix("file://")).resolve()
        if self.root.resolve() not in path.parents:
            raise ValueError("storage URI escapes configured root")
        return path.open("rb")
