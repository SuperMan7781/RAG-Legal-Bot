# Application Pipeline Overview

## Phase 1: Data Preparation
- Document hash deduplication (to prevent ingesting duplicates)
- Semantic chunking (structural split + table detection)
- Parent-child architecture setup
- Metadata insertion
- Index building

## Phase 2: Query Expansion 
- Create synonym dictionary
- Implement query expander module
- Test with synonym-heavy queries

## Phase 3: Multi-Hop Retrieval 
- Add related_sections metadata
- Implement hop follower logic
- Result-level deduplication (to filter duplicate chunks from context)

## Phase 4: Hybrid Retrieval
- BM25 indexing
- Dense embedding with BGE-M3
- RRF fusion implementation

## Phase 5: Precision Reranking
- Cross-encoder integration
- Query-document scoring
- Top-3 extraction

## Phase 6: Context Assembly
- Parent injection logic
- Table formatting preservation
- Citation tracking

## Phase 7: LLM Integration
- Grounded prompting
- Answer generation
- Confidence scoring

## Phase 8: Evaluation & Monitoring
- Create golden test set (15 Qs)
- Implement RAGAS scoring
- Setup logging & alerting

## Phase 9: Guardrails
- Guardrails setup

## Phase 10: Future Enhancements
- Streaming response support
- Multi-document corpus expansion
- Fine-tuned domain embeddings
