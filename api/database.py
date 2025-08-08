"""
Configuration de la base de données PostgreSQL pour SaveOS
"""
import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, BigInteger, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

# Configuration base de données
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://saveos:saveos123@localhost:5432/saveos")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Modèles de données selon la spécification

class Tenant(Base):
    """Table des tenants pour multi-tenancy"""
    __tablename__ = "tenants"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    quota_bytes = Column(BigInteger, default=1000000000)  # 1GB par défaut
    retention_policy = Column(Text, default='{"daily": 30, "weekly": 12, "monthly": 12}')
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relations
    users = relationship("User", back_populates="tenant")
    agents = relationship("Agent", back_populates="tenant")

class User(Base):
    """Table des utilisateurs"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    role = Column(String(50), default="user")  # admin, user
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relations
    tenant = relationship("Tenant", back_populates="users")

class Agent(Base):
    """Table des agents de sauvegarde"""
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    hostname = Column(String(255), nullable=False)
    platform = Column(String(50))  # windows, macos, linux
    token = Column(String(512), unique=True, nullable=False)  # Token d'authentification
    last_seen = Column(DateTime, default=datetime.utcnow)
    config = Column(Text)  # Configuration JSON de l'agent
    status = Column(String(50), default="active")  # active, inactive, error
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relations
    tenant = relationship("Tenant", back_populates="agents")
    jobs = relationship("Job", back_populates="agent")

class Job(Base):
    """Table des jobs de sauvegarde"""
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    type = Column(String(50), nullable=False)  # backup, restore, check
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"), nullable=True)
    error_message = Column(Text)
    config = Column(Text)  # Configuration spécifique du job
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relations
    agent = relationship("Agent", back_populates="jobs")
    snapshot = relationship("Snapshot", back_populates="job")

class Snapshot(Base):
    """Table des snapshots/archives"""
    __tablename__ = "snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    name = Column(String(255), nullable=False)  # Nom du snapshot Borg
    repo_path = Column(String(512), nullable=False)  # Chemin du repository
    size_bytes = Column(BigInteger, default=0)
    is_full = Column(Boolean, default=True)
    checksum = Column(String(128))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relations
    job = relationship("Job", back_populates="snapshot")

def get_db():
    """Générateur de session de base de données"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """Créer toutes les tables"""
    Base.metadata.create_all(bind=engine)