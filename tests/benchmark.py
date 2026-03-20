import os
import sys
import json
import time

# Add parent directory to path to fix imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from legal_agent import get_answer

def run_benchmark():
    # 1. Load Golden Queries
    try:
        with open("tests/golden_questions.json", "r") as f:
            questions = json.load(f)
    except FileNotFoundError:
        print("❌ Error: tests/golden_questions.json not found.")
        return

    print(f"🚀 Running Benchmark for {len(questions)} Golden Questions...\n")
    print(f"{'ID':<4} | {'Category':<12} | {'Faithfulness':<12} | {'Relevance':<10} | {'Query'}")
    print("-" * 80)

    results = []
    total_faithfulness = 0
    total_relevance = 0
    valid_scores_count = 0

    for q in questions:
        query_text = q["query"]
        category = q["category"]
        
        start_time = time.time()
        # Call the agent
        ans, sources, scores = get_answer(query_text)
        elapsed = time.time() - start_time

        faith = scores.get("faithfulness", 0)
        rel = scores.get("relevance", 0)

        # Skip adding 0 scores to average if they are safety rejections (or treat them specially)
        # For q5 (safety), if it refuses accurately, faithfulness is 5, relevance might be judged differently.
        total_faithfulness += faith
        total_relevance += rel
        valid_scores_count += 1

        print(f"{q['id']:<4} | {category:<12} | {faith}/5 {'✅' if faith>=4 else '⚠️' if faith>=3 else '❌'} | {rel}/5 {'✅' if rel>=4 else '⚠️' if rel>=3 else '❌'} | {query_text[:40]}...")

        results.append({
            "id": q["id"],
            "query": query_text,
            "category": category,
            "faithfulness": faith,
            "relevance": rel,
            "time_taken": elapsed
        })

    # 2. Calculate Averages
    if valid_scores_count > 0:
        avg_faith = total_faithfulness / valid_scores_count
        avg_rel = total_relevance / valid_scores_count
    else:
        avg_faith = avg_rel = 0

    print("\n" + "=" * 40)
    print(" 📊 BENCHMARK SUMMARY")
    print("=" * 40)
    print(f"Total Questions : {len(questions)}")
    print(f"Avg Faithfulness: {avg_faith:.2f}/5")
    print(f"Avg Relevance   : {avg_rel:.2f}/5")
    print("=" * 40)

if __name__ == "__main__":
    run_benchmark()
