"""Golden rule 5: kinetiq-core imports no web framework, ORM, cloud SDK or provider code."""

import ast
from pathlib import Path

SOURCE = Path(__file__).parent.parent / "src" / "kinetiq_core"
ALLOWED = {"numpy", "scipy", "kinetiq_contracts", "kinetiq_core"}
STDLIB = {"ast", "collections", "dataclasses", "math", "pathlib", "typing"}


def imported_packages(path: Path) -> set[str]:
    packages: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            packages.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            packages.add(node.module.split(".")[0])
    return packages


def test_only_numeric_libraries_are_imported() -> None:
    files = list(SOURCE.glob("**/*.py"))
    assert files
    for path in files:
        unexpected = imported_packages(path) - ALLOWED - STDLIB
        assert not unexpected, f"{path.name} imports {sorted(unexpected)}"
