"""
Client API pour l'agent SaveOS
"""
import requests
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import urllib3

# Désactiver les warnings SSL pour le MVP (certificat self-signed)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class SaveOSAPIClient:
    """Client pour interagir avec l'API SaveOS"""
    
    def __init__(self, api_url: str, token: Optional[str] = None, verify_ssl: bool = False):
        self.api_url = api_url.rstrip('/')
        self.token = token
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        
        if self.token:
            self.session.headers.update({
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            })
    
    def set_token(self, token: str):
        """Met à jour le token d'authentification"""
        self.token = token
        self.session.headers.update({
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        })
    
    def register_agent(self, hostname: str, platform: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Enregistre l'agent auprès du serveur"""
        data = {
            "hostname": hostname,
            "platform": platform,
            "config": config or {}
        }
        
        try:
            response = self.session.post(
                f"{self.api_url}/api/v1/agents/register",
                json=data,
                verify=self.verify_ssl,
                timeout=30
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def send_heartbeat(self, status: str = "active", config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Envoie un heartbeat au serveur"""
        if not self.token:
            return {"success": False, "error": "Token d'authentification requis"}
        
        data = {
            "status": status,
            "config": config or {}
        }
        
        try:
            response = self.session.post(
                f"{self.api_url}/api/v1/agents/heartbeat",
                json=data,
                verify=self.verify_ssl,
                timeout=30
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_backup_job(self, agent_id: int, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Crée un job de sauvegarde"""
        if not self.token:
            return {"success": False, "error": "Token d'authentification requis"}
        
        data = {
            "agent_id": agent_id,
            "type": "backup",
            "config": config or {}
        }
        
        try:
            response = self.session.post(
                f"{self.api_url}/api/v1/backup",
                json=data,
                verify=self.verify_ssl,
                timeout=30
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_job_status(self, job_id: int) -> Dict[str, Any]:
        """Récupère le statut d'un job"""
        if not self.token:
            return {"success": False, "error": "Token d'authentification requis"}
        
        try:
            response = self.session.get(
                f"{self.api_url}/api/v1/jobs/{job_id}",
                verify=self.verify_ssl,
                timeout=30
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_snapshots(self, agent_id: int) -> Dict[str, Any]:
        """Liste les snapshots de l'agent"""
        if not self.token:
            return {"success": False, "error": "Token d'authentification requis"}
        
        try:
            response = self.session.get(
                f"{self.api_url}/api/v1/backup/{agent_id}/snapshots",
                verify=self.verify_ssl,
                timeout=30
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_agent_stats(self) -> Dict[str, Any]:
        """Récupère les statistiques de l'agent"""
        if not self.token:
            return {"success": False, "error": "Token d'authentification requis"}
        
        try:
            response = self.session.get(
                f"{self.api_url}/api/v1/agents/stats",
                verify=self.verify_ssl,
                timeout=30
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def health_check(self) -> Dict[str, Any]:
        """Vérifie la santé de l'API"""
        try:
            response = self.session.get(
                f"{self.api_url}/health",
                verify=self.verify_ssl,
                timeout=10
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
        except Exception as e:
            return {"success": False, "error": str(e)}