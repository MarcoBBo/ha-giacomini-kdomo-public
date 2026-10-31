#!/usr/bin/env python3
"""Build reproducible ZIPs from an explicit public-file allowlist."""

import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_ROOT_FILES = {
    "README.md",
    "LICENSE",
    "NOTICE.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CHANGELOG.md",
    "pyproject.toml",
    "requirements-test.txt",
    "requirements-test-min.txt",
    "hacs.json",
    "package.json",
    "package-lock.json",
    ".gitignore",
}
ALLOWED_DIRECTORIES = {"custom_components", "docs", "tests", "scripts", ".github"}
ALLOWED_SUFFIXES = {".py", ".json", ".md", ".yaml", ".yml", ".txt", ".js", ".mjs"}


def public_files() -> list[Path]:
    files = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        parts = path.relative_to(ROOT).parts
        if any(
            part.startswith("__pycache__") or part in (".git", ".pytest_cache", ".ruff_cache", "node_modules")
            for part in parts
        ):
            continue
        if len(parts) == 1 and path.name in ALLOWED_ROOT_FILES:
            files.append(path)
        elif parts[0] in ALLOWED_DIRECTORIES and (
            path.suffix in ALLOWED_SUFFIXES or path.name == "CODEOWNERS"
        ):
            files.append(path)
    return sorted(files)


def archive(destination: Path, files: list[Path], prefix: str = "") -> None:
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as handle:
        for path in files:
            relative = path.relative_to(ROOT).as_posix()
            info = zipfile.ZipInfo(prefix + relative, date_time=(2026, 10, 26, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            handle.writestr(info, path.read_bytes())


def main() -> None:
    version = json.loads((ROOT / "custom_components/kdomo/manifest.json").read_text())["version"]
    destination = ROOT / "dist"
    destination.mkdir(exist_ok=True)
    files = public_files()
    repo = destination / f"Giacomini_K-Domo_Home_Assistant_{version}.zip"
    component = destination / f"kdomo-{version}.zip"
    archive(repo, files, "kdomo-home-assistant/")
    archive(component, [p for p in files if p.relative_to(ROOT).parts[0] == "custom_components"])
    sums = []
    for path in (repo, component):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        sums.append(f"{digest}  {path.name}")
        print(f"{path.name}: {path.stat().st_size} bytes, SHA256 {digest}")
    (destination / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n")


if __name__ == "__main__":
    main()
