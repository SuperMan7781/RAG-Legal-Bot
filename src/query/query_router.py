import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

class QueryRouter:
    """
    Analyzes user queries using a fast, cheap LLM call to classify 
    the intent and route it to optimize prompt context / compute budget.
    Categories:
    - Simple: Basic document questions (e.g., "Who filed this?", "What year?")
    - Standard: Requires typical search (e.g., "What are their risk factors?")
    - Multi-Hop: Complex synthesized reasoning (e.g., "Compare risks in Item 1A to item 7 financial data")
    """
    def __init__(self, api_key: str = None):
        api_key = api_key or os.getenv("GROQ_API_KEY")
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.1-8b-instant" # Fast & cheap for classification

    def route(self, query: str) -> dict:
        """
        Classifies the query and extracts potential metadata filters (e.g., specific item numbers).
        Returns a dict: {"category": "Simple|Standard|Multi-Hop", "filters": {...}}
        """
        # Pre-seed some regex rules first for extreme speed / fallback
        if any(w in query.lower() for w in ["who filed", "what company", "filing date"]):
             if len(query.split()) < 6:
                  return {"category": "Simple", "filters": {"company": "Accenture", "fiscal_year": 2023}}

        prompt = f"""
        You are an expert Query Router for a Legal 10-K RAG System.
        Analyze the USER QUERY and classify it into EXACTLY ONE of these 3 categories:

        1. Simple: Requests static document metadata (e.g., filing date, company name, year) or 1-word lookups.
        2. Multi-Hop: Explicitly asks to compare, contrast, or link information across TWO or MORE different items/sections. (e.g., "Compare risk factors in Item 1A with financial results in Item 8").
        3. Standard: Broad or narrative questions requiring retrieval of standard paragraphs to answer.

        OUTPUT FORMAT: Return strictly a valid JSON object with the following keys:
          - "category": (String: "Simple", "Standard", or "Multi-Hop")
          - "filters": (Object: any explicit metadata filters found, e.g., {{"item_number": "Item 1A"}} or empty {{}})
          - "reasoning": (String: 1 sentence justifying selection)

        USER QUERY: "{query}"
        """
        
        try:
            chat = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0,
                response_format={"type": "json_object"}
            )
            
            response_text = chat.choices[0].message.content
            return json.loads(response_text)
            
        except Exception as e:
            # Safe Fallback
            print(f"⚠️ QueryRouter Error: {e}")
            return {"category": "Standard", "filters": {}, "reasoning": "Fallback to Standard"}

if __name__ == "__main__":
    # Smoke test execution
    router = QueryRouter()
    
    test_queries = [
        "What company is this filing for?",
        "What are the main risks associated with AI?",
        "Compare the legal proceedings in Item 3 with the financial consolidated statement in Item 8."
    ]
    
    print("--- 🚦 Query Routing Test ---")
    for q in test_queries:
        res = router.route(q)
        print(f"\nQuery: '{q}'")
        print(f"Category: {res.get('category')}")
        print(f"Reasoning: {res.get('reasoning')}")
        print(f"Filters: {res.get('filters')}")
