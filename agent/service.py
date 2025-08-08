#!/usr/bin/env python3
"""
Gestion des services système pour l'agent SaveOS
"""
import os
import sys
import platform
import subprocess
from pathlib import Path
from typing import Dict, Any

class ServiceManager:
    """Gestionnaire de services système pour l'agent SaveOS"""
    
    def __init__(self, agent_path: str):
        self.agent_path = agent_path
        self.platform = platform.system().lower()
        self.service_name = "saveos-agent"
    
    def install_service(self) -> Dict[str, Any]:
        """Installe l'agent comme service système"""
        try:
            if self.platform == "linux":
                return self._install_systemd_service()
            elif self.platform == "darwin":  # macOS
                return self._install_launchd_service()
            elif self.platform == "windows":
                return self._install_windows_service()
            else:
                return {"success": False, "error": f"Plateforme non supportée: {self.platform}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _install_systemd_service(self) -> Dict[str, Any]:
        """Installe le service systemd sur Linux"""
        service_content = f"""[Unit]
Description=SaveOS Backup Agent
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
WorkingDirectory={Path(self.agent_path).parent}
ExecStart=/usr/bin/python3 {self.agent_path} daemon
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
"""
        
        service_file = f"/etc/systemd/system/{self.service_name}.service"
        
        try:
            # Écrire le fichier de service
            with open(service_file, 'w') as f:
                f.write(service_content)
            
            # Recharger systemd
            subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
            
            # Activer le service
            subprocess.run(["sudo", "systemctl", "enable", self.service_name], check=True)
            
            return {"success": True, "message": f"Service {self.service_name} installé et activé"}
            
        except subprocess.CalledProcessError as e:
            return {"success": False, "error": f"Erreur systemctl: {e}"}
        except PermissionError:
            return {"success": False, "error": "Permissions insuffisantes (sudo requis)"}
    
    def _install_launchd_service(self) -> Dict[str, Any]:
        """Installe le service launchd sur macOS"""
        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.saveos.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>{self.agent_path}</string>
        <string>daemon</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{Path(self.agent_path).parent}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/var/log/saveos-agent.log</string>
    <key>StandardErrorPath</key>
    <string>/var/log/saveos-agent-error.log</string>
</dict>
</plist>
"""
        
        plist_file = f"/Library/LaunchDaemons/com.saveos.agent.plist"
        
        try:
            # Écrire le fichier plist
            with open(plist_file, 'w') as f:
                f.write(plist_content)
            
            # Charger le service
            subprocess.run(["sudo", "launchctl", "load", plist_file], check=True)
            
            return {"success": True, "message": "Service launchd installé et chargé"}
            
        except subprocess.CalledProcessError as e:
            return {"success": False, "error": f"Erreur launchctl: {e}"}
        except PermissionError:
            return {"success": False, "error": "Permissions insuffisantes (sudo requis)"}
    
    def _install_windows_service(self) -> Dict[str, Any]:
        """Installe le service Windows"""
        try:
            import win32serviceutil
            import win32service
            import win32event
            import servicemanager
        except ImportError:
            return {"success": False, "error": "Module pywin32 requis pour les services Windows"}
        
        # Pour Windows, on utilise une approche simplifiée avec une tâche planifiée
        return self._install_windows_task()
    
    def _install_windows_task(self) -> Dict[str, Any]:
        """Installe une tâche planifiée Windows"""
        task_xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <BootTrigger>
      <Enabled>true</Enabled>
    </BootTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>ServiceAccount</LogonType>
      <UserId>S-1-5-18</UserId>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>false</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>true</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>python</Command>
      <Arguments>"{self.agent_path}" daemon</Arguments>
      <WorkingDirectory>{Path(self.agent_path).parent}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""
        
        try:
            # Créer le fichier XML temporaire
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
                f.write(task_xml)
                temp_file = f.name
            
            # Créer la tâche planifiée
            cmd = [
                "schtasks", "/create", 
                "/tn", "SaveOS Agent",
                "/xml", temp_file,
                "/f"  # Force overwrite
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Nettoyer le fichier temporaire
            os.unlink(temp_file)
            
            if result.returncode == 0:
                return {"success": True, "message": "Tâche planifiée Windows créée"}
            else:
                return {"success": False, "error": f"Erreur schtasks: {result.stderr}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def start_service(self) -> Dict[str, Any]:
        """Démarre le service"""
        try:
            if self.platform == "linux":
                subprocess.run(["sudo", "systemctl", "start", self.service_name], check=True)
            elif self.platform == "darwin":
                subprocess.run(["sudo", "launchctl", "start", "com.saveos.agent"], check=True)
            elif self.platform == "windows":
                subprocess.run(["schtasks", "/run", "/tn", "SaveOS Agent"], check=True)
            
            return {"success": True, "message": "Service démarré"}
            
        except subprocess.CalledProcessError as e:
            return {"success": False, "error": str(e)}
    
    def stop_service(self) -> Dict[str, Any]:
        """Arrête le service"""
        try:
            if self.platform == "linux":
                subprocess.run(["sudo", "systemctl", "stop", self.service_name], check=True)
            elif self.platform == "darwin":
                subprocess.run(["sudo", "launchctl", "stop", "com.saveos.agent"], check=True)
            elif self.platform == "windows":
                subprocess.run(["schtasks", "/end", "/tn", "SaveOS Agent"], check=True)
            
            return {"success": True, "message": "Service arrêté"}
            
        except subprocess.CalledProcessError as e:
            return {"success": False, "error": str(e)}
    
    def get_service_status(self) -> Dict[str, Any]:
        """Récupère le statut du service"""
        try:
            if self.platform == "linux":
                result = subprocess.run(
                    ["systemctl", "is-active", self.service_name], 
                    capture_output=True, text=True
                )
                active = result.stdout.strip() == "active"
                
            elif self.platform == "darwin":
                result = subprocess.run(
                    ["launchctl", "list", "com.saveos.agent"],
                    capture_output=True, text=True
                )
                active = result.returncode == 0
                
            elif self.platform == "windows":
                result = subprocess.run(
                    ["schtasks", "/query", "/tn", "SaveOS Agent"],
                    capture_output=True, text=True
                )
                active = "Ready" in result.stdout or "Running" in result.stdout
            
            return {
                "success": True, 
                "active": active,
                "status": "running" if active else "stopped"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

if __name__ == "__main__":
    # Test du gestionnaire de services
    import sys
    if len(sys.argv) < 3:
        print("Usage: python service.py <agent_path> <action>")
        print("Actions: install, start, stop, status")
        sys.exit(1)
    
    agent_path = sys.argv[1]
    action = sys.argv[2]
    
    manager = ServiceManager(agent_path)
    
    if action == "install":
        result = manager.install_service()
    elif action == "start":
        result = manager.start_service()
    elif action == "stop":
        result = manager.stop_service()
    elif action == "status":
        result = manager.get_service_status()
    else:
        print(f"Action inconnue: {action}")
        sys.exit(1)
    
    if result["success"]:
        print(f"✅ {result.get('message', 'Succès')}")
        if 'status' in result:
            print(f"Status: {result['status']}")
    else:
        print(f"❌ {result['error']}")
        sys.exit(1)