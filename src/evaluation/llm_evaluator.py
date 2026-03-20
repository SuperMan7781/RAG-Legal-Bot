import os
import json
from typing import Dict, Any
from groq import Groq

class LLMEvaluator:
    """
    LLM-as-a-Judge for Response Quality Evaluation.
    Scores the generated answer against the source context for Faithfulness and Relevance.
    """
    def __init__(self, api_key: str = None):
        api_key = api_key or os.getenv("GROQ_API_KEY")
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.1-8b-instant"

    def evaluate(self, query: str, context: str, answer: str) -> Dict[str, Any]:
        """
        Evaluates the answer on a scale of 1 to 5 for Faithfulness and Relevance.
        Returns grading metrics and a 1-sentence justification in JSON format.
        """
        prompt = f"""
        You are an impartial Judge reviewing a RAG-based AI answer.
        Rate the generated answer ON A SCALE OF 1 TO 5 (5 is best) on two metrics:

        1. **Faithfulness**: Is the answer derived *only* from the provided context without hallucinating outside facts? (5 = perfect match, 1 = fabricated)
        2. **Relevance**: Does the answer directly, accurately, and adequately answer the user's question? (5 = perfectly answers, 1 = completely missed)

        [Retrieved Context]
        {context[:3000]}

        [User Question]
        {query}

        [Generated AI Answer]
        {answer}

        OUTPUT FORMAT: You must deliver EXACT JSON only with these literal keys:
        {{
          "faithfulness": <int 1-5>,
          "relevance": <int 1-5>,
          "justification": "<1 sentence reasoning>"
        }}
        Do not include markdown tags like ```json or explanations outside the JSON block.
        """
        
        try:
            chat = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0,
            )
            response_text = chat.choices[0].message.content.strip()
            
            # Remove any wrapping markdown if model ignored instruction
            if response_text.startswith("```"):
                response_text = response_text.replace("```json", "", 1).replace("```", "", -1).strip()
                
            return json.loads(response_text)
            
        except Exception as e:
            print(f"⚠️ LLM Evaluator Error: {e}")
            return {
                "faithfulness": 0,
                "relevance": 0,
                "justification": f"Evaluation failed: {e}"
            }
