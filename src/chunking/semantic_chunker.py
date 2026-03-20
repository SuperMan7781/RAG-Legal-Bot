import re
from typing import List, Dict, Any
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

class SemanticChunker:
    """
    Splits the 10-K PDF into semantic chunks based on structural boundaries.
    """
    
    def __init__(self, chunk_size: int = 512, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size, 
            chunk_overlap=self.overlap,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        
        # Matches "Item 1:", "Item 1A:", "Item 2.", etc.
        self.item_pattern = re.compile(r"^(?:PART\s+[IVX]+)?\s*Item\s+\d+[A-Z]?[\.:]", re.IGNORECASE)

    def is_table(self, text: str) -> bool:
        """Heuristic check to determine if text block is a table."""
        # Check for multiple piped columns or excessive spacing characteristic of tables
        pipe_count = text.count("|")
        newline_count = text.count("\n")
        
        # High ratio of numbers/symbols might also indicate a table
        if pipe_count > 3 and newline_count > 2:
            return True
            
        # Check for row-like structures (e.g. "Cloud      $12.4     17%")
        lines = text.split('\n')
        structured_lines = 0
        for line in lines:
            # Matches strings with wide gaps
            if re.search(r'\s{4,}', line) and any(char.isdigit() for char in line):
                structured_lines += 1
                
        if len(lines) > 0 and (structured_lines / len(lines)) > 0.3:
            return True
            
        return False
        
    def chunk_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Parses the PDF and chunks it while preserving section boundaries."""
        loader = PyPDFLoader(pdf_path)
        pages = loader.load()
        
        chunks = []
        current_section = "Intro"
        current_section_text = []
        section_start_page = 1
        
        # First Pass: Assemble sections
        sections = [] # List of tuples: (Section Name, Text, Start Page, End Page)
        
        for i, page in enumerate(pages):
            page_text = page.page_content
            lines = page_text.split('\n')
            
            for line in lines:
                match = self.item_pattern.search(line.strip())
                if match:
                    # Save previous section
                    if current_section_text:
                        full_text = "\n".join(current_section_text)
                        sections.append((current_section, full_text, section_start_page, i + 1))
                        
                    current_section = match.group(0).strip()
                    current_section_text = [line]
                    section_start_page = i + 1
                else:
                    current_section_text.append(line)
                    
        # Save the final section
        if current_section_text:
            sections.append((current_section, "\n".join(current_section_text), section_start_page, len(pages)))
            
        # Second Pass: Chunk each section
        for section_idx, (section_name, text, start_page, _) in enumerate(sections):
            
            # Split section by double newlines for paragraph-level analysis
            blocks = text.split("\n\n")
            
            for block_idx, block in enumerate(blocks):
                if not block.strip():
                    continue
                    
                is_tbl = self.is_table(block)
                
                if is_tbl:
                    # Tables stay intact as a single chunk
                    chunks.append({
                        "content": block.strip(),
                        "page": start_page, # Approximation for table start
                        "section": section_name,
                        "content_type": "table"
                    })
                else:
                    # Regular text gets split
                    text_chunks = self.text_splitter.split_text(block)
                    for tc in text_chunks:
                        chunks.append({
                            "content": tc.strip(),
                            "page": start_page, # Approximation within section
                            "section": section_name,
                            "content_type": "text"
                        })
                        
        print(f"Detected {len(sections)} structural sections.")
        print(f"Generated {len(chunks)} total chunks.")
        
        return chunks

if __name__ == "__main__":
    # Smoke test
    import os
    pdf_path = "Accenture_FY23_10K.pdf"
    if os.path.exists(pdf_path):
        chunker = SemanticChunker()
        chunks = chunker.chunk_pdf(pdf_path)
        print(f"Sample chunk: {chunks[0]}")
    else:
        print(f"PDF not found at {pdf_path}. Create empty file for test or download actual PDF.")
