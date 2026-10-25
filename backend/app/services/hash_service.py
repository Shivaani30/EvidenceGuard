import hashlib
from pathlib import Path

class HashService:
    @staticmethod
    def compute_sha256(data: bytes | Path) -> str:
        """Compute SHA-256 hash of bytes or file path."""
        h = hashlib.sha256()
        if isinstance(data, (bytes, bytearray)):
            h.update(data)
        elif isinstance(data, Path):
            with open(data, "rb") as f:
                while chunk := f.read(65536):
                    h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def compute_sha512(data: bytes | Path) -> str:
        """Compute SHA-512 hash of bytes or file path."""
        h = hashlib.sha512()
        if isinstance(data, (bytes, bytearray)):
            h.update(data)
        elif isinstance(data, Path):
            with open(data, "rb") as f:
                while chunk := f.read(65536):
                    h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def verify_integrity(file_path: Path, expected_sha256: str) -> bool:
        """Verify that file on disk matches expected SHA-256 hash."""
        current_hash = HashService.compute_sha256(file_path)
        return current_hash.lower() == expected_sha256.lower()

hash_service = HashService()
