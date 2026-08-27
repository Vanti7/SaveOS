# SaveOS v1.8.0

**Date de publication :** 27/08/2026

## Changements

- Connexion utilisateur réelle (email/mot de passe, JWT via python-jose, hachage bcrypt) devient le chemin principal du tableau de bord, session en cookie httpOnly côté serveur
- Rôles appliqués : admin gère les utilisateurs et provisionne des agents pour son propre tenant uniquement, user a accès en lecture/écriture à son propre tenant
- Gestion des tenants (création/liste) reste réservée au token dashboard statique (DASHBOARD_API_TOKEN, désormais secret de service/bootstrap uniquement)
- Correction : passlib remplacé par bcrypt direct (incompatibilité avec la version de bcrypt installée)

## Installation

```bash
# Télécharger la version 1.8.0
git checkout v1.8.0

# Lancer SaveOS
./scripts/setup.sh
```

## Compatibilité

- Python 3.8+
- Docker et Docker Compose
- Windows 10+, macOS 10.15+, Linux

---

Pour plus de détails, consultez le [CHANGELOG.md](CHANGELOG.md).
