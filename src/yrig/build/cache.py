import hashlib
from pathlib import Path

from yrig.io.json import export_json, load_json


def file_hash(filepath: Path) -> str:
    with filepath.open("rb") as file:
        digest = hashlib.file_digest(file, "sha256")
    return digest.hexdigest()


def is_cache_valid(cache_filepath: Path, source_filepath: Path) -> bool:
    """Return whether a cache exists and matches its source."""
    metadata_filepath = cache_filepath.with_suffix(".json")

    if not cache_filepath.exists() or not metadata_filepath.exists():
        return False

    try:
        metadata = load_json(metadata_filepath, dict)
        return metadata.get("source_hash") == file_hash(source_filepath)
    except Exception:
        return False


def write_cache_metadata(cache_filepath: Path, source_filepath: Path) -> None:
    """Write cache metadata for a source file."""
    metadata_filepath = cache_filepath.with_suffix(".json")
    export_json(metadata_filepath, {"source_hash": file_hash(source_filepath)}, pretty=False)
