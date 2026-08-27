"""
Schémas Pydantic pour l'API SaveOS
"""
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

class JobType(str, Enum):
    BACKUP = "backup"
    RESTORE = "restore" 
    CHECK = "check"

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    READY_FOR_AGENT = "ready_for_agent"  # restore target=agent : paquet prêt, en attente de récupération
    COMPLETED = "completed"
    FAILED = "failed"

class AgentStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"

# Schémas pour les tenants
class TenantCreate(BaseModel):
    name: str
    quota_bytes: Optional[int] = 1000000000  # 1GB par défaut
    retention_policy: Optional[Dict[str, int]] = None

class TenantResponse(BaseModel):
    id: int
    name: str
    quota_bytes: int
    retention_policy: str
    created_at: datetime

    class Config:
        from_attributes = True

class TenantCreateResponse(TenantResponse):
    registration_secret: str  # en clair, une seule fois (comme AgentResponse.token)

class TenantUpdate(BaseModel):
    quota_bytes: Optional[int] = None
    retention_policy: Optional[Dict[str, int]] = None

class TenantUsageResponse(TenantResponse):
    used_bytes: int
    quota_percent: float
    estimated_cost: float

# Schémas pour les utilisateurs et l'authentification
class UserCreate(BaseModel):
    email: str
    password: str
    role: str = "user"  # admin, user

class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    tenant_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# Schémas pour l'enregistrement d'agent
class AgentRegister(BaseModel):
    hostname: str
    platform: str  # windows, macos, linux
    registration_secret: str
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

class AgentPublic(BaseModel):
    """Comme AgentResponse mais sans le token (même haché, il n'a rien à
    faire dans une réponse de listing/détail — seul AgentResponse doit
    l'exposer, pour la remise en clair unique à l'enregistrement)."""
    id: int
    hostname: str
    platform: str
    status: AgentStatus
    last_seen: datetime
    created_at: datetime

    class Config:
        from_attributes = True

class AgentDetailResponse(AgentPublic):
    total_snapshots: int
    total_size_bytes: int
    last_backup: Optional[datetime]

class AgentUpdate(BaseModel):
    hostname: Optional[str] = None

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
    agent_id: int
    name: str
    repo_path: str
    size_bytes: int
    is_full: bool
    checksum: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

# Schémas pour la restauration granulaire
class RestoreTarget(str, Enum):
    DOWNLOAD = "download"
    AGENT = "agent"

class RestoreJobCreate(BaseModel):
    agent_id: int
    snapshot_id: int
    selected_paths: List[str]
    target: RestoreTarget
    restore_path: Optional[str] = None  # requis si target == AGENT
    passphrase: Optional[str] = None

class ArchiveEntry(BaseModel):
    path: str
    type: Optional[str] = None
    size: Optional[int] = None
    mtime: Optional[str] = None

class ArchiveBrowseRequest(BaseModel):
    path: str = ""
    passphrase: Optional[str] = None

class ArchiveBrowseResponse(BaseModel):
    path: str
    entries: List[ArchiveEntry]

class PendingRestoreJob(BaseModel):
    id: int
    snapshot_id: Optional[int]
    config: Dict[str, Any]
    created_at: datetime

class AgentReportRequest(BaseModel):
    status: JobStatus
    error_message: Optional[str] = None

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