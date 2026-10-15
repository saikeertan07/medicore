from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import User, AIConversation, AIMessage
from app.schemas.schemas import AIChatRequest, AIChatResponse
from app.ai.engine import ai_engine
from app.services.audit_service import record_audit_log

router = APIRouter(prefix="/ai", tags=["AI Assistant"])

@router.post("/chat", response_model=AIChatResponse)
def chat_with_agent(
    chat_req: AIChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not chat_req.message.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message cannot be empty.")

    result = ai_engine.process_chat(
        db=db,
        current_user=current_user,
        message=chat_req.message.strip(),
        conversation_id=chat_req.conversation_id
    )

    # Record audit log for AI tool executions
    if result.get("tool_calls"):
        record_audit_log(
            db=db,
            action="AI_TOOL_EXECUTE",
            resource_type="AIConversation",
            resource_id=str(result["conversation_id"]),
            user_id=current_user.id,
            details={"tool_calls": result["tool_calls"]}
        )

    return AIChatResponse(
        conversation_id=result["conversation_id"],
        message=result["message"],
        tool_calls=result.get("tool_calls"),
        sources=result.get("sources")
    )

@router.get("/conversations")
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    convs = db.query(AIConversation).filter(
        AIConversation.user_id == current_user.id
    ).order_by(AIConversation.created_at.desc()).all()
    return [{"id": c.id, "title": c.title, "created_at": c.created_at} for c in convs]

@router.get("/conversations/{conversation_id}/messages")
def get_conversation_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    conv = db.query(AIConversation).filter(
        AIConversation.id == conversation_id,
        AIConversation.user_id == current_user.id
    ).first()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")

    messages = db.query(AIMessage).filter(
        AIMessage.conversation_id == conversation_id
    ).order_by(AIMessage.created_at.asc()).all()

    return [{
        "id": m.id,
        "sender": m.sender,
        "content": m.content,
        "tool_calls": m.tool_calls,
        "tool_results": m.tool_results,
        "created_at": m.created_at
    } for m in messages]
