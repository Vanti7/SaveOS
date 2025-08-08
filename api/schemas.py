"""
Schémas Pydantic pour l'API SaveOS
"""
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

class JobType(str, Enum):
    BACKUP = "backup"
    RESTORE = "restore" 
    CHECK = "check"

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class AgentStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"

# Schémas pour l'enregistrement d'agent
class AgentRegister(BaseModel):
    hostname: str
    platform: str  # windows, macos, linux
    config: Optional[Dict[str, Any]] = {}

class AgentResponse(BaseModel):
    id: int
    hostname: str
    platform: str
    token: str
    status: AgentStatus
    last_seen: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True

# Schémas pour les jobs
class JobCreate(BaseModel):
    agent_id: int
    type: JobType
    config: Optional[Dict[str, Any]] = {}

class JobResponse(BaseModel):
    id: int
    agent_id: int
    type: JobType
    status: JobStatus
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    snapshot_id: Optional[int]
    error_message: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

# Schémas pour les snapshots
class SnapshotResponse(BaseModel):
    id: int
    job_id: int
    name: str
    repo_path: str
    size_bytes: int
    is_full: bool
    checksum: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

# Schémas pour l'authentification
class Token(BaseModel):
    access_token: str
    token_type: str

class AgentHeartbeat(BaseModel):
    status: AgentStatus
    config: Optional[Dict[str, Any]] = {}

# Schémas pour les stats
class AgentStats(BaseModel):
    total_snapshots: int
    total_size_bytes: int
    last_backup: Optional[datetime]
    status: AgentStatus