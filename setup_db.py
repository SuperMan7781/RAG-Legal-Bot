import os
from qdrant_client import QdrantClient
from src.chunking.semantic_chunker import SemanticChunker
from src.chunking.metadata_builder import MetadataBuilder

def build_vector_db():
    pdf_path = "Accenture_FY23_10K.pdf"
    db_path = "./qdrant_db"
    collection_name = "accenture_10k"

    if not os.path.exists(pdf_path):
        print(f"❌ Error: {pdf_path} not found!")
        return

    # 1. Load and Split Semantically
    print("📄 Processing PDF Semantically...")
    chunker = SemanticChunker(chunk_size=512, overlap=50)
    raw_chunks = chunker.chunk_pdf(pdf_path)
    
    # 2. Attach Rich Metadata
    print("🔖 Attaching Metadata (Phase 1)...")
    enhanced_chunks = MetadataBuilder.attach_metadata(raw_chunks)
    
    # Save standalone metadata for hybrid querying later
    os.makedirs("indexes", exist_ok=True)
    MetadataBuilder.save_metadata(enhanced_chunks, "indexes/metadata.json")

    # Extract for Qdrant
    texts = [c["content"] for c in enhanced_chunks]
    metadata_list = [c["metadata"] for c in enhanced_chunks]
    ids = [c["id"] for c in enhanced_chunks]

    # 3. Initialize and Upload to Qdrant
    client = QdrantClient(path=db_path)
    
    print("🧠 Creating Vectors...")
    client.add(
        collection_name=collection_name,
        documents=texts,
        metadata=metadata_list,
        ids=ids
    )
    
    print("✅ Database built successfully with Phase 1 logic!")
    client.close()

if __name__ == "__main__":
    build_vector_db()