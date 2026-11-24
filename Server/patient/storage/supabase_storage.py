"""
Supabase Storage Adapter for Patient Reports.

Provides persistent cloud object storage for uploaded patient diagnostic reports
(PDFs, scanned images) on Supabase Storage Free Tier (1 GB free storage).

Features:
- Seamless zero-dependency REST API integration via requests.
- Automatic fallback: If Supabase credentials are not configured or unreachable,
  falls back safely to local disk storage without failing user requests.
- Public URL and signed URL generation.
- Bucket existence verification / creation.
"""

import os
import mimetypes
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import requests
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()


class SupabaseStorage:
    """
    Client for interacting with Supabase Storage REST API.
    """

    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        bucket_name: Optional[str] = None,
    ):
        raw_url = (supabase_url or os.getenv("SUPABASE_URL") or "").strip()
        parsed = urlparse(raw_url)
        if parsed.scheme and parsed.netloc:
            # Normalize to origin scheme://netloc (removes trailing paths like /rest/v1)
            self.supabase_url = f"{parsed.scheme}://{parsed.netloc}"
        else:
            self.supabase_url = raw_url.rstrip("/")
        self.supabase_key = (
            supabase_key
            or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            or os.getenv("SUPABASE_KEY")
            or os.getenv("SUPABASE_ANON_KEY")
            or ""
        )
        self.bucket = bucket_name or os.getenv("SUPABASE_STORAGE_BUCKET") or "patient-reports"

    @property
    def is_configured(self) -> bool:
        """Returns True if Supabase URL and Key are available."""
        return bool(self.supabase_url and self.supabase_key)

    def _get_headers(self, content_type: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def ensure_bucket_exists(self, is_public: bool = True) -> bool:
        """
        Ensures the target storage bucket exists. If not, attempts to create it.
        """
        if not self.is_configured:
            return False

        url = f"{self.supabase_url}/storage/v1/bucket/{self.bucket}"
        try:
            resp = requests.get(url, headers=self._get_headers(), timeout=10)
            if resp.status_code == 200:
                return True

            # If 404, attempt creation
            create_url = f"{self.supabase_url}/storage/v1/bucket"
            payload = {
                "id": self.bucket,
                "name": self.bucket,
                "public": is_public,
                "file_size_limit": 52428800,  # 50 MB
            }
            create_resp = requests.post(
                create_url,
                headers=self._get_headers("application/json"),
                json=payload,
                timeout=10,
            )
            return create_resp.status_code in (200, 201)
        except Exception as e:
            print(f"[SupabaseStorage] Warning verifying/creating bucket: {e}")
            return False

    def upload_file(
        self,
        local_path: str,
        destination_path: str,
        content_type: Optional[str] = None,
        is_public: bool = True,
    ) -> Optional[str]:
        """
        Uploads a file from local disk to Supabase Storage.

        Returns:
            Public or accessible URL string if successful, or None on failure.
        """
        if not self.is_configured:
            return None

        if not os.path.isfile(local_path):
            print(f"[SupabaseStorage] File not found: {local_path}")
            return None

        # Resolve MIME type if not provided
        if not content_type:
            content_type, _ = mimetypes.guess_type(local_path)
            content_type = content_type or "application/octet-stream"

        # Sanitize destination path (strip leading slash)
        clean_dest = destination_path.lstrip("/")

        url = f"{self.supabase_url}/storage/v1/object/{self.bucket}/{clean_dest}"
        headers = self._get_headers(content_type)
        headers["x-upsert"] = "true"

        try:
            with open(local_path, "rb") as f:
                file_bytes = f.read()

            response = requests.post(url, headers=headers, data=file_bytes, timeout=30)

            # If bucket didn't exist (400 / 404), attempt to create and retry once
            if response.status_code in (400, 404) and "not found" in response.text.lower():
                if self.ensure_bucket_exists(is_public=is_public):
                    response = requests.post(url, headers=headers, data=file_bytes, timeout=30)

            if response.status_code in (200, 201):
                if is_public:
                    return self.get_public_url(clean_dest)
                return self.get_signed_url(clean_dest)
            else:
                print(f"[SupabaseStorage] Upload failed ({response.status_code}): {response.text}")
                return None
        except Exception as e:
            print(f"[SupabaseStorage] Upload exception: {e}")
            return None

    def upload_bytes(
        self,
        file_bytes: bytes,
        destination_path: str,
        content_type: str = "application/pdf",
        is_public: bool = True,
    ) -> Optional[str]:
        """
        Uploads raw bytes directly to Supabase Storage.
        """
        if not self.is_configured:
            return None

        clean_dest = destination_path.lstrip("/")
        url = f"{self.supabase_url}/storage/v1/object/{self.bucket}/{clean_dest}"
        headers = self._get_headers(content_type)
        headers["x-upsert"] = "true"

        try:
            response = requests.post(url, headers=headers, data=file_bytes, timeout=30)
            if response.status_code in (200, 201):
                if is_public:
                    return self.get_public_url(clean_dest)
                return self.get_signed_url(clean_dest)
            return None
        except Exception as e:
            print(f"[SupabaseStorage] Byte upload exception: {e}")
            return None

    def get_public_url(self, file_path: str) -> str:
        """
        Returns the permanent public URL for an object in a public bucket.
        """
        clean_path = file_path.lstrip("/")
        return f"{self.supabase_url}/storage/v1/object/public/{self.bucket}/{clean_path}"

    def get_signed_url(self, file_path: str, expires_in: int = 3600) -> Optional[str]:
        """
        Creates a time-limited signed download URL for private bucket objects.
        """
        if not self.is_configured:
            return None

        clean_path = file_path.lstrip("/")
        url = f"{self.supabase_url}/storage/v1/object/sign/{self.bucket}/{clean_path}"
        headers = self._get_headers("application/json")

        try:
            response = requests.post(url, headers=headers, json={"expiresIn": expires_in}, timeout=10)
            if response.status_code == 200:
                data = response.json()
                signed_path = data.get("signedURL") or data.get("signedUrl")
                if signed_path:
                    if signed_path.startswith("http"):
                        return signed_path
                    return f"{self.supabase_url}/storage/v1{signed_path}"
            return None
        except Exception as e:
            print(f"[SupabaseStorage] Signed URL error: {e}")
            return None

    def download_file(self, file_path: str) -> Optional[bytes]:
        """
        Downloads the raw bytes of a file from Supabase Storage.
        """
        if not self.is_configured:
            return None

        clean_path = file_path.lstrip("/")
        url = f"{self.supabase_url}/storage/v1/object/{self.bucket}/{clean_path}"
        try:
            resp = requests.get(url, headers=self._get_headers(), timeout=30)
            if resp.status_code == 200:
                return resp.content
            return None
        except Exception as e:
            print(f"[SupabaseStorage] Download error: {e}")
            return None

    def delete_file(self, file_path: str) -> bool:
        """
        Deletes a file from Supabase Storage.
        """
        if not self.is_configured:
            return False

        clean_path = file_path.lstrip("/")
        url = f"{self.supabase_url}/storage/v1/object/{self.bucket}/{clean_path}"
        try:
            resp = requests.delete(url, headers=self._get_headers(), timeout=10)
            return resp.status_code in (200, 204)
        except Exception as e:
            print(f"[SupabaseStorage] Delete error: {e}")
            return False
