"""
Debug specific Qdrant chunk IDs — inspect content and metadata.
Run from project root: python scripts/debug_chunks.py
"""
from pathlib import Path
import sys
import json

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from qdrant_client import QdrantClient

client = QdrantClient(path=str(ROOT / "qdrant_db"))

ids = [
    "6f9dfe3a-39d9-5cd3-8073-bf8c88e67cb0",
    "cd342ea1-6b23-5700-a412-74e506a87e17",
    "a48ec463-b0bf-5836-91cc-68b579d1bb2e",
]

print("--- 🔍 Debugging Retrieved Chunks ---")
for doc_id in ids:
    res = client.retrieve(collection_name="accenture_10k", ids=[doc_id])
    if res:
        print(f"\nID: {doc_id}")
        print(f"Content: {res[0].payload.get('document', '')[:300]}...")
        print(f"Metadata: {json.dumps(res[0].payload, indent=2)}")
    else:
        print(f"\nID: {doc_id} NOT FOUND")

client.close()
