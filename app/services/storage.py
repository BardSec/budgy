import os
import uuid
import logging
from abc import ABC, abstractmethod
from werkzeug.utils import secure_filename
from flask import current_app

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    @abstractmethod
    def save(self, file_data, object_key: str, content_type: str) -> dict:
        """Save a file. Returns metadata dict."""
        pass

    @abstractmethod
    def get(self, object_key: str) -> tuple:
        """Returns (file_data_bytes, content_type)."""
        pass

    @abstractmethod
    def delete(self, object_key: str) -> bool:
        pass


class LocalStorage(StorageBackend):
    def __init__(self, base_path: str):
        self.base_path = base_path

    def save(self, file_data, object_key: str, content_type: str) -> dict:
        full_path = os.path.join(self.base_path, object_key)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        file_data.save(full_path)
        file_size = os.path.getsize(full_path)
        return {
            "storage_backend": "local",
            "stored_filename": object_key,
            "object_key": object_key,
            "bucket_name": None,
            "file_size": file_size,
        }

    def get(self, object_key: str) -> tuple:
        full_path = os.path.join(self.base_path, object_key)
        with open(full_path, "rb") as f:
            return f.read(), None

    def delete(self, object_key: str) -> bool:
        full_path = os.path.join(self.base_path, object_key)
        try:
            os.remove(full_path)
            return True
        except FileNotFoundError:
            return False


class R2Storage(StorageBackend):
    def __init__(self):
        import boto3

        self.bucket_name = current_app.config["R2_BUCKET_NAME"]
        self.client = boto3.client(
            "s3",
            endpoint_url=current_app.config["R2_ENDPOINT_URL"],
            aws_access_key_id=current_app.config["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=current_app.config["R2_SECRET_ACCESS_KEY"],
            region_name="auto",
        )

    def save(self, file_data, object_key: str, content_type: str) -> dict:
        file_bytes = file_data.read()
        self.client.put_object(
            Bucket=self.bucket_name,
            Key=object_key,
            Body=file_bytes,
            ContentType=content_type,
        )
        return {
            "storage_backend": "r2",
            "stored_filename": object_key,
            "object_key": object_key,
            "bucket_name": self.bucket_name,
            "file_size": len(file_bytes),
        }

    def get(self, object_key: str) -> tuple:
        response = self.client.get_object(
            Bucket=self.bucket_name,
            Key=object_key,
        )
        return response["Body"].read(), response.get("ContentType")

    def delete(self, object_key: str) -> bool:
        self.client.delete_object(Bucket=self.bucket_name, Key=object_key)
        return True


def get_storage_backend() -> StorageBackend:
    backend = current_app.config["STORAGE_BACKEND"]
    if backend == "r2":
        return R2Storage()
    return LocalStorage(current_app.config["LOCAL_UPLOAD_PATH"])


def generate_object_key(
    fiscal_year_label: str, purchase_id: int, original_filename: str
) -> str:
    safe_name = secure_filename(original_filename)
    unique_id = uuid.uuid4().hex[:12]
    return f"uploads/{fiscal_year_label}/{purchase_id}/{unique_id}_{safe_name}"


def allowed_file(filename: str) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config["ALLOWED_EXTENSIONS"]
