import os
import pickle
from dotenv import load_dotenv
from groq import Groq
from qdrant_client import QdrantClient

# Import Phase 2 Retrieval Modules
from src.retrieval.dense_retriever import DenseRetriever
from src.retrieval.rrf_fusion import RRFFusion
from src.retrieval.cross_encoder_reranker import CrossEncoderReranker
from rank_bm25 import BM25Okapi

# Import Phase 3 Query Enhancement Modules
from src.query.query_router import QueryRouter
from src.query.query_expander import QueryExpander
from src.query.multi_hop_retriever import MultiHopRetriever
from src.query.crag_evaluator import CragEvaluator
from src.evaluation.llm_evaluator import LLMEvaluator

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DB_PATH = "./qdrant_db"
COLLECTION_NAME = "accenture_10k"
BM25_INDEX_PATH = "indexes/bm25_index.pkl"

# Initialize global clients/models at startup to save compute on queries
groq_client = Groq(api_key=GROQ_API_KEY)

# Single shared Qdrant client to prevent database locking errors
global_qdrant_client = QdrantClient(path=DB_PATH)

dense_retriever = DenseRetriever(db_path=DB_PATH, collection_name=COLLECTION_NAME, client=global_qdrant_client)
fusion = RRFFusion()
reranker = CrossEncoderReranker(model_name="cross-encoder/mmarco-mMiniLMv2-L12-H384-v1")

# Initialize Phase 3 Query Modules
query_router = QueryRouter()
query_expander = QueryExpander()
multi_hop_retriever = MultiHopRetriever(dense_retriever)

# Load BM25 Index
bm25_model = None
doc_ids_mapping = []

if os.path.exists(BM25_INDEX_PATH):
    with open(BM25_INDEX_PATH, 'rb') as f:
        bm25_data = pickle.load(f)
        bm25_model = bm25_data["bm25"]
        doc_ids_mapping = bm25_data["doc_ids"]

def tokenize_bm25(text: str) -> list[str]:
    import re
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)
    return [word for word in text.split() if len(word) >= 2]

def get_answer(query):
    try:
        print(f"\n--- 🚦 Query routing and expansion for: '{query}' ---")
        
        # 1. Query Routing
        route_info = query_router.route(query)
        category = route_info.get("category", "Standard")
        filters = route_info.get("filters", {})
        
        print(f"[{category}] Reasoning: {route_info.get('reasoning')}")

        if category == "Simple":
            # Direct static LLM synthesis (no heavy hybrid RAG required)
            prompt = f"""
            You are a Legal AI Assistant. The user is asking a basic metadata question about the document layer.
            Answer clearly based on the fact that this is any 10-K document filing for Accenture FY2023.
            
            QUESTION: {query}
            """
            chat = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant",
                temperature=0
            )
            final_answer = chat.choices[0].message.content
            return final_answer, [], {"faithfulness": 5, "relevance": 5}

        # 2. Query Expansion (Standard & Multi-Hop)
        expanded_queries = query_expander.expand(query, method="llm")
        print(f"📚 Expanded into {len(expanded_queries)} variations.")

        all_bm25_results = []
        all_dense_results = []

        # 3. Retrieval Loop over expanded queries
        for eq in expanded_queries:
            # BM25 Search
            if bm25_model:
                query_tokens = tokenize_bm25(eq)
                scores = bm25_model.get_scores(query_tokens)
                scored_docs = list(zip(doc_ids_mapping, scores))
                scored_docs = sorted(scored_docs, key=lambda x: x[1], reverse=True)[:10] # 10 per variant
                
                for doc_id, score in scored_docs:
                    res = global_qdrant_client.retrieve(collection_name=COLLECTION_NAME, ids=[doc_id])
                    if res:
                        all_bm25_results.append({
                            "chunk_id": doc_id,
                            "score": score,
                            "content": res[0].payload.get("document", ""),
                            "metadata": res[0].payload
                        })

            # Dense Search
            dense_vars = dense_retriever.search(eq, top_k=10)
            all_dense_results.extend(dense_vars)

        # 4. Reciprocal Rank Fusion (Merge & Deduplicate)
        fused_results = fusion.fuse(all_bm25_results, all_dense_results, top_k=20)

        # 5. Multi-Hop Expansion (If Classified)
        if category == "Multi-Hop":
            # We follow references found in the top candidates to pull secondary context
            fused_results = multi_hop_retriever.retrieve(query, fused_results[:5], max_hops=2)
        
        # 4. Cross-Encoder Reranking
        limit = 6 if category == "Multi-Hop" else 3
        final_results = reranker.rerank(query, fused_results, top_k=limit)
        
        # 5. Corrective RAG (CRAG) Evaluation
        crag = CragEvaluator(confidence_threshold=0.20)
        crag_result = crag.evaluate(query, final_results)
        
        if crag_result["decision"] == "Reject":
            print(f"\n--- 🤖 Legal AI Answer ---")
            print(f"Fallback Triggered: {crag_result['reason']}")
            print("I do not have enough specific context in the 10-K to accurately answer this question.")
            return "Reject: No context", [], {"faithfulness": 5, "relevance": 1} # Safety triggers get faithful point due to refusal

        final_results = crag_result["chunks"]
        
        # Extract context
        source_chunks = [res["content"] for res in final_results]
        source_ids = [res["chunk_id"] for res in final_results]
        
        context_text = "\n\n".join(source_chunks)[:4000]

        prompt = f"""
        You are a Legal AI Expert. Answer the question strictly using the context below.
        If the information is missing, say it's not in the document.
        
        CONTEXT:
        {context_text}
        
        QUESTION:
        {query}
        """
        
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
            temperature=0,
        )
        final_answer = chat_completion.choices[0].message.content
        
        # 6. Answer Quality Evaluation
        evaluator = LLMEvaluator()
        scores = evaluator.evaluate(query, context_text, final_answer)
        
        print("\n--- 📊 Answer Quality Score ---")
        print(f"Faithfulness (No Hallucination): {scores.get('faithfulness', 0)}/5")
        print(f"Relevance: {scores.get('relevance', 0)}/5")
        print(f"Justification: {scores.get('justification', 'N/A')}")
        
        # Return answer + source lists for validation logging
        return final_answer, source_ids, scores
    except Exception as e:
        return f"System Error: {str(e)}", [], {"faithfulness": 0, "relevance": 0}

if __name__ == "__main__":
    import sys
    import json
    if len(sys.argv) > 1:
        query = sys.argv[1]
        # Run answer pipeline
        ans, sources, scores = get_answer(query)
        # Output strictly JSON for Node.js to parse safely
        print(json.dumps({
            "answer": ans,
            "sources": sources,
            "scores": scores
        }))
    else:
        print(json.dumps({"answer": "No query provided.", "sources": [], "scores": {}}))