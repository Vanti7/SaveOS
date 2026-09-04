# ADR 0010 — Contraste des champs de saisie (texte invisible en mode sombre)

## Statut

Accepté

## Contexte

Rapporté en testant réellement l'application : sur l'écran de connexion, le texte saisi dans les champs Email/Mot de passe était invisible.

Cause constatée dans le CSS réellement servi par le conteneur `web` :

- `.input-field` ne déclarait **ni** `color` **ni** `background-color` (uniquement largeur, bordure, arrondi, padding) — la couleur du texte était donc héritée du `body`.
- `globals.css` contenait un bloc `@media (prefers-color-scheme: dark)` hérité du starter Next.js, basculant `--foreground-rgb` à `255, 255, 255`.

Sur un système en mode sombre, le texte saisi devenait donc blanc, sur un champ posé sur une `.card` en `bg-white` : blanc sur blanc. Le symptôme ne dépend que du réglage d'apparence du système de l'utilisateur, ce qui explique qu'il n'ait pas été vu plus tôt — et il touchait **tous** les champs de l'application (connexion, téléchargements, paramètres, modales), pas seulement la connexion.

## Décision

1. **Suppression du bloc `prefers-color-scheme: dark`.** Le tableau de bord n'a aucune variante sombre : toutes les surfaces sont claires (`.card` en `bg-white`) et tous les textes fixent explicitement leur couleur (`text-gray-*`). Ce bloc n'avait donc aucun thème sombre à servir — son seul effet réel était de casser le contraste des éléments qui héritent leur couleur du `body`.
2. **`.input-field` fixe explicitement `bg-white text-gray-900`.** Un contrôle de formulaire ne doit pas dépendre de la couleur héritée du `body` pour rester lisible — c'est ce qui empêche la même classe de bug de revenir (réintroduction d'un bloc sombre, préférence de contraste forcée par le navigateur, etc.).

## Limites de vérification

Vérifié sur le CSS compilé réellement servi par le conteneur `web` reconstruit : `.input-field` porte désormais `background-color`/`color` explicites, et plus aucune règle `prefers-color-scheme: dark` n'est émise. Non vérifié dans un vrai navigateur en mode sombre (aucun binaire de navigateur disponible dans cet environnement, cf. limite déjà rencontrée pour les tests d'interface) — la vérification porte sur les règles CSS produites, pas sur un rendu observé.

## Conséquences

Le fond de page en mode sombre redevient le dégradé clair prévu par le design, au lieu du noir hérité du starter. C'est cohérent avec le reste de l'interface (cartes blanches, textes sombres) : l'application assume d'être claire uniquement. Proposer un véritable thème sombre resterait un chantier séparé, qui devrait alors traiter toutes les surfaces, pas seulement la couleur héritée du `body`.
