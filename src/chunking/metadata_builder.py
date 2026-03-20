import json
import re
from typing import List, Dict, Any
import hashlib
import uuid

class MetadataBuilder:
    """
    Enhances chunk dictionaries with rich metadata for filtering, RRF fusion, and multi-hop.
    """
    
    # Financial synonyms/keywords to index for semantic tags
    FINANCIAL_TERMS = {
        "revenue": ["sales", "income", "earnings", "receipts"],
        "risk": ["danger", "threat", "exposure", "hazard", "uncertainty"],
        "employee": ["staff", "worker", "personnel", "talent", "headcount"],
        "facility": ["location", "office", "site", "center", "real estate"],
        "expense": ["cost", "spending", "outlay", "expenditure"],
        "margin": ["profit", "ebitda", "net income"],
        "acquisition": ["merger", "buyout", "purchased", "acquired"],
        "digital": ["cloud", "security", "ai", "data", "technology"]
    }

    @staticmethod
    def _generate_chunk_id(content: str, parent_id: str, seq: int) -> str:
        """Deterministic UUID based on content hash and hierarchy."""
        unique_string = f"{parent_id}_{seq}_{content}"
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, unique_string))

    @staticmethod
    def _extract_related_sections(text: str) -> List[str]:
        """Looks for cross-references like "See Item 8" or "Refer to Part II"."""
        related = []
        
        # Matches "See Item 8", "Item 1A", "Item 7", "Note 1" etc.
        patterns = [
            r"See\s+Item\s+(\d+[A-Z]?)",
            r"refer\s+to\s+Item\s+(\d+[A-Z]?)",
            r"discussed\s+in\s+Item\s+(\d+[A-Z]?)",
            r"See\s+Note\s+(\d+)"
        ]
        
        for p in patterns:
            matches = re.finditer(p, text, re.IGNORECASE)
            for m in matches:
                item_ref = m.group(1).upper()
                if "NOTE" in p.upper():
                    related.append(f"Note {item_ref}")
                else:
                    related.append(f"Item {item_ref}")
                    
        return list(set(related))

    @staticmethod
    def _extract_semantic_tags(text: str) -> List[str]:
        """Tags chunk if it contains core financial concepts."""
        tags = set()
        text_lower = text.lower()
        
        for category, synonyms in MetadataBuilder.FINANCIAL_TERMS.items():
            if category in text_lower:
                tags.add(category)
            for syn in synonyms:
                if syn in text_lower:
                    tags.add(category) # Map synonym back to root category
                    
        return list(tags)

    @classmethod
    def attach_metadata(cls, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process flat chunks into rich dictionary objects."""
        enhanced_chunks = []
        
        for i, chunk in enumerate(chunks):
            content = chunk.get("content", "")
            section = chunk.get("section", "Unknown")
            page_num = chunk.get("page", 0)
            c_type = chunk.get("content_type", "text")
            
            # Extract features
            related = cls._extract_related_sections(content)
            tags = cls._extract_semantic_tags(content)
            word_count = len(content.split())
            
            # Deterministic ID
            chunk_id = cls._generate_chunk_id(content, section, i)
            
            metadata = {
                "chunk_id": chunk_id,
                "parent_id": section,
                "section_title": section,
                "page_number": page_num,
                "chunk_sequence": i,
                "content_type": c_type,
                "word_count": word_count,
                "company": "Accenture",
                "fiscal_year": 2023,
                "related_sections": related,
                "semantic_tags": tags,
                "hop_eligible": len(related) > 0
            }
            
            # Flatten dictionary for vector DB insertion
            enhanced_chunk = {
                "id": chunk_id,
                "content": content,
                "metadata": metadata
            }
            
            enhanced_chunks.append(enhanced_chunk)
            
        return enhanced_chunks

    @classmethod
    def save_metadata(cls, enhanced_chunks: List[Dict[str, Any]], output_path: str):
        """Save just the metadata index to disk for fast lookup."""
        metadata_index = {
            c["id"]: c["metadata"] for c in enhanced_chunks
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metadata_index, f, indent=2)
        
        print(f"Saved metadata for {len(metadata_index)} chunks to {output_path}")

if __name__ == "__main__":
    # Smoke test
    sample_chunks = [
        {"content": "As discussed in Item 8, our revenue grew by 15% due to digital transformations.", "section": "Item 1", "page": 5},
        {"content": "Cloud  |  $12.4B  |  +17%", "section": "Item 8", "page": 68, "content_type": "table"}
    ]
    
    enhanced = MetadataBuilder.attach_metadata(sample_chunks)
    print(json.dumps(enhanced, indent=2))
