"""Lazy tree-sitter Python language loader."""
from functools import lru_cache
from tree_sitter import Language, Parser
import tree_sitter_python as tspython


@lru_cache(maxsize=1)
def get_parser() -> Parser:
    language = Language(tspython.language())
    return Parser(language)
