"""
Gestion de l'authentification pour SaveOS
"""
import os
import secrets
import hashlib
import bcrypt
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from api.database import get_db, Agent, Tenant, User

security = HTTPBearer()

JWT_ALGORITHM = "HS256"

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

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash un mot de passe utilisateur (bcrypt direct — voir
        docs/adr/0005-gestion-utilisateurs-roles.md : passlib[bcrypt] est
        incompatible avec la version de bcrypt installée)."""
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Vérifie un mot de passe en clair contre son hash bcrypt"""
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))

    @staticmethod
    def create_access_token(user: User) -> str:
        """Émet un JWT pour un utilisateur authentifié. Échoue explicitement
        si JWT_SECRET_KEY n'est pas configuré (pas de défaut silencieux)."""
        secret = os.getenv("JWT_SECRET_KEY")
        if not secret:
            raise RuntimeError("JWT_SECRET_KEY n'est pas configuré")
        expire_minutes = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
            "tenant_id": user.tenant_id,
            "exp": datetime.utcnow() + timedelta(minutes=expire_minutes),
        }
        return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)

    @staticmethod
    def decode_access_token(token: str) -> Optional[dict]:
        """Décode un JWT ; renvoie None sur tout échec (secret absent, signature
        invalide, expiré) — utilisé comme simple tentative d'authentification,
        jamais censé faire échouer la requête en cas d'erreur de décodage."""
        secret = os.getenv("JWT_SECRET_KEY")
        if not secret:
            return None
        try:
            return jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
        except JWTError:
            return None

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
    """Identité de l'appelant authentifié : un agent, un utilisateur connecté
    (JWT, voir docs/adr/0005-gestion-utilisateurs-roles.md), ou le tableau de
    bord (token admin statique, pont d'auth temporaire MVP — voir
    docs/adr/0001-restauration-granulaire-mvp.md)."""

    def __init__(self, agent: Optional[Agent] = None, is_dashboard: bool = False, user: Optional[User] = None):
        self.agent = agent
        self.is_dashboard = is_dashboard
        self.user = user

    def can_act_on_agent(self, agent_id: int) -> bool:
        """Le tableau de bord peut agir pour n'importe quel agent ;
        un agent ne peut agir que pour lui-même."""
        return self.is_dashboard or (self.agent is not None and self.agent.id == agent_id)

    def tenant_scope(self) -> Optional[int]:
        """Tenant auquel ce principal est restreint : celui de l'utilisateur
        connecté, ou None si token dashboard statique (pas de restriction,
        comportement actuel inchangé)."""
        return self.user.tenant_id if self.user is not None else None


async def get_current_principal(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Principal:
    """Authentifie un agent (token existant), un utilisateur connecté (JWT),
    ou le tableau de bord (token admin statique DASHBOARD_API_TOKEN), dans
    cet ordre."""

    token = credentials.credentials
    dashboard_token = os.getenv("DASHBOARD_API_TOKEN")

    if dashboard_token and secrets.compare_digest(token, dashboard_token):
        return Principal(is_dashboard=True)

    claims = AuthManager.decode_access_token(token)
    if claims:
        user = db.query(User).filter(User.id == int(claims["sub"])).first()
        if user:
            return Principal(user=user)

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


async def require_admin_or_dashboard(
    principal: Principal = Depends(get_current_principal),
) -> Principal:
    """Réserve un endpoint au tableau de bord (token admin statique) ou à un
    utilisateur de rôle admin (limité à son propre tenant, voir
    resolve_scoped_tenant_id)."""

    if principal.is_dashboard or (principal.user is not None and principal.user.role == "admin"):
        return principal
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Réservé au tableau de bord ou à un administrateur",
    )


def resolve_scoped_tenant_id(principal: Principal, requested_tenant_id: Optional[int]) -> Optional[int]:
    """Résout le tenant_id effectif pour un endpoint tenant-scopé : forcé au
    tenant de l'utilisateur connecté (403 si une valeur différente était
    explicitement demandée), sinon la valeur demandée telle quelle (token
    dashboard statique : optionnelle, omise = tous les tenants)."""

    scope = principal.tenant_scope()
    if scope is None:
        return requested_tenant_id
    if requested_tenant_id is not None and requested_tenant_id != scope:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé à votre tenant",
        )
    return scope