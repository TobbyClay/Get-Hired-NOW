"""Build the standalone skill ZIP and verify all local reference links resolve."""

import argparse
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "get-hired-now"


def files():
    return sorted(p for p in SKILL.rglob("*") if p.is_file() and "__pycache__" not in p.parts
                  and p.suffix in {".md", ".json", ".yaml", ".py"})


def validate_bundle():
    entry = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    if not entry.startswith("---\nname: get-hired-now\n") or "\ndescription:" not in entry.split("\n---", 1)[0]:
        raise ValueError("Skill entrypoint needs valid discovery metadata")
    for path in files():
        if path.is_symlink():
            raise ValueError("Skill bundles cannot contain symlinks")
        if path.suffix != ".md":
            continue
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("#"):
                continue
            resolved = (path.parent / target.split("#")[0]).resolve()
            if not resolved.is_relative_to(SKILL.resolve()) or not resolved.exists():
                raise ValueError(f"Broken or external skill reference in {path.name}: {target}")


def build(destination):
    validate_bundle()
    destination = Path(destination).resolve()
    if destination.is_relative_to(SKILL.resolve()):
        raise ValueError("Write release artifacts outside the installed skill")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files():
            archive.write(path, "get-hired-now/" + path.relative_to(SKILL).as_posix())
        archive.write(ROOT / "LICENSE", "get-hired-now/LICENSE")
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = build(args.output)
    print(f"Standalone skill packaged: {output.name} ({len(files()) + 1} files)")
