# ADR 0001 — Restauration granulaire : token dashboard temporaire et exécution centralisée par le worker

## Statut

Accepté

## Contexte

La roadmap demandait la restauration granulaire (sélection de fichiers/dossiers dans un snapshot) via l'interface web, avec deux cibles : téléchargement navigateur et dépôt direct sur la machine agent. Deux contraintes structurelles de l'existant ont dû être résolues pour livrer ça sans déborder sur d'autres chantiers de la roadmap (« Gestion des utilisateurs et authentification ») :

1. **Aucune authentification du tableau de bord.** Seuls les agents disposent d'un token Bearer ; chaque endpoint vérifie qu'un agent n'agit que pour lui-même. Le dashboard web n'avait donc aucun moyen d'appeler l'API pour déclencher une restauration.
2. **L'agent n'exécute jamais Borg localement.** Le worker centralisé exécute déjà `borg create` (et maintenant `borg list`/`borg extract`) sur un dépôt qu'il partage avec l'API via un volume Docker (`borg_repos`). L'agent (client Python léger, `requests` + `click`) n'a pas Borg installé et n'a historiquement aucun canal pour recevoir un job poussé par le serveur.

## Décisions

### 1. Token dashboard statique, explicitement temporaire

Le dashboard s'authentifie via un unique token partagé (`DASHBOARD_API_TOKEN`, variable d'environnement), vérifié par `get_current_principal` (api/auth.py) au même titre qu'un token agent. Un `Principal` avec `is_dashboard=True` peut agir pour n'importe quel `agent_id` (`can_act_on_agent()`), alors qu'un agent reste restreint à lui-même.

**Implication sécurité assumée** : quiconque atteint les routes proxy du dashboard (`web/app/api/**`) obtient un accès complet, à l'échelle du tenant, à tous les agents/jobs/snapshots — il n'y a aucune notion d'utilisateur ni de rôle. C'est un pont MVP, pas une solution finale. Le token ne doit jamais atteindre le navigateur : il est porté uniquement par `web/app/lib/serverApi.ts` (jamais importé par un composant `'use client'`), et les composants clients passent par les routes proxy Next.js plutôt que d'appeler l'API distante directement.

Ce pont sera remplacé par le vrai système d'authentification utilisateur (roadmap séparée) — à ce moment-là, `require_dashboard`/`Principal.is_dashboard` devront être reliés à une session utilisateur réelle plutôt qu'à un secret statique.

### 2. Le worker fait toute l'extraction Borg ; l'agent applique un paquet déjà construit

Plutôt que de construire un mécanisme d'exécution Borg côté agent (ce qui aurait aussi supposé refondre la façon dont les sauvegardes s'exécutent aujourd'hui — hors périmètre de cet item de roadmap), la restauration réutilise l'architecture existante :

- Le **worker** (qui a déjà l'accès direct au dépôt Borg) liste le contenu d'une archive (`BorgManager.list_archive_contents`) et extrait les chemins sélectionnés (`BorgManager.extract`), puis empaquette le résultat en zip sur un volume partagé (`restore_packages`).
- Pour une restauration téléchargée, le dashboard sert ce zip via `GET /api/v1/restore/{job_id}/download`.
- Pour une restauration « agent », l'agent récupère le **même** zip via ce **même** endpoint (avec son propre token) puis le décompresse localement avec `zipfile` — il n'a jamais besoin d'installer Borg ni d'accéder au dépôt.

Ceci introduit un nouveau statut de job, `ready_for_agent` : le worker y place le job une fois le paquet prêt ; l'agent le fait passer à `completed`/`failed` via `POST /api/v1/jobs/{job_id}/agent-report` une fois l'extraction locale terminée. C'est le premier mécanisme par lequel le serveur "délègue" du travail à un agent (via un polling, `GET /api/v1/agents/me/pending-restores`, appelé depuis la boucle `daemon` existante) — jusqu'ici l'agent ne faisait que créer ses propres jobs et suivre leur statut.

## Conséquences

- Aucune modification du modèle d'exécution des sauvegardes existant (toujours centralisé sur le worker).
- L'agent reste un client léger : `requests` + `click` + `zipfile`, pas de dépendance Borg.
- Le dashboard n'a toujours pas de notion d'utilisateur/rôle — à traiter explicitement lors de l'item roadmap « Gestion des utilisateurs et authentification », qui devra remplacer `DASHBOARD_API_TOKEN` plutôt que le superposer.
- Pas d'index persistant du contenu des archives : chaque navigation relance `borg list` sur l'archive complète et filtre côté API. Acceptable à l'échelle MVP ; à revisiter si les archives deviennent volumineuses (borg list peut devenir lent).
