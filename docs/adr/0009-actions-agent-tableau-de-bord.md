# ADR 0009 — Actions réelles sur un agent (Détails/Configurer/Supprimer)

## Statut

Accepté

## Contexte

Rapporté en testant réellement l'application : sur la page Agents, les boutons "Détails", "Configurer" et "Supprimer" de chaque ligne n'avaient aucun gestionnaire (`onClick`) et aucun endpoint backend correspondant — clic sans effet. Décision validée avec l'utilisateur : construire ces actions maintenant plutôt que de simplement retirer les boutons.

## Décisions

- **Détails** : nouveau `GET /api/v1/agents/{agent_id}` (tableau de bord ou utilisateur de son propre tenant, 403 sinon), renvoie l'agent et ses statistiques (nombre de snapshots, volume total, dernière sauvegarde) — réutilise la logique déjà écrite pour `GET /api/v1/agents/stats` (extraite dans `_compute_agent_stats`, partagée entre les deux endpoints).
- **Configurer** : nouveau `PATCH /api/v1/agents/{agent_id}`, limité au renommage du hostname. Le modèle de données ne stocke aucune planification ni chemin de sauvegarde par agent (les chemins sont fournis à chaque job, voir `Job.config`) — il n'y a donc rien d'autre de réellement configurable côté serveur aujourd'hui. Conflit de hostname au sein du même tenant → 409 (même contrainte que `provision_agent`).
- **Supprimer** : nouveau `DELETE /api/v1/agents/{agent_id}`. Décision validée avec l'utilisateur : **suppression en cascade** — les jobs et snapshots de l'agent sont supprimés en base ; tout job de restauration (sur cet agent ou un autre) référençant un de ces snapshots via `Job.snapshot_id` est d'abord nullifié pour respecter la contrainte de clé étrangère. Les données Borg elles-mêmes restent sur le disque de stockage — SaveOS n'en garde simplement plus la trace après suppression (aucune suppression de fichiers déclenchée par cet endpoint).
- Les trois endpoints partagent `_get_agent_in_scope` : 404 si l'agent n'existe pas, 403 si un utilisateur connecté tente d'agir sur un agent d'un autre tenant que le sien ; le tableau de bord (token statique) n'a aucune restriction de tenant, comme partout ailleurs dans l'API.
- **Fuite de token corrigée au passage** (signalée et validée avec l'utilisateur, sans lien direct avec la demande initiale) : `GET /api/v1/agents` (listing) renvoyait le token de chaque agent — haché (SHA-256), jamais le secret en clair, mais un champ qui n'a rien à faire dans une réponse de listing. Nouveau schéma `AgentPublic` (sans `token`) pour le listing et le détail ; `AgentResponse` (avec `token`) reste utilisé uniquement par `register_agent`/`provision_agent`, où l'exposition en clair est intentionnelle et unique (comme `TenantCreateResponse.registration_secret`).

## Limites de vérification

Testé via la suite pytest (12 nouveaux tests : détail/configuration/suppression, isolation multi-tenant, cascade, nullification croisée, 404/409/403) et manuellement contre le conteneur `api` reconstruit. Non vérifié : effet réel d'une suppression sur un vrai repository Borg (les données restant sur disque par design, aucune interaction avec `BorgManager` n'est déclenchée par cet endpoint — cohérent avec le reste de l'API, qui ne gère jamais directement les fichiers Borg depuis le serveur).

## Conséquences

Les trois boutons de la page Agents sont désormais fonctionnels. Le renommage d'un agent (Configurer) reste volontairement limité — étendre les configurations réellement éditables (ex. politique de rétention par agent) resterait un chantier séparé si le besoin apparaît. La suppression en cascade signifie qu'un opérateur perd l'historique de restauration granulaire d'un agent supprimé, même si les données Borg physiques persistent — comportement assumé, documenté dans le message de confirmation de suppression côté interface.
