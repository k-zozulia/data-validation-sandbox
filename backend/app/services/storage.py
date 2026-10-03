"""Object storage for uploaded files and job artifacts.

The single point of storage abstraction: the database keeps metadata, while raw
bytes (source files, per-row validation results) live here. Locally that's a
directory (a Docker volume); for a cloud deployment switch STORAGE_BACKEND=s3,
which also works with any S3-compatible store such as MinIO.
"""
from __future__ import annotations

import shutil
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from app.config import settings


class Storage(Protocol):
    def put(self, key: str, data: bytes) -> None: ...
    def get(self, key: str) -> bytes | None: ...
    def delete_prefix(self, prefix: str) -> None: ...
    def ping(self) -> bool: ...


class LocalStorage:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):          # no "../" escapes
            raise ValueError(f"Invalid storage key: {key!r}")
        return path

    def put(self, key: str, data: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(path)                                 # atomic on POSIX

    def get(self, key: str) -> bytes | None:
        path = self._path(key)
        return path.read_bytes() if path.is_file() else None

    def delete_prefix(self, prefix: str) -> None:
        path = self._path(prefix)
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        elif path.is_file():
            path.unlink(missing_ok=True)

    def ping(self) -> bool:
        return self.root.is_dir()


class S3Storage:
    def __init__(self, bucket: str, endpoint_url: str | None = None):
        import boto3  # imported lazily: only needed for the S3 backend

        self.bucket = bucket
        self.client = boto3.client("s3", endpoint_url=endpoint_url)

    def put(self, key: str, data: bytes) -> None:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data)

    def get(self, key: str) -> bytes | None:
        from botocore.exceptions import ClientError

        try:
            return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()
        except ClientError as exc:
            if exc.response["Error"]["Code"] in ("NoSuchKey", "404"):
                return None
            raise

    def delete_prefix(self, prefix: str) -> None:
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            keys = [{"Key": o["Key"]} for o in page.get("Contents", [])]
            if keys:
                self.client.delete_objects(Bucket=self.bucket, Delete={"Objects": keys})

    def ping(self) -> bool:
        self.client.head_bucket(Bucket=self.bucket)
        return True


@lru_cache(maxsize=1)
def get_storage() -> Storage:
    if settings.storage_backend == "s3":
        return S3Storage(settings.s3_bucket, settings.s3_endpoint_url)
    return LocalStorage(settings.storage_dir)
