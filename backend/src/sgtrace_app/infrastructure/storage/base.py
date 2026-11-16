"""Blob storage contract."""
from dataclasses import dataclass
from typing import BinaryIO


@dataclass(frozen=True)
class StoredObject:
    uri: str
    sha256: str
    size_bytes: int
    content_type: str


class Storage:
    def put(self, stream: BinaryIO, key: str, content_type: str, max_bytes: int) -> StoredObject:
        raise NotImplementedError

    def open(self, uri: str) -> BinaryIO:
        raise NotImplementedError
