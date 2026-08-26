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
from api.database import get_db, Agent, Tenant

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

    @staticmethod
    def verify_registration_secret(db: Session, secret: str) -> Optional[Tenant]:
        """Vérifie un secret d'enregistrement de tenant et retourne le tenant correspondant"""
        hashed_secret = AuthManager.hash_token(secret)
        return db.query(Tenant).filter(Tenant.registration_secret_hash == hashed_secret).first()

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


class Principal:
    """Identité de l'appelant authentifié : soit un agent, soit le tableau de
    bord (token admin statique, pont d'auth temporaire MVP — voir
    docs/adr/0001-restauration-granulaire-mvp.md)."""

    def __init__(self, agent: Optional[Agent] = None, is_dashboard: bool = False):
        self.agent = agent
        self.is_dashboard = is_dashboard

    def can_act_on_agent(self, agent_id: int) -> bool:
        """Le tableau de bord peut agir pour n'importe quel agent ;
        un agent ne peut agir que pour lui-même."""
        return self.is_dashboard or (self.agent is not None and self.agent.id == agent_id)


async def get_current_principal(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Principal:
    """Authentifie soit un agent (token existant), soit le tableau de bord
    (token admin statique DASHBOARD_API_TOKEN)."""

    token = credentials.credentials
    dashboard_token = os.getenv("DASHBOARD_API_TOKEN")

    if dashboard_token and secrets.compare_digest(token, dashboard_token):
        return Principal(is_dashboard=True)

    agent = AuthManager.verify_agent_token(db, token)
    if agent:
        agent.last_seen = datetime.utcnow()
        db.commit()
        return Principal(agent=agent)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token d'authentification invalide",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def require_dashboard(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> None:
    """Réserve un endpoint au tableau de bord (token admin statique)."""

    dashboard_token = os.getenv("DASHBOARD_API_TOKEN")
    if not dashboard_token or not secrets.compare_digest(credentials.credentials, dashboard_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Réservé au tableau de bord",
        )