import os
import pytest


class TestStorageSelection:
    def test_local_backend_selected(self, app):
        with app.app_context():
            app.config["STORAGE_BACKEND"] = "local"
            from app.services.storage import get_storage_backend, LocalStorage

            backend = get_storage_backend()
            assert isinstance(backend, LocalStorage)

    def test_allowed_file(self, app):
        with app.app_context():
            from app.services.storage import allowed_file

            assert allowed_file("receipt.pdf") is True
            assert allowed_file("photo.jpg") is True
            assert allowed_file("photo.jpeg") is True
            assert allowed_file("scan.png") is True
            assert allowed_file("script.exe") is False
            assert allowed_file("noextension") is False
            assert allowed_file("archive.zip") is False

    def test_generate_object_key(self, app):
        with app.app_context():
            from app.services.storage import generate_object_key

            key = generate_object_key("2025-2026", 42, "my receipt.pdf")
            assert key.startswith("uploads/2025-2026/42/")
            assert key.endswith("_my_receipt.pdf")
            assert len(key) > 30
