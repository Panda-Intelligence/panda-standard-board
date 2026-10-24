#!/usr/bin/env python3
"""Package a Panda Standard Board KiCad project for import into https://heypcb.ai/dashboard.

Why this shape
--------------
heypcb's dashboard accepts one of: `.kicad_pcb`, `.kicad_sch`, or `.zip` (<= 50 MB,
`0x3200000` bytes). Its own UI copy advises zipping the board and leaving 3D models
(.step/.wrl) out of the archive, because the board imports without them.

A KiCad project only reopens with its *local* symbol/footprint libraries intact, so this
script vendors every project-local library next to the design and rewrites only the
library-table URIs (`fp-lib-table`, `sym-lib-table`) so `${KIPRJMOD}/libs/...` resolves
inside the archive. This mirrors KiCad's own File -> Archive Project behaviour.

Authoritative design files (`*.kicad_pcb`, `*.kicad_sch`, `*.kicad_pro`, `*.kicad_dru`)
are copied byte-for-byte and never rewritten. The manifest records both the original and
packaged SHA-256 for every design file so that identity is provable.

Usage:
    python3 packaging/package-for-heypcb.py <variant-dir> <project-dir> [--out DIR]
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path

# Files that are UI state, lock files, OS cruft or build residue: never ship these.
EXCLUDE_SUFFIXES = {".kicad_prl", ".lck", ".DS_Store", ".bak", ".pyc"}
EXCLUDE_NAMES = {".DS_Store", "component-index.json"}
EXCLUDE_DIR_NAMES = {"__pycache__", "-backups"}

# 3D models: heypcb explicitly says the board imports without them.
MODEL_SUFFIXES = {".step", ".stp", ".wrl", ".stl", ".igs"}

# KiCad design files that are authoritative and must be copied byte-for-byte.
DESIGN_SUFFIXES = {".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_dru"}

# KiCad-managed library tables that we are allowed to re-point.
LIB_TABLE_NAMES = {"fp-lib-table", "sym-lib-table"}

# Deterministic archive timestamps (1980-01-01 is the zip epoch floor).
ZIP_DATE_TIME = (1980, 1, 1, 0, 0, 0)
FIXED_MTIME = 315532800  # 1980-01-01T00:00:00Z, for on-disk reproducibility

HEYPCB_MAX_BYTES = 0x3200000  # 50 MiB, read out of the dashboard bundle


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_kiprjmod_uris(lib_table: Path) -> list[str]:
    """Return every ${KIPRJMOD}/... URI referenced by a KiCad library table."""
    text = lib_table.read_text(encoding="utf-8", errors="replace")
    return sorted(set(re.findall(r"\$\{KIPRJMOD\}/([^\")]+)", text)))


def is_excluded(path: Path) -> bool:
    if path.name in EXCLUDE_NAMES:
        return True
    if path.suffix in EXCLUDE_SUFFIXES:
        return True
    if path.suffix in MODEL_SUFFIXES:
        return True
    return any(part in EXCLUDE_DIR_NAMES for part in path.parts)


def collect_project_files(project_dir: Path) -> list[Path]:
    """Design + docs sitting directly in the project directory."""
    out: list[Path] = []
    for p in sorted(project_dir.iterdir()):
        if p.is_file() and not is_excluded(p):
            out.append(p)
    return out


def collect_local_libs(project_dir: Path) -> tuple[list[Path], list[Path]]:
    """Resolve every ${KIPRJMOD} library reference to a real path on disk.

    Returns (library files/dirs to vendor, missing references).
    """
    found: list[Path] = []
    missing: list[Path] = []
    seen: set[Path] = set()

    for table_name in sorted(LIB_TABLE_NAMES):
        table = project_dir / table_name
        if not table.is_file():
            continue
        for rel in parse_kiprjmod_uris(table):
            target = (project_dir / rel).resolve()
            if target in seen:
                continue
            seen.add(target)
            if target.exists():
                found.append(target)
            else:
                missing.append(project_dir / rel)
    return found, missing


def rewrite_lib_table(text: str, lib_basenames: set[str]) -> str:
    """Re-point every ${KIPRJMOD}/... URI at ${KIPRJMOD}/libs/<basename>."""

    def repl(match: re.Match[str]) -> str:
        rel = match.group(1)
        base = Path(rel).name
        if base in lib_basenames:
            return f"${{KIPRJMOD}}/libs/{base}"
        return match.group(0)

    return re.sub(r"\$\{KIPRJMOD\}/([^\")]+)", repl, text)


def build_package(variant_dir: Path, project_dir: Path, out_dir: Path) -> int:
    board_stem = next(
        (p.stem for p in sorted(project_dir.glob("*.kicad_pcb"))), project_dir.name
    )
    pkg_name = f"{variant_dir.name}-{board_stem}-heypcb"
    stage = out_dir / f".stage-{pkg_name}"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)

    originals: list[tuple[str, Path]] = []
    design_files = collect_project_files(project_dir)

    missing_libs: list[Path] = []
    lib_entries, missing_libs = collect_local_libs(project_dir)
    lib_basenames = {p.name for p in lib_entries}

    # 1. Copy design files byte-for-byte; re-point library tables.
    for src in design_files:
        dest = stage / src.name
        if src.name in LIB_TABLE_NAMES:
            text = src.read_text(encoding="utf-8", errors="replace")
            dest.write_text(rewrite_lib_table(text, lib_basenames), encoding="utf-8")
        elif src.suffix in DESIGN_SUFFIXES:
            shutil.copy2(src, dest)
            originals.append((src.name, src))
        else:
            shutil.copy2(src, dest)

    # 2. Vendor every project-local library under libs/.
    libs_dir = stage / "libs"
    libs_dir.mkdir(exist_ok=True)
    for src in lib_entries:
        dest = libs_dir / src.name
        if src.is_dir():
            shutil.copytree(
                src,
                dest,
                ignore=shutil.ignore_patterns(*EXCLUDE_DIR_NAMES, "*.step", "*.stp", "*.wrl"),
            )
        else:
            shutil.copy2(src, dest)

    # 3. Preserve the provenance notes that shipped with the project (text only).
    models_src = project_dir / "models"
    if models_src.is_dir():
        keep = [
            p
            for p in sorted(models_src.iterdir())
            if p.is_file() and p.suffix in {".md", ".txt"}
        ]
        if keep:
            models_dest = stage / "models"
            models_dest.mkdir(exist_ok=True)
            for p in keep:
                shutil.copy2(p, models_dest / p.name)

    # 4. Make the tree reproducible on disk.
    for root, dirs, files in os.walk(stage):
        for name in dirs + files:
            os.utime(Path(root) / name, (FIXED_MTIME, FIXED_MTIME))

    # 5. Manifest: original vs packaged hash for authoritative design files.
    manifest = [
        "# heypcb import package manifest",
        f"# source variant : {variant_dir}",
        f"# project dir    : {project_dir}",
        f"# package        : {pkg_name}.zip",
        "",
        "## Authoritative design files (copied byte-for-byte)",
        "# status  sha256(original)                                                 sha256(packaged)                                                 path",
    ]
    for name, src in originals:
        packaged = stage / name
        orig_hash = sha256_file(src)
        pkg_hash = sha256_file(packaged)
        status = "IDENTICAL" if orig_hash == pkg_hash else "CHANGED"
        manifest.append(f"{status:9s} {orig_hash}  {pkg_hash}  {name}")

    manifest += [
        "",
        "## Library tables (URI rewritten to ${KIPRJMOD}/libs/, design data untouched)",
    ]
    for table_name in sorted(LIB_TABLE_NAMES):
        if (stage / table_name).is_file():
            manifest.append(
                f"{sha256_file(stage / table_name)}  {table_name}"
            )

    manifest += ["", "## Vendored project-local libraries"]
    for src in lib_entries:
        rel = f"libs/{src.name}"
        manifest.append(f"{rel}")

    if missing_libs:
        manifest += ["", "## WARNING: unresolved ${KIPRJMOD} references"]
        manifest += [f"MISSING  {p}" for p in missing_libs]

    (stage / "MANIFEST.sha256").write_text("\n".join(manifest) + "\n", encoding="utf-8")

    # 6. Import instructions.
    (stage / "PACKAGE-README.md").write_text(
        f"""# {pkg_name}

Portable KiCad package of **{variant_dir.name}** for import at
<https://heypcb.ai/dashboard> ("Import board, schematic, or zip").

## What to upload

Upload **`{pkg_name}.zip`** (this archive). The dashboard also accepts a bare
`.kicad_pcb`; `{board_stem}.kicad_pcb` at the root of this archive is that file.

## Contents

- `{board_stem}.kicad_pcb` — the board (authoritative, byte-for-byte)
- `{board_stem}.kicad_sch` + sub-sheets — the schematic (authoritative, byte-for-byte)
- `{board_stem}.kicad_pro`, `{board_stem}.kicad_dru` — project + custom DRC rules
- `fp-lib-table`, `sym-lib-table` — re-pointed at `libs/` so they resolve inside this zip
- `libs/` — every project-local symbol/footprint library the design depends on
- `MANIFEST.sha256` — original vs packaged hashes for the authoritative files

## Not included

- 3D models (`.step`/`.wrl`): heypcb imports the board without them and draws those
  parts as boxes. This project vendors no local 3D models, so nothing was dropped.
- `.kicad_prl`, `.lck`, OS cruft — machine-local UI state, not design data.

## Note on standard KiCad libraries

Footprints/symbols named from KiCad's own bundled libraries (`Resistor_SMD`,
`Capacitor_SMD`, `Device`, ...) resolve against heypcb's KiCad install. Footprint
geometry is also embedded in the `.kicad_pcb` itself, so the board renders and routes
without them.

## Status

This board is a placement-only engineering candidate and is **not routed** and **not a
manufacturing release**. Check the variant's own README for its release gates.
""",
        encoding="utf-8",
    )

    if (variant_dir / "README.md").is_file():
        shutil.copy2(variant_dir / "README.md", stage / "PROJECT-README.md")

    # 7. Deterministic zip.
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"{pkg_name}.zip"
    if zip_path.exists():
        zip_path.unlink()

    members: list[tuple[str, Path]] = []
    for root, dirs, files in os.walk(stage):
        dirs.sort()
        for name in sorted(files):
            full = Path(root) / name
            members.append((str(full.relative_to(stage)), full))
    members.sort()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for arcname, full in members:
            info = zipfile.ZipInfo(arcname, date_time=ZIP_DATE_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o644 & 0xFFFF) << 16
            zf.writestr(info, full.read_bytes())

    shutil.rmtree(stage)

    size = zip_path.stat().st_size
    pct = 100.0 * size / HEYPCB_MAX_BYTES
    print(f"package : {zip_path}")
    print(f"files   : {len(members)}")
    print(f"size    : {size:,} bytes ({size / 1048576:.2f} MiB, {pct:.1f}% of heypcb's 50 MiB limit)")
    print(f"sha256  : {sha256_file(zip_path)}")
    if missing_libs:
        print("WARNING: unresolved libraries:", *missing_libs, sep="\n  ")
        return 2
    if size > HEYPCB_MAX_BYTES:
        print("ERROR: package exceeds heypcb's 50 MiB upload limit")
        return 3
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("variant_dir", type=Path, help="e.g. hardware/thin18-compact/c4d2-96x68-sgm62125")
    ap.add_argument("project_dir", type=Path, help="KiCad project dir (holds the .kicad_pro)")
    ap.add_argument("--out", type=Path, default=Path("dist/heypcb"), help="output directory")
    args = ap.parse_args()

    variant_dir = args.variant_dir.resolve()
    project_dir = args.project_dir.resolve()
    if not (project_dir / ".gitignore").exists() and not any(project_dir.glob("*.kicad_pro")):
        print(f"ERROR: {project_dir} does not look like a KiCad project dir", file=sys.stderr)
        return 1
    return build_package(variant_dir, project_dir, args.out.resolve())


if __name__ == "__main__":
    raise SystemExit(main())