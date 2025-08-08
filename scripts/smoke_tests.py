#!/usr/bin/env python3
"""
Tests de fumée pour SaveOS
Tests rapides pour valider le déploiement
"""
import requests
import time
import sys
import argparse
from typing import Dict, List
import urllib3

# Désactiver les warnings SSL pour les tests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class SmokeTests:
    """Tests de fumée pour SaveOS"""
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self.session.verify = False  # Pour les certificats self-signed
        
    def test_api_health(self) -> bool:
        """Test de santé de l'API"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=self.timeout)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ API Health: {e}")
            return False
    
    def test_api_metrics(self) -> bool:
        """Test des métriques"""
        try:
            response = self.session.get(f"{self.base_url}/metrics", timeout=self.timeout)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ API Metrics: {e}")
            return False
    
    def test_api_docs(self) -> bool:
        """Test de la documentation API"""
        try:
            response = self.session.get(f"{self.base_url}/docs", timeout=self.timeout)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ API Docs: {e}")
            return False
    
    def test_agent_download(self) -> bool:
        """Test du téléchargement d'agent"""
        try:
            response = self.session.get(f"{self.base_url}/download/agent/linux", timeout=self.timeout)
            return response.status_code == 200 and len(response.content) > 1000
        except Exception as e:
            print(f"❌ Agent Download: {e}")
            return False
    
    def test_web_interface(self, web_url: str) -> bool:
        """Test de l'interface web"""
        try:
            response = self.session.get(web_url, timeout=self.timeout)
            return response.status_code == 200 and 'SaveOS' in response.text
        except Exception as e:
            print(f"❌ Web Interface: {e}")
            return False
    
    def test_database_connection(self) -> bool:
        """Test de connexion à la base de données (indirect via API)"""
        try:
            # Test qui nécessite la DB
            response = self.session.post(
                f"{self.base_url}/api/v1/agents/register",
                json={"hostname": "smoke-test", "platform": "linux"},
                timeout=self.timeout
            )
            # On s'attend à une erreur d'auth, pas une erreur de DB
            return response.status_code in [401, 422, 200]
        except Exception as e:
            print(f"❌ Database Connection: {e}")
            return False
    
    def run_all_tests(self, web_url: str = None) -> Dict[str, bool]:
        """Exécute tous les tests de fumée"""
        tests = [
            ("API Health", self.test_api_health),
            ("API Metrics", self.test_api_metrics),
            ("API Documentation", self.test_api_docs),
            ("Agent Download", self.test_agent_download),
            ("Database Connection", self.test_database_connection),
        ]
        
        if web_url:
            tests.append(("Web Interface", lambda: self.test_web_interface(web_url)))
        
        results = {}
        
        print("🧪 === Tests de Fumée SaveOS ===\\n")
        
        for name, test_func in tests:
            print(f"🔍 {name}...", end=" ")
            try:
                result = test_func()
                results[name] = result
                if result:
                    print("✅")
                else:
                    print("❌")
            except Exception as e:
                print(f"❌ ({e})")
                results[name] = False
            
            time.sleep(1)  # Pause entre les tests
        
        return results

def main():
    parser = argparse.ArgumentParser(description='Tests de fumée SaveOS')
    parser.add_argument('--api-url', default='https://localhost:8000', help='URL de l\'API')
    parser.add_argument('--web-url', help='URL de l\'interface web')
    parser.add_argument('--timeout', type=int, default=30, help='Timeout des requêtes')
    parser.add_argument('--env', choices=['local', 'staging', 'production'], default='local', help='Environnement')
    
    args = parser.parse_args()
    
    # URLs par défaut selon l'environnement
    if args.env == 'staging':
        api_url = 'https://api-staging.saveos.com'
        web_url = 'https://staging.saveos.com'
    elif args.env == 'production':
        api_url = 'https://api.saveos.com'
        web_url = 'https://app.saveos.com'
    else:
        api_url = args.api_url
        web_url = args.web_url or 'http://localhost:3000'
    
    print(f"🎯 Environnement: {args.env}")
    print(f"🔗 API URL: {api_url}")
    print(f"🌐 Web URL: {web_url}")
    print()
    
    # Exécuter les tests
    smoke_tests = SmokeTests(api_url, args.timeout)
    results = smoke_tests.run_all_tests(web_url)
    
    # Résultats
    print("\\n" + "="*50)
    print("📊 RÉSULTATS DES TESTS DE FUMÉE:")
    print("="*50)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:25} : {status}")
    
    print(f"\\n🎯 Score: {passed}/{total} tests réussis")
    
    if passed == total:
        print("🎉 Tous les tests de fumée sont passés!")
        print("✅ Le système est opérationnel")
        return 0
    else:
        print("⚠️ Certains tests ont échoué")
        print("❌ Le système pourrait avoir des problèmes")
        return 1

if __name__ == "__main__":
    sys.exit(main())