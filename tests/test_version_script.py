"""
Test de non-régression : scripts/version.py doit lire/écrire ses fichiers
en UTF-8 explicite. Sans ça, sur un système dont l'encodage par défaut
n'est pas UTF-8 (ex. Windows/cp1252), la recherche de "## [Non publié]"
(accents) échoue silencieusement et aucune entrée n'est insérée dans
CHANGELOG.md, alors que le script rapporte un succès.
"""
import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "version_script", Path(__file__).parent.parent / "scripts" / "version.py"
)
version_script = importlib.util.module_from_spec(spec)
sys.modules["version_script"] = version_script
spec.loader.exec_module(version_script)


def test_add_changelog_entry_inserts_after_non_publie_heading(tmp_path):
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        "# Changelog\n\n## [Non publié]\n\n### Prévu\n- Autre chose\n",
        encoding="utf-8",
    )

    vm = version_script.VersionManager(str(tmp_path))
    vm.add_changelog_entry("1.2.0", ["Restauration granulaire"], "minor")

    content = changelog.read_text(encoding="utf-8")
    assert "## [1.2.0]" in content
    assert "Restauration granulaire" in content
    # L'entrée doit précéder la section "Prévu" existante, pas la remplacer
    assert content.index("## [1.2.0]") < content.index("### Prévu")
