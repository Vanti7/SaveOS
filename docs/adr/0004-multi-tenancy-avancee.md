# ADR 0004 — Multi-tenancy avancée : isolation réelle, secret d'enregistrement, quota

## Statut

Accepté

## Contexte

La roadmap demandait une "multi-tenancy avancée" (README, section Limitations du MVP : "Multi-tenancy basique"). L'exploration a montré que le schéma existait déjà (`Tenant`, `User` dans `api/database.py`) mais n'était **jamais réellement utilisé** — même motif que plusieurs autres items de cette session (Traefik jamais câblé, `ServiceManager` jamais appelé, `docker-release` avec un `outputs:` toujours vide) :

- Un seul tenant "default" était créé au premier agent (`db.query(Tenant).first() or create`, dupliqué dans `register_agent` ET `provision_agent`) — tout le monde y était rattaché silencieusement, aucun moyen d'en créer un second.
- Aucune requête (`list_all_agents`, `list_all_jobs`, `list_all_snapshots`) n'était filtrée par tenant — n'importe quel token (agent ou dashboard) voyait tout, tous tenants confondus.
- `Tenant.quota_bytes` était défini mais **jamais lu** nulle part.
- `POST /api/v1/agents/register` (auto-enregistrement) et `POST /api/v1/agents/provision` (provisioning) étaient **tous deux totalement ouverts, sans authentification** — n'importe qui sur le réseau pouvait créer un agent ou faire émettre un token valide, gratuitement.
- `Agent.hostname` n'avait aucune contrainte d'unicité en base ; la vérification applicative existante était **globale**, pas par tenant.
- `User` (email/password_hash/role) reste complètement inerte, volontairement non touché — c'est le socle du futur item séparé "Gestion des utilisateurs et rôles".

Décision validée avec l'utilisateur : isolation complète, pas seulement une correction du modèle de données.

## Décisions

### 1. Aucune nouvelle abstraction sur `Principal`

Les endpoints "liste tout" (`list_all_agents/jobs/snapshots`) restent `Depends(require_dashboard)` uniquement, gagnent juste un paramètre `tenant_id: Optional[int] = None` (omis = vue super-admin, tous tenants). Les endpoints déjà scopés par agent/job (`get_agent_stats`, `get_job_status`, `list_agent_snapshots`) étaient déjà tenant-safe transitivement (un agent ne peut agir que pour lui-même) — aucun changement là.

### 2. Pas de `tenant_id` dénormalisé sur `Job`/`Snapshot`

Le join existant via `Agent` suffit à cette échelle (petit système self-hosted) ; évite une deuxième source de vérité et une colonne `NOT NULL` de plus sur une base sans outil de migration.

### 3. Secret d'enregistrement par tenant, hashé comme un token d'agent

`Tenant.registration_secret_hash` (même schéma que `Agent.token`/`AuthManager.hash_token`) remplace le rattachement silencieux au premier tenant trouvé. `register_agent` exige désormais ce secret ; `AuthManager.verify_registration_secret` réutilise `hash_token` tel quel, pas de nouveau mécanisme de hachage. Le secret est retourné en clair une seule fois à la création du tenant (`POST /api/v1/tenants`), jamais par `GET /api/v1/tenants` — même précédent que le token d'un agent.

### 4. `provision_agent` authentifié, tenant explicite

Faille de sécurité pré-existante fermée : `provision_agent` n'exigeait aucune authentification et émettait un token d'agent valide à quiconque. Exige désormais `Depends(require_dashboard)` et un `tenant_id` explicite (404 si inconnu, 409 si hostname déjà pris pour ce tenant).

### 5. Hostname unique par tenant, pas globalement

`Agent.__table_args__` gagne `UniqueConstraint('tenant_id', 'hostname')`. Deux tenants peuvent désormais chacun avoir une machine "DESKTOP-01" sans collision silencieuse (le pré-check applicatif dans `register_agent`/`provision_agent` est lui aussi scopé par tenant).

### 6. Quota appliqué à la création d'un job de sauvegarde

`create_backup_job` rejette (403) un nouveau job de type `backup` si l'espace déjà consommé par le tenant (`sum(Snapshot.size_bytes)` joint via `Job`→`Agent`) atteint `Tenant.quota_bytes`. Vérifie l'espace déjà consommé par les sauvegardes **terminées**, pas la taille du job à venir (impossible à connaître à l'avance) — simplification assumée. Les jobs `check`/`restore` ne sont pas bloqués par le quota.

### 7. Tableau de bord : un seul token admin, conscient du tenant sélectionné

`DASHBOARD_API_TOKEN` reste un unique secret statique global (pas de per-tenant login — c'est le périmètre du futur item "Gestion des utilisateurs et rôles"). Le tableau de bord passe par ses routes proxy Next.js existantes (`web/app/api/**`, token côté serveur uniquement, `web/app/lib/serverApi.ts`), threadant un `tenant_id` optionnel à travers elles. Sélection persistée côté navigateur en `localStorage` (convention déjà utilisée dans ce projet pour l'état de confort viewer-side), `null` = "tous les tenants" — vue super-admin légitime pour un token admin unique.

`provisionAgent` (auparavant appelé **directement** depuis le navigateur, sans authentification) migre vers une nouvelle route proxy (`/api/agents/provision`), puisque le provisioning exige désormais le token dashboard, jamais accessible côté client.

### 8. Authentification du dashboard applicative explicitement hors scope

Pas de per-tenant dashboard token, pas de login utilisateur — reporté au futur item "Gestion des utilisateurs et rôles".

## Limites de vérification

Aucun outil de migration (Alembic) dans ce dépôt — `create_tables()` est `CREATE TABLE IF NOT EXISTS`, jamais `ALTER TABLE`. La nouvelle colonne `Tenant.registration_secret_hash` et la nouvelle contrainte `UniqueConstraint('tenant_id', 'hostname')` ne s'appliquent qu'à une base fraîchement créée. Conséquences pour un déploiement existant :

- Les tables `tenants`/`agents` existent déjà en prod ; ces changements de schéma n'y sont **jamais appliqués automatiquement** — intervention manuelle requise avant de dépendre du nouveau comportement : ajouter la colonne (`ALTER TABLE tenants ADD COLUMN registration_secret_hash VARCHAR(128) UNIQUE`), créer au moins un tenant via `POST /api/v1/tenants`, redistribuer son secret.
- Les agents déjà enregistrés ne sont pas affectés : leur `token` ne change pas, heartbeats/backups continuent de fonctionner normalement.
- Le prochain **auto-enregistrement** (agent qui reperd son état local, ou installation depuis un package source déjà téléchargé avant cette mise à jour) échouera tant que l'opérateur n'a pas suivi les étapes ci-dessus — en 500 (colonne manquante) plutôt qu'un 401 propre si la migration manuelle n'a pas encore eu lieu.
- `provision_agent` exige désormais le token dashboard : tout script externe l'appelant sans authentification recevra 403 (comportement voulu).
- Vérifié dans ce sandbox : suite pytest complète (base SQLite en mémoire, recréée à chaque test — la nouvelle colonne/contrainte s'y appliquent normalement, aucun souci de migration côté tests), suite Vitest + vérification de types côté web. **Non vérifié** : comportement d'upgrade sur un déploiement Postgres existant déjà peuplé (aucune base de ce type disponible ici) — même limite que documentée dans l'ADR 0002 (packaging macOS/Linux) et l'ADR 0003 (émission réelle de certificats Let's Encrypt), seul un vrai déploiement peut la fermer.

## Conséquences

- Le package source téléchargeable (`/download/agent/{platform}`) embarque désormais le secret d'enregistrement du tenant dans son `config.json` lorsqu'il est fourni — sans lui, l'agent installé échouera à s'auto-enregistrer.
- Le bug pré-existant où `register_agent` retourne le token *hashé* (pas en clair) lors d'une mise à jour d'un agent déjà existant (`existing_agent` renvoyé directement comme `AgentResponse`) reste présent, non corrigé ici — hors périmètre de cet item, signalé pour un futur correctif.
