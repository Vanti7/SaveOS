# ADR 0002 — Packaging des agents : redirection vers GitHub Releases, exécutables figés adaptés à ServiceManager

## Statut

Accepté

## Contexte

La roadmap demandait des installeurs natifs (exe/dmg/deb) pour l'agent, jusqu'ici distribué uniquement comme une archive de code source (zip/tar.gz) nécessitant Python installé sur la machine cible. L'exploration a montré deux choses :

1. `api/main.py::generate_agent_package` embarquait une **copie dupliquée et obsolète** de l'agent (une string Python géante) plutôt que le vrai package `agent/` — sans la restauration ni la gestion de service, ajoutées après coup au vrai code.
2. `agent/service.py` (`ServiceManager`, install/start/stop/status systemd/launchd/tâche planifiée) était déjà entièrement écrit mais **jamais appelé** depuis `agent/cli.py` — code mort, jamais exercé en conditions réelles.

Décisions validées avec l'utilisateur : publication à la fois sur GitHub Releases **et** via l'API/dashboard ; installeur graphique complet (pas un binaire nu) avec enregistrement automatique du service.

## Décisions

### 1. PyInstaller construit depuis le vrai point d'entrée, pas une copie

`packaging/saveos-agent.spec` construit l'exécutable depuis `agent.cli:cli` — le même point d'entrée que le console-script `saveos-agent` déjà déclaré dans `setup.py`. Aucune duplication : ce qui est empaqueté est ce qui tourne réellement en développement. `generate_agent_package()` (le téléchargement "code source" existant) a été corrigé pour la même raison : il zippe désormais les vrais fichiers `agent/*.py`.

### 2. L'API reste stateless : redirection vers GitHub Releases, pas de proxy binaire

`GET /download/agent/{platform}/installer` répond par une redirection HTTP 302 vers l'asset de la GitHub Release correspondant à la `VERSION` courante, plutôt que de stocker ou proxyer les binaires. Alternative envisagée et écartée : baker les installeurs dans l'image Docker de l'API au moment du build — rejeté car ça couple le build de l'image API au pipeline de release des installeurs (deux artefacts de nature différente, cycles de vie différents), pour un gain minime (la redirection coûte une requête de plus, négligeable pour un téléchargement d'installeur).

**Implication** : les noms de fichiers générés par le job CI (`.github/workflows/release.yml::build-agent-installers`) et la table `_INSTALLER_ASSET_TEMPLATES` de `api/main.py` doivent rester synchronisés manuellement — pas de source unique de vérité entre les deux. Documenté par un commentaire à chaque bout.

### 3. ServiceManager adapté aux exécutables figés, garde-fou pywin32 mort retiré

`ServiceManager` générait des commandes supposant un script Python lancé par un interpréteur système (`ExecStart=/usr/bin/python3 {agent_path} daemon`), incompatible avec un exécutable autonome (qui EST l'interpréteur+script). Ajout de `is_frozen` (auto-détecté via `sys.frozen`) pour générer la bonne commande dans les trois implémentations (systemd, launchd, tâche planifiée Windows).

En testant réellement `dist/saveos-agent.exe service install` sur cette machine, découverte d'un second bug bloquant : `_install_windows_service()` exigeait `pywin32` (import mort, jamais utilisé — l'implémentation réelle est `schtasks`) avant de déléguer à `_install_windows_task()`. pywin32 n'étant jamais installé sur une machine utilisateur type, ce garde-fou bloquait systématiquement l'installation du service pour tout le monde. Retiré.

### 4. Élévation requise pour l'enregistrement du service (assumé, pas contourné)

La tâche planifiée Windows s'exécute sous le compte SYSTEM (`LogonType=ServiceAccount`, `UserId=S-1-5-18`), ce qui exige un contexte élevé pour `schtasks /create` — confirmé en testant sans élévation sur cette machine (erreur `The task XML contains a value which is incorrectly formatted or out of range`, message caractéristique d'un défaut d'élévation, pas d'un problème de XML). `packaging/windows/installer.iss` déclare `PrivilegesRequired=admin`, donc l'installeur réel s'exécute élevé et `service install` fonctionnera dans ce contexte — non re-testé avec élévation sur cette machine (aurait modifié l'état système du poste de développement pour une vérification).

## Limites de vérification

- **Windows** : construction PyInstaller + exécution réelle (`--help`, `service status`, `service install` sans élévation) testées en local sur cette machine. Compilation Inno Setup non vérifiable localement (Chocolatey nécessite des droits admin indisponibles dans ce sandbox) — seulement via la matrice CI.
- **macOS** (`.pkg`/`.dmg`) et **Linux** (`.deb`) : aucun environnement disponible en local — vérifiables uniquement via les runners `macos-latest`/`ubuntu-latest` de la matrice CI. Plusieurs itérations de correction sont probables au premier déclenchement (trois chaînes d'outils entièrement nouvelles pour ce dépôt : PyInstaller, Inno Setup, pkgbuild, fpm).

## Conséquences

- Le package source téléchargeable et l'installeur natif restent tous les deux disponibles — le premier pour inspecter/modifier le code, le second pour une installation sans dépendance Python.
- `docker-release` (job préexistant de `release.yml`, jamais fonctionnel faute de `outputs:` sur le job `release`) fonctionne maintenant comme effet de bord de la correction nécessaire pour `build-agent-installers`.
- Prochaine étape naturelle si le besoin se confirme : signature de code (Windows Authenticode, notarization Apple) — non traitée ici, hors périmètre de cet item de roadmap.
