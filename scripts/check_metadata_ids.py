"""
List all unique parent_id values in the chunk metadata index.
Run from project root: python scripts/check_metadata_ids.py
"""
from pathlib import Path
import json

ROOT = Path(__file__).parent.parent
metadata_path = ROOT / "indexes" / "metadata.json"

try:
    with open(metadata_path, "r") as f:
        data = json.load(f)

    parent_ids = set()
    for item in data:
        meta = item.get("metadata", {})
        p_id = meta.get("parent_id")
        if p_id:
            parent_ids.add(p_id)

    print("--- 📚 All Unique parent_id Values in Index ---")
    for pid in sorted(list(parent_ids)):
        print(f"- '{pid}'")

except Exception as e:
    print(f"Error reading metadata: {e}")
