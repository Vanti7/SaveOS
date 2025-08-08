"""
Gestion de l'authentification pour SaveOS
"""
import os
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from api.database import get_db, Agent

security = HTTPBearer()

class AuthManager:
    """Gestionnaire d'authentification pour les agents"""
    
    @staticmethod
    def generate_agent_token() -> str:
        """Génère un token sécurisé pour un agent"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def hash_token(token: str) -> str:
        """Hash un token pour le stockage sécurisé"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    @staticmethod
    def verify_agent_token(db: Session, token: str) -> Optional[Agent]:
        """Vérifie un token d'agent et retourne l'agent correspondant"""
        hashed_token = AuthManager.hash_token(token)
        agent = db.query(Agent).filter(Agent.token == hashed_token).first()
        return agent

async def get_current_agent(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Agent:
    """Récupère l'agent actuel à partir du token d'authentification"""
    
    token = credentials.credentials
    agent = AuthManager.verify_agent_token(db, token)
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token d'authentification invalide",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Mettre à jour le last_seen
    agent.last_seen = datetime.utcnow()
    db.commit()
    
    return agent