# ADR 0007 — Package source réellement connecté au provisioning

## Statut

Accepté

## Contexte

Trouvé en testant réellement l'application déployée (rapportée "bancale") : le flux "Téléchargements" → "Package source" du tableau de bord provisionnait un agent (`POST /api/v1/agents/provision`, crée un `Agent` + un token dédié côté serveur) puis téléchargeait un package (`GET /download/agent/{platform}`) **totalement déconnecté de ce provisioning** :

- Le `config.json` du package embarquait un hostname générique (`"{platform}-agent"`), jamais celui saisi par l'opérateur ni celui réellement provisionné.
- Le package n'embarquait jamais le token déjà généré par le provisioning — à la place, le script d'installation appelait `agent.cli register`, qui exige un **secret d'enregistrement de tenant** (différent du token d'agent), demandé via un `prompt()` navigateur brut sans aucune indication d'où le trouver. Ce secret n'est affiché qu'une seule fois, à la création du tenant (`POST /api/v1/tenants`) — un opérateur qui ne l'avait pas noté n'avait aucun moyen de terminer l'installation.

Le provisioning existait déjà précisément pour éviter d'avoir besoin de ce secret (voir docs/adr/0004-multi-tenancy-avancee.md) mais le lien avec le téléchargement n'avait jamais été fait.

## Décisions

### 1. Le package embarque directement le token provisionné

`POST /api/v1/agents/provision` renvoie déjà `{agent_id, token, hostname, platform, api_url}`. `downloads/page.tsx` transmet désormais `hostname` et `token` (ceux renvoyés par le provisioning, pas ceux saisis séparément) à `GET /download/agent/{platform}?hostname=...&token=...` — le `prompt()` du secret de tenant est supprimé, plus rien à ressaisir.

### 2. Nouvelle commande CLI `configure`, distincte de `register`

`agent.cli configure --token <token>` sauvegarde directement le token (aucun appel réseau), pour un agent déjà créé côté serveur par le provisioning. `register` (secret de tenant, appel réseau, crée l'agent à l'installation) reste inchangée et disponible pour le flux sans provisioning préalable (téléchargement direct du package, secret de tenant obtenu autrement).

### 3. `generate_agent_package` choisit le script d'installation en fonction des paramètres reçus

Avec `token` fourni : le script embarqué appelle `configure --token`. Sans lui (`registration_secret` seul, ou aucun des deux) : comportement inchangé, `register`. `hostname` fourni : utilisé tel quel dans `config.json` ; sinon repli sur le placeholder générique existant.

## Limites de vérification

Vérifié en conditions réelles (pas seulement la suite de tests) : provisioning via l'API, téléchargement du package avec le hostname/token renvoyés, inspection du `config.json` et du script d'installation générés — confirmé que le script appelle `configure --token` avec la bonne valeur et plus jamais `register`. L'exécution réelle du script d'installation sur une machine cible reste hors de portée de ce sandbox (comme documenté depuis ADR 0002).

## Conséquences

Deux problèmes distincts, non traités ici et remontés à l'utilisateur séparément :
- `GET /download/agent/{platform}/installer` (installeur natif) redirige vers un asset GitHub Release qui n'existe pas : aucune release n'a jamais été publiée sur ce dépôt, donc le job CI qui construit les binaires (`build-agent-installers`, ADR 0002) ne s'est jamais exécuté.
- Les actions "Détails" / "Configurer" / "Supprimer" de la page Agents n'ont jamais été reliées à quoi que ce soit (ni bouton ni endpoint) — antérieur à cette session, jamais dans la roadmap traitée.
