#!/usr/bin/env python3
"""
Gestionnaire de versions pour SaveOS
Système de versioning sémantique professionnel
"""
import os
import re
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

class VersionManager:
    """Gestionnaire de versions SaveOS"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.version_file = self.project_root / "VERSION"
        self.changelog_file = self.project_root / "CHANGELOG.md"
        self.package_json = self.project_root / "web" / "package.json"
        
    def get_current_version(self) -> str:
        """Récupère la version actuelle"""
        if self.version_file.exists():
            return self.version_file.read_text().strip()
        return "0.0.0"
    
    def parse_version(self, version: str) -> dict:
        """Parse une version sémantique"""
        # Regex pour semantic versioning
        pattern = r'^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9\-\.]+))?(?:\+([a-zA-Z0-9\-\.]+))?$'
        match = re.match(pattern, version)
        
        if not match:
            raise ValueError(f"Version invalide: {version}")
        
        major, minor, patch, prerelease, build = match.groups()
        
        return {
            'major': int(major),
            'minor': int(minor),
            'patch': int(patch),
            'prerelease': prerelease,
            'build': build,
            'full': version
        }
    
    def increment_version(self, current: str, bump_type: str, prerelease: str = None) -> str:
        """Incrémente une version selon le type"""
        parsed = self.parse_version(current)
        
        if bump_type == "major":
            parsed['major'] += 1
            parsed['minor'] = 0
            parsed['patch'] = 0
            parsed['prerelease'] = None
        elif bump_type == "minor":
            parsed['minor'] += 1
            parsed['patch'] = 0
            parsed['prerelease'] = None
        elif bump_type == "patch":
            parsed['patch'] += 1
            parsed['prerelease'] = None
        elif bump_type == "prerelease":
            if parsed['prerelease']:
                # Incrémenter la version prerelease existante
                parts = parsed['prerelease'].split('.')
                if len(parts) > 1 and parts[-1].isdigit():
                    parts[-1] = str(int(parts[-1]) + 1)
                    parsed['prerelease'] = '.'.join(parts)
                else:
                    parsed['prerelease'] += '.1'
            else:
                parsed['prerelease'] = prerelease or 'alpha.1'
        
        # Construire la nouvelle version
        version = f"{parsed['major']}.{parsed['minor']}.{parsed['patch']}"
        if parsed['prerelease']:
            version += f"-{parsed['prerelease']}"
        
        return version
    
    def update_version_files(self, new_version: str):
        """Met à jour tous les fichiers de version"""
        # VERSION
        self.version_file.write_text(new_version)
        print(f"✅ VERSION mis à jour: {new_version}")
        
        # package.json (interface web)
        if self.package_json.exists():
            with open(self.package_json, 'r') as f:
                package_data = json.load(f)
            
            package_data['version'] = new_version
            
            with open(self.package_json, 'w') as f:
                json.dump(package_data, f, indent=2)
            
            print(f"✅ package.json mis à jour: {new_version}")
        
        # setup.py (agent)
        setup_file = self.project_root / "setup.py"
        if setup_file.exists():
            content = setup_file.read_text()
            content = re.sub(
                r'version="[^"]*"',
                f'version="{new_version}"',
                content
            )
            setup_file.write_text(content)
            print(f"✅ setup.py mis à jour: {new_version}")
    
    def add_changelog_entry(self, version: str, changes: list, bump_type: str):
        """Ajoute une entrée au changelog"""
        if not self.changelog_file.exists():
            return
        
        content = self.changelog_file.read_text()
        date = datetime.now().strftime("%Y-%m-%d")
        
        # Déterminer le type de version
        version_type = {
            'major': '🚀 Version majeure',
            'minor': '✨ Nouvelles fonctionnalités', 
            'patch': '🐛 Corrections de bugs',
            'prerelease': '🧪 Version de test'
        }.get(bump_type, '📦 Mise à jour')
        
        # Créer l'entrée
        entry = f"""
## [{version}] - {date}

### {version_type}

"""
        
        # Ajouter les changements
        if changes:
            for change in changes:
                entry += f"- {change}\n"
        else:
            entry += "- Mise à jour de version\n"
        
        entry += "\n---\n"
        
        # Insérer après la ligne "## [Non publié]"
        content = content.replace(
            "## [Non publié]",
            f"## [Non publié]{entry}"
        )
        
        self.changelog_file.write_text(content)
        print(f"✅ CHANGELOG.md mis à jour avec la version {version}")
    
    def create_release_notes(self, version: str, changes: list) -> str:
        """Crée les notes de version"""
        notes = f"""# SaveOS v{version}

**Date de publication :** {datetime.now().strftime("%d/%m/%Y")}

## Changements

"""
        if changes:
            for change in changes:
                notes += f"- {change}\n"
        else:
            notes += "- Mise à jour de version\n"
        
        notes += f"""
## Installation

```bash
# Télécharger la version {version}
git checkout v{version}

# Lancer SaveOS
./scripts/setup.sh
```

## Compatibilité

- Python 3.8+
- Docker et Docker Compose
- Windows 10+, macOS 10.15+, Linux

---

Pour plus de détails, consultez le [CHANGELOG.md](CHANGELOG.md).
"""
        
        return notes
    
    def bump_version(self, bump_type: str, message: str = None, changes: list = None, prerelease: str = None):
        """Incrémente la version et met à jour tous les fichiers"""
        current = self.get_current_version()
        new_version = self.increment_version(current, bump_type, prerelease)
        
        print(f"🔄 Mise à jour de version: {current} → {new_version}")
        
        # Mettre à jour les fichiers
        self.update_version_files(new_version)
        
        # Mettre à jour le changelog
        if changes:
            self.add_changelog_entry(new_version, changes, bump_type)
        
        # Créer les notes de version
        release_notes = self.create_release_notes(new_version, changes or [])
        release_file = self.project_root / f"RELEASE_NOTES_v{new_version}.md"
        release_file.write_text(release_notes)
        print(f"✅ Notes de version créées: {release_file}")
        
        print(f"\n🎉 Version {new_version} prête!")
        print(f"📝 Prochaines étapes:")
        print(f"   1. Vérifier les changements")
        print(f"   2. Commiter: git add . && git commit -m 'v{new_version}: {message or 'Mise à jour de version'}'")
        print(f"   3. Tagger: git tag v{new_version}")
        print(f"   4. Pousser: git push origin main --tags")
        
        return new_version

def main():
    parser = argparse.ArgumentParser(description='Gestionnaire de versions SaveOS')
    parser.add_argument('command', choices=['current', 'bump', 'info'], help='Commande à exécuter')
    parser.add_argument('--type', choices=['major', 'minor', 'patch', 'prerelease'], help='Type de bump')
    parser.add_argument('--message', '-m', help='Message de commit')
    parser.add_argument('--changes', nargs='*', help='Liste des changements')
    parser.add_argument('--prerelease', help='Type de prerelease (alpha, beta, rc)')
    
    args = parser.parse_args()
    
    vm = VersionManager()
    
    if args.command == 'current':
        version = vm.get_current_version()
        print(f"Version actuelle: {version}")
        
    elif args.command == 'info':
        version = vm.get_current_version()
        parsed = vm.parse_version(version)
        print(f"Version: {parsed['full']}")
        print(f"Major: {parsed['major']}")
        print(f"Minor: {parsed['minor']}")
        print(f"Patch: {parsed['patch']}")
        if parsed['prerelease']:
            print(f"Prerelease: {parsed['prerelease']}")
        
    elif args.command == 'bump':
        if not args.type:
            print("❌ --type requis pour bump")
            sys.exit(1)
        
        vm.bump_version(
            args.type, 
            args.message, 
            args.changes,
            args.prerelease
        )

if __name__ == "__main__":
    main()