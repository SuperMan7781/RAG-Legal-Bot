from typing import List, Dict, Any

class RRFFusion:
    """
    Implements Reciprocal Rank Fusion (RRF) to merge BM25 (lexical) 
    and Dense (semantic) search results into a unified, high-precision ranking.
    """
    def __init__(self, k: int = 60):
        self.k = k

    def fuse(self, bm25_results: List[Dict[str, Any]], dense_results: List[Dict[str, Any]], top_k: int = 20) -> List[Dict[str, Any]]:
        """
        Merges results mathematically.
        RRF Score = 1 / (k + rank)
        """
        fused_scores = {}
        document_store = {}

        # Process BM25 Results
        for rank, res in enumerate(bm25_results):
            chunk_id = res['chunk_id']
            if chunk_id not in fused_scores:
                fused_scores[chunk_id] = 0.0
                document_store[chunk_id] = res

            fused_scores[chunk_id] += 1.0 / (self.k + rank)

        # Process Dense Results
        for rank, res in enumerate(dense_results):
            chunk_id = res['chunk_id']
            if chunk_id not in fused_scores:
                fused_scores[chunk_id] = 0.0
                document_store[chunk_id] = res

            fused_scores[chunk_id] += 1.0 / (self.k + rank)

        # Sort combined scores descending
        sorted_results = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)

        # Reconstruct exactly the top_k requested with final RRF scores
        final_list = []
        for chunk_id, rrf_score in sorted_results[:top_k]:
            doc = document_store[chunk_id]
            doc['rrf_score'] = rrf_score
            final_list.append(doc)

        return final_list

if __name__ == "__main__":
    # Smoke test mock execution
    fusion = RRFFusion()
    
    mock_bm25 = [
        {"chunk_id": "item1a_99", "content": "Risk factor 1...", "metadata": {}},
        {"chunk_id": "item7_12", "content": "MD&A analysis...", "metadata": {}}
    ]
    
    mock_dense = [
        {"chunk_id": "item8_45", "content": "Financial statement...", "metadata": {}},
        {"chunk_id": "item1a_99", "content": "Risk factor 1...", "metadata": {}}
    ]
    
    final = fusion.fuse(mock_bm25, mock_dense)
    for i, res in enumerate(final):
        print(f"Rank {i+1}: Chunk {res['chunk_id']} (RRF: {res['rrf_score']:.4f})")
