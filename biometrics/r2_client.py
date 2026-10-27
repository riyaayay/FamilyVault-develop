"""Cloudflare R2 (S3-compatible) client plus a local-disk fallback.

When R2 credentials are present we mint a presigned PUT URL as before. When
they are absent (local dev) and local storage is allowed, we hand back a URL
against this service's own ``local-upload`` endpoint so the whole
upload -> recognise -> route pipeline still works end to end.
"""

import os

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

from config import ALLOW_LOCAL_STORAGE, PRESIGN_EXPIRATION_SECONDS, storage_mode

load_dotenv()

R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "familyvault-media")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL")
R2_PUBLIC_DOMAIN = os.getenv("R2_PUBLIC_DOMAIN")


class R2ConfigurationError(RuntimeError):
    """Raised when no usable object-storage backend is configured."""


def get_r2_client():
    """Initializes and returns a boto3 client configured for Cloudflare R2."""
    missing = [
        name
        for name, value in {
            "R2_ACCESS_KEY_ID": R2_ACCESS_KEY_ID,
            "R2_SECRET_ACCESS_KEY": R2_SECRET_ACCESS_KEY,
            "R2_ENDPOINT_URL": R2_ENDPOINT_URL,
        }.items()
        if not value
    ]
    if missing:
        raise R2ConfigurationError(
            "Missing Cloudflare R2 configuration: "
            + ", ".join(missing)
            + ". Set these in biometrics/.env or the docker-compose environment."
        )
    return boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT_URL,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto",  # R2 uses "auto" for region
    )


def generate_presigned_upload_url(
    file_name: str,
    content_type: str,
    base_url: str = "",
    expiration: int = PRESIGN_EXPIRATION_SECONDS,
):
    """Return ``{upload_url, public_url, file_name, storage}``.

    ``storage`` is ``"r2"`` for a real presigned URL or ``"local"`` for the
    on-disk fallback used when R2 is not configured.
    """
    if storage_mode() == "r2":
        s3_client = get_r2_client()
        try:
            response = s3_client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": R2_BUCKET_NAME,
                    "Key": file_name,
                    "ContentType": content_type,
                },
                ExpiresIn=expiration,
            )
        except ClientError as exc:
            print(f"Error generating presigned URL: {exc}")
            return None

        public_url = f"{R2_PUBLIC_DOMAIN.rstrip('/')}/{file_name}" if R2_PUBLIC_DOMAIN else ""
        return {
            "upload_url": response,
            "public_url": public_url,
            "file_name": file_name,
            "storage": "r2",
        }

    if not ALLOW_LOCAL_STORAGE:
        raise R2ConfigurationError(
            "Cloudflare R2 is not configured and local storage is disabled "
            "(BIOMETRICS_ALLOW_LOCAL_STORAGE=0)."
        )

    base = base_url.rstrip("/")
    return {
        "upload_url": f"{base}/api/v1/biometrics/local-upload/{file_name}",
        "public_url": f"{base}/api/v1/biometrics/media/{file_name}",
        "file_name": file_name,
        "storage": "local",
    }
