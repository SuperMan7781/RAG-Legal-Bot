import os
import re
import json
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.http import models
from groq import Groq

# Import Phase 2/3 dependencies if needed
from src.retrieval.dense_retriever import DenseRetriever

class MultiHopRetriever:
    """
    Follows cross-references (e.g., "See Item 8") inside candidate chunks 
    to retrieve secondary snippets that provide richer synthesized context.
    Uses an LLM Query Translator to decompose aggregate queries into targeted section payloads.
    """
    def __init__(self, dense_retriever: DenseRetriever, api_key: str = None):
        self.dense_retriever = dense_retriever
        api_key = api_key or os.getenv("GROQ_API_KEY")
        self.llm_client = Groq(api_key=api_key)
        self.model = "llama-3.1-8b-instant"

    def _translate_query(self, query: str, ref: str) -> str:
        """
        Translates the aggregate multi-hop query into a localized, keyword-rich 
        search payload strictly targeted at the referenced section.
        """
        prompt = f"""
        You are an expert Query Translator for a 10-K RAG System.
        Translate the aggregate USER QUERY into a highly targeted search query strictly looking for details inside {ref}.
        Discard references to other items/sections. 
        Generate only a short, keyword-rich payload of financial or contextual terms suitable for Dense Semantic Search.
        Do not output any conversational text. Do not output the word "Item" or the section number itself. Only output the pure search keywords.
        
        USER QUERY: "{query}"
        TARGET SECTION: {ref}
        """
        try:
            chat = self.llm_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0,
            )
            # Remove any wrapping quotes if generation included them
            return chat.choices[0].message.content.strip().strip('"').strip("'")
        except Exception as e:
            print(f"⚠️ Query Translation Error: {e}")
            return f"{query} {ref}"

    def _extract_references(self, text: str, metadata: dict) -> List[str]:
        """
        Extracts referenced items from either structured metadata 
        or raw regex parsing as a fallback.
        """
        refs = metadata.get("related_sections", [])
        if isinstance(refs, str):
             # Handle possible stringified JSON
             try: refs = json.loads(refs)
             except: refs = [refs]
        
        related = list(refs)
        
        # Fallback Regex to catch any missed cross-references
        patterns = [
            r"Item\s+(\d+[A-Z]?)",
            r"Note\s+(\d+)"
        ]
        for p in patterns:
            matches = re.finditer(p, text, re.IGNORECASE)
            for m in matches:
                item_ref = f"Item {m.group(1).upper()}"
                if item_ref not in related:
                    related.append(item_ref)
                    
        return related

    def retrieve(self, query: str, initial_results: List[Dict[str, Any]], max_hops: int = 2) -> List[Dict[str, Any]]:
        """
        Executes multi-hop retrieval following candidate node references AND 
        explicit structure keywords in the original query.
        """
        print(f"\n🔄 Entering Multi-Hop Retrieval (Max Hops: {max_hops})")
        
        visited_ids = {r["chunk_id"] for r in initial_results}
        all_results = list(initial_results)
        visited_references = set()

        # 1. Inspect the ORIGINAL QUERY for explicit section mentions (e.g. "Item 1A", "Item 7")
        query_refs = self._extract_references(query, {})
        print(f"📋 Found {len(query_refs)} explicit section mentions in query: {query_refs}")

        # 2. Add query refs to extraction loop pool
        candidates_to_process = list(initial_results)
        if query_refs:
             # Create a dummy candidate to inject original query references
             candidates_to_process.append({"content": query, "metadata": {"related_sections": query_refs}, "chunk_id": "query_override"})

        for candidate in candidates_to_process:
            content = candidate.get("content", "")
            metadata = candidate.get("metadata", {})
            refs = self._extract_references(content, metadata)

            for ref in refs:
                if ref in visited_references:
                    continue
                visited_references.add(ref)

                # 3. Hop Query Translation with Strict Metadata Filter
                hop_query = self._translate_query(query, ref)
                
                # Build Qdrant-compliant strict Filter on parent_id
                query_filter = None
                if "Item" in ref:
                    # Trailing dot is expected in some parent_id forms (e.g., "Item 1A.")
                    # Let's match both or use a should match for highest safety
                    prefix = ref.strip()
                    if not prefix.endswith("."):
                         prefix = f"{prefix}."
                    
                    query_filter = models.Filter(
                        must=[
                            models.FieldCondition(
                                key="parent_id",
                                match=models.MatchValue(value=prefix)
                            )
                        ]
                    )
                
                print(f"👉 Sub-Query Reference Jump: '{ref}' (Applying Filter: {prefix if query_filter else 'None'}) -> Searching: '{hop_query}'")
                
                # Fetch secondary snippets with strict bound criteria
                secondary_res = self.dense_retriever.search(hop_query, top_k=5, query_filter=query_filter)
                
                for s_res in secondary_res:
                    s_content = s_res.get("content", "")
                    s_word_count = len(s_content.split())
                    
                    # 🔥 CRITICAL EXCLUSION: Skip page layout headers/Index links with very short texts
                    if s_word_count < 15:
                         continue

                    if s_res["chunk_id"] not in visited_ids:
                        visited_ids.add(s_res["chunk_id"])
                        s_res["hop_level"] = 2
                        all_results.append(s_res)

        return all_results

if __name__ == "__main__":
    # Smoke test execution
    db_path = "./qdrant_db"
    coll_name = "accenture_10k"
    
    # Initialize components safely
    client = QdrantClient(path=db_path)
    dense = DenseRetriever(db_path=db_path, collection_name=coll_name, client=client)
    multi_hop = MultiHopRetriever(dense)

    # Fake initial results mimicking a query about financial results pointing to Item 8
    fake_candidates = [{
        "chunk_id": "fake-123",
         "content": "Our risk factors are expanding. See Item 1A for details, and Note 8 for financial proceeds.",
         "metadata": {"related_sections": ["Item 1A"]},
         "score": 0.9
    }]

    print("--- 🔄 Multi-Hop Testing ---")
    combo = multi_hop.retrieve("What are the risk factors?", fake_candidates)
    
    print(f"\nCombined count: {len(combo)} snippets fetched.")
    for res in combo:
         print(f"- Chunk: {res['chunk_id']} (Hop Level: {res.get('hop_level', 1)})")
