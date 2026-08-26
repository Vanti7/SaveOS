# ADR 0003 — Certificats TLS valides en production : câblage Traefik/Let's Encrypt, vérification côté client

## Statut

Accepté

## Contexte

La roadmap demandait des certificats TLS valides en production (README, section Limitations du MVP : "Certificats TLS self-signed, non adaptés à la production"). L'exploration a montré que l'outillage nécessaire existait déjà, mais n'était jamais réellement utilisé :

1. `docker-compose.prod.yml` déclare un service `proxy` (Traefik) avec un résolveur ACME Let's Encrypt entièrement configuré (`--certificatesresolvers.letsencrypt.acme.*`), et `deploy/environments.yml`/`docs/CI-CD.md` anticipent déjà des URLs `https://api.saveos.com`/`https://app.saveos.com` et les secrets `DOMAIN`/`ACME_EMAIL`. Mais **seul le dashboard Traefik lui-même** avait des labels de routage (`traefik.http.routers.dashboard.*`) — `api` et `web` publiaient leurs ports directement sur l'hôte (`8000:8000`, `3000:3000`), sans aucun label, donc sans jamais passer par Traefik ni obtenir de certificat. Le CMD Docker de `api-prod` ne passe d'ailleurs aucun `--ssl-*` à uvicorn : le trafic réel restait entièrement en clair.
2. Le dashboard Traefik lui-même était exposé directement sur `8080:8080`, sans authentification, en clair sur l'hôte.
3. Les clients (agent CLI, dashboard web) désactivaient la vérification TLS **partout, inconditionnellement** (`verify_ssl: False` en dur dans `agent/config.py` et `api/main.py::generate_agent_package`, `rejectUnauthorized: false` en dur dans `web/app/lib/api.ts`) — y compris dans un hypothétique déploiement prod avec certificat valide. Un certificat serveur valide ne protège de rien si tous les clients ignorent les erreurs TLS par construction.

C'est le même type de bug ("fonctionnalité déclarée mais jamais reliée au reste") déjà rencontré plusieurs fois cette session : job CI `docker-release` avec un `needs.release.outputs.version` toujours vide (voir historique), `ServiceManager` jamais appelé depuis le CLI de l'agent (ADR 0002).

En vérifiant la validité structurelle du fichier (`docker compose -f docker-compose.prod.yml config`), un second bug latent bloquant a été trouvé : `api` et `web` déclarent à la fois `container_name` fixe et `deploy.replicas` — incompatible, Compose refuse le fichier. Ce fichier n'avait donc jamais pu être validé structurellement jusqu'ici.

## Décisions

### 1. Un seul `DOMAIN`, routage par sous-domaine

`traefik.http.routers.api.rule=Host(\`api.${DOMAIN}\`)` et `...routers.web.rule=Host(\`app.${DOMAIN}\`)`, cohérent avec le label déjà existant du dashboard (`traefik.${DOMAIN}`) et avec `deploy/environments.yml`. Pas de nouvelle variable `API_DOMAIN`/`WEB_DOMAIN` — une seule variable à fournir au déploiement.

### 2. Ports hôte directs retirés, Traefik comme unique point d'entrée TLS

`api`, `web` et le dashboard Traefik (8000, 3000, 8080) ne publient plus de port hôte direct (`expose:` à la place, réseau Docker interne uniquement) : tout le trafic externe passe par Traefik sur 443, seul point où un certificat Let's Encrypt valide s'applique réellement. Sans ce retrait, le certificat obtenu par Traefik n'aurait aucun effet sur le trafic réel — encore accessible en clair via les anciens ports.

Le dashboard Traefik reste joignable, mais uniquement via son routeur HTTPS déjà déclaré (`https://traefik.${DOMAIN}`) — l'authentification applicative (basicauth) reste **explicitement hors scope** de cet item : fermer l'exposition en clair traite le trou le plus grave (accès admin non authentifié depuis internet), ajouter une authentification est une extension distincte (gestion de secrets/htpasswd) documentée ici comme suite possible, pas traitée.

### 3. `verify_ssl` déduit de l'hôte plutôt qu'un nouveau réglage obligatoire

`localhost`/`127.0.0.1` → `False` (dev, certificat self-signed de `scripts/generate_certs.sh`) ; tout autre hôte → `True` (prod, certificat Let's Encrypt désormais réellement servi). Appliqué de façon identique dans trois endroits indépendants (pas d'import croisé entre `agent/`, `api/` et `web/` — AGENT.MD impose la séparation stricte) :

- `agent/config.py::AgentConfig._default_verify_ssl(api_url)`, utilisé pour le défaut de premier lancement et par `agent/cli.py::register` (nouveau flag `--verify-ssl/--no-verify-ssl` pour override explicite, prioritaire sur la déduction automatique).
- `api/main.py::generate_agent_package()` : même logique inline sur `API_HOST`, pour le `config.json` du package téléchargeable.
- `web/app/lib/api.ts` : même logique sur l'hôte de `NEXT_PUBLIC_API_URL`, pour le client navigateur (`apiClient`).

Choisi plutôt qu'un nouveau réglage obligatoire (variable d'env supplémentaire à documenter et à ne pas oublier de positionner) : correct par défaut dans les deux environnements sans configuration additionnelle, et un override explicite reste possible côté agent.

### 4. `web/app/lib/serverApi.ts` non touché sur ce plan

Ce client ne parle jamais qu'au nom Docker interne `api` — jamais à un domaine public avec certificat Let's Encrypt. La déduction par hôte n'a donc pas de sens ici. Ce qui a changé : `docker-compose.prod.yml` fixe désormais explicitement `API_URL=http://api:8000` pour `web` (absent auparavant, donc le défaut de `serverApi.ts`, `https://api:8000`, s'appliquait tel quel en prod — un handshake TLS contre un serveur qui n'en sert jamais en interne, ce qui échoue silencieusement). Ce saut reste sur le réseau Docker interne, jamais exposé, donc intentionnellement en clair — TLS termine chez Traefik, pas dans le conteneur `api`.

### 5. Dev inchangé

`docker-compose.yml` et `scripts/generate_certs.sh` ne sont pas modifiés : self-signed + vérification désactivée reste correct pour le développement local.

## Limites de vérification

Aucun domaine DNS réel ni accès à un endpoint ACME (staging ou production) Let's Encrypt n'est joignable depuis ce sandbox — l'obtention effective d'un certificat par Traefik (challenge HTTP-01) **ne peut pas être vérifiée ici**, seulement au premier déploiement réel avec un `DOMAIN` dont les enregistrements DNS (`api.`, `app.`, `traefik.`) pointent vers le serveur et le port 80 joignable depuis internet. Même limite que le packaging macOS/Linux de l'item précédent (ADR 0002) : vérifiable uniquement à l'usage réel, pas dans ce sandbox.

Ce qui est vérifié ici :
- Validité structurelle de `docker-compose.prod.yml` (`docker compose config`), y compris le bug `container_name`/`replicas` — confirmé en échec avant correction, en succès après.
- Présence des labels Traefik attendus et absence des ports directs (tests `tests/test_docker_compose_prod.py`, assertions texte + un test `@integration` qui shell-out vers `docker compose config`).
- Logique de déduction `verify_ssl`/`rejectUnauthorized` en isolation, côté agent (`tests/test_agent_config.py`, `tests/test_agent_cli.py`), côté API (`tests/test_agent_package.py`) et côté web (`web/app/lib/api.test.ts`).

## Conséquences

- Premier déploiement réel : prévoir les enregistrements DNS avant de démarrer `proxy`, sans quoi le challenge HTTP-01 échoue et Traefik ne sert aucun certificat valide (repli automatique sur un certificat par défaut auto-signé de Traefik, ce qui redonnerait l'ancien problème sous une autre forme — à surveiller aux premiers logs de `proxy`).
- Authentification du dashboard Traefik : suite possible, non traitée ici (voir décision 2).
- `container_name` fixe + `deploy.replicas` : la même incompatibilité pourrait resurgir si un futur service de `docker-compose.prod.yml` combine les deux — le nouveau test structurel ne couvre que `api`/`web`, pas une règle générale.
