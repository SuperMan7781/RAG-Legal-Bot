import os
import pickle
import re
from qdrant_client import QdrantClient
from rank_bm25 import BM25Okapi

class BM25Indexer:
    """
    Builds an inverted index for lexical keyword search (BM25) over the document chunks.
    Extracts chunks directly from the Qdrant local database.
    """
    def __init__(self, db_path: str = "./qdrant_db", collection_name: str = "accenture_10k"):
        self.client = QdrantClient(path=db_path)
        self.collection_name = collection_name
        self.index_path = "indexes/bm25_index.pkl"

    def tokenize(self, text: str) -> list[str]:
        """
        Tokenization strategy:
        - Lowercase all text
        - Strip punctuation
        - Discard short tokens (< 2 chars)
        """
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s]', '', text)
        return [word for word in text.split() if len(word) >= 2]

    def build_index(self):
        print(f"📥 Fetching documents from Qdrant collection '{self.collection_name}'...")
        records, _ = self.client.scroll(
            collection_name=self.collection_name,
            limit=10000,
            with_payload=True,
            with_vectors=False
        )
        
        if not records:
            print("❌ No records found in Qdrant database.")
            return

        print(f"🔄 Tokenizing {len(records)} documents...")
        tokenized_corpus = []
        doc_ids = []
        
        for record in records:
            # When using Qdrant client.add(documents=...), the text lands in payload['document']
            content = record.payload.get("document", "")
            if not content:
                continue
                
            tokenized_corpus.append(self.tokenize(content))
            doc_ids.append(record.id)

        print("🧮 Building BM25 index...")
        bm25 = BM25Okapi(tokenized_corpus)
        
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        
        print(f"💾 Saving index and mapping to {self.index_path}...")
        with open(self.index_path, 'wb') as f:
            pickle.dump({
                "bm25": bm25,
                "doc_ids": doc_ids
            }, f)
            
        print("✅ BM25 Index built successfully!")

if __name__ == "__main__":
    indexer = BM25Indexer()
    indexer.build_index()
