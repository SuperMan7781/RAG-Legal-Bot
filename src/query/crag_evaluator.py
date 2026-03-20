from typing import List, Dict, Any

class CragEvaluator:
    """
    Corrective RAG (CRAG) Evaluator.
    Intercepts retrieved chunks before generation to ensure the system 
    actually holds relevant information, preventing forced hallucinations.
    """
    def __init__(self, confidence_threshold: float = 0.20):
        self.confidence_threshold = confidence_threshold

    def evaluate(self, query: str, top_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluates the top reranked chunks directly based on their confidence scores.
        """
        if not top_chunks:
            return {
                "decision": "Reject",
                "reason": "No context chunks retrieved.",
                "chunks": []
            }

        # The chunks are expected to be sorted descending by the Cross-Encoder.
        # Check the highest confidence score.
        highest_score = top_chunks[0].get("score", 0.0)

        # Cast to float in case numpy/torch types bleed through
        try:
            highest_score = float(highest_score)
        except (TypeError, ValueError):
            highest_score = 0.0

        print(f"\n--- 🛡️ CRAG Evaluation ---")
        print(f"Highest Context Confidence: {highest_score:.4f} (Threshold: {self.confidence_threshold})")

        if highest_score < self.confidence_threshold:
            print("❌ Decision: REJECT. Generating fallback.")
            return {
                "decision": "Reject",
                "reason": f"Top confidence score ({highest_score:.4f}) is below the minimum threshold required to answer safely.",
                "chunks": top_chunks
            }

        print("✅ Decision: PROCEED. Context is sufficient.")
        return {
            "decision": "Proceed",
            "reason": "Confidence is sufficient.",
            "chunks": top_chunks
        }
