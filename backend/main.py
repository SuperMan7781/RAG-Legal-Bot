import sys
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

# Add parent directory to path to fix imports for legal_agent
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from legal_agent import get_answer

app = FastAPI(title="Accenture Legal Bot API", description="FastAPI Microservice for persistent RAG loading.")

class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    answer: str
    sources: List[str]
    scores: Dict[str, Any]

@app.get("/health")
def health():
    return {"status": "healthy", "service": "accenture-legal-bot-rag"}

@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        query = request.query
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")

        # Call our Persistent RAG Pipeline
        ans, sources, scores = get_answer(query)
        
        return {
            "answer": str(ans),
            "sources": sources,
            "scores": scores
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
