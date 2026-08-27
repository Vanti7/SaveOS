# ADR 0008 — Erreur claire quand l'installeur natif n'est pas encore publié

## Statut

Accepté

## Contexte

Rapporté en testant réellement l'application : le bouton "Installeur natif" renvoie un 404. Cause : `GET /download/agent/{platform}/installer` redirige (302, stateless) vers un asset de GitHub Release construit par `.github/workflows/release.yml::build-agent-installers` (voir docs/adr/0002-packaging-agents.md) — mais **aucune release n'a jamais été publiée sur ce dépôt**, donc l'asset ciblé n'existe pas et GitHub renvoie son propre 404, opaque pour l'utilisateur (aucune indication de la cause réelle).

Décision validée avec l'utilisateur : ne pas déclencher de publication de release maintenant (chantier séparé, plus lourd — premier vrai test de bout en bout d'un pipeline jamais exécuté). Se limiter à rendre l'échec compréhensible.

## Décision

`_release_asset_exists(url)` (nouveau) vérifie par une requête `HEAD` que l'asset existe réellement avant de rediriger. S'il n'existe pas, l'endpoint renvoie un 404 avec un message explicite (version/plateforme concernées, lien vers les releases du dépôt, suggestion d'utiliser le package source en attendant) plutôt que de laisser échouer la redirection sur le 404 brut de GitHub. Une erreur réseau lors de la vérification (API sans accès sortant) ne bloque pas la redirection — elle est tentée quand même, cohérent avec le caractère non bloquant voulu pour ce endpoint.

## Limites de vérification

Vérifié en conditions réelles (conteneur `api` avec accès réseau sortant réel vers github.com) : le message d'erreur clair s'affiche bien en l'absence de release. Le chemin "release existe réellement" (redirection réussie vers un vrai asset) reste non vérifiable ici tant qu'aucune release n'a été publiée — même limite que documentée dans l'ADR 0002.

## Conséquences

Le bouton "Installeur natif" reste inutilisable tant qu'aucune release n'est publiée sur ce dépôt — ce chantier ne change pas ce fait, il rend seulement l'échec compréhensible. Publier une vraie release (et donc vérifier pour de bon le pipeline `build-agent-installers`) reste à faire séparément.
