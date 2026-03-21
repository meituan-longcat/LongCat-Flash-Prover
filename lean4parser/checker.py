import re
from typing import List, Tuple, Union

from .ast import (
    ASTNode, Definition, Macro, MacroRules, Elab, Syntax,
    NotationDecl, Notation, Infix, Prefix, Postfix,
    AttributeDeclaration, SetOption, Namespace, Section, Module, Mutual,
    Variable, Instance, Structure, Class, Inductive
)
from .lexer import Lexer, Token, TokenType
from .parser import Parser


class Checker:
    def __init__(self):
        pass

    def parse_ast(self, code: str, return_tokens: bool = False, normalize_symbols: bool = True) -> Union[ASTNode, Tuple[List[Token], Union[ASTNode, None]]]:
        lexer = Lexer(code)
        tokens = lexer.tokenize()

        if normalize_symbols:
            # Token-level normalization for syntactic sugar and Unicode symbols
            for t in tokens:
                if t.type not in (TokenType.STRING, TokenType.CHAR, TokenType.LINE_COMMENT, TokenType.BLOCK_COMMENT, TokenType.DOC):
                    if t.raw == 'λ':
                        t.raw = t.value = 'fun'
                        t.type = TokenType.FUN
                    elif t.raw == '↦':
                        t.raw = t.value = '=>'
                        t.type = TokenType.DARROW
                    elif t.raw == '→':
                        t.raw = t.value = '->'
                        t.type = TokenType.ARROW
                    elif t.raw == '∀':
                        t.raw = t.value = 'forall'
                        t.type = TokenType.FORALL
                    elif t.raw == '≤':
                        t.raw = t.value = '<='
                    elif t.raw == '≥':
                        t.raw = t.value = '>='
                    elif t.raw == '≠':
                        t.raw = t.value = '!='

        tokens = [t for t in tokens if t.type not in [
            TokenType.LINE_COMMENT, TokenType.BLOCK_COMMENT, TokenType.DOC
        ]]
        parser = Parser(tokens, code)
        code = ' '.join(t.raw for t in tokens)
        ast = parser.parse()
        expected_clean = re.sub(r'\s+', '', code)
        actual_clean = re.sub(r'\s+', '', ast.to_source())
        if expected_clean != actual_clean:
            print(f"Failed to parse code into AST:\n# Expected\n{expected_clean}\n# Got\n{actual_clean}")
            ast = None
        if return_tokens:
            return tokens, ast
        else:
            return ast

    def check_ast_consistency(self, formal_statement: str, proof: str, allow_sorry: bool = False) -> Tuple[bool, str]:
        """
        Check if formal_statement and proof are consistent, and if the proof has no cheating risks.
        Logic:
        0. Check for duplicate definition names.
        1. Check if the last definition in problem is def/theorem/lemma, and proof has a matching definition.
        2. Check prerequisite definitions for allowed kind transitions and signature/body consistency.
        3. Check for illegal new definitions (e.g., axioms) in proof.
        4. Check for modified global variables or meta/syntax components.
        Returns:
        Tuple[bool, str]: (True, message) if the proof and formal_statement define the same problem to be proved,
                         (False, message) if the proof modified the problem or there are cheating suspicions.
        """
        import signal

        class TimeoutException(Exception):
            pass

        def timeout_handler(signum, frame):
            raise TimeoutException("Parsing AST timed out")

        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(600) # 600 seconds timeout

        try:
            problem_tokens, problem_ast = self.parse_ast(formal_statement, return_tokens=True)
            problem_identifiers = [t.value for t in problem_tokens if t.type == TokenType.IDENT]
            proof_ast = self.parse_ast(proof)
        except ValueError as e:
            return False, f"Parsing AST failed: {e}"
        except TimeoutException:
            return False, "Parsing AST timed out after 600 seconds."
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

        if problem_ast is None or proof_ast is None:
            return False, "failed to parse ast"

        # 1. Helper function: recursively flatten the AST tree to extract all nodes
        def walk_ast(nodes: List[ASTNode]):
            for node in nodes:
                yield node
                # If there are nested structures, traverse deeper
                if isinstance(node, (Namespace, Section, Module, Mutual)):
                    yield from walk_ast(node.body)
        
        def clean_source(node):
            if not node: return ""
            return re.sub(r'[\s;]+', '', node.to_source())

        # Define meta-syntax/attribute nodes that need strict control
        META_CLASSES = (
            Macro, MacroRules, Elab, Syntax,
            NotationDecl, Notation, Infix, Prefix, Postfix,
            AttributeDeclaration
        )

        # Dangerous SetOption blacklist (blocks configurations that ignore proofs or bypass checks)
        DANGEROUS_OPTIONS = {
            "skip_proofs", "warningAsError", "check_evidence"
        }

        # --- Step 1: Extract baseline information from the Problem ---
        problem_meta_sources = set()
        problem_variables = set()
        problem_variable_names = set()
        problem_local_names = set()
        problem_defs = []
        named_problem_nodes = {}

        for node in walk_ast([problem_ast]):
            if isinstance(node, META_CLASSES):
                # Store the source code with leading/trailing spaces removed for later comparison
                problem_meta_sources.add(clean_source(node))
            elif isinstance(node, Variable):
                problem_variables.add(clean_source(node))
                for binder in node.binders:
                    for name in binder.names:
                        if name != "_":
                            problem_variable_names.add(name)
            elif isinstance(node, (Definition, Instance, Structure, Class, Inductive)):
                if node.name == '':
                    node.name = clean_source(node)
                problem_defs.append(node)

            # Collect all locally bound names in the problem to avoid False Negatives on redefinition
            if hasattr(node, 'binders') and node.binders:
                for binder in node.binders:
                    for name in binder.names:
                        if name != "_":
                            problem_local_names.add(name)

        # If there are no Definitions in the Problem, it indicates a parsing error, block immediately
        if not problem_defs:
            raise ValueError(f"No Definition found in problem:\n{formal_statement}")
            
        # 0. Check for duplicate definition names in problem
        problem_def_names = set()
        for node in problem_defs:
            if node.name in problem_def_names:
                raise ValueError(f"Multiple definitions with the same name '{node.name}' found in problem:\n{formal_statement}\n{proof_ast.to_tree()}")
            problem_def_names.add(node.name)
            named_problem_nodes[node.name] = node

        # Background identifiers are those used in the problem but NOT locally bound
        # and NOT the names of the definitions themselves.
        problem_background_identifiers = set(problem_identifiers) - problem_local_names - problem_def_names - problem_variable_names

        problem_main_thm = problem_defs[-1]

        # 1. Check last definition in problem
        def get_type(node):
            return node.kind if isinstance(node, Definition) else type(node).__name__.lower()
        
        if get_type(problem_main_thm) not in ("def", "theorem", "lemma"):
            raise ValueError(f"The last definition in problem must be 'def', 'theorem', or 'lemma', but got '{get_type(problem_main_thm)}'.")

        # --- Step 2: Extract signature (remove spaces to prevent false positives) ---
        def get_signature(node):
            # Extract and sort modifiers
            mods = sorted([m.name for m in getattr(node, 'modifiers', [])])
            mods_str = "|".join(mods)
            # Remove all spaces and newlines to ensure only the syntactic essence is compared
            binders_str = "".join(clean_source(b) for b in node.binders) if hasattr(node, 'binders') and node.binders else ""
            type_str = clean_source(node.type) if hasattr(node, 'type') and node.type else ""

            extra_str = ""
            if isinstance(node, (Structure, Class)):
                extends_str = "".join(clean_source(e) for e in getattr(node, 'extends', []))
                fields_str = "".join(clean_source(f) for f in getattr(node, 'fields', []))
                extra_str = extends_str + fields_str
            elif isinstance(node, Inductive):
                ctors_str = "".join(clean_source(c) for c in getattr(node, 'ctors', []))
                extra_str = ctors_str
            elif isinstance(node, Instance):
                # fields is a list of tuples: (name, binders, value) or (name, value)
                fields_str = ""
                for field in getattr(node, 'fields', []):
                    if len(field) == 3:
                        name, binders, value = field
                        binders_str_field = "".join(clean_source(b) for b in binders)
                        fields_str += name + binders_str_field + clean_source(value)
                    else:
                        name, value = field
                        fields_str += name + clean_source(value)
                extra_str = fields_str

            return getattr(node, 'name', ""), mods_str, binders_str, type_str, extra_str

        # --- Step 3: Audit the Proof code ---
        proof_defs = []
        named_proof_nodes = {}

        for node in walk_ast([proof_ast]):
            # A. Check Meta/Syntax components: If the Proof contains something not in the Problem, consider it cheating
            if isinstance(node, META_CLASSES):
                if clean_source(node) not in problem_meta_sources:
                    return False, f"Cheating suspicious: Meta/Syntax components were modified or added:\n{node.to_source().strip()}"
            
            # B. Check Variables: If the Proof modifies global variables, it might change theorem signatures or add premises
            elif isinstance(node, Variable):
                if clean_source(node) not in problem_variables:
                    return False, f"Cheating suspicious: Global variable declarations were modified or added:\n{node.to_source().strip()}"

            # C. Check SetOption: Touching the blacklist is considered cheating
            elif isinstance(node, SetOption):
                if any(dangerous in node.name for dangerous in DANGEROUS_OPTIONS):
                    return False, f"Cheating suspicious: Blacklisted SetOption used:\n{node.to_source().strip()}"

            # D. Collect Definitions
            elif isinstance(node, (Definition, Instance, Structure, Class, Inductive)):
                proof_defs.append(node)

                # Check if the proof defines a symbol that was a variable in the problem (shadowing/tampering)
                if getattr(node, 'name', None) in problem_variable_names:
                    return False, f"Cheating suspicious: Proof defines '{node.name}' as a {get_type(node)} which was a variable in the Problem."

        # 0. Check for duplicate definition names in proof
        proof_def_names = set()
        for node in proof_defs:
            name = getattr(node, 'name', "")
            if name:
                if name in proof_def_names:
                    return False, f"Cheating suspicious: Multiple definitions with the same name '{name}' found in proof."
                proof_def_names.add(name)
                named_proof_nodes[name] = node
            else:
                # Anonymous nodes (e.g., anonymous instances)
                if isinstance(node, Instance):
                    # We allow anonymous instances unless they are local (which is often used for cheating)
                    if any(m.name == "local" for m in getattr(node, 'modifiers', [])):
                        return False, "Cheating suspicious: Proof adds new anonymous local instance."

                    # Use the source as a unique name for anonymous instances
                    name = clean_source(node)
                    proof_def_names.add(name)
                    named_proof_nodes[name] = node

        # Definition kind transition matrix (Problem Kind -> Proof Kind)
        # True: Allowed (no cheating risk)
        # False: Cheating suspicious
        ALLOWED_KIND_TRANSITIONS = {
            "def":     {"def": True,  "theorem": False, "lemma": False, "abbrev": True,  "example": False, "opaque": False, "axiom": False},
            "theorem": {"def": True,  "theorem": True,  "lemma": True,  "abbrev": True,  "example": False, "opaque": False, "axiom": False},
            "lemma":   {"def": True,  "theorem": True,  "lemma": True,  "abbrev": True,  "example": False, "opaque": False, "axiom": False},
            "abbrev":  {"def": True,  "theorem": False, "lemma": False, "abbrev": True,  "example": False, "opaque": False, "axiom": False},
            "example": {"def": False, "theorem": False, "lemma": False, "abbrev": False, "example": True,  "opaque": False, "axiom": False},
            "opaque":  {"def": False, "theorem": False, "lemma": False, "abbrev": False, "example": False, "opaque": True,  "axiom": False},
            "axiom":   {"def": True,  "theorem": True,  "lemma": True,  "abbrev": True,  "example": False, "opaque": True,  "axiom": True }
        }

        # 2. Check prerequisite definitions
        for name, problem_node in named_problem_nodes.items():
            if name == problem_main_thm.name:
                continue

            if name in named_proof_nodes:
                proof_node = named_proof_nodes[name]
                prob_kind = problem_node.kind if isinstance(problem_node, Definition) else type(problem_node).__name__
                prf_kind = proof_node.kind if isinstance(proof_node, Definition) else type(proof_node).__name__

                # 2.a Check type transition
                if prob_kind in ALLOWED_KIND_TRANSITIONS and prf_kind in ALLOWED_KIND_TRANSITIONS[prob_kind]:
                    if not ALLOWED_KIND_TRANSITIONS[prob_kind][prf_kind]:
                        return False, f"Cheating suspicious: Illegal kind transition in prerequisite '{name}': {prob_kind} -> {prf_kind}"
                elif prob_kind != prf_kind:
                    return False, f"Cheating suspicious: Unknown kind transition in prerequisite '{name}': {prob_kind} -> {prf_kind}"

                # 2.b Check signature
                if get_signature(proof_node) != get_signature(problem_node):
                    return False, f"Cheating suspicious: Signature of prerequisite '{name}' was changed:\n{proof_node.to_source().strip()}\n<-->\n{problem_node.to_source().strip()}"

                # Check body for data definitions
                if prob_kind in ("def", "abbrev", "opaque", "example"):
                    prob_body = problem_node.body if isinstance(problem_node, Definition) else None
                    prf_body = proof_node.body if isinstance(proof_node, Definition) else None
                    if clean_source(prf_body) != clean_source(prob_body):
                        return False, f"Cheating suspicious: Body of prerequisite '{name}' (kind: {prob_kind}) was changed."
        
        # 3. Check new definitions in proof
        for name, proof_node in named_proof_nodes.items():
            if name not in named_problem_nodes:
                is_axiom = isinstance(proof_node, Definition) and proof_node.kind in ("axiom", "opaque")
                is_restricted = any(m.name in ["unsafe", "partial"] for m in getattr(proof_node, 'modifiers', []))
                is_instance = isinstance(proof_node, Instance)
                is_local = any(m.name == "local" for m in getattr(proof_node, 'modifiers', []))
                is_redefinition = name in problem_background_identifiers

                # Check for sorry/admit in the body of new definitions
                has_sorry = False
                if isinstance(proof_node, Definition) and proof_node.body:
                    body_src = clean_source(proof_node.body).lower()
                    if "sorry" in body_src or "admit" in body_src:
                        has_sorry = True
                elif isinstance(proof_node, Instance):
                    if proof_node.type:
                        type_src = clean_source(proof_node.type).lower()
                        if "sorry" in type_src or "admit" in type_src:
                            has_sorry = True
                    if not has_sorry and proof_node.fields:
                        for field in proof_node.fields:
                            # field is (name, binders, value) or (name, value)
                            val = field[-1]
                            val_src = clean_source(val).lower()
                            if "sorry" in val_src or "admit" in val_src:
                                has_sorry = True
                                break

                if is_axiom:
                    return False, f"Cheating suspicious: Proof adds new axiom/opaque definition '{name}'."
                if is_restricted:
                    return False, f"Cheating suspicious: Proof adds new node with restricted modifier '{' '.join(m.name for m in proof_node.modifiers)} {name}'."
                if is_instance and is_local:
                    return False, f"Cheating suspicious: Proof adds new local instance '{name}'."
                if is_redefinition:
                    return False, f"Cheating suspicious: Redefining background concept '{name}' in the problem statement."
                if has_sorry and not allow_sorry:
                    return False, f"Cheating suspicious: Proof adds new definition '{name}' containing 'sorry' or 'admit'."

        # 1. Check target definition in proof
        proof_main_thm = named_proof_nodes.get(problem_main_thm.name)
        if not proof_main_thm:
            return False, f"Cheating suspicious: Missing target definition '{problem_main_thm.name}' in proof."
        
        if not isinstance(proof_main_thm, Definition) or proof_main_thm.kind not in ("def", "theorem", "lemma"):
            return False, f"Cheating suspicious: Target definition '{getattr(proof_main_thm, 'name', '')}' in proof must be 'def', 'theorem', or 'lemma', but got '{proof_main_thm.kind if isinstance(proof_main_thm, Definition) else type(proof_main_thm).__name__}'."

        if get_signature(proof_main_thm) != get_signature(problem_main_thm):
            return False, f"Cheating suspicious: Signature of target definition '{problem_main_thm.name}' was changed:\n{proof_main_thm.to_source().strip()}\n<-->\n{problem_main_thm.to_source().strip()}"

        # All checks passed
        return True, "All checks passed"
