# ADR 0012 — Corrections de bugs latents (lot 2 : snapshot_id, Next.js, Node 20)

## Statut

Accepté

## Contexte

Suite aux bugs latents déjà catalogués lors des tests bout-en-bout d'août 2026 (voir docs/adr/0001, 0004, 0009), un nouveau passage a permis de vérifier lesquels restaient réellement ouverts.

## Décisions

### 1. `job.snapshot_id` restait à NULL après un backup réussi (corrigé)

`worker/tasks.py::process_backup_job` faisait `db.add(snapshot)` puis lisait immédiatement `snapshot.id` — sans flush, l'auto-incrément n'était pas encore résolu, donc `job.snapshot_id` recevait toujours `None`. Un `db.flush()` a été ajouté entre les deux. Test de non-régression : `tests/test_worker_metrics.py::test_process_backup_job_success_sets_job_snapshot_id`.

### 2. Provisioning agent (`DEPTH_ZERO_SELF_SIGNED_CERT`) — déjà corrigé, pas de code changé

Vérifié : `api.provisionAgent` (`web/app/lib/api.ts`) appelle désormais `/api/agents/provision` (route proxy Next.js authentifiée, `web/app/lib/serverApi.ts` gère le bypass TLS côté serveur), plus l'ancien `/api/v1/agents/provision` qui passait par le rewrite brut sans bypass. Ce changement a eu lieu lors des travaux multi-tenancy (docs/adr/0004), sans mise à jour de la liste de bugs latents. Couvert par `web/app/lib/api.test.ts`.

### 3. `tests/test_basic.py` (3 assertions pré-existantes en échec) — déjà corrigé

Les 10 tests du fichier passent tous actuellement. Plus de trace du désalignement `User.username`/`AgentConfig.api_url`/`SaveOSClient` mentionné dans le catalogue de bugs d'origine.

### 4. `next@14.0.4` → `14.2.35` (patch de sécurité, corrigé)

`npm audit` : `next@14.0.4` était critique (SSRF, cache poisoning, plusieurs DoS). `14.2.35` reste dans la même ligne majeure (`isSemVerMajor: false` côté npm) et corrige la majorité des avis applicables à la branche 14.x.

**Piège rencontré et corrigé au passage** : après le bump, `next build` échouait sur *toutes* les pages en prérendu (`Error: Element type is invalid… got: undefined`), y compris `/_not-found`. Cause isolée par bissection (voir historique de session) : `next.config.js` déclarait `experimental.serverComponentsExternalPackages: ['axios']`. Sous 14.2.35, cette option casse la résolution de module pour tout composant client import(ant) transitivement `axios` (ici `TenantProvider`/`SessionProvider` → `web/app/lib/api.ts`) — un simple `import { useTenant } from './TenantProvider'` suffisait à déclencher le crash, même sans l'appeler. Retirer l'option (axios ne nécessite aucune externalisation : pas de binding natif) restaure un build propre. Vérifié : build Next local, `docker build --target web-builder`, et démarrage réel du serveur standalone (`node .next/standalone/server.js`, `/login` et `/api/health` répondent 200).

`eslint-config-next` a été aligné sur `14.2.35` (même ligne que `next`, requis par le package).

**Résiduel non traité** : `npm audit` continue de signaler `next` comme critique — l'avis agrège des CVEs corrigées seulement en 15.x/16.x. Une remédiation complète impliquerait un saut de version majeure (`next@16.3.4` proposé par `npm audit fix --force`), avec migration App Router / React potentiellement associée : décision hors périmètre de ce lot, à traiter séparément si souhaité.

### 5. Images `node:18-alpine` (EOL) → `node:20-alpine` (corrigé)

`Dockerfile.prod` (stages `web-builder`/`web-prod`), `web/Dockerfile` (stages `builder`/`runner`), `web/Dockerfile.dev`. Aligné sur la CI, déjà passée sur Node 20 (voir docs/adr précédent sur l'EOL Node 18). Vérifié : les trois images se construisent sans erreur.

### 6. Entropie Borg sous Docker Desktop/WSL2 — investigué, pas d'action en prod

Hypothèse initiale : `--encryption=repokey` bloquerait par manque d'entropie, avec comme mitigation standard `haveged` — mais `haveged` doit écrire dans le pool d'entropie du noyau (ioctl sur `/dev/random`), ce qui exige root ou `CAP_SYS_ADMIN`, alors que `Dockerfile.prod`'s stage `worker-prod` tourne délibérément en non-root (`USER saveos`). Avant de défaire ce durcissement, vérification sur un vrai hôte Linux plutôt que sur la machine locale (Docker Desktop/WSL2, seul environnement où le hang avait été observé) : workflow jetable sur runner GitHub Actions (`ubuntu-latest`, run [34549051520](https://github.com/Vanti7/SaveOS/actions/runs/34549051520), depuis supprimé) exécutant `borg init --encryption=repokey` 4 fois de suite.

**Résultat : aucun blocage, chaque exécution ~0,25–0,3s.** Confirme que le hang est spécifique à la VM WSL2 fraîchement démarrée de Docker Desktop (probablement un délai d'amorçage du CSPRNG du noyau propre à cet environnement), pas un risque réel sur les hôtes CI/staging/prod (noyau déjà amorcé en entropie bien avant qu'un conteneur ne démarre). **Décision : ne rien changer en prod** — pas de `haveged`, pas d'assouplissement du non-root. Le contournement `--encryption=none` reste disponible pour du test local si le hang se reproduit.

## Conséquences

Réduction concrète de la surface de vulnérabilités connues côté web, restauration du comportement correct de `job.snapshot_id`, alignement Node 20 partout, clarification (avec preuve) qu'aucune action n'est requise côté entropie Borg en production.

## Hors périmètre (décision de conception à part, non traitée ici)

- **`agent/cli.py` envoie des chemins locaux (`repo_path`, `source_paths`) au serveur** : ce ne sont pas de simples chemins mal formatés à corriger — le worker exécute `borg` directement dans son propre conteneur Linux (`subprocess.run(['borg', ...], ...)`, `worker/tasks.py`), qui n'a strictement aucun accès au système de fichiers de la machine agent. C'est une limitation d'architecture (l'agent ne transfère jamais ses fichiers au worker). L'utilisateur a demandé un chantier de conception dédié plutôt qu'une décision prise dans ce lot de correctifs — pas encore cadré.
