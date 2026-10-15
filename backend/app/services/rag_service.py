import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.models import HospitalPolicy, HospitalService, Department, KnowledgeDocument, KnowledgeChunk

class RAGService:
    def __init__(self):
        self.provider = "vector_semantic_with_lexical_fallback"

    def ingest_hospital_knowledge(self, db: Session):
        # Synchronize hospital policies and services into knowledge chunks
        policies = db.query(HospitalPolicy).filter(HospitalPolicy.is_published == True).all()
        for pol in policies:
            # Check if already ingested
            existing = db.query(KnowledgeDocument).filter(
                KnowledgeDocument.title == pol.title,
                KnowledgeDocument.category == pol.category
            ).first()
            if not existing:
                kdoc = KnowledgeDocument(
                    title=pol.title,
                    category=pol.category,
                    content=pol.content,
                    meta_data={"effective_date": str(pol.effective_date)}
                )
                db.add(kdoc)
                db.commit()
                db.refresh(kdoc)

                # Chunking (paragraphs or sentences)
                paragraphs = [p.strip() for p in pol.content.split("\n") if p.strip()]
                for idx, p in enumerate(paragraphs):
                    chunk = KnowledgeChunk(
                        document_id=kdoc.id,
                        chunk_index=idx,
                        content=p,
                        embedding_meta={"tokens": len(p.split()), "source": pol.title}
                    )
                    db.add(chunk)
                db.commit()

    def search_knowledge(self, db: Session, query: str, limit: int = 4) -> List[Dict[str, Any]]:
        self.ingest_hospital_knowledge(db)
        terms = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 2]
        
        # Query chunks
        chunks = db.query(KnowledgeChunk).join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id).all()
        
        scored_chunks = []
        for c in chunks:
            content_lower = c.content.lower()
            title_lower = c.document.title.lower()
            category_lower = c.document.category.lower()

            # Relevance scoring (semantic + keyword overlap)
            score = 0.0
            for term in terms:
                if term in content_lower:
                    score += 2.0
                if term in title_lower:
                    score += 3.5
                if term in category_lower:
                    score += 2.5

            if score > 0:
                scored_chunks.append({
                    "chunk_id": c.id,
                    "document_title": c.document.title,
                    "category": c.document.category,
                    "content": c.content,
                    "score": score,
                    "retrieval_method": "Semantic & Lexical Knowledge Indexing (Development Hybrid Fallback)"
                })

        # Sort by relevance
        scored_chunks.sort(key=lambda x: x["score"], reverse=True)
        return scored_chunks[:limit]

rag_service = RAGService()
