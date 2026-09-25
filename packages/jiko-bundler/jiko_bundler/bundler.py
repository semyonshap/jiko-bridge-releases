"""Conservative AST-based flattening into one shared Python namespace.

Inputs are parsed, never imported or executed. Unsupported module semantics
are errors rather than silently replaced by a runtime module loader.
"""

import ast
import importlib.util
import os
import symtable
import tempfile
import tokenize
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, NoReturn, TypeGuard

# AST visitors use visit_NodeName; graph state intentionally holds per-module metadata.
# pylint: disable=invalid-name,too-many-instance-attributes,too-many-branches


class BundleError(ValueError):
    """An input cannot be safely represented as a flat source bundle."""


@dataclass(frozen=True)
class BundleResult:
    """Generated source and input files in dependency order, entry last."""

    source: str
    modules: tuple[Path, ...]


@dataclass
class _Module:
    name: str
    path: Path
    tree: ast.Module
    source: str
    dependencies: set[str] = field(default_factory=set)
    # Bound name -> (kind, identity); kind is definition, external, or local.
    bindings: dict[str, tuple[str, str]] = field(default_factory=dict)
    aliases: dict[str, str] = field(default_factory=dict)
    shadowed: set[str] = field(default_factory=set)
    replacements: dict[int, list[ast.stmt]] = field(default_factory=dict)

    def fail(self, node: ast.AST, message: str) -> NoReturn:
        """Raise a diagnostic at the originating source location."""
        raise BundleError(f"{self.path}:{getattr(node, 'lineno', 1)}: {message}")


def _main_guard(node: ast.AST) -> TypeGuard[ast.If]:
    if not isinstance(node, ast.If) or not isinstance(node.test, ast.Compare):
        return False
    test = node.test
    if len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq):
        return False
    left, right = test.left, test.comparators[0]
    return any(
        isinstance(name, ast.Name)
        and name.id == "__name__"
        and isinstance(value, ast.Constant)
        and value.value == "__main__"
        for name, value in ((left, right), (right, left))
    )


def _docstring(node: ast.AST) -> TypeGuard[ast.Expr]:
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


class _StripDocstrings(ast.NodeTransformer):
    def _strip(self, node):
        self.generic_visit(node)
        if node.body and _docstring(node.body[0]):
            node.body.pop(0)
        if not node.body:
            node.body.append(ast.Pass())
        return node

    visit_FunctionDef = _strip
    visit_AsyncFunctionDef = _strip
    visit_ClassDef = _strip


class _StringAnnotations(ast.NodeTransformer):
    """Preserve postponed annotations per module without a bundle-wide future flag."""

    def visit_arg(self, node):
        """Stringify a parameter annotation."""
        if node.annotation is not None:
            node.annotation = ast.Constant(value=ast.unparse(node.annotation))
        return node

    def visit_FunctionDef(self, node):
        """Stringify a return annotation and visit all parameters and nested code."""
        if node.returns is not None:
            node.returns = ast.Constant(value=ast.unparse(node.returns))
        return self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_AnnAssign(self, node):
        """Stringify variable annotations, leaving assigned values unchanged."""
        node.annotation = ast.Constant(value=ast.unparse(node.annotation))
        return self.generic_visit(node)


class _ImportBlock:
    """Collect unconditional imports, preserving aliases and distinct submodules."""

    def __init__(self) -> None:
        self.statements: list[ast.stmt] = []
        self.seen: set[tuple[str, str, int, str, str | None]] = set()
        self.groups: dict[tuple[str, int], ast.ImportFrom] = {}

    def extract(self, body: list[ast.stmt]) -> list[ast.stmt]:
        """Remove only direct imports; never move imports out of a nested scope."""
        remaining = []
        for node in body:
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                remaining.append(node)
                continue
            for alias in node.names:
                module = (node.module or "") if isinstance(node, ast.ImportFrom) else ""
                level = node.level if isinstance(node, ast.ImportFrom) else 0
                key = (type(node).__name__, module, level, alias.name, alias.asname)
                if key in self.seen:
                    continue
                self.seen.add(key)
                if isinstance(node, ast.Import):
                    self.statements.append(ast.Import(names=[alias]))
                else:
                    group = (module, level)
                    if group not in self.groups:
                        statement = ast.ImportFrom(module=node.module, names=[], level=level)
                        self.groups[group] = statement
                        self.statements.append(statement)
                    self.groups[group].names.append(alias)
        return remaining


class _FlattenModules(ast.NodeTransformer):
    """Replace static module.symbol access with the symbol's flat name."""

    def __init__(self, builder, module):
        self.builder = builder
        self.module = module

    def visit_Attribute(self, node: ast.Attribute) -> ast.AST:
        """Resolve the longest known module prefix before visiting its root name."""
        parts: list[str] = []
        root: ast.expr = node
        while isinstance(root, ast.Attribute):
            parts.insert(0, root.attr)
            root = root.value
        if not isinstance(root, ast.Name) or root.id not in self.module.aliases:
            return self.generic_visit(node)
        target = self.module.aliases[root.id]
        while parts and target + "." + parts[0] in self.builder.modules:
            target += "." + parts.pop(0)
        if not parts or target not in self.builder.modules:
            self.module.fail(node, "Local module objects cannot be used as runtime values.")
        if not isinstance(node.ctx, ast.Load):
            self.module.fail(node, "Assignment through a local module alias is unsupported.")
        symbol = parts.pop(0)
        self.builder.identity(self.builder.modules[target], symbol)
        if symbol in self.module.shadowed:
            self.module.fail(node, f"Flattened symbol {symbol!r} could capture a local binding.")
        replacement: ast.expr = ast.Name(id=symbol, ctx=ast.Load())
        for attribute in parts:
            replacement = ast.Attribute(value=replacement, attr=attribute, ctx=ast.Load())
        return ast.copy_location(replacement, node)

    def visit_Name(self, node):
        """Module aliases may only occur as the root of an attribute access."""
        if node.id in self.module.aliases:
            self.module.fail(node, "Local module objects cannot be passed around or inspected.")
        if node.id == "__name__" and self.module.name != "__entry__":
            return ast.copy_location(ast.Constant(value=self.module.name), node)
        return node


class _Builder:
    def __init__(
        self,
        entry: str | Path,
        search_paths: Iterable[str | Path],
        external: Iterable[str],
        strip_docstrings: bool,
    ) -> None:
        self.entry = Path(entry).resolve()
        self.roots = tuple(
            dict.fromkeys([Path(path).resolve() for path in search_paths] + [self.entry.parent])
        )
        for root in self.roots:
            if not root.is_dir():
                raise BundleError(f"Import root is not a directory: {root}")
        self.external = tuple(external)
        self.strip_docstrings = strip_docstrings
        self.modules: dict[str, _Module] = {}
        self.paths: dict[Path, str] = {}
        self.futures: set[str] = set()

    def locate(self, name: str) -> Path | None:
        """Resolve a source module only inside the explicitly configured roots."""
        if any(name == item or name.startswith(item + ".") for item in self.external):
            return None
        found = set()
        for root in self.roots:
            stem = root.joinpath(*name.split("."))
            # Python gives a regular package precedence over a sibling .py file.
            for candidate in (stem / "__init__.py", stem.with_suffix(".py")):
                if candidate.is_file():
                    found.add(candidate.resolve())
                    break
        if len(found) > 1:
            choices = ", ".join(map(str, sorted(found)))
            raise BundleError(f"Ambiguous local module {name}: {choices}")
        return next(iter(found), None)

    def load(self, name: str, path: Path) -> _Module:
        """Parse a source once and recursively discover its imports."""
        if name in self.modules:
            return self.modules[name]
        if path in self.paths:
            raise BundleError(f"Source has two module names: {self.paths[path]}, {name}: {path}")
        try:
            with tokenize.open(path) as stream:
                source = stream.read()
            if name == "__entry__" and not source.strip():
                raise BundleError(f"Entry point is empty: {path}")
            tree = ast.parse(source, filename=str(path))
            compile(tree, str(path), "exec")
        except (SyntaxError, UnicodeError) as error:
            raise BundleError(f"{path}: {error}") from error
        module = _Module(name, path, tree, source)
        self.modules[name] = module
        self.paths[path] = name
        # An imported script's __main__ branch must not run inside the bundle.
        if name != "__entry__":
            tree.body = [
                item
                for node in tree.body
                for item in (node.orelse if _main_guard(node) else [node])
            ]
            # Export lists and package versions do not define a flat module's metadata.
            # Remove only literal, unread metadata; explicit imports will fail identity checks.
            reads = {
                node.id
                for node in ast.walk(tree)
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
            }
            retained: list[ast.stmt] = []
            for node in tree.body:
                if (
                    isinstance(node, ast.Assign)
                    and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and node.targets[0].id in {"__all__", "__version__"} - reads
                ):
                    try:
                        ast.literal_eval(node.value)
                    except (ValueError, TypeError):
                        retained.append(node)
                    continue
                retained.append(node)
            tree.body = retained
        self.analyze(module)
        return module

    def dependency(self, module: _Module, name: str, node: ast.AST) -> _Module | None:
        """Include a local dependency and its declarative package initializers."""
        path = self.locate(name)
        if path is None:
            if any(name == item or name.startswith(item + ".") for item in self.external):
                return None
            # A missing submodule of a local package is almost always a typo.
            if "." in name and self.locate(name.split(".")[0]) is not None:
                module.fail(node, f"Local module not found: {name}")
            return None
        if name != module.name:
            module.dependencies.add(name)
        dependency = self.load(name, path)
        # Python executes package initializers even for 'from pkg.child import X'.
        # Declarative initializers can be included without partial-module execution.
        parts = name.split(".")
        for index in range(1, len(parts)):
            parent = ".".join(parts[:index])
            parent_path = self.locate(parent)
            if parent_path is None:
                module.fail(node, f"Namespace packages are unsupported: {parent}")
            parent_module = self.load(parent, parent_path)
            for statement in parent_module.tree.body:
                if not (
                    _docstring(statement) or isinstance(statement, (ast.Import, ast.ImportFrom))
                ):
                    parent_module.fail(
                        statement,
                        "Implicit package initializers must contain only imports and docstrings. "
                        "Move initialization into an explicit function.",
                    )
        return dependency

    def base_name(self, module: _Module, node: ast.ImportFrom) -> str:
        """Resolve a relative import against the module's package."""
        if not node.level:
            return node.module or ""
        package = (
            module.name if module.path.name == "__init__.py" else module.name.rpartition(".")[0]
        )
        if module.name == "__entry__" or not package:
            module.fail(node, "Relative imports require a package module, not an entry script.")
        try:
            return importlib.util.resolve_name("." * node.level + (node.module or ""), package)
        except ImportError as error:
            module.fail(node, str(error))
        raise AssertionError("unreachable")

    def bind(self, module: _Module, name: str, value: tuple[str, str], node: ast.AST):
        """Record a binding without allowing ambiguous import reassignment."""
        previous = module.bindings.get(name)
        if previous is not None and previous != value:
            module.fail(node, f"Rebinding imported name {name!r} is unsupported.")
        module.bindings[name] = value

    def analyze_import(self, module: _Module, node: ast.AST, top_level: bool):
        """Separate host imports from local symbols and module aliases."""
        # pylint: disable=too-many-statements
        if isinstance(node, ast.Import):
            retained = []
            for alias in node.names:
                if self.locate(alias.name) is not None:
                    if not top_level:
                        module.fail(node, "Local imports must be unconditional at module level.")
                    self.dependency(module, alias.name, node)
                    bound = alias.asname or alias.name.split(".")[0]
                    target = alias.name if alias.asname else bound
                    if bound in module.aliases and module.aliases[bound] != target:
                        module.fail(node, f"Conflicting local module alias {bound!r}.")
                    module.aliases[bound] = target
                    continue
                retained.append(alias)
                if top_level:
                    bound = alias.asname or alias.name.split(".")[0]
                    identity = alias.name if alias.asname else bound
                    self.bind(module, bound, ("external", identity), node)
            if top_level:
                module.replacements[id(node)] = [ast.Import(names=retained)] if retained else []
            return
        if not isinstance(node, ast.ImportFrom):
            return
        if node.module == "__future__":
            if any(alias.name != "annotations" or alias.asname for alias in node.names):
                module.fail(node, "Only 'from __future__ import annotations' is supported.")
            self.futures.update(alias.name for alias in node.names)
            module.replacements[id(node)] = []
            return
        if any(alias.name == "*" for alias in node.names):
            module.fail(node, "Wildcard imports are unsupported; list imported symbols explicitly.")
        base = self.base_name(module, node)
        if all(self.locate(base + "." + alias.name) is not None for alias in node.names):
            if not top_level:
                module.fail(node, "Local imports must be unconditional at module level.")
            for alias in node.names:
                target = base + "." + alias.name
                self.dependency(module, target, node)
                bound = alias.asname or alias.name
                if bound in module.aliases and module.aliases[bound] != target:
                    module.fail(node, f"Conflicting local module alias {bound!r}.")
                module.aliases[bound] = target
            module.replacements[id(node)] = []
            return
        dependency = self.dependency(module, base, node)
        if dependency is None:
            if node.level:
                module.fail(node, f"Relative module not found: {base}")
            if top_level:
                for alias in node.names:
                    self.bind(
                        module,
                        alias.asname or alias.name,
                        ("external", base + "." + alias.name),
                        node,
                    )
            return
        if not top_level:
            module.fail(node, "Local imports must be unconditional and at module level.")
        replacement: list[ast.stmt] = []
        for alias in node.names:
            if self.locate(base + "." + alias.name) is not None:
                target = base + "." + alias.name
                self.dependency(module, target, node)
                module.aliases[alias.asname or alias.name] = target
                continue
            bound = alias.asname or alias.name
            self.bind(module, bound, ("local", base + ":" + alias.name), node)
            if alias.asname and alias.asname != alias.name:
                replacement.append(
                    ast.Assign(
                        targets=[ast.Name(id=alias.asname, ctx=ast.Store())],
                        value=ast.Name(id=alias.name, ctx=ast.Load()),
                    )
                )
        module.replacements[id(node)] = replacement

    def analyze(self, module: _Module):
        """Reject module-dependent constructs and collect global name bindings."""
        top_nodes = {id(node) for node in module.tree.body}
        guarded_names = {
            id(item)
            for node in module.tree.body
            if _main_guard(node)
            for item in ast.walk(node.test)
        }
        for node in ast.walk(module.tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                self.analyze_import(module, node, id(node) in top_nodes)
            if isinstance(node, ast.Name) and node.id in {
                "__file__",
                "__path__",
                "__package__",
                "__spec__",
                "__loader__",
                "__cached__",
            }:
                module.fail(node, f"{node.id} depends on module identity and cannot be flattened.")
            if isinstance(node, ast.Name) and node.id == "__name__":
                if not isinstance(node.ctx, ast.Load):
                    module.fail(node, "Reassigning __name__ is unsupported.")
                if module.name == "__entry__" and id(node) not in guarded_names:
                    module.fail(node, "Entry __name__ requires a top-level __main__ guard.")
            if isinstance(node, ast.Call):
                function = node.func
                if (
                    isinstance(function, ast.Name)
                    and function.id in {"__import__", "exec", "eval", "globals", "locals"}
                ) or (
                    isinstance(function, ast.Attribute)
                    and function.attr in {"import_module", "reload"}
                ):
                    module.fail(node, "Dynamic execution or namespace inspection unsupported")
        # A shared namespace must not capture globals that were unbound in another module.
        table = symtable.symtable(ast.unparse(module.tree), str(module.path), "exec")
        for symbol in table.get_symbols():
            if symbol.is_assigned() or symbol.is_namespace():
                self.bind(module, symbol.get_name(), ("definition", module.name), module.tree)
            if (
                symbol.is_imported()
                and symbol.get_name() not in module.bindings
                and symbol.get_name() not in module.aliases
                and symbol.get_name() not in self.futures
            ):
                module.fail(module.tree, "Conditional module-level imports are unsupported.")
        for alias in module.aliases:
            if alias in module.bindings:
                module.fail(module.tree, f"Local module alias {alias!r} is rebound.")

        def check_aliases(scope):
            for child in scope.get_children():
                for symbol in child.get_symbols():
                    if not symbol.is_global() and symbol.is_local():
                        module.shadowed.add(symbol.get_name())
                    if symbol.get_name() in module.aliases and not symbol.is_global():
                        module.fail(module.tree, f"Module alias {symbol.get_name()!r} is shadowed.")
                check_aliases(child)

        check_aliases(table)
        for node in ast.walk(module.tree):
            if (
                isinstance(node, ast.Attribute)
                and node.attr == "modules"
                and isinstance(node.value, ast.Name)
                and module.bindings.get(node.value.id) == ("external", "sys")
            ):
                module.fail(node, "sys.modules is unavailable for flattened local modules.")
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if any(alias + "." in node.value for alias in module.aliases):
                    module.fail(node, "String references to local module aliases are unsupported.")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                origin = module.bindings.get(node.func.id)
                if (
                    origin
                    and origin[0] == "external"
                    and origin[1]
                    in {
                        "importlib.import_module",
                        "importlib.reload",
                        "builtins.__import__",
                        "builtins.exec",
                        "builtins.eval",
                        "builtins.globals",
                        "builtins.locals",
                    }
                ):
                    module.fail(node, "Aliased dynamic imports/namespace inspection unsupported")
            if isinstance(node, ast.Global):
                for name in node.names:
                    if name not in module.bindings:
                        module.fail(node, f"Declare global {name!r} at module level first.")
        if ("external", "sys.modules") in module.bindings.values():
            module.fail(module.tree, "Importing sys.modules is unsupported in a flat bundle.")

    def order(self) -> list[_Module]:
        """Topologically sort dependencies, reporting the full cycle on failure."""
        ordered = []
        active: list[str] = []
        done = set()

        def visit(name):
            if name in active:
                raise BundleError("Circular local imports: " + " -> ".join([*active, name]))
            if name in done:
                return
            active.append(name)
            module = self.modules[name]
            for dependency in sorted(module.dependencies):
                visit(dependency)
            active.pop()
            done.add(name)
            ordered.append(module)

        for name in sorted(self.modules):
            if name != "__entry__":
                visit(name)
        visit("__entry__")
        return ordered

    def identity(self, module: _Module, name: str, seen=()) -> tuple[str, str]:
        """Follow static re-exports to the original binding identity."""
        key = (module.name, name)
        if key in seen:
            raise BundleError(f"Circular re-export: {module.name}.{name}")
        binding = module.bindings.get(name)
        if binding is None:
            raise BundleError(f"{module.path}: Imported symbol {name!r} is not statically defined.")
        kind, value = binding
        if kind == "local":
            target, symbol = value.split(":")
            return self.identity(self.modules[target], symbol, (*seen, key))
        return kind, value + (":" + name if kind == "definition" else "")

    def validate_bindings(self, ordered: list[_Module]):
        """Reject collisions and accidental capture in the shared namespace."""
        owners: dict[str, tuple[tuple[str, str], _Module]] = {}
        for module in ordered:
            for name in module.bindings:
                identity = self.identity(module, name)
                if name in owners and owners[name][0] != identity:
                    raise BundleError(
                        f"Global collision {name!r}: {owners[name][1].path} and {module.path}. "
                        "Rename the symbol or use a consistent import alias."
                    )
                owners[name] = (identity, module)

        def check(scope, module):
            for symbol in scope.get_symbols():
                name = symbol.get_name()
                if (
                    symbol.is_referenced()
                    and symbol.is_global()
                    and name not in module.bindings
                    and name in owners
                ):
                    raise BundleError(
                        f"{module.path}: Global {name!r} would accidentally bind to "
                        f"a symbol in {owners[name][1].path}."
                    )
            for child in scope.get_children():
                check(child, module)

        for module in ordered:
            table = symtable.symtable(ast.unparse(module.tree), str(module.path), "exec")
            check(table, module)

    def build(self) -> BundleResult:
        """Emit a deterministic source file with dependency section markers."""
        self.load("__entry__", self.entry)
        ordered = self.order()
        self.validate_bindings(ordered)
        chunks = ["# Generated by jiko-bundler. Edit the source files, not this bundle."]
        imports = _ImportBlock()
        for module in ordered:
            body = [
                statement
                for node in module.tree.body
                for statement in module.replacements.get(id(node), [node])
            ]
            # Module docstrings become section comments rather than stray expressions.
            doc = ast.get_docstring(ast.Module(body=body, type_ignores=[]))
            if body and _docstring(body[0]):
                body.pop(0)
            tree = ast.Module(body=body, type_ignores=[])
            tree = _FlattenModules(self, module).visit(tree)
            if any(
                isinstance(node, ast.ImportFrom) and node.module == "__future__"
                for node in module.tree.body
            ):
                tree = _StringAnnotations().visit(tree)
            if self.strip_docstrings:
                tree = _StripDocstrings().visit(tree)
            tree.body = imports.extract(tree.body)
            ast.fix_missing_locations(tree)
            label = module.name if module.name != "__entry__" else self.entry.name
            chunks.append(f"# --- {label} ---")
            if doc and not self.strip_docstrings:
                chunks.append("\n".join("# " + line for line in doc.splitlines()))
            chunks.append(ast.unparse(tree))
        if imports.statements:
            import_tree = ast.Module(body=imports.statements, type_ignores=[])
            ast.fix_missing_locations(import_tree)
            chunks.insert(1, ast.unparse(import_tree))
        source = "\n\n".join(chunks) + "\n"
        try:
            compile(source, "<jiko-bundle>", "exec")
        except SyntaxError as error:
            raise BundleError(f"Invalid flattened source: {error}") from error
        return BundleResult(source, tuple(module.path for module in ordered))


def bundle(
    entry: str | Path,
    *,
    search_paths: Iterable[str | Path] = (),
    external: Iterable[str] = (),
    strip_docstrings: bool = False,
) -> BundleResult:
    """Bundle an entry script and local static imports without executing inputs.

    Only explicit import roots and the entry's directory are searched. Imports
    not found there remain external. See README for the supported Python subset.
    """
    return _Builder(entry, search_paths, external, strip_docstrings).build()


def bundle_to_file(
    entry: str | Path,
    output: str | Path,
    *,
    search_paths: Iterable[str | Path] = (),
    external: Iterable[str] = (),
    strip_docstrings: bool = False,
) -> BundleResult:
    """Build and atomically replace output; never overwrite any input module."""
    result = bundle(
        entry,
        search_paths=search_paths,
        external=external,
        strip_docstrings=strip_docstrings,
    )
    destination = Path(output).resolve()
    if destination in result.modules:
        raise BundleError(f"Output would overwrite an input source: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=destination.parent,
            prefix=destination.name + ".",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(result.source)
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return result
