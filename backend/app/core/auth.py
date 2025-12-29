from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import hashlib

from app.database import get_db
from app.models import User, Session as SessionModel
from app.core.security import decode_access_token
from app.config import settings

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get the current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise credentials_exception

    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get the current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def create_session(db: Session, user: User, token: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> SessionModel:
    """Create a new session for a user"""
    # Hash the token before storing
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    session = SessionModel(
        user_id=user.id,
        token_hash=token_hash,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=datetime.utcnow() + timedelta(hours=settings.SESSION_EXPIRE_HOURS)
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return session


def verify_session(db: Session, token: str) -> Optional[SessionModel]:
    """Verify a session token"""
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    session = db.query(SessionModel).filter(
        SessionModel.token_hash == token_hash,
        SessionModel.expires_at > datetime.utcnow()
    ).first()

    if session:
        # Update last activity
        session.last_activity = datetime.utcnow()
        db.commit()

    return session


def delete_session(db: Session, token: str) -> bool:
    """Delete a session (logout)"""
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    session = db.query(SessionModel).filter(SessionModel.token_hash == token_hash).first()
    if session:
        db.delete(session)
        db.commit()
        return True

    return False
