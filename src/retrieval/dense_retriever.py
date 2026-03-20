import os
from pprint import pprint
from qdrant_client import QdrantClient
from qdrant_client.http import models

class DenseRetriever:
    """
    Performs semantic vector search against the Qdrant local database.
    Since Phase 1 used Qdrant's built-in FastEmbed integration, we pass the raw query text
    and rely on Qdrant to generate the vector using the same FastEmbed model internally.
    """
    def __init__(self, db_path: str = "./qdrant_db", collection_name: str = "accenture_10k", client: QdrantClient = None):
        if client:
            self.client = client
        else:
            self.client = QdrantClient(path=db_path)
        self.collection_name = collection_name

    def search(self, query: str, top_k: int = 20, query_filter: models.Filter = None) -> list[dict]:
        """
        Embeds the query and fetches the top_k most semantically similar chunks.
        Supports Qdrant structural filtering (e.g. scoping to a parent_id).
        """
        print(f"🔍 Performing Dense Semantic Search for: '{query}'")
        
        results = self.client.query(
            collection_name=self.collection_name,
            query_text=query,
            query_filter=query_filter,
            limit=top_k
        )
        
        parsed_results = []
        for r in results:
            parsed_results.append({
                "chunk_id": getattr(r, 'id', str(r.id)),
                "score": r.score,
                "content": r.document,
                "metadata": r.metadata
            })
            
        return parsed_results

if __name__ == "__main__":
    # Smoke test execution
    retriever = DenseRetriever()
    
    test_query = "What are the main risks associated with digital transformation and cloud services?"
    results = retriever.search(test_query, top_k=3)
    
    for i, res in enumerate(results):
        print(f"\n--- Dense Rank {i+1} (Score: {res['score']:.4f}) ---")
        print(f"Chunk ID: {res['chunk_id']}")
        print(f"Parent Section: {res['metadata'].get('parent_id')}")
        print(f"Preview: {res['content'][:150]}...")
