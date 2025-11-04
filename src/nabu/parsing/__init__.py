"""
Nabu Parsing Module

Implements  three-phase processing pipeline:
1. Raw AST Extraction (tree-sitter → lightweight RawNode list)
2. Semantic Frame Creation (RawNode → AstFrameBase hierarchy)
3. Symbol Resolution (cross-reference resolution after structure is complete)

This separation enables independent testing, debugging, and flexibility.
Addresses the current implementation's mixed concerns in one giant method.
"""

from nabu.parsing.raw_extraction import RawNode, LanguageParser
from nabu.parsing.graph_builder import GraphBuilder
from nabu.parsing.symbol_resolver import SymbolResolver
from nabu.parsing.multi_pass_parser import MultiPassParser

__all__ = [
    'RawNode',
    'LanguageParser',
    'GraphBuilder',
    'SymbolResolver',
    'MultiPassParser'
]