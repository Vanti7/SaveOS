# -*- mode: python ; coding: utf-8 -*-
"""
Spec PyInstaller pour l'agent SaveOS (exécutable autonome, --onefile).

Invocation (depuis la racine du dépôt) :
    pip install -r requirements-build.txt
    pyinstaller packaging/saveos-agent.spec

Produit dist/saveos-agent(.exe). Point d'entrée : agent.cli:cli — le même
que le console-script `saveos-agent` déclaré dans setup.py, pas une copie.
"""
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(SPEC)))

a = Analysis(
    [os.path.join(REPO_ROOT, 'agent', 'cli.py')],
    pathex=[REPO_ROOT],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='saveos-agent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
