#!/usr/bin/env python3
"""
Tests locaux pour SaveOS (sans Docker)
"""
import os
import sys
import json
import time
import requests
import subprocess
import tempfile
from pathlib import Path

# Désactiver les warnings SSL
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_api_health():
    """Test de santé de l'API"""
    print("🔍 Test de l'API...")
    try:
        response = requests.get("https://localhost:8000/health", verify=False, timeout=5)
        if response.status_code == 200:
            print("✅ API accessible")
            return True
        else:
            print(f"❌ API retourne {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API non accessible: {e}")
        return False

def test_agent_creation():
    """Test de création d'un agent"""
    print("🤖 Test de création d'agent...")
    
    # Simuler la création d'un agent
    from api.main import generate_agent_package
    
    try:
        # Générer un package pour Linux
        package_data = generate_agent_package("linux")
        
        if len(package_data) > 1000:  # Package non vide
            print("✅ Package d'agent généré")
            return True
        else:
            print("❌ Package trop petit")
            return False
    except Exception as e:
        print(f"❌ Erreur génération package: {e}")
        return False

def test_agent_config():
    """Test de configuration d'agent"""
    print("⚙️ Test de configuration d'agent...")
    
    try:
        # Tester la classe AgentConfig
        sys.path.append('.')
        from agent.config import AgentConfig
        
        # Créer un répertoire temporaire
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = AgentConfig(temp_dir)
            config = config_manager.load_config()
            
            # Vérifier la configuration par défaut
            if 'hostname' in config and 'platform' in config:
                print("✅ Configuration d'agent valide")
                return True
            else:
                print("❌ Configuration manquante")
                return False
                
    except Exception as e:
        print(f"❌ Erreur configuration: {e}")
        return False

def test_database_schema():
    """Test du schéma de base de données"""
    print("🗄️ Test du schéma de base de données...")
    
    try:
        from api.database import Base, Agent, Job, Snapshot, Tenant
        
        # Vérifier que les modèles sont bien définis
        models = [Agent, Job, Snapshot, Tenant]
        for model in models:
            if hasattr(model, '__tablename__'):
                print(f"✅ Modèle {model.__name__} défini")
            else:
                print(f"❌ Modèle {model.__name__} invalide")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur schéma DB: {e}")
        return False

def test_agent_cli():
    """Test de l'interface CLI de l'agent"""
    print("💻 Test de l'interface CLI...")
    
    try:
        # Tester l'import de l'agent CLI
        from agent.cli import cli
        
        print("✅ Agent CLI importable")
        return True
        
    except Exception as e:
        print(f"❌ Erreur CLI: {e}")
        return False

def test_worker_tasks():
    """Test des tâches worker"""
    print("⚙️ Test des tâches worker...")
    
    try:
        from worker.tasks import BorgManager
        
        # Tester le gestionnaire Borg
        borg = BorgManager("/tmp/test_repo", "test_passphrase")
        
        if hasattr(borg, 'init_repo') and hasattr(borg, 'create_backup'):
            print("✅ BorgManager fonctionnel")
            return True
        else:
            print("❌ BorgManager incomplet")
            return False
            
    except Exception as e:
        print(f"❌ Erreur worker: {e}")
        return False

def run_all_tests():
    """Exécute tous les tests"""
    print("🧪 === Tests SaveOS (version locale) ===\\n")
    
    tests = [
        ("Schéma DB", test_database_schema),
        ("Agent CLI", test_agent_cli), 
        ("Config Agent", test_agent_config),
        ("Worker Tasks", test_worker_tasks),
        ("Création Agent", test_agent_creation),
        ("API Health", test_api_health),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\\n--- {name} ---")
        result = test_func()
        results.append((name, result))
        time.sleep(0.5)
    
    # Résumé
    print("\\n" + "="*50)
    print("📊 RÉSUMÉ DES TESTS:")
    print("="*50)
    
    passed = 0
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name:20} : {status}")
        if result:
            passed += 1
    
    print(f"\\n🎯 Résultat: {passed}/{len(results)} tests réussis")
    
    if passed == len(results):
        print("🎉 Tous les tests sont passés!")
    else:
        print("⚠️ Certains tests ont échoué")
    
    return passed == len(results)

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)