import uuid
import asyncio
from functools import partial
import boto3
from botocore.client import Config
from fastapi import UploadFile
from config import settings


def _get_client():
    return boto3.client(
        "s3",
        region_name=settings.OCI_REGION,
        endpoint_url=settings.OCI_ENDPOINT,
        aws_access_key_id=settings.OCI_ACCESS_KEY,
        aws_secret_access_key=settings.OCI_SECRET_KEY,
        config=Config(signature_version="s3v4"),
    )


async def upload_image(file: UploadFile, folder: str = "products") -> str:
    ext = (file.filename or "img").rsplit(".", 1)[-1].lower()
    key = f"{folder}/{uuid.uuid4()}.{ext}"
    data = await file.read()
    client = _get_client()
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        partial(
            client.put_object,
            Bucket=settings.OCI_BUCKET,
            Key=key,
            Body=data,
            ContentType=file.content_type or "image/jpeg",
        ),
    )
    # Return the public OCI object URL
    return f"{settings.OCI_PUBLIC_URL_BASE}/{key}"


async def delete_image(key: str):
    client = _get_client()
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        partial(client.delete_object, Bucket=settings.OCI_BUCKET, Key=key),
    )
