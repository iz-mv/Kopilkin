import json
import os
import uuid
from urllib.parse import urlparse

from fastapi import HTTPException, UploadFile
from minio import Minio
from minio.error import S3Error


MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "kopilkin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "kopilkin_minio_password")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "kopilkin-files")
MINIO_PUBLIC_URL = os.getenv(
    "MINIO_PUBLIC_URL",
    f"http://localhost:9000/{MINIO_BUCKET}"
)

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


minio_client = Minio(
    endpoint=MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False,
)


def ensure_bucket_exists() -> None:
    try:
        if not minio_client.bucket_exists(MINIO_BUCKET):
            minio_client.make_bucket(MINIO_BUCKET)

        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{MINIO_BUCKET}/*"],
                }
            ],
        }

        minio_client.set_bucket_policy(
            MINIO_BUCKET,
            json.dumps(policy)
        )

    except S3Error as error:
        raise HTTPException(
            status_code=500,
            detail=f"MinIO bucket error: {error}"
        )


def get_object_name_from_url(file_url: str | None) -> str | None:

    if not file_url:
        return None

    parsed = urlparse(file_url)
    path = parsed.path.lstrip("/")

    bucket_prefix = f"{MINIO_BUCKET}/"

    if path.startswith(bucket_prefix):
        return path.replace(bucket_prefix, "", 1)

    public_prefix = f"{MINIO_PUBLIC_URL.rstrip('/')}/"
    if file_url.startswith(public_prefix):
        return file_url.replace(public_prefix, "", 1)

    return None


def upload_image_to_minio(file: UploadFile, folder: str) -> str:
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG and WEBP images are allowed"
        )

    ensure_bucket_exists()

    extension = ALLOWED_IMAGE_TYPES[file.content_type]
    safe_folder = folder.strip("/")
    object_name = f"{safe_folder}/{uuid.uuid4()}{extension}"

    try:
        minio_client.put_object(
            bucket_name=MINIO_BUCKET,
            object_name=object_name,
            data=file.file,
            length=-1,
            part_size=10 * 1024 * 1024,
            content_type=file.content_type,
        )

    except S3Error as error:
        raise HTTPException(
            status_code=500,
            detail=f"File upload failed: {error}"
        )

    return f"{MINIO_PUBLIC_URL.rstrip('/')}/{object_name}"


def delete_file_from_minio(file_url: str | None) -> None:
    object_name = get_object_name_from_url(file_url)

    if not object_name:
        return

    try:
        minio_client.remove_object(
            bucket_name=MINIO_BUCKET,
            object_name=object_name,
        )
        print(f"[MinIO] Deleted file: {object_name}")

    except S3Error as error:
        print(f"[MinIO] Failed to delete file {object_name}: {error}")


def cleanup_user_avatars_except_current(user_id: str, current_avatar_url: str | None) -> None:
    ensure_bucket_exists()

    prefix = f"avatars/{user_id}/"
    current_object_name = get_object_name_from_url(current_avatar_url)

    try:
        for item in minio_client.list_objects(
            bucket_name=MINIO_BUCKET,
            prefix=prefix,
            recursive=True,
        ):
            if item.object_name != current_object_name:
                minio_client.remove_object(
                    bucket_name=MINIO_BUCKET,
                    object_name=item.object_name,
                )
                print(f"[MinIO] Cleaned old avatar: {item.object_name}")

    except S3Error as error:
        print(f"[MinIO] Avatar cleanup failed for user={user_id}: {error}")
