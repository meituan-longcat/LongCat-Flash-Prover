# parser.py
"""
Lean 4 Parser - Simplified version: only captures top-level structure.
Expressions are stored as raw tokens.
"""

from .ast import *
from .lexer import Token, TokenType


class ParserError(Exception):
    pass


class Parser:
    def __init__(self, tokens: List[Token], source: str = None):
        self.tokens = [t for t in tokens if t.type not in (
            TokenType.WHITESPACE, TokenType.INDENT, TokenType.DEDENT
        ) and not (t.type == TokenType.IDENT and not t.value)]
        self.source_lines = source.split("\n") if source else None
        self.pos = 0
        self.current_doc: Optional[str] = None

    def error(self, msg: str) -> None:
        token = self.peek()
        if self.source_lines is None:
            raise ParserError(f"{token.line}:{token.column}:\n{msg}\nWhen processing {token}")
        else:
            tokens_in_line = [token_ for token_ in self.tokens if token.line + 1 >= token_.line >= token.line - 1]
            original_lines = "\n".join([f"{idx+1:>4} {self.source_lines[idx]}" for idx in range(max(0, token.line-1-8), min(len(self.source_lines), token.line-1+8))])
            raise ParserError(f"{token.line}:{token.column}:\n{msg}\nWhen processing {token}\nOriginal context:\n```\n{original_lines}\n```\nTokens around line {token.line}:\n{tokens_in_line}")

    def peek(self, offset: int = 0) -> Token:
        pos = self.pos + offset
        if pos >= len(self.tokens):
            return self.tokens[-1] if self.tokens else Token(TokenType.EOF, '', 0, 0, '')
        return self.tokens[pos]

    def advance(self) -> Token:
        if self.pos >= len(self.tokens):
            return self.peek()
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def expect(self, token_type: TokenType, value: Optional[str] = None) -> Token:
        token = self.peek()
        if token.type != token_type:
            self.error(f"Expected {token_type.name}, got {token.type.name}")
        if value is not None and token.value != value:
            self.error(f"Expected '{value}', got '{token.value}'")
        return self.advance()

    def match(self, *token_types: TokenType) -> bool:
        return self.peek().type in token_types

    def match_keyword(self, keyword: str) -> bool:
        return self.peek().type == TokenType.IDENT and self.peek().value == keyword

    def consume_if(self, token_type: TokenType) -> bool:
        if self.match(token_type):
            self.advance()
            return True
        return False

    def consume_newlines(self) -> None:
        while self.match(TokenType.NEWLINE):
            self.advance()

    def consume_whitespace_and_comments(self) -> None:
        while self.match(TokenType.NEWLINE, TokenType.LINE_COMMENT, TokenType.BLOCK_COMMENT):
            self.advance()

    def expect_ident(self) -> str:
        if self.match(TokenType.IDENT, TokenType.UNDERSCORE):
            val = self.advance().value
            if val == '_' and self.match(TokenType.IDENT):
                val += self.advance().value
            return val
        token = self.peek()
        self.error(f"Expected identifier, got {token.type.name}")
        return ""

    # ------------------------------------------------------------
    # Raw expression parsing (collect tokens until terminator)
    # ------------------------------------------------------------
    # Set of top-level keywords that end a raw expression block
    TOP_LEVEL_KEYWORDS = {
        'def', 'theorem', 'lemma', 'example', 'axiom', 'opaque', 'abbrev',
        'instance', 'class', 'structure', 'inductive', 'coinductive', 'namespace', 'section',
        'end', 'import', 'elab',
        'macro', 'syntax', 'macro_rules', 'initialize', 'add_decl_doc',
        'variable', 'universe', '#align', '#align_import', '#noalign',
        'private', 'protected', 'noncomputable', 'partial', 'mutual',
        'notation', 'infix', 'infixl', 'infixr', 'prefix', 'postfix',
        'open', 'set_option', 'include', 'omit', 'variables', 'universes', 'attribute',
        'register_option'
    }

    def _is_kw_token(self, token: Token) -> bool:
        if token.value in self.TOP_LEVEL_KEYWORDS:
            return True
        if token.raw in self.TOP_LEVEL_KEYWORDS:
            return True
        if token.raw.startswith('#') and len(token.raw) > 1 and token.raw[1].isalpha():
            return True
        return False

    def is_top_level_keyword(self, offset=0):
        token = self.peek(offset)
        if not self._is_kw_token(token):
            return False
        if token.value in ('set_option', 'open'):
            j = offset + 1
            found_in = False
            is_expr_mod = False
            while True:
                next_tok = self.peek(j)
                if next_tok.type.name == 'EOF':
                    break
                if next_tok.value == 'in':
                    found_in = True
                    k = j + 1
                    while self.peek(k).type.name == 'NEWLINE':
                        k += 1
                    after_in = self.peek(k)
                    if after_in.type.name != 'EOF' and not self._is_kw_token(after_in):
                        is_expr_mod = True
                    break
                if self._is_kw_token(next_tok):
                    break
                j += 1
            if is_expr_mod:
                return False
        return True


    def parse_raw_expr_until(self, terminators) -> RawExpr:
        """
        Collect tokens until one of the terminators is encountered
        at depth 0. Returns a RawExpr with the concatenated token strings.
        """
        parts = []
        depth = 0

        if callable(terminators):
            is_term_fn = terminators
        else:
            def is_term_fn(p, d, t):
                if d != 0: return False
                if t.value in terminators or t.raw in terminators:
                    if p._is_kw_token(t):
                        return p.is_top_level_keyword(0)
                    return True
                if p._is_kw_token(t) and 'def' in terminators:
                    return p.is_top_level_keyword(0)
                return False

        while True:
            token = self.peek()
            # Stop if at depth 0 and token.type is a doc comment or block comment
            if depth == 0 and token.type in (TokenType.DOC, TokenType.MOD_DOC, TokenType.BLOCK_COMMENT):
                break
            # Stop if at depth 0 and token.value is a terminator
            if is_term_fn(self, depth, token):
                break
            # Stop at EOF (but we still want to collect what's left)
            if token.type == TokenType.EOF:
                break

            self.advance()

            # Update nesting depth
            if token.type in (TokenType.LPAREN, TokenType.LBRACE, TokenType.LBRACKET) or token.value == '⟨':
                depth += 1
            elif token.type in (TokenType.RPAREN, TokenType.RBRACE, TokenType.RBRACKET) or token.value == '⟩':
                depth -= 1
            # Also handle ⦃ and ⦄ (strict implicit binders)
            if token.value == '⦃':
                depth += 1
            elif token.value == '⦄':
                depth -= 1

            # Append token raw with a space separator
            if parts:
                # Simple heuristic: add space unless previous token ended with a symbol
                # that typically doesn't need a space.  We just always add a space.
                parts.append('')
            parts.append(token.raw)

        return RawExpr(''.join(parts))

    def parse_raw_expr(self, terminators: set) -> RawExpr:
        """Wrapper for parse_raw_expr_until (same)."""
        return self.parse_raw_expr_until(terminators)

    # ------------------------------------------------------------
    # Module and top-level items
    # ------------------------------------------------------------
    def parse(self) -> Module:
        module = Module()
        self.consume_newlines()

        # Header comments
        while self.match(TokenType.LINE_COMMENT, TokenType.BLOCK_COMMENT):
            if self.match(TokenType.LINE_COMMENT):
                token = self.advance()
                module.header_comments.append(Comment(token.value, is_block=False))
            else:
                token = self.advance()
                module.header_comments.append(Comment(token.value, is_block=True))

        if self.match(TokenType.MOD_DOC):
            token = self.advance()
            module.header_comments.append(Comment(token.value, is_mod_doc=True))

        self.consume_newlines()

        # Module-level items
        while not self.match(TokenType.EOF):
            self.consume_newlines()
            if self.match(TokenType.EOF):
                break

            if self.match(TokenType.IMPORT):
                module.body.append(self.parse_import())
                continue

            item = self.parse_module_item()
            if item:
                module.body.append(item)

        return module

    def parse_import(self) -> Import:
        self.expect(TokenType.IMPORT)
        runtime = False
        if self.peek().value == "runtime":
            self.advance()
            runtime = True

        parts = []
        while self.match(TokenType.IDENT):
            parts.append(self.advance().value)
            if self.match(TokenType.DOT):
                self.advance()
            else:
                break

        module = '.'.join(parts)
        return Import(module, runtime)

    def parse_module_item(self) -> Optional[ASTNode]:
        # Comments and docs
        if self.match(TokenType.LINE_COMMENT):
            return Comment(self.advance().value, is_block=False)

        if self.match(TokenType.BLOCK_COMMENT):
            return Comment(self.advance().value, is_block=True)

        if self.match(TokenType.DOC):
            self.current_doc = self.advance().value
            self.consume_newlines()

        if self.match(TokenType.MOD_DOC):
            return Comment(self.advance().value, is_mod_doc=True)

        # Attributes
        attrs = []
        has_at = False
        if self.match(TokenType.LBRACKET):
            attrs = self.parse_attributes()
            self.consume_newlines()
        elif self.match(TokenType.AT) and self.peek(1).type == TokenType.LBRACKET:
            has_at = True
            self.advance()
            attrs = self.parse_attributes()
            self.consume_newlines()

        if self.match(TokenType.EOF):
            return None

        item_start_token = self.peek()
        item_start_col = item_start_token.column

        # Modifiers
        modifiers = []
        while True:
            token = self.peek()
            if token.value in ('private', 'protected', 'noncomputable', 'partial', 'unsafe', 'local', 'scoped', 'global'):
                mod_name = token.value
                self.advance()
                # Check for [namespace] after scoped
                if mod_name == 'scoped' and self.match(TokenType.LBRACKET):
                    self.advance()
                    if self.match(TokenType.IDENT):
                        ns = self.advance().value
                        mod_name = f"scoped [{ns}]"
                    self.expect(TokenType.RBRACKET)
                modifiers.append(Modifier(mod_name))
                self.consume_newlines()
            elif token.value in ('set_option', 'open'):
                j = 1
                found_in = False
                while True:
                    next_tok = self.peek(j)
                    if next_tok.type.name == 'EOF':
                        break
                    if next_tok.value == 'in':
                        found_in = True
                        break
                    if self._is_kw_token(next_tok):
                        break
                    j += 1
                if found_in:
                    if token.value == 'set_option':
                        opt = self.parse_set_option()
                        self.expect(TokenType.IDENT, 'in')
                        modifiers.append(Modifier(f"{opt.to_source()} in"))
                    else:
                        op = self.parse_open()
                        self.expect(TokenType.IDENT, 'in')
                        modifiers.append(Modifier(f"{op.to_source()} in"))
                    self.consume_newlines()
                else:
                    break
            else:
                break

        token = self.peek()

        # Various commands
        if token.type == TokenType.SET_OPTION:
            return self.parse_set_option()
        if token.type == TokenType.OPEN:
            return self.parse_open()
        if token.type in (TokenType.VARIABLE, TokenType.VARIABLES):
            return self.parse_variable()
        if token.type in (TokenType.UNIVERSE, TokenType.UNIVERSES):
            return self.parse_universe()
        if token.type == TokenType.ATTRIBUTE:
            return self.parse_attribute_decl(modifiers)
        if token.type == TokenType.ELAB:
            return self.parse_elab(modifiers)
        if token.type == TokenType.MACRO:
            return self.parse_macro(modifiers)
        if token.type == TokenType.SYNTAX:
            return self.parse_syntax(modifiers)
        if token.type == TokenType.MACRO_RULES:
            return self.parse_macro_rules(modifiers)
        if token.type == TokenType.INITIALIZE:
            return self.parse_initialize()
        if token.type == TokenType.IDENT and token.value == 'register_option':
            return self.parse_register_option()
        if token.type == TokenType.ADD_DECL_DOC:
            return self.parse_add_decl_doc()

        if token.type in (TokenType.INFIX, TokenType.INFIXL, TokenType.INFIXR,
                          TokenType.PREFIX, TokenType.POSTFIX, TokenType.NOTATION):
            return self.parse_notation(token.type, modifiers)

        # Align commands
        if token.type == TokenType.ALIGN:
            return self.parse_align()
        if token.type == TokenType.ALIGN_IMPORT:
            return self.parse_align_import()
        if token.type == TokenType.NOALIGN:
            return self.parse_noalign()

        # Hash commands (#check, #eval, #reduce, #print, etc.)
        if token.type in (TokenType.CHECK, TokenType.EVAL, TokenType.REDUCE, TokenType.PRINT):
            return self.parse_hash_command(token.type)
        if token.type == TokenType.HASH:
            if token.raw == '#exit':
                tokens = []
                while not self.match(TokenType.EOF):
                    tokens.append(self.advance().raw)
                return IgnoredContent(''.join(tokens))
            else:
                # Consume until newline or EOF
                tokens = []
                while not self.match(TokenType.NEWLINE, TokenType.EOF):
                    tokens.append(self.advance().raw)
                return RawExpr(''.join(tokens))

        # Include / Omit commands
        if token.type == TokenType.INCLUDE:
            return self.parse_include()
        if token.type == TokenType.OMIT:
            return self.parse_omit()

        # Namespace / Section / Mutual
        if token.type == TokenType.NAMESPACE:
            return self.parse_namespace()
        if token.type == TokenType.SECTION:
            return self.parse_section(modifiers)
        if token.type == TokenType.IDENT and token.value == "mutual":
            return self.parse_mutual(modifiers)
        if token.type == TokenType.END:
            self.advance()  # Consume the END token
            return None

        # Declarations
        if token.type in (TokenType.DEF, TokenType.THEOREM, TokenType.LEMMA, TokenType.EXAMPLE, TokenType.AXIOM, TokenType.OPAQUE, TokenType.ABBREV):
            return self.parse_definition(attrs, item_start_col, modifiers, kind=token.value, has_at=has_at)
        if token.type == TokenType.INSTANCE:
            return self.parse_instance(attrs, item_start_col, modifiers)
        if token.type == TokenType.CLASS:
            return self.parse_class(attrs, item_start_col, modifiers)
        if token.type == TokenType.STRUCTURE:
            return self.parse_structure(attrs, item_start_col, modifiers, has_at=has_at)
        if token.type == TokenType.INDUCTIVE:
            return self.parse_inductive(attrs, item_start_col, modifiers)

        self.error(f"Unexpected token: {token}")
        return None

    # ------------------------------------------------------------
    # Attribute parsing
    # ------------------------------------------------------------
    def parse_attributes(self) -> List[Attribute]:
        attrs = []
        self.expect(TokenType.LBRACKET)

        while not self.match(TokenType.RBRACKET, TokenType.EOF):
            if self.match(TokenType.IDENT, TokenType.INSTANCE, TokenType.LOCAL):
                attr_name = self.advance().value
            else:
                self.error(f"Expected IDENT or INSTANCE, got {self.peek().type.name}")
            priority = None
            args = []

            while not self.match(TokenType.COMMA, TokenType.RBRACKET, TokenType.EOF):
                if self.peek().value.isdigit():
                    priority = int(self.advance().value)
                else:
                    args.append(self.advance().value)

            attrs.append(Attribute(attr_name, args if args else None, priority))

            if self.match(TokenType.COMMA):
                self.advance()

        self.expect(TokenType.RBRACKET)
        return attrs

    def parse_set_option(self) -> SetOption:
        self.expect(TokenType.SET_OPTION)
        name_parts = []
        if self.match(TokenType.IDENT):
            name_parts.append(self.expect_ident())
            while self.match(TokenType.DOT):
                self.advance()
                if self.match(TokenType.IDENT):
                    name_parts.append(self.expect_ident())
                else:
                    break
        name = '.'.join(name_parts)

        if self.match(TokenType.IDENT):
            val_str = self.advance().value
            if val_str == "true":
                value = True
            elif val_str == "false":
                value = False
            else:
                value = val_str
        elif self.match(TokenType.NAT):
            value = int(self.advance().value)
        else:
            value = self.advance().value

        return SetOption(name, value)

    def parse_open(self) -> Open:
        self.expect(TokenType.OPEN)
        is_scoped = False
        if self.peek().value == "scoped":
            self.advance()
            is_scoped = True

        namespaces = []
        while self.match(TokenType.IDENT):
            name_parts = [self.advance().value]
            while self.match(TokenType.DOT):
                self.advance()
                if self.match(TokenType.IDENT):
                    name_parts.append(self.advance().value)
                else:
                    break
            namespaces.append('.'.join(name_parts))

        explicit = None
        if self.match(TokenType.LPAREN):
            self.advance()
            explicit = []
            while self.match(TokenType.IDENT):
                explicit.append(self.advance().value)
            self.expect(TokenType.RPAREN)

        abbrev = False
        hiding = None
        renaming = None

        if self.peek().value == "abbrev":
            self.advance()
            abbrev = True

        if self.peek().value == "hiding":
            self.advance()
            hiding = []
            while self.match(TokenType.IDENT):
                hiding.append(self.advance().value)

        if self.peek().value == "renaming":
            self.advance()
            renaming = {}
            while self.match(TokenType.IDENT):
                old = self.advance().value
                self.expect(TokenType.ARROW)
                new = self.expect_ident()
                renaming[old] = new

        return Open(namespaces, hiding, renaming, abbrev, is_scoped, explicit)

    def parse_variable(self) -> Variable:
        self.advance()
        binders = self.parse_binders()
        return Variable(binders)

    def parse_universe(self) -> Universe:
        self.advance()
        names = []
        while self.match(TokenType.IDENT):
            names.append(self.advance().value)
        return Universe(names)

    def parse_attribute_decl(self, modifiers: List[Modifier]) -> AttributeDeclaration:
        self.expect(TokenType.ATTRIBUTE)

        # In Lean 4, modifiers can also appear after `attribute`
        while True:
            if self.peek().value in ("local", "global", "scoped"):
                modifiers.append(Modifier(self.advance().value))
            else:
                break

        attrs = self.parse_attributes()
        names = []
        while self.match(TokenType.IDENT):
            name_parts = [self.advance().value]
            while self.match(TokenType.DOT):
                self.advance()
                if self.match(TokenType.IDENT):
                    name_parts.append(self.advance().value)
                else:
                    break
            names.append('.'.join(name_parts))

        return AttributeDeclaration(attrs, names, modifiers)

    # ------------------------------------------------------------
    # Elab / Macro / Syntax / Notation (simplified – body stored as string)
    # ------------------------------------------------------------
    def parse_elab(self, modifiers: List[Modifier]) -> Elab:
        self.expect(TokenType.ELAB)
        head = None
        if self.match(TokenType.IDENT) and self.peek().value in ('tactic', 'command', 'term'):
            head = self.advance().value

        args = []
        while not self.match(TokenType.EOF, TokenType.DEDENT) and not (
            self.peek().type == TokenType.IDENT and self.peek().value == '=>'
        ):
            args.append(self.advance().raw)

        if self.match(TokenType.IDENT) and self.peek().value == '=>':
            self.advance()

        body_tokens = []
        while not self.match(TokenType.EOF, TokenType.NEWLINE, TokenType.DEDENT):
            body_tokens.append(self.advance().raw)

        return Elab(head, args, ''.join(body_tokens) if body_tokens else None, modifiers=modifiers)

    def parse_macro(self, modifiers: List[Modifier]) -> Macro:
        self.expect(TokenType.MACRO)
        head = None
        if self.match(TokenType.IDENT) and self.peek().value in ('tactic', 'command', 'term', 'rules'):
            head = self.advance().value

        args = []
        while not self.match(TokenType.EOF, TokenType.DEDENT) and not (
            self.peek().type == TokenType.IDENT and self.peek().value in ('=>', ':=')
        ):
            args.append(self.advance().raw)

        if self.match(TokenType.IDENT) and self.peek().value in ('=>', ':='):
            self.advance()

        body_tokens = []
        while not self.match(TokenType.EOF, TokenType.NEWLINE, TokenType.DEDENT):
            body_tokens.append(self.advance().raw)

        return Macro(head, args, ''.join(body_tokens) if body_tokens else None, modifiers=modifiers)

    def parse_syntax(self, modifiers: List[Modifier]) -> Syntax:
        self.expect(TokenType.SYNTAX)
        head = None
        if self.match(TokenType.IDENT) and self.peek().value in ('tactic', 'command', 'term', 'cat'):
            head = self.advance().value

        args = []
        precedence = None
        while not self.match(TokenType.EOF, TokenType.DEDENT) and not (
            self.peek().type == TokenType.COLON or
            (self.peek().type == TokenType.IDENT and self.peek().value in (':=', '=>'))
        ):
            token = self.advance()
            if token.type == TokenType.NAT and not args:
                precedence = int(token.value)
            else:
                args.append(token.raw)

        if self.match(TokenType.COLON):
            self.advance()
            category = None
            if self.match(TokenType.IDENT):
                category = self.advance().value
            return Syntax(head, args, precedence, category, modifiers=modifiers)
        elif self.match(TokenType.IDENT) and self.peek().value in (':=', '=>'):
            self.advance()
            body_tokens = []
            while not self.match(TokenType.EOF, TokenType.NEWLINE, TokenType.DEDENT):
                body_tokens.append(self.advance().raw)
            return Syntax(head, args, precedence, body=''.join(body_tokens) if body_tokens else None, modifiers=modifiers)

        return Syntax(head, args, precedence, modifiers=modifiers)

    def parse_notation(self, token_type: TokenType, modifiers: List[Modifier]) -> NotationDecl:
        kind_map = {
            TokenType.INFIX: 'infix',
            TokenType.INFIXL: 'infixl',
            TokenType.INFIXR: 'infixr',
            TokenType.PREFIX: 'prefix',
            TokenType.POSTFIX: 'postfix',
            TokenType.NOTATION: 'notation',
        }
        kind = kind_map.get(token_type, 'notation')
        self.advance()

        precedence = None
        if self.match(TokenType.COLON):
            self.advance()
            if self.match(TokenType.NAT):
                precedence = self.advance().value
            elif self.match(TokenType.IDENT):
                precedence = self.advance().value

        pattern_tokens = []
        while not self.match(TokenType.EOF, TokenType.NEWLINE, TokenType.DEDENT) and not self.match(TokenType.DARROW):
            token = self.advance()
            if token.type == TokenType.STRING:
                pattern_tokens.append(f'"{token.value}"')
            else:
                pattern_tokens.append(token.raw if token.raw else token.value)
        pattern = ''.join(pattern_tokens) if pattern_tokens else None

        body = None
        if self.match(TokenType.DARROW):
            self.advance()
            body_tokens = []
            while not self.match(TokenType.EOF, TokenType.NEWLINE, TokenType.DEDENT):
                if self.match(TokenType.STRING):
                    body_tokens.append(f'"{self.advance().value}"')
                elif self.match(TokenType.IDENT, TokenType.NAT, TokenType.UNDERSCORE):
                    body_tokens.append(self.advance().value)
                else:
                    body_tokens.append(self.advance().value)
            body = ''.join(body_tokens) if body_tokens else None

        return NotationDecl(kind, precedence, pattern, body, modifiers=modifiers)

    def parse_macro_rules(self, modifiers: List[Modifier]) -> MacroRules:
        self.expect(TokenType.MACRO_RULES)
        self.consume_newlines()
        precedence = None
        if self.match(TokenType.NAT):
            precedence = int(self.advance().value)

        args = []
        while not self.match(TokenType.EOF, TokenType.DEDENT, TokenType.BAR, TokenType.DARROW, TokenType.NEWLINE):
            token = self.advance()
            args.append(token.raw)

        rules = []
        self.consume_newlines()
        if self.match(TokenType.DARROW):
            self.advance()
            def is_rule_term(p, d, t):
                if d == 0 and t.type == TokenType.BAR:
                    return True
                if d == 0 and p.is_top_level_keyword(0):
                    return True
                return False
            rule_expr = self.parse_raw_expr_until(is_rule_term)
            rules.append(rule_expr.to_source())

        # Parse multiple rules separated by |
        while True:
            # Skip newlines
            while self.match(TokenType.NEWLINE):
                self.advance()

            # Check for rule pattern starting with |
            if self.match(TokenType.BAR):
                self.advance()  # consume |
                def is_rule_term(p, d, t):
                    if d == 0 and t.type == TokenType.BAR:
                        return True
                    if d == 0 and p.is_top_level_keyword(0):
                        return True
                    return False
                rule_expr = self.parse_raw_expr_until(is_rule_term)
                rules.append(rule_expr.to_source())
            else:
                break


        return MacroRules(precedence, args, rules, modifiers=modifiers)

    def parse_register_option(self) -> RegisterOption:
        self.expect(TokenType.IDENT, 'register_option')

        name_parts = []
        if self.match(TokenType.IDENT):
            name_parts.append(self.expect_ident())
            while self.match(TokenType.DOT):
                self.advance()
                if self.match(TokenType.IDENT):
                    name_parts.append(self.expect_ident())
                else:
                    break
        name = '.'.join(name_parts)

        def is_reg_term(p, d, t):
            if d == 0 and t.type == TokenType.NEWLINE:
                i = 1
                while p.peek(i).type == TokenType.NEWLINE:
                    i += 1
                next_tok = p.peek(i)
                if next_tok.type == TokenType.EOF:
                    return True
                if next_tok.type in (TokenType.DOC, TokenType.MOD_DOC):
                    return True
                if next_tok.type == TokenType.AT and p.peek(i+1).type == TokenType.LBRACKET:
                    return True
                if p._is_kw_token(next_tok):
                    return p.is_top_level_keyword(i)
            if d == 0 and t.value in p.TOP_LEVEL_KEYWORDS:
                return p.is_top_level_keyword(0)
            return False

        body_expr = self.parse_raw_expr_until(is_reg_term)

        doc = self.current_doc
        self.current_doc = None

        # We just store the rest as body for simplicity
        return RegisterOption(name, None, body_expr.to_source() if body_expr else None, doc)

    def parse_initialize(self) -> Initialize:
        self.expect(TokenType.INITIALIZE)

        def is_init_term(p, d, t):
            if d == 0 and t.type == TokenType.NEWLINE:
                i = 1
                while p.peek(i).type == TokenType.NEWLINE:
                    i += 1
                next_tok = p.peek(i)
                if next_tok.type == TokenType.EOF:
                    return True
                if next_tok.type in (TokenType.DOC, TokenType.MOD_DOC):
                    return True
                if next_tok.type == TokenType.AT and p.peek(i+1).type == TokenType.LBRACKET:
                    return True
                if p._is_kw_token(next_tok):
                    return p.is_top_level_keyword(i)
            if d == 0 and t.value in p.TOP_LEVEL_KEYWORDS:
                return p.is_top_level_keyword(0)
            return False

        body_expr = self.parse_raw_expr_until(is_init_term)

        return Initialize(None, None, None, body_expr.to_source() if body_expr else None)

    def parse_add_decl_doc(self) -> AddDeclDoc:
        self.expect(TokenType.ADD_DECL_DOC)
        name_parts = []
        while self.match(TokenType.IDENT):
            name_parts.append(self.advance().value)
            if self.match(TokenType.DOT):
                self.advance()
            else:
                break
        return AddDeclDoc('.'.join(name_parts))

    def parse_align(self) -> Align:
        self.expect(TokenType.ALIGN)

        old_parts = []
        if self.match(TokenType.IDENT):
            old_parts.append(self.advance().value)
            while self.match(TokenType.DOT):
                self.advance()
                if self.match(TokenType.IDENT):
                    old_parts.append(self.advance().value)
                else:
                    break
        old_name = '.'.join(old_parts) if old_parts else self.advance().value

        new_parts = []
        if self.match(TokenType.IDENT):
            new_parts.append(self.advance().value)
            while self.match(TokenType.DOT):
                self.advance()
                if self.match(TokenType.IDENT):
                    new_parts.append(self.advance().value)
                else:
                    break
        new_name = '.'.join(new_parts) if new_parts else self.advance().value

        return Align(old_name, new_name)

    def parse_align_import(self) -> AlignImport:
        self.expect(TokenType.ALIGN_IMPORT)
        parts = []
        while self.match(TokenType.IDENT):
            parts.append(self.advance().value)
            if self.match(TokenType.DOT):
                self.advance()
            else:
                break
        module = '.'.join(parts)
        source = ""
        if self.peek().value == "from":
            self.advance()
            if self.match(TokenType.STRING):
                source = self.advance().value
                if self.match(TokenType.AT):
                    self.advance()
                    if self.match(TokenType.STRING):
                        source += "@" + self.advance().value
        return AlignImport(module, source)

    def parse_noalign(self) -> NoAlign:
        self.expect(TokenType.NOALIGN)
        name = self.advance().value
        return NoAlign(name)

    def parse_include(self) -> Include:
        self.expect(TokenType.INCLUDE)
        names = []
        while self.match(TokenType.IDENT):
            names.append(self.advance().value)
        return Include(names)

    def parse_omit(self) -> Omit:
        self.expect(TokenType.OMIT)
        names = []
        while self.match(TokenType.IDENT):
            names.append(self.advance().value)
        return Omit(names)

    def parse_hash_command(self, token_type: TokenType) -> HashCommand:
        """Parse #check, #eval, #reduce, #print commands."""
        token = self.advance()
        cmd = token.value
        tokens = []
        while not self.match(TokenType.NEWLINE, TokenType.EOF):
            tokens.append(self.advance())
        if tokens:
            # Strip leading space from first token and join
            expr_str = ''.join(t.raw for t in tokens).lstrip()
            expr = RawExpr(expr_str)
        else:
            expr = None
        return HashCommand(cmd, expr)

    def parse_namespace(self) -> Namespace:
        self.expect(TokenType.NAMESPACE)
        name_parts = [self.expect_ident()]
        while self.match(TokenType.DOT):
            self.advance()
            name_parts.append(self.expect_ident())
        name = '.'.join(name_parts)

        body = []
        while not self.match(TokenType.END, TokenType.EOF):
            self.consume_newlines()
            if self.match(TokenType.END, TokenType.EOF):
                break
            item = self.parse_module_item()
            if item:
                body.append(item)

        # Handle optional END - namespaces can be implicitly closed at EOF
        if self.match(TokenType.END):
            self.expect(TokenType.END)
            if self.match(TokenType.IDENT) and self.peek().value == name:
                self.advance()
            has_end = True
        else:
            self.expect(TokenType.EOF)
            has_end = False

        return Namespace(name, body, has_end=has_end)

    def parse_section(self, modifiers: List[Modifier]) -> Section:
        self.expect(TokenType.SECTION)
        name = None
        if self.match(TokenType.IDENT):
            name = self.advance().value

        body = []
        while not self.match(TokenType.END, TokenType.EOF):
            self.consume_newlines()
            if self.match(TokenType.END, TokenType.EOF):
                break
            item = self.parse_module_item()
            if item:
                body.append(item)

        # Handle optional END - sections can be implicitly closed at EOF
        if self.match(TokenType.END):
            self.expect(TokenType.END)
            if name and self.match(TokenType.IDENT) and self.peek().value == name:
                self.advance()
            has_end = True
        else:
            self.expect(TokenType.EOF)
            has_end = False

        return Section(name, body, modifiers=modifiers, has_end=has_end)

    def parse_mutual(self, modifiers: List[Modifier]) -> Mutual:
        self.expect(TokenType.IDENT, "mutual")

        body = []
        while not self.match(TokenType.END, TokenType.EOF):
            self.consume_newlines()
            if self.match(TokenType.END, TokenType.EOF):
                break
            item = self.parse_module_item()
            if item:
                body.append(item)

        if self.match(TokenType.END):
            self.expect(TokenType.END)

        return Mutual(body, modifiers=modifiers)

    # ------------------------------------------------------------
    # Binder parsing (preserved, but types are RawExpr)
    # ------------------------------------------------------------
    def parse_binders(self) -> List[Binder]:
        binders = []
        while True:
            self.consume_newlines()
            if (self.match(TokenType.LPAREN, TokenType.LBRACE, TokenType.LBRACKET) or
                (self.match(TokenType.IDENT) and self.peek().value == '⦃')):
                binder = self.parse_binder()
                if binder:
                    binders.append(binder)
            else:
                break
        return binders

    def parse_binder(self) -> Optional[Binder]:
        if self.match(TokenType.LPAREN):
            return self.parse_explicit_binder()
        elif self.match(TokenType.LBRACE):
            return self.parse_implicit_binder()
        elif self.match(TokenType.LBRACKET):
            return self.parse_inst_implicit_binder()
        elif self.match(TokenType.IDENT) and self.peek().value == '⦃':
            return self.parse_strict_implicit_binder()
        return None

    def parse_explicit_binder(self) -> Binder:
        self.expect(TokenType.LPAREN)
        names = []
        while self.match(TokenType.IDENT, TokenType.UNDERSCORE):
            names.append(self.advance().value)

        type_expr = None
        default_value = None

        if self.match(TokenType.COLON):
            self.advance()
            def is_type_end(p, d, t):
                return d == 0 and (t.type == TokenType.RPAREN or t.type == TokenType.COLONEQ)
            type_expr = self.parse_raw_expr_until(is_type_end)
            # Type* syntax is captured as part of raw expr, no special handling needed

        if self.match(TokenType.COLONEQ):
            self.advance()
            def is_default_end(p, d, t):
                return d == 0 and t.type == TokenType.RPAREN
            default_value = self.parse_raw_expr_until(is_default_end)

        self.expect(TokenType.RPAREN)

        return Binder(names, type_expr, default_value=default_value)

    def parse_implicit_binder(self) -> Binder:
        self.expect(TokenType.LBRACE)
        names = []
        while self.match(TokenType.IDENT, TokenType.UNDERSCORE):
            names.append(self.advance().value)

        type_expr = None
        default_value = None
        if self.match(TokenType.COLON):
            self.advance()
            def is_type_end(p, d, t):
                return d == 0 and (t.type == TokenType.RBRACE or t.type == TokenType.COLONEQ)
            type_expr = self.parse_raw_expr_until(is_type_end)

        if self.match(TokenType.COLONEQ):
            self.advance()
            def is_default_end(p, d, t):
                return d == 0 and t.type == TokenType.RBRACE
            default_value = self.parse_raw_expr_until(is_default_end)

        self.expect(TokenType.RBRACE)

        return Binder(names, type_expr, default_value=default_value, is_implicit=True)

    def parse_strict_implicit_binder(self) -> Binder:
        self.expect(TokenType.IDENT)  # ⦃
        names = []
        while self.match(TokenType.IDENT, TokenType.UNDERSCORE):
            names.append(self.advance().value)

        type_expr = None
        default_value = None
        if self.match(TokenType.COLON):
            self.advance()
            def is_type_end(p, d, t):
                return d == 0 and (t.value == '⦄' or t.type == TokenType.COLONEQ)
            type_expr = self.parse_raw_expr_until(is_type_end)

        if self.match(TokenType.COLONEQ):
            self.advance()
            def is_default_end(p, d, t):
                return d == 0 and t.value == '⦄'
            default_value = self.parse_raw_expr_until(is_default_end)

        self.expect(TokenType.IDENT)  # ⦄

        return Binder(names, type_expr, default_value=default_value, is_strict_implicit=True)

    def parse_inst_implicit_binder(self) -> Binder:
        self.expect(TokenType.LBRACKET)

        if self.match(TokenType.IDENT):
            next_tok = self.peek(1)
            if next_tok.type == TokenType.COLON:
                name = self.advance().value
                self.advance()
                def is_type_end(p, d, t):
                    return d == 0 and (t.type == TokenType.RBRACKET or t.type == TokenType.COLONEQ)
                type_expr = self.parse_raw_expr_until(is_type_end)

                default_value = None
                if self.match(TokenType.COLONEQ):
                    self.advance()
                    def is_default_end(p, d, t):
                        return d == 0 and t.type == TokenType.RBRACKET
                    default_value = self.parse_raw_expr_until(is_default_end)

                self.expect(TokenType.RBRACKET)
                return Binder([name], type_expr, default_value=default_value, is_inst_implicit=True)

        def is_type_end2(p, d, t):
            return d == 0 and (t.type == TokenType.RBRACKET or t.type == TokenType.COLONEQ)
        type_expr = self.parse_raw_expr_until(is_type_end2)

        default_value = None
        if self.match(TokenType.COLONEQ):
            self.advance()
            def is_default_end2(p, d, t):
                return d == 0 and t.type == TokenType.RBRACKET
            default_value = self.parse_raw_expr_until(is_default_end2)

        self.expect(TokenType.RBRACKET)
        return Binder(["_"], type_expr, default_value=default_value, is_inst_implicit=True)

    # ------------------------------------------------------------
    # Top-level declaration parsers
    # ------------------------------------------------------------
    def parse_definition(self, attrs: List[Attribute], item_start_col: int, modifiers: List[Modifier], kind: str = "def", has_at: bool = False) -> Definition:
        kw_token = self.peek()
        self.advance()  # keyword
        kw_col = item_start_col

        name_parts = []
        if self.match(TokenType.IDENT):
            name_parts.append(self.expect_ident())
            while self.match(TokenType.DOT):
                self.advance()
                if self.match(TokenType.IDENT):
                    name_parts.append(self.expect_ident())
                else:
                    break
        name = '.'.join(name_parts)

        while self.match(TokenType.NEWLINE):
            self.advance()

        # Binders
        binders = []
        while True:
            self.consume_whitespace_and_comments()
            if (self.match(TokenType.LPAREN, TokenType.LBRACE, TokenType.LBRACKET) or
               (self.match(TokenType.IDENT) and self.peek().value == '⦃')):
                binders.extend(self.parse_binders())
            else:
                break

        self.consume_whitespace_and_comments()

        # Type annotation
        type_expr = None
        if self.match(TokenType.COLON):
            self.advance()
            if kind in ("axiom", "opaque"):
                def is_axiom_type_term(p, d, t):
                    if d != 0:
                        return False
                    if p.is_top_level_keyword(0):
                        return True
                    if t.type == TokenType.NEWLINE:
                        i = 1
                        while p.peek(i).type == TokenType.NEWLINE:
                            i += 1
                        next_tok = p.peek(i)
                        if next_tok.type == TokenType.EOF:
                            return True
                        if next_tok.type in (TokenType.DOC, TokenType.MOD_DOC):
                            return True
                        if next_tok.type == TokenType.AT and p.peek(i+1).type == TokenType.LBRACKET:
                            return True
                        if p.is_top_level_keyword(i):
                            return True
                    return False
                type_expr = self.parse_raw_expr_until(is_axiom_type_term)
            else:
                # Keep `|` as a terminator for equation-style declarations, but
                # allow `match ... with | ...` to remain inside type expressions.
                pending_lets = 0
                last_token_was_coloneq = False
                def is_def_type_term(p, d, t):
                    if d != 0:
                        return False
                    nonlocal pending_lets, last_token_was_coloneq

                    if t.type.name == 'NEWLINE':
                        pass
                    elif t.value == 'let':
                        pending_lets += 1
                        last_token_was_coloneq = False
                    elif t.value == ':=' and pending_lets > 0:
                        pending_lets -= 1
                        last_token_was_coloneq = True
                        return False
                    elif t.value == 'by' and last_token_was_coloneq:
                        last_token_was_coloneq = False
                        return False
                    else:
                        last_token_was_coloneq = False

                    if (t.value in {':=', 'by', 'where', 'with', '|'} and pending_lets == 0):
                        return True
                    if p.is_top_level_keyword(0):
                        return True
                    if t.type == TokenType.NEWLINE:
                        i = 1
                        while p.peek(i).type == TokenType.NEWLINE:
                            i += 1
                        next_tok = p.peek(i)
                        if next_tok.type == TokenType.EOF:
                            return True
                        if next_tok.type in (TokenType.DOC, TokenType.MOD_DOC):
                            return True
                        if next_tok.type == TokenType.AT and p.peek(i+1).type == TokenType.LBRACKET:
                            return True
                        if p.is_top_level_keyword(i):
                            return True
                    return False
                type_expr = self.parse_raw_expr_until(is_def_type_term)
                if self.match(TokenType.WITH):
                    pending_lets_with = 0
                    last_token_was_coloneq_with = False
                    def is_with_term(p, d, t):
                        if d != 0:
                            return False
                        nonlocal pending_lets_with, last_token_was_coloneq_with

                        if t.type.name == 'NEWLINE':
                            pass
                        elif t.value == 'let':
                            pending_lets_with += 1
                            last_token_was_coloneq_with = False
                        elif t.value == ':=' and pending_lets_with > 0:
                            pending_lets_with -= 1
                            last_token_was_coloneq_with = True
                            return False
                        elif t.value == 'by' and last_token_was_coloneq_with:
                            last_token_was_coloneq_with = False
                            return False
                        else:
                            last_token_was_coloneq_with = False

                        if (t.value in {':=', 'by', 'where'} and pending_lets_with == 0) or p.is_top_level_keyword(0):
                            return True
                        if t.type == TokenType.NEWLINE:
                            i = 1
                            while p.peek(i).type == TokenType.NEWLINE:
                                i += 1
                            next_tok = p.peek(i)
                            if next_tok.type == TokenType.EOF:
                                return True
                            if next_tok.type in (TokenType.DOC, TokenType.MOD_DOC):
                                return True
                            if next_tok.type == TokenType.AT and p.peek(i+1).type == TokenType.LBRACKET:
                                return True
                            if next_tok.value in ('variables', 'universes'):
                                return True
                        return False
                    match_tail = self.parse_raw_expr_until(is_with_term)
                    if type_expr and match_tail:
                        type_expr = RawExpr(f"{type_expr.to_source()} {match_tail.to_source()}")
                    else:
                        type_expr = match_tail

        self.consume_whitespace_and_comments()

        # Body
        body_expr = None
        has_coloneq = False
        if kind != "axiom":
            # Check for :=, by, or | (pattern matching start)
            if (self.match(TokenType.COLONEQ) or
                self.match(TokenType.BY) or
                self.match(TokenType.BAR) or
                self.match(TokenType.WHERE) or
                (self.match(TokenType.IDENT) and self.peek().value == 'where')):
                if self.match(TokenType.COLONEQ):
                    self.advance()  # consume :=
                    has_coloneq = True
                # For `by`, `|`, and `where`, we do NOT consume them – they will be part of the raw expr.
                def is_body_term(p, d, t):
                    if d != 0:
                        return False
                    if p.is_top_level_keyword(0):
                        return True
                    # Handle new definition after modifier like 'unsafe def', 'partial def', etc.
                    if t.value in ('unsafe', 'partial', 'mutual'):
                        next_i = 1
                        while p.peek(next_i).type == TokenType.NEWLINE:
                            next_i += 1
                        next_tok = p.peek(next_i)
                        if next_tok.type in (TokenType.DEF, TokenType.THEOREM, TokenType.LEMMA,
                                           TokenType.EXAMPLE, TokenType.AXIOM, TokenType.OPAQUE,
                                           TokenType.ABBREV, TokenType.INSTANCE):
                            return True
                    if t.type == TokenType.NEWLINE:
                        i = 1
                        while p.peek(i).type == TokenType.NEWLINE:
                            i += 1
                        next_tok = p.peek(i)
                        if next_tok.type == TokenType.EOF:
                            return True
                        if next_tok.type in (TokenType.DOC, TokenType.MOD_DOC):
                            return True
                        if next_tok.type == TokenType.AT and p.peek(i+1).type == TokenType.LBRACKET:
                            return True
                        if p.is_top_level_keyword(i):
                            return True
                    return False
                body_expr = self.parse_raw_expr_until(is_body_term)

        doc = self.current_doc
        self.current_doc = None

        return Definition(
            name=name,
            attributes=attrs,
            doc=doc,
            binders=binders,
            type=type_expr,
            body=body_expr,
            kind=kind,
            modifiers=modifiers,
            has_at=has_at,
            has_coloneq=has_coloneq
        )

    def parse_instance(self, attrs: List[Attribute], item_start_col: int, modifiers: List[Modifier]) -> Instance:
        self.expect(TokenType.INSTANCE)

        priority = None
        if self.match(TokenType.NAT):
            priority = self.advance().value
        elif self.match(TokenType.LPAREN) and self.peek(1).value == 'priority':
            self.advance() # (
            self.advance() # priority
            self.expect(TokenType.COLONEQ)
            val = self.advance().value
            self.expect(TokenType.RPAREN)
            priority = f"(priority := {val})" 

        name_parts = []
        if self.match(TokenType.IDENT):
            name_parts.append(self.expect_ident())
            while self.match(TokenType.DOT):
                self.advance()
                if self.match(TokenType.IDENT):
                    name_parts.append(self.expect_ident())
                else:
                    break
        name = '.'.join(name_parts)

        while self.match(TokenType.NEWLINE):
            self.advance()

        binders = []
        while (self.match(TokenType.LPAREN, TokenType.LBRACE, TokenType.LBRACKET) or
               (self.match(TokenType.IDENT) and self.peek().value == '⦃')):
            binders.extend(self.parse_binders())
            while self.match(TokenType.NEWLINE):
                self.advance()

        if self.match(TokenType.COLON):
            self.advance()
            type_expr = self.parse_raw_expr_until({'where'} | self.TOP_LEVEL_KEYWORDS)
        else:
            type_expr = None

        while self.match(TokenType.NEWLINE):
            self.advance()

        fields = []
        if self.match(TokenType.WHERE) or (self.match(TokenType.IDENT) and self.peek().value == "where"):
            self.advance()
            while self.match(TokenType.NEWLINE):
                self.advance()
            while self.match(TokenType.IDENT, TokenType.BAR, TokenType.DOC, TokenType.NEWLINE):
                if self.match(TokenType.NEWLINE):
                    self.advance()
                    continue
                if self.match(TokenType.DOC):
                    lookahead_pos = 1
                    while self.peek(lookahead_pos).type == TokenType.NEWLINE:
                        lookahead_pos += 1
                    next_tok = self.peek(lookahead_pos)
                    if next_tok.type in (TokenType.DEF, TokenType.THEOREM, TokenType.LEMMA, TokenType.EXAMPLE, TokenType.AXIOM, TokenType.OPAQUE, TokenType.ABBREV, TokenType.INSTANCE, TokenType.CLASS, TokenType.STRUCTURE, TokenType.INDUCTIVE, TokenType.NAMESPACE, TokenType.SECTION, TokenType.END, TokenType.IMPORT, TokenType.OPEN, TokenType.SET_OPTION, TokenType.ATTRIBUTE, TokenType.LOCAL, TokenType.ELAB, TokenType.MACRO, TokenType.SYNTAX, TokenType.MACRO_RULES, TokenType.INITIALIZE, TokenType.ADD_DECL_DOC, TokenType.VARIABLE, TokenType.UNIVERSE, TokenType.ALIGN, TokenType.ALIGN_IMPORT, TokenType.NOALIGN):
                        break
                    if next_tok.type == TokenType.IDENT and self.is_top_level_keyword(lookahead_pos):
                        break
                    doc = self.advance().value
                    continue

                if self.match(TokenType.IDENT) and self.is_top_level_keyword(0):
                    break

                start_token = self.peek()
                if self.match(TokenType.BAR):
                    start_token = self.advance()
                field_name = self.expect(TokenType.IDENT).value
                field_col = start_token.column

                field_binders = []
                while (self.match(TokenType.LPAREN, TokenType.LBRACE, TokenType.LBRACKET) or
                       (self.match(TokenType.IDENT) and self.peek().value == '⦃') or
                       (self.match(TokenType.IDENT) and not self.is_top_level_keyword(0) and self.peek().value != ':=')):
                    if self.match(TokenType.IDENT) and self.peek().value not in ('⦃', ':=') and not self.is_top_level_keyword(0):
                        # Simple identifier binder
                        field_binders.append(Binder([self.advance().value], None, has_parens=False))
                    else:
                        field_binders.extend(self.parse_binders())

                self.expect(TokenType.COLONEQ)

                def is_inst_field_term(p, d, t):
                    if d == 0 and p.is_top_level_keyword(0):
                        return True
                    # Handle @ prefix for explicit applications
                    if d == 0 and t.type == TokenType.AT:
                        return True
                    if d == 0 and t.type == TokenType.NEWLINE:
                        i = 1
                        while p.peek(i).type == TokenType.NEWLINE:
                            i += 1
                        next_tok = p.peek(i)
                        if next_tok.type == TokenType.EOF:
                            return True
                        if next_tok.column <= field_col:
                            return True
                        if p.is_top_level_keyword(i):
                            return True
                    return False

                field_value = self.parse_raw_expr_until(is_inst_field_term)
                fields.append((field_name, field_binders, field_value))

        doc = self.current_doc
        self.current_doc = None

        return Instance(
            name=name,
            attributes=attrs,
            doc=doc,
            binders=binders,
            type=type_expr,
            fields=fields,
            is_priority=priority,
            modifiers=modifiers
        )

    def parse_class(self, attrs: List[Attribute], item_start_col: int, modifiers: List[Modifier]) -> Class:
        self.expect(TokenType.CLASS)
        name = self.expect_ident()

        while self.match(TokenType.NEWLINE):
            self.advance()

        binders = []
        while (self.match(TokenType.LPAREN, TokenType.LBRACE, TokenType.LBRACKET) or
               (self.match(TokenType.IDENT) and self.peek().value == '⦃')):
            binders.extend(self.parse_binders())
            while self.match(TokenType.NEWLINE):
                self.advance()

        type_expr = None
        if self.match(TokenType.COLON):
            self.advance()
            type_expr = self.parse_raw_expr_until({'extends', 'where'} | self.TOP_LEVEL_KEYWORDS)

        extends = []
        if self.peek().value == "extends":
            self.advance()
            while True:
                extends.append(self.parse_raw_expr_until({','} | {'where'} | self.TOP_LEVEL_KEYWORDS))
                while self.match(TokenType.NEWLINE):
                    self.advance()
                if self.match(TokenType.COMMA):
                    self.advance()
                else:
                    break

        has_where = False
        if self.match(TokenType.WHERE):
            self.advance()
            has_where = True
        elif self.match(TokenType.IDENT) and self.peek().value == "where":
            self.advance()
            has_where = True

        while self.match(TokenType.NEWLINE):
            self.advance()

        fields = []
        while (self.match(TokenType.IDENT, TokenType.DOC, TokenType.LINE_COMMENT, TokenType.NEWLINE) or
               self.match(TokenType.LBRACKET)):
            while self.match(TokenType.NEWLINE):
                self.advance()

            if self.match(TokenType.EOF):
                break

            if self.peek().type in (TokenType.DEF, TokenType.THEOREM, TokenType.LEMMA, TokenType.EXAMPLE, TokenType.AXIOM, TokenType.OPAQUE, TokenType.ABBREV, TokenType.INSTANCE, TokenType.CLASS, TokenType.STRUCTURE, TokenType.INDUCTIVE, TokenType.NAMESPACE, TokenType.SECTION, TokenType.END, TokenType.IMPORT, TokenType.OPEN, TokenType.SET_OPTION, TokenType.ATTRIBUTE, TokenType.LOCAL, TokenType.ELAB, TokenType.MACRO, TokenType.SYNTAX, TokenType.MACRO_RULES, TokenType.INITIALIZE, TokenType.ADD_DECL_DOC, TokenType.VARIABLE, TokenType.UNIVERSE, TokenType.ALIGN, TokenType.ALIGN_IMPORT, TokenType.NOALIGN):
                break

            if self.match(TokenType.IDENT) and self.is_top_level_keyword(0):
                break

            if self.match(TokenType.IDENT) and self.peek().value == 'deriving':
                break

            if self.match(TokenType.LINE_COMMENT):
                self.advance()
                continue

            doc = None
            if self.match(TokenType.DOC):
                lookahead_pos = 1
                while self.peek(lookahead_pos).type == TokenType.NEWLINE:
                    lookahead_pos += 1
                next_tok = self.peek(lookahead_pos)
                if next_tok.type in (TokenType.DEF, TokenType.THEOREM, TokenType.LEMMA, TokenType.EXAMPLE, TokenType.AXIOM, TokenType.OPAQUE, TokenType.ABBREV, TokenType.INSTANCE, TokenType.CLASS, TokenType.STRUCTURE, TokenType.INDUCTIVE, TokenType.NAMESPACE, TokenType.SECTION, TokenType.END, TokenType.IMPORT, TokenType.OPEN, TokenType.SET_OPTION, TokenType.ATTRIBUTE, TokenType.LOCAL, TokenType.ELAB, TokenType.MACRO, TokenType.SYNTAX, TokenType.MACRO_RULES, TokenType.INITIALIZE, TokenType.ADD_DECL_DOC, TokenType.VARIABLE, TokenType.UNIVERSE, TokenType.ALIGN, TokenType.ALIGN_IMPORT, TokenType.NOALIGN):
                    break
                if next_tok.type == TokenType.IDENT and self.is_top_level_keyword(lookahead_pos):
                    break
                doc = self.advance().value
                while self.match(TokenType.NEWLINE):
                    self.advance()

            if self.match(TokenType.LBRACKET):
                binder = self.parse_inst_implicit_binder()
                field_name = binder.names[0] if binder.names else "_"
                field_type = binder.type if binder.type else RawExpr("_")
                fields.append(ClassField(field_name, field_type, doc))
                continue

            start_token = self.peek()
            field_name = self.expect(TokenType.IDENT).value
            field_col = start_token.column

            # Optional field binders (e.g., (x : Nat) → ...) – they become part of the raw type
            field_binders = []
            while (self.match(TokenType.LPAREN, TokenType.LBRACE, TokenType.LBRACKET) or
                   (self.match(TokenType.IDENT) and self.peek().value == '⦃')):
                field_binders.extend(self.parse_binders())

            self.expect(TokenType.COLON)

            def is_class_field_term(p, d, t):
                if d == 0 and p.is_top_level_keyword(0):
                    return True
                if d == 0 and t.type == TokenType.NEWLINE:
                    i = 1
                    while p.peek(i).type == TokenType.NEWLINE:
                        i += 1
                    next_tok = p.peek(i)
                    if next_tok.type == TokenType.EOF:
                        return True
                    if next_tok.column <= field_col:
                        return True
                return False

            field_type = self.parse_raw_expr_until(is_class_field_term)
            # If field_binders, we could wrap in Pi, but for raw expr we keep as is
            # (the binders are already part of the raw string if we collected them before :)
            # Actually, we haven't collected them into field_type; we need to combine them.
            # For simplicity, we treat field_binders as separate, but we'll not wrap;
            # we'll just store the raw type after colon, ignoring field binders.
            # This may lose some information, but for comparison of type signatures,
            # field binders are part of the type anyway.
            fields.append(ClassField(field_name, field_type, binders=field_binders, doc=doc))

        doc = self.current_doc
        self.current_doc = None

        return Class(
            name=name,
            attributes=attrs,
            doc=doc,
            binders=binders,
            type=type_expr,
            extends=extends,
            fields=fields,
            has_where=has_where,
            modifiers=modifiers
        )

    def parse_structure(self, attrs: List[Attribute], item_start_col: int, modifiers: List[Modifier], has_at: bool = False) -> Structure:
        self.expect(TokenType.STRUCTURE)
        name = self.expect_ident()

        while self.match(TokenType.NEWLINE):
            self.advance()

        binders = []
        while (self.match(TokenType.LPAREN, TokenType.LBRACE, TokenType.LBRACKET) or
               (self.match(TokenType.IDENT) and self.peek().value == '⦃')):
            binders.extend(self.parse_binders())
            while self.match(TokenType.NEWLINE):
                self.advance()

        type_expr = None
        if self.match(TokenType.COLON):
            self.advance()
            type_expr = self.parse_raw_expr_until({'extends', 'where'} | self.TOP_LEVEL_KEYWORDS)

        extends = []
        if self.peek().value == "extends":
            self.advance()
            while True:
                extends.append(self.parse_raw_expr_until({','} | {'where'}))
                if self.match(TokenType.COMMA):
                    self.advance()
                else:
                    break

        has_where = False
        if self.match(TokenType.WHERE):
            self.advance()
            has_where = True
        elif self.match(TokenType.IDENT) and self.peek().value == "where":
            self.advance()
            has_where = True

        while self.match(TokenType.NEWLINE):
            self.advance()

        ctor_name = None
        if self.match(TokenType.IDENT) and self.peek(1).value == "::":
            ctor_name = self.advance().value
            self.advance()  # ::

        fields = []
        while True:
            while self.match(TokenType.NEWLINE):
                self.advance()

            if self.match(TokenType.LPAREN, TokenType.LBRACE, TokenType.LBRACKET) or (self.match(TokenType.IDENT) and self.peek().value == '⦃'):
                field_binders = self.parse_binders()
                for b in field_binders:
                    for binder_name in b.names:
                        fields.append(StructureField(name=binder_name, type=b.type, default=b.default_value, is_binder=True))
                continue

            if not (self.match(TokenType.IDENT, TokenType.DOC, TokenType.LINE_COMMENT, TokenType.BAR) or
                    (self.match(TokenType.IDENT) and self.peek().value in ('mk', '::'))):
                break

            if self.peek().type in (TokenType.DEF, TokenType.THEOREM, TokenType.LEMMA, TokenType.EXAMPLE, TokenType.AXIOM, TokenType.OPAQUE, TokenType.ABBREV, TokenType.INSTANCE, TokenType.CLASS, TokenType.STRUCTURE, TokenType.INDUCTIVE, TokenType.NAMESPACE, TokenType.SECTION, TokenType.END, TokenType.IMPORT, TokenType.OPEN, TokenType.SET_OPTION, TokenType.ATTRIBUTE, TokenType.LOCAL, TokenType.ELAB, TokenType.MACRO, TokenType.SYNTAX, TokenType.MACRO_RULES, TokenType.INITIALIZE, TokenType.ADD_DECL_DOC, TokenType.VARIABLE, TokenType.UNIVERSE, TokenType.ALIGN, TokenType.ALIGN_IMPORT, TokenType.NOALIGN):
                break

            if self.match(TokenType.IDENT) and self.is_top_level_keyword(0):
                break

            if self.match(TokenType.IDENT) and self.peek().value == 'deriving':
                break

            if self.match(TokenType.UNDERSCORE):
                break

            doc = None
            if self.match(TokenType.DOC):
                lookahead_pos = 1
                while self.peek(lookahead_pos).type == TokenType.NEWLINE:
                    lookahead_pos += 1
                next_tok = self.peek(lookahead_pos)
                if next_tok.type in (TokenType.DEF, TokenType.THEOREM, TokenType.LEMMA, TokenType.EXAMPLE, TokenType.AXIOM, TokenType.OPAQUE, TokenType.ABBREV, TokenType.INSTANCE, TokenType.CLASS, TokenType.STRUCTURE, TokenType.INDUCTIVE, TokenType.NAMESPACE, TokenType.SECTION, TokenType.END, TokenType.IMPORT, TokenType.OPEN, TokenType.SET_OPTION, TokenType.ATTRIBUTE, TokenType.LOCAL, TokenType.ELAB, TokenType.MACRO, TokenType.SYNTAX, TokenType.MACRO_RULES, TokenType.INITIALIZE, TokenType.ADD_DECL_DOC, TokenType.VARIABLE, TokenType.UNIVERSE, TokenType.ALIGN, TokenType.ALIGN_IMPORT, TokenType.NOALIGN):
                    break
                if next_tok.type == TokenType.IDENT and self.is_top_level_keyword(lookahead_pos):
                    break
                doc = self.advance().value
                while self.match(TokenType.NEWLINE):
                    self.advance()

            start_token = self.peek()
            if self.match(TokenType.IDENT) and self.peek().value == 'protected':
                self.advance()

            field_name = self.expect(TokenType.IDENT).value
            field_col = start_token.column

            if field_name in ('mk', '::'):
                continue

            # Optional field binders (e.g., (x : G) → ...) – we'll ignore for raw type
            # Also handle implicit parameters without brackets like `x y : Type`
            field_binders = []
            while (self.match(TokenType.LPAREN, TokenType.LBRACE, TokenType.LBRACKET) or
                   (self.match(TokenType.IDENT) and self.peek().value == '⦃')):
                field_binders.extend(self.parse_binders())

            # Handle implicit parameters without brackets (e.g., `x y : Type`)
            # These are identifiers followed by another identifier or underscore before colon
            implicit_names = []
            while True:
                # Check if current token is an identifier or underscore
                if not (self.match(TokenType.IDENT) or self.match(TokenType.UNDERSCORE)):
                    break
                # Look ahead to see what's next
                next_token = self.peek(1)
                # If next is colon, this is the type annotation - add current and consume it
                if next_token.type == TokenType.COLON:
                    # Add current token as implicit param name
                    implicit_names.append(self.advance().value)
                    break
                # If next is another identifier or underscore, it's another implicit param
                if next_token.type in (TokenType.IDENT, TokenType.UNDERSCORE):
                    implicit_names.append(self.advance().value)
                else:
                    break

            field_type = None
            if self.match(TokenType.COLON):
                self.advance()
                def is_field_term(p, d, t):
                    if d == 0 and (t.value in {':='} or p.is_top_level_keyword(0)):
                        return True
                    if d == 0 and t.type == TokenType.NEWLINE:
                        i = 1
                        while p.peek(i).type == TokenType.NEWLINE:
                            i += 1
                        next_tok = p.peek(i)
                        if next_tok.type == TokenType.EOF:
                            return True
                        if next_tok.column <= field_col:
                            return True
                        if p.is_top_level_keyword(i):
                            return True
                    return False

                field_type = self.parse_raw_expr_until(is_field_term)

                # If we have implicit names, prepend them to the type in a special format
                # Format: "implicit_names type" (without colon, since field already adds colon)
                if implicit_names:
                    # Just prepend to the type string, but we'll store implicit_names separately
                    field_type = RawExpr(field_type.to_source())  # Keep original type

            default = None
            if self.match(TokenType.COLONEQ):
                self.advance()
                def is_default_term(p, d, t):
                    if d == 0 and p.is_top_level_keyword(0):
                        return True
                    if d == 0 and t.type == TokenType.NEWLINE:
                        i = 1
                        while p.peek(i).type == TokenType.NEWLINE:
                            i += 1
                        next_tok = p.peek(i)
                        if next_tok.type == TokenType.EOF:
                            return True
                        if next_tok.column <= field_col:
                            return True
                        if p.is_top_level_keyword(i):
                            return True
                    return False
                default = self.parse_raw_expr_until(is_default_term)

            fields.append(StructureField(name=field_name, type=field_type, binders=field_binders, implicit_names=implicit_names, default=default, doc=doc))

        # Handle deriving clause
        deriving = []
        while self.match(TokenType.NEWLINE):
            self.advance()
        if self.match(TokenType.IDENT) and self.peek().value == "deriving":
            self.advance()  # consume 'deriving'
            while self.match(TokenType.IDENT):
                deriving.append(self.advance().value)
                if self.match(TokenType.COMMA):
                    self.advance()

        doc = self.current_doc
        self.current_doc = None

        return Structure(
            name=name,
            attributes=attrs,
            has_at=has_at,
            doc=doc,
            binders=binders,
            type=type_expr,
            extends=extends,
            ctor_name=ctor_name,
            fields=fields,
            has_where=has_where,
            modifiers=modifiers,
            deriving=deriving
        )

    def parse_inductive(self, attrs: List[Attribute], item_start_col: int, modifiers: List[Modifier]) -> Inductive:
        kw_token = self.peek()
        self.expect(TokenType.INDUCTIVE)
        kw_col = item_start_col
        name = self.expect_ident()

        while self.match(TokenType.NEWLINE):
            self.advance()

        binders = []
        while (self.match(TokenType.LPAREN, TokenType.LBRACE, TokenType.LBRACKET) or
               (self.match(TokenType.IDENT) and self.peek().value == '⦃')):
            binders.extend(self.parse_binders())
            while self.match(TokenType.NEWLINE):
                self.advance()

        type_expr = None
        if self.match(TokenType.COLON):
            self.advance()
            def is_ind_type_term(p, d, t):
                if d == 0 and (t.value in {'|', 'where'} or p.is_top_level_keyword(0)):
                    return True
                if d == 0 and t.type == TokenType.NEWLINE:
                    i = 1
                    while p.peek(i).type == TokenType.NEWLINE:
                        i += 1
                    next_tok = p.peek(i)
                    if next_tok.type == TokenType.EOF:
                        return True
                    if next_tok.column <= kw_col:
                        return True
                return False
            type_expr = self.parse_raw_expr_until(is_ind_type_term)

        ctor_style = None
        if self.match(TokenType.WHERE) or (self.match(TokenType.IDENT) and self.peek().value == "where"):
            self.advance()
            ctor_style = "where"
        elif self.match(TokenType.COLONEQ):
            # Support `inductive ... :=` form.
            self.advance()
            ctor_style = ":="

        while self.match(TokenType.NEWLINE):
            self.advance()

        ctors = []
        while True:
            while self.match(TokenType.NEWLINE):
                self.advance()
            if not self.match(TokenType.BAR, TokenType.DOC):
                break
            if self.match(TokenType.DOC):
                lookahead_pos = 1
                while self.peek(lookahead_pos).type == TokenType.NEWLINE:
                    lookahead_pos += 1
                next_tok = self.peek(lookahead_pos)
                if next_tok.type in (TokenType.DEF, TokenType.THEOREM, TokenType.LEMMA, TokenType.EXAMPLE, TokenType.AXIOM, TokenType.OPAQUE, TokenType.ABBREV, TokenType.INSTANCE, TokenType.CLASS, TokenType.STRUCTURE, TokenType.INDUCTIVE, TokenType.NAMESPACE, TokenType.SECTION, TokenType.END, TokenType.IMPORT, TokenType.OPEN, TokenType.SET_OPTION, TokenType.ATTRIBUTE, TokenType.LOCAL, TokenType.ELAB, TokenType.MACRO, TokenType.SYNTAX, TokenType.MACRO_RULES, TokenType.INITIALIZE, TokenType.ADD_DECL_DOC, TokenType.VARIABLE, TokenType.UNIVERSE, TokenType.ALIGN, TokenType.ALIGN_IMPORT, TokenType.NOALIGN):
                    break
                if next_tok.type == TokenType.IDENT and self.is_top_level_keyword(lookahead_pos):
                    break
                doc = self.advance().value
                while self.match(TokenType.NEWLINE):
                    self.advance()
            else:
                doc = None

            bar_token = self.expect(TokenType.BAR)
            bar_col = bar_token.column
            ctor_name = self.expect(TokenType.IDENT).value
            ctor_binders = self.parse_binders()
            ctor_type = None
            if self.match(TokenType.COLON):
                self.advance()
                # For inductive constructors, don't stop at newlines - they can span multiple lines
                def is_ctor_type_term(p, d, t):
                    if d == 0 and (t.value in {'|'} or p.is_top_level_keyword(0)):
                        return True
                    if d == 0 and t.type == TokenType.NEWLINE:
                        i = 1
                        while p.peek(i).type == TokenType.NEWLINE:
                            i += 1
                        next_tok = p.peek(i)
                        if next_tok.type == TokenType.EOF:
                            return True
                        if next_tok.column <= bar_col:
                            return True
                        if p.is_top_level_keyword(i):
                            return True
                    return False
                ctor_type = self.parse_raw_expr_until(is_ctor_type_term)

            ctors.append(InductiveCtor(ctor_name, ctor_binders, ctor_type, doc))

        # Handle deriving clause
        deriving = []
        if self.match(TokenType.IDENT) and self.peek().value == "deriving":
            self.advance()  # consume 'deriving'
            while self.match(TokenType.IDENT):
                deriving.append(self.advance().value)
                if self.match(TokenType.COMMA):
                    self.advance()

        doc = self.current_doc
        self.current_doc = None

        return Inductive(
            name=name,
            attributes=attrs,
            doc=doc,
            binders=binders,
            type=type_expr,
            ctors=ctors,
            ctor_style=ctor_style,
            deriving=deriving,
            modifiers=modifiers
        )