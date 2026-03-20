"""
Check chunk counts grouped by parent_id.
Run from project root: python scripts/check_metadata_counts.py
"""
from pathlib import Path
import json

ROOT = Path(__file__).parent.parent
metadata_path = ROOT / "indexes" / "metadata.json"

try:
    with open(metadata_path, "r") as f:
        data = json.load(f)

    counts = {}
    for k, item in data.items():
        p_id = item.get("parent_id", "Unknown")
        counts[p_id] = counts.get(p_id, 0) + 1

    print("--- 📊 Chunk Counts by parent_id ---")
    for pid, count in sorted(counts.items()):
        print(f"- '{pid}': {count} chunks")

except Exception as e:
    print(f"Error reading metadata: {e}")
