# Samplyze.spec

# -*- mode: python ; coding: utf-8 -*-

import os

HERE = os.path.abspath(os.path.dirname(SPECPATH))

a = Analysis(
    ['run.py'],  # This is the main script that starts your app
    pathex=[],
    binaries=[],
    datas=[
        # UPDATED: Simplified paths and added the 'shared_files' directory.
        # This is a more robust way to include data files.
        ('templates', 'templates'),
        ('static', 'static'),
        ('instance', 'instance'),
        ('shared_files', 'shared_files')
    ],
    hiddenimports=['sqlalchemy.sql.default_comparator'], # Helps with SQLAlchemy compatibility
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Samplyze',  # The name of your final .exe file
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to False for a windowed app (no command prompt)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='samplyzelogo.ico',  # Your specified icon file
)
