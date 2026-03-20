from typing import List, Dict, Any
from sentence_transformers import CrossEncoder

class CrossEncoderReranker:
    """
    Reranks a candidate list of chunks against a query using a powerful Cross-Encoder model.
    Unlike Bi-Encoders (Dense retrieval), Cross-Encoders pass both the query and doc together
    through the transformer layers simultaneously, yielding much higher accuracy at the cost of speed.
    """
    def __init__(self, model_name: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"):
        print(f"🔄 Loading Cross-Encoder Model '{model_name}' (First run will download ~70MB)...")
        self.model = CrossEncoder(model_name)

    def rerank(self, query: str, candidates: List[Dict[str, Any]], top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Takes the RRF fused results and re-scores them for ultimate precision.
        """
        if not candidates:
            return []

        # Create pairs: [ [query, doc1], [query, doc2], ... ]
        pairs = [[query, doc["content"]] for doc in candidates]
        
        print(f"🧠 Reranking {len(candidates)} candidates...")
        # Get raw cross-encoder float scores
        scores = self.model.predict(pairs)
        
        # Attach scores back to documents
        for doc, score in zip(candidates, scores):
            doc["cross_encoder_score"] = float(score)

        # Sort descending by the new CE score
        reranked = sorted(candidates, key=lambda x: x["cross_encoder_score"], reverse=True)
        
        return reranked[:top_k]

if __name__ == "__main__":
    # Smoke test execution
    reranker = CrossEncoderReranker()
    
    mock_query = "What are revenue figures?"
    mock_candidates = [
        {"chunk_id": "bad_match", "content": "The company focuses on long term sustainability revenue goals.", "metadata": {}},
        {"chunk_id": "perfect_match", "content": "Fiscal 2023 Revenue was $64.1 Billion, an increase of 4%.", "metadata": {}},
        {"chunk_id": "okay_match", "content": "We recognize revenue when services are rendered.", "metadata": {}}
    ]
    
    results = reranker.rerank(mock_query, mock_candidates)
    
    print("\n--- Reranking Results ---")
    for i, res in enumerate(results):
        print(f"Rank {i+1}: {res['chunk_id']} (Score: {res['cross_encoder_score']:.4f})")
        print(f"Content: {res['content']}\n")
