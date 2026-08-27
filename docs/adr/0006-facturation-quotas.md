# ADR 0006 — Facturation et quotas : rétention appliquée, usage visible, coût estimé

## Statut

Accepté

## Contexte

Dernier item de la roadmap. Décision validée avec l'utilisateur : "Quotas complets, pas de paiement réel" — pas d'intégration Stripe/paiement (aucune trace de facturation nulle part dans le dépôt, confirmé par grep ; un vrai moteur de paiement est un chantier de nature différente, hors périmètre), mais rendre les quotas déjà partiellement construits réellement utilisables.

État constaté :
- `Tenant.quota_bytes` était déjà appliqué (bloque un nouveau job de backup à 403 si dépassé, ajouté par l'item multi-tenancy — ADR 0004) mais **invisible** : aucun endpoint ni page ne montrait la consommation réelle.
- `Tenant.retention_policy` (JSON `{"daily": N, "weekly": N, "monthly": N}`) est stocké depuis la toute première version du projet mais **jamais appliqué** — `worker/tasks.py::BorgManager` n'avait pas de méthode `prune`, alors que Borg a une commande dédiée exactement pour ça.
- **Découverte en cherchant où afficher la consommation de quota** : `web/app/page.tsx` (page d'accueil du tableau de bord) affichait des statistiques **entièrement fictives** ("Pour le MVP, on simule les stats... Dans une vraie implémentation, on ferait appel à l'API") — jamais corrigée alors que toutes les autres pages (agents, monitoring, snapshots) ont été branchées sur l'API réelle au fil des items précédents de cette session. Même chose pour sa section "Activité récente" (trois entrées codées en dur) et les boutons "Actions rapides" (aucun gestionnaire de clic).

## Décisions

### 1. Purge automatique après chaque sauvegarde réussie

`process_backup_job` (`worker/tasks.py`) appelle `BorgManager.prune(retention_policy)` juste après la création réussie d'un snapshot, sur le même repository. Pas de nouveau système de tâches planifiées — ce dépôt n'a pas de scheduler branché sur RQ, et enchaîner `create` puis `prune` est l'usage standard de Borg. Politique absente ou sans clé reconnue (`daily`/`weekly`/`monthly`) = aucune purge, comportement par défaut préservé (pas de suppression surprise).

### 2. Réconciliation de la base après purge

`_reconcile_pruned_snapshots` re-liste les archives réellement présentes (`BorgManager.list_archives`, déjà existant) et supprime les lignes `Snapshot` dont l'archive a disparu — en mettant d'abord `Job.snapshot_id` à `NULL` pour toute ligne qui y référence (contrainte FK sur `snapshots.id`, colonne utilisée à la fois pour le snapshot produit par un backup et pour le snapshot source d'une restauration). Garde-fou explicite : une liste d'archives vide n'entraîne jamais de suppression en masse (protection contre une anomalie de parsing côté Borg).

### 3. Endpoint d'usage distinct de la liste de tenants

`GET /api/v1/tenants/{tenant_id}` (nouveau) est différent de `GET /api/v1/tenants` (liste, reste `require_dashboard` strict, inchangé depuis l'ADR 0004/0005) : accessible au token dashboard (n'importe quel tenant) **ou** à un utilisateur authentifié pour son propre tenant uniquement (403 sinon, via `resolve_scoped_tenant_id` déjà utilisé ailleurs). Retourne `used_bytes`, `quota_percent`, `estimated_cost` — la requête d'agrégation était déjà écrite dans `create_backup_job`, extraite en `compute_tenant_consumed_bytes` pour être réutilisée sans duplication.

### 4. Ajustement du quota après création

`PATCH /api/v1/tenants/{tenant_id}` (nouveau, dashboard uniquement — même périmètre que la création de tenant) permet de modifier `quota_bytes`/`retention_policy` après coup. Sans lui, un quota resterait figé à la valeur choisie à la création du tenant. Pas d'interface web dédiée : la gestion de tenants reste une action d'exploitation via l'API, cohérent avec la décision déjà prise dans l'item précédent (ADR 0005) de retirer la gestion de tenants du tableau de bord.

### 5. Coût estimé, pas de facturation réelle

`estimated_cost = (used_bytes / 1 Go) * BILLING_PRICE_PER_GB` (variable d'environnement, défaut `0.02`) — un simple calcul affiché dans la même réponse d'usage, aucune persistance, aucune facture générée, aucune intégration de paiement. Volontairement minimal, cohérent avec le périmètre choisi.

### 6. Page d'accueil corrigée en même temps

`web/app/page.tsx` branché sur les vraies données (stats, activité récente, boutons d'action) et gagne la carte "Utilisation du tenant" (barre de progression colorée selon `quota_percent`, coût estimé) — c'est l'endroit naturel pour rendre le quota visible, et la corriger faisait partie du même geste que d'y ajouter cette carte.

## Limites de vérification

- **`borg prune` non testable avec un vrai binaire/repository dans ce sandbox** — même limite que pour tout `BorgManager` existant dans ce dépôt (`create_backup`, `init_repo`, `extract`, etc.), déjà acceptée avant ce chantier : tous les tests mockent au niveau méthode (`@patch('worker.tasks.BorgManager.prune')`), jamais de vrai `subprocess` vers un binaire Borg réel.
- **Aucune vérification d'un vrai cycle de facturation externe** — assumé dès le départ (pas de Stripe/paiement dans le périmètre retenu), pas une limite de ce sandbox mais une décision de portée.

## Conséquences

- La purge automatique supprime réellement des sauvegardes anciennes dès qu'un tenant a une `retention_policy` avec au moins une clé reconnue — la valeur par défaut du modèle (`{"daily": 30, "weekly": 12, "monthly": 12}`) s'applique donc désormais activement à tout tenant qui ne l'a jamais explicitement modifiée, alors qu'elle ne faisait rien auparavant. Comportement voulu (c'est l'objet de ce chantier), mais à garder en tête pour un déploiement existant : le premier backup après mise à jour peut purger des archives déjà anciennes qui s'étaient accumulées sans jamais être purgées.
