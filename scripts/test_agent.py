"""
End-to-end smoke test for the legal agent pipeline.
Run from project root: python scripts/test_agent.py
"""
from pathlib import Path
import sys

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from legal_agent import get_answer


def run_test():
    query = "Compare the risk factors in Item 1A with the revenue summary details in Item 7."

    print(f"🚀 Running Multi-Hop Hybrid RAG Test for Query: '{query}'\n")

    answer, source_ids, scores = get_answer(query)

    print("\n--- 🤖 Legal AI Answer ---")
    print(answer)
    print("\n--- 📄 Supporting Source Chunk IDs ---")
    for identifier in source_ids:
        print(f"- {identifier}")
    print("\n--- 📊 Quality Scores ---")
    print(f"Faithfulness: {scores.get('faithfulness', 'N/A')}/5")
    print(f"Relevance:    {scores.get('relevance', 'N/A')}/5")


if __name__ == "__main__":
    run_test()
