"""Extract structured AST context from Python source using tree-sitter.

Output schema (passed to the AI as ground truth):
{
  "imports": ["os", "json", ...],
  "functions": [
    {"name": "...", "args": ["..."], "decorators": ["..."],
     "line": int, "nested": [ ...recursive... ]}
  ],
  "classes": [
    {"name": "...", "bases": ["..."], "decorators": ["..."],
     "line": int, "methods": [ ...same shape as functions... ]}
  ]
}
"""
from .tree_sitter_setup import get_parser


def _text(node, src: bytes) -> str:
    return src[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _collect_decorators(node, src: bytes) -> list[str]:
    """Decorators sit in a `decorated_definition` parent above the def/class."""
    parent = node.parent
    if parent is None or parent.type != "decorated_definition":
        return []
    out = []
    for child in parent.children:
        if child.type == "decorator":
            # decorator text is "@name(...)" — strip leading @
            text = _text(child, src).lstrip("@").strip()
            out.append(text)
    return out


def _func_info(node, src: bytes) -> dict:
    name_node = node.child_by_field_name("name")
    params_node = node.child_by_field_name("parameters")
    args: list[str] = []
    if params_node is not None:
        for p in params_node.named_children:
            # capture identifier text for typed/untyped/default params
            if p.type == "identifier":
                args.append(_text(p, src))
            else:
                ident = p.child_by_field_name("name")
                if ident is not None:
                    args.append(_text(ident, src))
                else:
                    args.append(_text(p, src).split(":")[0].split("=")[0].strip())

    body = node.child_by_field_name("body")
    nested = []
    if body is not None:
        for child in body.named_children:
            real = child
            if child.type == "decorated_definition":
                # find inner def
                for c in child.named_children:
                    if c.type == "function_definition":
                        real = c
                        break
            if real.type == "function_definition":
                nested.append(_func_info(real, src))

    return {
        "name": _text(name_node, src) if name_node else "",
        "args": args,
        "decorators": _collect_decorators(node, src),
        "line": node.start_point[0] + 1,
        "nested": nested,
    }


def _class_info(node, src: bytes) -> dict:
    name_node = node.child_by_field_name("name")
    bases_node = node.child_by_field_name("superclasses")
    bases: list[str] = []
    if bases_node is not None:
        for b in bases_node.named_children:
            bases.append(_text(b, src))

    methods = []
    body = node.child_by_field_name("body")
    if body is not None:
        for child in body.named_children:
            real = child
            if child.type == "decorated_definition":
                for c in child.named_children:
                    if c.type == "function_definition":
                        real = c
                        break
            if real.type == "function_definition":
                methods.append(_func_info(real, src))

    return {
        "name": _text(name_node, src) if name_node else "",
        "bases": bases,
        "decorators": _collect_decorators(node, src),
        "line": node.start_point[0] + 1,
        "methods": methods,
    }


def _collect_imports(root, src: bytes) -> list[str]:
    out: list[str] = []
    cursor = root.walk()

    def visit(node):
        if node.type == "import_statement":
            for c in node.named_children:
                out.append(_text(c, src))
        elif node.type == "import_from_statement":
            mod = node.child_by_field_name("module_name")
            mod_text = _text(mod, src) if mod else ""
            # tree-sitter-python doesn't field-name the imported names; the
            # module_name is the FIRST dotted_name child — everything after is a name.
            names = []
            seen_module = False
            for c in node.named_children:
                if c.type in ("dotted_name", "aliased_import", "identifier"):
                    if not seen_module and mod is not None and c.start_byte == mod.start_byte:
                        seen_module = True
                        continue
                    names.append(_text(c, src))
            if names:
                out.append(f"from {mod_text} import {', '.join(names)}")
            else:
                out.append(f"from {mod_text}")
        for child in node.children:
            visit(child)

    visit(root)
    # de-dup, preserve order
    seen = set()
    uniq = []
    for i in out:
        if i not in seen:
            seen.add(i)
            uniq.append(i)
    return uniq


def parse_python(source: str) -> dict:
    """Top-level AST extraction. Returns the schema documented above."""
    src_bytes = source.encode("utf-8")
    tree = get_parser().parse(src_bytes)
    root = tree.root_node

    functions: list[dict] = []
    classes: list[dict] = []

    for child in root.named_children:
        real = child
        if child.type == "decorated_definition":
            for c in child.named_children:
                if c.type in ("function_definition", "class_definition"):
                    real = c
                    break
        if real.type == "function_definition":
            functions.append(_func_info(real, src_bytes))
        elif real.type == "class_definition":
            classes.append(_class_info(real, src_bytes))

    return {
        "imports": _collect_imports(root, src_bytes),
        "functions": functions,
        "classes": classes,
    }
