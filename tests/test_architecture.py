"""Guard the dependency direction without importing application modules."""

import ast
from importlib.util import resolve_name
from pathlib import Path


def test_core_modules_do_not_import_http_layer() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "aggregator"
    for path in root.rglob("*.py"):
        relative = path.relative_to(root)
        if relative.parts[0] == "api":
            continue
        package = ".".join(("aggregator", *relative.parts[:-1]))
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if node.level:
                    module = resolve_name("." * node.level + module, package)
                names = [module, *(f"{module}.{alias.name}" for alias in node.names)]
            assert not any(
                name == "aggregator.api" or name.startswith("aggregator.api.") for name in names
            ), f"{relative} imports the HTTP layer"
