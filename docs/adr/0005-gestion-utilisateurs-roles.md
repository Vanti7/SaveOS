# ADR 0005 — Gestion des utilisateurs et rôles : connexion, JWT, rôles appliqués

## Statut

Accepté

## Contexte

La roadmap demandait une vraie gestion des utilisateurs et des rôles (README, limitation MVP : "Authentification simplifiée, pas de gestion utilisateurs"). L'exploration a montré, une fois de plus, un schéma et des dépendances déclarés mais jamais utilisés :

- La table `User` (`api/database.py`) existe depuis le début du projet (`email`, `password_hash`, `role`, `tenant_id`) mais n'avait **aucune référence** ailleurs dans le code.
- `requirements.txt` déclare `python-jose[cryptography]==3.3.0` (JWT) et `passlib[bcrypt]==1.7.4` (hachage de mots de passe), tous deux installés dans le venv mais **jamais importés nulle part**.

Aujourd'hui, le tableau de bord n'a aucune notion d'identité : un unique secret statique (`DASHBOARD_API_TOKEN`) donne un accès complet à tout, sans distinction d'utilisateur ni de rôle.

**Découverte en testant les dépendances déjà déclarées** : `passlib[bcrypt]==1.7.4` (2020) est incompatible avec la version de `bcrypt` réellement installée par ce fichier (5.0.0, tirée transitivement par l'extra `[bcrypt]`) — tout appel à `CryptContext(schemes=['bcrypt']).hash(...)` plante immédiatement (`AttributeError: module 'bcrypt' has no attribute '__about__'`, bug de compatibilité connu, passlib n'étant plus maintenu depuis ~2020). Confirmé en testant directement dans ce venv. `bcrypt` utilisé directement (`hashpw`/`checkpw`) fonctionne correctement — `passlib[bcrypt]` retiré de `requirements.txt`, remplacé par `bcrypt==5.0.0` en dépendance directe.

**Découverte annexe, hors périmètre** : `alembic.ini` existe à la racine depuis la toute première version du projet et déclare `script_location = migrations`, mais ce dossier n'a jamais été créé — Alembic n'a jamais été réellement initialisé. Ça nuance ce que les ADR 0003/0004 affirmaient ("aucun outil de migration dans ce dépôt") : l'outil est déclaré et configuré, juste jamais mis en service. Cet item ne touche à aucun schéma de `api/database.py` (`User` existe déjà tel quel), donc ça ne bloque rien ici — suggéré comme futur chantier séparé.

Décision validée avec l'utilisateur : "Connexion + rôles appliqués" — une vraie page de connexion devient le chemin principal du tableau de bord, avec des rôles réellement appliqués, `DASHBOARD_API_TOKEN` conservé comme identifiant de secours documenté.

## Décisions

### 1. Session en cookie httpOnly, jamais de JWT côté navigateur

Next.js émet et lit le cookie de session server-side uniquement (`next/headers`, `web/app/lib/session.ts`). Aucune librairie JWT côté web nécessaire — le JWT reste un jeton opaque du point de vue du navigateur, immunisé contre le vol par XSS (contrairement à un stockage `localStorage`).

### 2. `DASHBOARD_API_TOKEN` conservé, comme secret de service/bootstrap

Le tableau de bord web arrête de s'appuyer dessus par défaut une fois la connexion en place — `web/app/lib/session.ts::authHeaders()` transmet le JWT de la session si elle existe, sinon le défaut `DASHBOARD_API_TOKEN` déjà attaché à `serverApi` s'applique (utile pour des scripts/CI, ou avant qu'aucun utilisateur n'existe).

### 3. Un seul slot d'authentification, trois identités possibles

`get_current_principal` essaie, dans l'ordre : token dashboard statique → JWT utilisateur → token agent. `Principal` gagne un troisième type d'identité (`user: Optional[User]`), en plus de `agent`/`is_dashboard`.

### 4. Portée des rôles : tenant management reste exclusivement au token statique

`admin` gère les utilisateurs et provisionne des agents **au sein de son propre tenant uniquement** (`require_admin_or_dashboard` + `resolve_scoped_tenant_id`, qui force le tenant et rejette toute tentative de le contourner). La création/liste de *tenants* eux-mêmes (`POST/GET /api/v1/tenants`) reste **exclusivement réservée au token statique** — un admin de tenant ne devient jamais super-admin cross-tenant.

**Conséquence découverte en implémentant** : `TenantsCard` (ajoutée par l'item multi-tenancy précédent, ADR 0004) affichait un formulaire de création de tenant dans les Paramètres. Puisque `POST /api/v1/tenants` reste strictement `require_dashboard` et que plus aucune session web réelle ne porte jamais ce token statique une fois la connexion en place (décision 2), cette carte échouerait systématiquement (403) pour tout utilisateur connecté — retirée du tableau de bord plutôt que laissée visible mais non fonctionnelle. Créer un tenant reste possible via l'API (`DASHBOARD_API_TOKEN`), voir le README pour la séquence de bootstrap. Le sélecteur de tenant dans la barre latérale (`Sidebar.tsx`) ne s'affiche désormais que si `getTenants()` renvoie effectivement plusieurs tenants — en pratique, plus jamais pour une session `/login`, seulement pertinent pour un appel direct au token statique.

### 5. Bootstrap explicite, pas de seed automatique

`POST /api/v1/users` accepte soit le token dashboard (avec `tenant_id` explicite obligatoire — crée le tout premier admin d'un tenant), soit un `admin` déjà authentifié (`tenant_id` forcé au sien). Aucune donnée n'est créée automatiquement au démarrage de l'API.

### 6. `GET /api/v1/auth/me` exige un principal utilisateur

401 pour un agent ou le token dashboard statique — cohérent avec le fait que `middleware.ts` garantit qu'aucune page du tableau de bord n'est jamais rendue sans session valide, donc `Sidebar`/`SessionProvider` n'appellent cet endpoint que dans un contexte où un `User` authentifié est attendu.

## Limites de vérification

- **Middleware Next.js (`web/middleware.ts`) non testable avec l'outillage actuel** : le Edge Runtime n'est pas exercé par les tests de composants Vitest/jsdom existants, et ce dépôt n'a aucun outillage e2e (Playwright ou équivalent). Vérifié uniquement via `npm run build` (compilation/typage du middleware confirmés) et le comportement documenté ici — pas de test automatisé pour la redirection elle-même. Ne pas introduire un nouvel outillage de test pour ce seul fichier serait cohérent avec le principe de changements ciblés ; à revisiter si ce dépôt adopte un jour un outillage e2e pour d'autres raisons.
- **Bootstrap sur un déploiement existant sans aucun `User`** : créer un tenant via `POST /api/v1/tenants` (token dashboard), créer le premier admin via `POST /api/v1/users?tenant_id=...` (toujours le token dashboard), puis se connecter sur `/login` — chaîne entièrement vérifiée par `tests/test_auth_users.py` (base SQLite en mémoire), non vérifiée contre un déploiement Postgres réel déjà peuplé dans ce sandbox.
- Vérifié ici : suite pytest complète (151 tests), suite Vitest (15 tests), `npx tsc --noEmit`, `npm run build` (compilation de production, y compris le middleware).

## Conséquences

- `TenantsCard` retirée du tableau de bord (voir décision 4) — la gestion des tenants redevient une opération d'exploitation (API + `DASHBOARD_API_TOKEN`), documentée dans le README plutôt qu'accessible depuis l'interface.
- Toute installation existante doit suivre la séquence de bootstrap (tenant → premier admin → connexion) avant que quiconque puisse utiliser le tableau de bord web — il n'existe plus de mode "accès direct sans compte".
