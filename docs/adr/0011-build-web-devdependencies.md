# ADR 0011 — Le builder de l'image web installe les devDependencies

## Statut

Accepté

## Contexte

Le workflow « Deploy to Staging » a échoué **22 fois de suite**, à chaque merge sur `develop` entre le 26/08/2026 et le 11/09/2026, toujours au même endroit :

```
Type error: Cannot find module 'vitest/config' or its corresponding type declarations.
ERROR: process "/bin/sh -c npm run build" did not complete successfully: exit code: 1
```

Trois faits se combinent :

1. `Dockerfile.prod` (stage `web-builder`) installait avec `npm ci --only=production`, et `web/Dockerfile` avec `npm install --only=production` — les `devDependencies` étaient donc absentes du build.
2. `web/tsconfig.json` inclut `**/*.ts` / `**/*.tsx` et n'exclut que `node_modules`. `next build` type-check donc aussi `vitest.config.ts`, `vitest.setup.ts` et les quatre `*.test.ts(x)` — vérifié avec `npx tsc --noEmit --listFiles`.
3. Ces fichiers importent `vitest`, `@vitejs/plugin-react` et `@testing-library/*`, tous déclarés en `devDependencies` depuis l'introduction des tests web (26/08).

La CI ne pouvait pas voir le problème : le job « Tests Web » installe **toutes** les dépendances avec `npm install` avant de lancer `npm run build`. Le build CI et le build Docker n'exerçaient donc pas les mêmes conditions, et la CI est restée verte pendant que 22 déploiements consécutifs échouaient.

## Décision

1. **Le stage builder installe toutes les dépendances** (`npm ci` / `npm install`, sans `--only=production`). Un stage de build a besoin de ses outils de build ; c'est le stage d'exécution qui doit être minimal — et il l'est déjà, puisqu'il ne copie que la sortie `standalone` de Next.js. La taille de l'image finale est donc inchangée.

   L'alternative — exclure les fichiers de test du `tsconfig.json` — a été écartée : elle ferait perdre la vérification de types sur les tests (dans l'éditeur comme en CI) et demanderait de maintenir une liste d'exclusions à chaque nouveau fichier de test, pour une classe de bug qui reviendrait au prochain import de devDependency.

2. **La CI construit réellement l'image web** (`docker build --target web-builder`), de façon bloquante, dans le job « Docker Check ». C'est le seul endroit où le build est exercé avec les dépendances installées par le `Dockerfile` et non par la CI. Sans cette étape, la correction ci-dessus ne serait protégée par rien.

3. **Ajout de `.dockerignore`** (racine et `web/`), jusqu'ici impossible à committer : `.gitignore` contenait une section « Docker » qui ignorait `.dockerignore` lui-même. Le fichier ne pouvait donc jamais prendre effet. Sans lui, `COPY web/ .` recouvre le `node_modules` installé pour Alpine par celui de la machine hôte lors d'un build local, et `.env` / `certs/` transitent inutilement par le démon Docker.

## Limites de vérification

La chaîne causale est vérifiée localement : `npx tsc --noEmit --listFiles` confirme que `vitest.config.ts` et les quatre fichiers de test entrent bien dans la compilation, et que `vitest/config` est résolu depuis `node_modules`. Le build Docker lui-même n'a **pas** pu être rejoué sur cette machine (démon Docker arrêté) : la vérification réelle est faite par la nouvelle étape de CI, puis par le déploiement staging qui suit le merge.

`tests/test_web_docker_build.py` couvre le drapeau d'installation par assertions texte (rapides, sans Docker) et le build réel via un test marqué `@integration`, exclu de la CI Python comme le reste des tests d'intégration.

## Conséquences

Le déploiement staging redevient fonctionnel : les 97 commits accumulés sur `develop` depuis le 26/08 seront déployés au prochain merge. Le build web est désormais plus lent en CI (~2 min de plus, sans cache de couches), coût accepté pour ne plus découvrir ce type de rupture uniquement au déploiement.

Point non traité, hors périmètre : `web/Dockerfile` utilise `npm install` sans `package-lock.json` dans le contexte copié (seul `package.json` est copié), donc sans installation reproductible. `Dockerfile.prod`, lui, copie `web/package*.json` et utilise `npm ci`.
