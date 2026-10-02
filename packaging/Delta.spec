from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

project_root = Path(SPECPATH).parent
backend_root = project_root / "backend"
frontend_dist = project_root / "frontend" / "dist"

datas = [
    (str(backend_root / "alembic.ini"), "."),
    (str(backend_root / "alembic"), "alembic"),
    (str(frontend_dist), "frontend/dist"),
    (str(backend_root / "app" / "prompts"), "app/prompts"),
    (str(project_root / "shared" / "layouts.json"), "shared"),
    (str(project_root / "packaging" / "version.txt"), "."),
]
hiddenimports = []
for package in ("aiosqlite", "litellm", "keyring", "platformdirs", "playwright"):
    package_datas, package_binaries, package_hiddenimports = collect_all(package)
    datas.extend(package_datas)
    hiddenimports.extend(package_hiddenimports)
hiddenimports.extend(collect_submodules("aiosqlite"))

a = Analysis(
    [str(project_root / "launcher" / "main.py")],
    pathex=[str(backend_root)],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["torch", "transformers"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="Delta", console=True)
coll = COLLECT(exe, a.binaries, a.datas, name="Delta")
