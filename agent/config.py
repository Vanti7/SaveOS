"""
Configuration de l'agent SaveOS
"""
import os
import json
import platform
from pathlib import Path
from typing import Dict, Any, Optional

class AgentConfig:
    """Gestionnaire de configuration de l'agent"""
    
    def __init__(self, config_dir: Optional[str] = None):
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            # Répertoire de configuration par défaut selon l'OS
            if platform.system() == "Windows":
                self.config_dir = Path(os.environ.get("APPDATA", "")) / "SaveOS"
            elif platform.system() == "Darwin":  # macOS
                self.config_dir = Path.home() / "Library" / "Application Support" / "SaveOS"
            else:  # Linux
                self.config_dir = Path.home() / ".config" / "saveos"
        
        self.config_file = self.config_dir / "config.json"
        self.token_file = self.config_dir / "token"
        
        # Créer le répertoire de configuration
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuration par défaut
        self.default_config = {
            "api_url": "https://localhost:8000",
            "hostname": platform.node(),
            "platform": platform.system().lower(),
            "source_paths": self._get_default_source_paths(),
            "repo_path": str(self.config_dir / "borg_repo"),
            "passphrase": "changeme_default_passphrase",
            "heartbeat_interval": 300,  # 5 minutes
            "verify_ssl": False,  # Pour le MVP avec certificat self-signed
            "backup_schedule": "0 2 * * *",  # Tous les jours à 2h du matin
        }
    
    def _get_default_source_paths(self) -> list:
        """Détermine les chemins par défaut à sauvegarder selon l'OS"""
        system = platform.system().lower()
        
        if system == "windows":
            return [
                str(Path.home() / "Documents"),
                str(Path.home() / "Desktop"),
                str(Path.home() / "Pictures")
            ]
        elif system == "darwin":  # macOS
            return [
                str(Path.home() / "Documents"),
                str(Path.home() / "Desktop"),
                str(Path.home() / "Pictures"),
                str(Path.home() / "Movies")
            ]
        else:  # Linux
            return [
                str(Path.home() / "Documents"),
                str(Path.home() / "Desktop"),
                str(Path.home() / "Pictures"),
                str(Path.home() / "Videos")
            ]
    
    def load_config(self) -> Dict[str, Any]:
        """Charge la configuration depuis le fichier"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # Fusionner avec la config par défaut
                merged_config = {**self.default_config, **config}
                return merged_config
            except Exception as e:
                print(f"Erreur lors du chargement de la configuration: {e}")
                return self.default_config
        else:
            # Créer le fichier de configuration avec les valeurs par défaut
            self.save_config(self.default_config)
            return self.default_config
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """Sauvegarde la configuration dans le fichier"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Erreur lors de la sauvegarde de la configuration: {e}")
            return False
    
    def get_token(self) -> Optional[str]:
        """Récupère le token d'authentification"""
        if self.token_file.exists():
            try:
                return self.token_file.read_text(encoding='utf-8').strip()
            except Exception as e:
                print(f"Erreur lors de la lecture du token: {e}")
                return None
        return None
    
    def save_token(self, token: str) -> bool:
        """Sauvegarde le token d'authentification"""
        try:
            self.token_file.write_text(token, encoding='utf-8')
            # Permissions restrictives sur le fichier token
            if platform.system() != "Windows":
                os.chmod(self.token_file, 0o600)
            return True
        except Exception as e:
            print(f"Erreur lors de la sauvegarde du token: {e}")
            return False
    
    def delete_token(self) -> bool:
        """Supprime le token d'authentification"""
        try:
            if self.token_file.exists():
                self.token_file.unlink()
            return True
        except Exception as e:
            print(f"Erreur lors de la suppression du token: {e}")
            return False