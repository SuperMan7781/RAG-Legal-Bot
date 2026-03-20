import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

class QueryExpander:
    """
    Expands a user query with financial / legal synonyms & alternative phrasing
    to capture content that lexical search (BM25) might otherwise miss.
    
    Uses a hybrid approach:
    1. Static Dictionary Lookup for core 10-K terms.
    2. LLM Expansion for full syntactic variants.
    """
    
    FINANCIAL_SYNONYMS = {
        "expenditure": ["cost", "expense", "spending", "outlay", "disbursement"],
        "revenue": ["sales", "income", "earnings", "receipts", "top line"],
        "profit": ["margin", "ebitda", "net income", "earnings", "bottom line"],
        "risk": ["danger", "threat", "exposure", "hazard", "uncertainty"],
        "employee": ["staff", "worker", "personnel", "talent", "workforce"],
        "facility": ["location", "office", "site", "center", "real estate"],
        "acquisition": ["merger", "buyout", "purchased", "acquired", "takeover"],
        "digital": ["technology", "cloud", "software", "ai", "automated"]
    }

    def __init__(self, api_key: str = None):
        api_key = api_key or os.getenv("GROQ_API_KEY")
        self.client = None
        if api_key:
            self.client = Groq(api_key=api_key)
        self.model = "llama-3.1-8b-instant"

    def expand_local(self, query: str) -> list[str]:
        """
        Conservative dictionary expansion.
        Replaces matched keywords with their first synonym without altering structure.
        """
        words = query.split()
        variants = [query]
        
        for i, word in enumerate(words):
            word_clean = word.lower().strip("?,.-")
            if word_clean in self.FINANCIAL_SYNONYMS:
                syns = self.FINANCIAL_SYNONYMS[word_clean]
                # Create a variant using the first available synonym to avoid exploding the query count
                new_words = list(words)
                new_words[i] = syns[0]
                new_variant = " ".join(new_words)
                if new_variant not in variants:
                    variants.append(new_variant)
                    
        return variants[:3] # Limit explosion

    def expand_llm(self, query: str) -> list[str]:
        """
        Generates 2 alternative phrasing variants using an LLM.
        """
        if not self.client:
            print("⚠️ Groq client not initialized for expansion.")
            return [query]

        prompt = f"""
        You are an expert search engineer for a corporate legal search engine.
        Generate exactly 2 alternative phrasing variants of the user query below.
        
        RULES:
        1. Keep the core intent identical.
        2. Use strictly financial/legal synonyms where applicable.
        3. Output only the questions separated by newlines. No numbers, no headers.

        USER QUERY: "{query}"
        """
        
        try:
            chat = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.3
            )
            
            output = chat.choices[0].message.content.strip()
            variants = [v.strip() for v in output.split("\n") if v.strip()]
            return [query] + variants
            
        except Exception as e:
            print(f"⚠️ QueryExpander LLM Error: {e}")
            return [query]

    def expand(self, query: str, method: str = "llm") -> list[str]:
        """
        Wrapper interface to trigger expansion.
        """
        if method == "llm":
            return self.expand_llm(query)
        return self.expand_local(query)

if __name__ == "__main__":
    # Smoke test execution
    expander = QueryExpander()
    
    test_q = "What are the expenditures relating to facilities and AI?"
    
    print("--- 📚 Query Expansion Test ---")
    print(f"Original: '{test_q}'")
    
    print("\n[Method 1: Local Dictionary]")
    local_vars = expander.expand(test_q, method="local")
    for v in local_vars:
        print(f"- {v}")

    print("\n[Method 2: LLM Rephrase]")
    llm_vars = expander.expand(test_q, method="llm")
    for v in llm_vars:
        print(f"- {v}")
