"""
Shared data file utilities for collection, analysis, and chat.
"""
import glob
import json
import os
from datetime import datetime, timezone

from backend.config import WORK_DIR

DATA_DIR = os.path.join(WORK_DIR, "data")


def load_latest_collected_data(data_dir: str, category_key: str) -> str | None:
    """Load the most recent collected data file for a source category."""
    if not os.path.isdir(data_dir):
        return None

    pattern = os.path.join(data_dir, f"*_{category_key}_*.json")
    files = sorted(glob.glob(pattern), reverse=True)

    if not files:
        return None

    try:
        with open(files[0], "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("raw_content", "")
    except (json.JSONDecodeError, OSError):
        return None


def save_data_file(
    group_id: int,
    gsubject_id: int,
    category_key: str,
    item_id: int,
    data: dict,
) -> str:
    """Save a data file and return the file path."""
    dir_path = os.path.join(DATA_DIR, str(group_id), str(gsubject_id))
    os.makedirs(dir_path, exist_ok=True)

    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    file_path = os.path.join(dir_path, f"{date_str}_{category_key}_{item_id}.json")

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

    return file_path


def get_subject_data_dir(group_id: int, gsubject_id: int) -> str:
    """Get the data directory path for a subject."""
    return os.path.join(DATA_DIR, str(group_id), str(gsubject_id))


def get_existing_data_summary(data_dir: str) -> str:
    """Get a brief summary of what collected data exists for a subject."""
    if not os.path.isdir(data_dir):
        return "No data collected yet."

    files = glob.glob(os.path.join(data_dir, "*.json"))
    if not files:
        return "No data collected yet."

    # Group by category
    categories = {}
    for f in sorted(files):
        basename = os.path.basename(f)
        parts = basename.replace(".json", "").split("_", 2)
        if len(parts) >= 3:
            date = parts[0]
            cat = parts[1] if len(parts) == 3 else "_".join(parts[1:-1])
            categories.setdefault(cat, []).append(date)

    lines = []
    for cat, dates in sorted(categories.items()):
        latest = max(dates)
        lines.append(f"- {cat}: {len(dates)} collection(s), latest {latest}")

    return "\n".join(lines) if lines else "No data collected yet."
