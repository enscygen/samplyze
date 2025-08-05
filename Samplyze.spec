# Samplyze.spec

# -*- mode: python ; coding: utf-8 -*-

import os

# Get the directory where this spec file is located
HERE = os.path.abspath(os.path.dirname(SPECPATH))

a = Analysis(
    ['run.py'],  # This is the main script that starts your app
    pathex=[],
    binaries=[],
    datas=[
        # This is the most important part: it bundles your data files.
        # The format is ('source_path', 'destination_in_bundle')
        ('templates', 'templates'),
        ('static', 'static'),
        ('instance', 'instance'),
        ('appfiles', 'appfiles')
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
    console=False,  # Set to False to run without a command prompt window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='samplyzelogo.ico',  # Your specified icon file
)
