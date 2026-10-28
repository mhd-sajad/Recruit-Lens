"""Storage abstraction supporting local filesystem and Supabase Object Storage.

Provides secure signed URLs, file retention, and hard deletion.
Credentials are read strictly via the application settings module.
"""

import hashlib
import hmac
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from app.config import settings


class StorageBackend(ABC):
    """Abstract base class for resume file storage."""

    @abstractmethod
    async def save_file(
        self, file_path_key: str, data: bytes, content_type: str = "application/pdf"
    ) -> str:
        """Save bytes to storage and return storage key/path."""
        pass

    @abstractmethod
    async def get_file(self, file_path_key: str) -> bytes:
        """Retrieve file bytes from storage."""
        pass

    @abstractmethod
    async def get_signed_url(self, file_path_key: str, expires_in_seconds: int = 3600) -> str:
        """Generate a time-limited signed access URL."""
        pass

    @abstractmethod
    async def delete_file(self, file_path_key: str) -> bool:
        """Hard delete file from storage."""
        pass


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage backend for development and test environments."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or (settings.data_dir / "resumes_storage")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.signing_secret = settings.JWT_SECRET_KEY.encode("utf-8")

    def _resolve_path(self, file_path_key: str) -> Path:
        resolved = (self.base_dir / file_path_key).resolve()
        if not str(resolved).startswith(str(self.base_dir.resolve())):
            raise ValueError(f"Path traversal detected: {file_path_key}")
        return resolved

    async def save_file(
        self, file_path_key: str, data: bytes, content_type: str = "application/pdf"
    ) -> str:
        dest = self._resolve_path(file_path_key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return file_path_key

    async def get_file(self, file_path_key: str) -> bytes:
        dest = self._resolve_path(file_path_key)
        if not dest.exists():
            raise FileNotFoundError(f"File not found: {file_path_key}")
        return dest.read_bytes()

    async def get_signed_url(self, file_path_key: str, expires_in_seconds: int = 3600) -> str:
        dest = self._resolve_path(file_path_key)
        if not dest.exists():
            raise FileNotFoundError(f"File not found: {file_path_key}")
        exp = int((datetime.now(UTC) + timedelta(seconds=expires_in_seconds)).timestamp())
        sig_data = f"{file_path_key}:{exp}".encode()
        sig = hmac.new(self.signing_secret, sig_data, hashlib.sha256).hexdigest()
        return f"/api/v1/resumes/download/{file_path_key}?exp={exp}&sig={sig}"

    async def delete_file(self, file_path_key: str) -> bool:
        dest = self._resolve_path(file_path_key)
        if dest.exists():
            dest.unlink()
            return True
        return False


class SupabaseStorageBackend(StorageBackend):
    """Supabase object storage backend for production environments."""

    def __init__(self) -> None:
        self.supabase_url = settings.SUPABASE_URL.rstrip("/")
        self.api_key = settings.SUPABASE_KEY
        self.bucket = settings.SUPABASE_STORAGE_BUCKET

    async def save_file(
        self, file_path_key: str, data: bytes, content_type: str = "application/pdf"
    ) -> str:
        if not self.supabase_url or not self.api_key:
            raise RuntimeError(
                "Supabase storage configured but SUPABASE_URL or SUPABASE_KEY is missing."
            )
        url = f"{self.supabase_url}/storage/v1/object/{self.bucket}/{file_path_key}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "apiKey": self.api_key,
            "Content-Type": content_type,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, content=data)
            if resp.status_code not in (200, 201):
                raise RuntimeError(f"Supabase storage upload failed with status {resp.status_code}")
        return file_path_key

    async def get_file(self, file_path_key: str) -> bytes:
        if not self.supabase_url or not self.api_key:
            raise RuntimeError("Supabase storage credentials missing.")
        url = f"{self.supabase_url}/storage/v1/object/authenticated/{self.bucket}/{file_path_key}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "apiKey": self.api_key,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                raise FileNotFoundError(
                    f"Supabase object {file_path_key} returned status {resp.status_code}"
                )
            return resp.content

    async def get_signed_url(self, file_path_key: str, expires_in_seconds: int = 3600) -> str:
        if not self.supabase_url or not self.api_key:
            raise RuntimeError("Supabase storage credentials missing.")
        url = f"{self.supabase_url}/storage/v1/object/sign/{self.bucket}/{file_path_key}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "apiKey": self.api_key,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=headers, json={"expiresIn": expires_in_seconds})
            if resp.status_code != 200:
                raise RuntimeError(
                    f"Failed to generate Supabase signed URL: status {resp.status_code}"
                )
            data: dict[str, Any] = resp.json()
            signed_path = data.get("signedURL", "")
            return f"{self.supabase_url}/storage/v1{signed_path}"

    async def delete_file(self, file_path_key: str) -> bool:
        if not self.supabase_url or not self.api_key:
            raise RuntimeError("Supabase storage credentials missing.")
        url = f"{self.supabase_url}/storage/v1/object/{self.bucket}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "apiKey": self.api_key,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.request(
                "DELETE", url, headers=headers, json={"prefixes": [file_path_key]}
            )
            return resp.status_code == 200


def get_storage_backend() -> StorageBackend:
    """Factory creating configured storage backend."""
    if settings.STORAGE_BACKEND == "supabase":
        return SupabaseStorageBackend()
    return LocalStorageBackend()
