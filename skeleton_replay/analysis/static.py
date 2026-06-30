"""Minimal AST facts used to annotate runtime snapshots."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

from skeleton_replay.runtime.filters import TraceFilter


@dataclass(frozen=True)
class StaticSymbol:
    """A static module, class, or function summary."""

    id: str
    kind: str
    module: str
    name: str
    file: str
    line: int
    loc: int


@dataclass(frozen=True)
class StaticModule:
    """Static facts for a Python module."""

    id: str
    module: str
    file: str
    loc: int
    classes: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class StaticIndex:
    """Static facts keyed by snapshot node id."""

    modules: dict[str, StaticModule]
    symbols: dict[str, StaticSymbol]


@dataclass(frozen=True)
class StaticProjectScanner:
    """Scans project-local Python files for basic module/class/function facts."""

    project_root: Path

    def scan(self) -> StaticIndex:
        """Scan project-local Python files for basic static facts."""
        project_root = self.project_root.resolve()
        trace_filter = TraceFilter(project_root=project_root)
        modules: dict[str, StaticModule] = {}
        symbols: dict[str, StaticSymbol] = {}
        for path in sorted(project_root.rglob("*.py")):
            if not trace_filter.allows_file(str(path)):
                continue
            source = path.read_text(encoding="utf-8")
            tree = self._parse(path, source)
            if tree is None:
                continue
            module_name = trace_filter.module_from_path(path)
            module_id = f"module:{module_name}"
            classes, functions = self._index_symbols(tree=tree, module_name=module_name, path=path, symbols=symbols)
            modules[module_id] = StaticModule(
                id=module_id,
                module=module_name,
                file=str(path.resolve()),
                loc=self._count_loc(source),
                classes=classes,
                functions=functions,
                imports=self._imports(tree),
            )
        return StaticIndex(modules=modules, symbols=symbols)

    def _index_symbols(self, *, tree: ast.AST, module_name: str, path: Path, symbols: dict[str, StaticSymbol]) -> tuple[list[str], list[str]]:
        classes: list[str] = []
        functions: list[str] = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
                self._add_symbol(symbols=symbols, symbol_id=f"class:{module_name}.{node.name}", kind="class", module=module_name, name=node.name, path=path, node=node)
                self._index_class_methods(node=node, module_name=module_name, path=path, symbols=symbols)
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and TraceFilter.allows_function(node.name):
                functions.append(node.name)
                self._add_symbol(symbols=symbols, symbol_id=f"function:{module_name}.{node.name}", kind="function", module=module_name, name=node.name, path=path, node=node)
        return classes, functions

    def _index_class_methods(self, *, node: ast.ClassDef, module_name: str, path: Path, symbols: dict[str, StaticSymbol]) -> None:
        for child in node.body:
            if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef) and TraceFilter.allows_function(child.name):
                self._add_symbol(
                    symbols=symbols,
                    symbol_id=f"function:{module_name}.{node.name}.{child.name}",
                    kind="function",
                    module=module_name,
                    name=child.name,
                    path=path,
                    node=child,
                )

    def _add_symbol(self, *, symbols: dict[str, StaticSymbol], symbol_id: str, kind: str, module: str, name: str, path: Path, node: ast.AST) -> None:
        symbols[symbol_id] = StaticSymbol(
            id=symbol_id,
            kind=kind,
            module=module,
            name=name,
            file=str(path.resolve()),
            line=int(getattr(node, "lineno", 0)),
            loc=self._node_loc(node),
        )

    @staticmethod
    def _parse(path: Path, source: str) -> ast.AST | None:
        try:
            return ast.parse(source, filename=str(path))
        except SyntaxError:
            return None

    @staticmethod
    def _count_loc(source: str) -> int:
        return sum(1 for line in source.splitlines() if line.strip() and not line.lstrip().startswith("#"))

    @staticmethod
    def _node_loc(node: ast.AST) -> int:
        start = getattr(node, "lineno", 0)
        end = getattr(node, "end_lineno", start)
        return max(1, int(end) - int(start) + 1)

    @staticmethod
    def _imports(tree: ast.AST) -> list[str]:
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        return sorted(set(imports))
