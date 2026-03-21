"""
Lean4 Parser - A light-weight parser for Lean 4 proof legality detection.

This package provides a full parser for Lean 4 code, including:
- Lexical analysis (tokenization)
- Syntactic analysis (parsing into AST)
- Source code reconstruction from AST
"""
import re
from typing import Tuple

from .ast import *
from .lexer import Lexer, Token, TokenType
from .parser import Parser
from .checker import Checker

__version__ = "0.2.1"
__all__ = [
    "Lexer",
    "Token",
    "TokenType",
    "Parser",
    "Checker"
] + [name for name in dir() if name.startswith("AST") or name in [
    "Module", "Import", "Open", "Namespace", "Section", "Variable",
    "Definition", "Theorem", "Lemma", "Instance", "Class", "Structure",
    "Inductive", "Abbrev", "Axiom", "Opaque", "Example",
]]


def parse_file(filepath: str) -> ASTNode:
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()
    return parse(source)


def parse(source: str) -> ASTNode:
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    parser = Parser(tokens, source)
    return parser.parse()


def check_consistency(formal_statement: str, proof: str, allow_sorry: bool = False) -> Tuple[bool, str]:
    checker = Checker()
    try:
        return checker.check_ast_consistency(formal_statement, proof, allow_sorry)
    except Exception as e:
        import traceback
        return False, f"Failed to check ast consistency: {traceback.format_exc()}"


def parse_clean(source: str, normalize_symbols: bool = False) -> ASTNode:
    checker = Checker()
    ast = checker.parse_ast(source, normalize_symbols=normalize_symbols)
    return ast


def walk_ast(nodes: List[ASTNode]):
    for node in nodes:
        yield node
        if isinstance(node, (Namespace, Section, Module, Mutual)):
            yield from walk_ast(node.body)


def extract_last_theorem(formal_statement: str) -> str:
    ast = parse_clean(formal_statement, normalize_symbols=False)
    last_node = ast
    for node in walk_ast([ast]):
        last_node = node
    return re.sub('\s+', ' ', last_node.to_source())


def extract_axioms(formal_statement: str) -> List[str]:
    ast = parse_clean(formal_statement, normalize_symbols=False)
    axioms = []
    for node in walk_ast([ast]):
        if isinstance(node, Definition) and node.kind == 'axiom':
            axioms.append(re.sub('\s+', ' ', node.to_source()))
    return axioms


