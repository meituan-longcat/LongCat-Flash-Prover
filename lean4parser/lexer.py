"""
Lean 4 Lexer - Tokenizes Lean 4 source code.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Iterator


class TokenType(Enum):
    # Literals
    NAT = auto()           # Natural number literal
    INT = auto()           # Integer literal
    FLOAT = auto()         # Float literal
    STRING = auto()        # String literal
    CHAR = auto()          # Character literal
    IDENT = auto()         # General identifier

    # Keywords
    IMPORT = auto()
    OPEN = auto()
    NAMESPACE = auto()
    SECTION = auto()
    END = auto()
    VARIABLE = auto()
    VARIABLES = auto()
    UNIVERSE = auto()
    UNIVERSES = auto()

    DEF = auto()
    THEOREM = auto()
    LEMMA = auto()
    EXAMPLE = auto()
    AXIOM = auto()
    OPAQUE = auto()
    ABBREV = auto()
    INSTANCE = auto()
    CLASS = auto()
    STRUCTURE = auto()
    INDUCTIVE = auto()
    COINDUCTIVE = auto()

    WHERE = auto()
    EXTENDS = auto()
    BY = auto()
    HAVE = auto()
    LET = auto()
    IF = auto()
    THEN = auto()
    ELSE = auto()
    MATCH = auto()
    WITH = auto()
    FORALL = auto()
    EXISTS = auto()
    FUN = auto()
    ASSUME = auto()
    SHOW = auto()
    SORRY = auto()
    ADMIT = auto()

    SET_OPTION = auto()
    ATTRIBUTE = auto()
    LOCAL = auto()
    GLOBAL = auto()
    SCOPE = auto()

    # Meta-programming keywords
    ELAB = auto()
    MACRO = auto()
    MACRO_RULES = auto()
    SYNTAX = auto()
    INITIALIZE = auto()
    ADD_DECL_DOC = auto()

    # Special identifiers (start with #)
    ALIGN = auto()
    ALIGN_IMPORT = auto()
    NOALIGN = auto()

    # Command keywords
    CALC = auto()
    HAVE_ = auto()  # have tactic
    SUFFICES = auto()
    SHOW_ = auto()  # show tactic
    OMIT = auto()
    INCLUDE = auto()

    # Notation keywords
    INFIX = auto()
    INFIXL = auto()
    INFIXR = auto()
    PREFIX = auto()
    POSTFIX = auto()
    NOTATION = auto()
    SCOPED = auto()

    # Operators
    ARROW = auto()         # -> or →
    DARROW = auto()        # => or ⇒
    LARROW = auto()        # <- or ←
    LDARROW = auto()       # <= or ⇐

    MAPSTO = auto()        # ↦
    LAMBDA = auto()        # λ or \lambda

    EQ = auto()            # =
    NE = auto()            # ≠
    LT = auto()            # <
    GT = auto()            # >
    LE = auto()            # ≤ or <=
    GE = auto()            # ≥ or >=

    MEMBER = auto()        # ∈ (element of)
    NOT_MEMBER = auto()    # ∉ (not element of)

    COLON = auto()         # :
    COLON2 = auto()        # ::
    COLONEQ = auto()       # :=

    PLUS = auto()          # +
    MINUS = auto()         # -
    STAR = auto()          # *
    SLASH = auto()         # /
    DOUBLE_SLASH = auto()   # // (singleton type)
    DIV = auto()           # ÷
    PERCENT = auto()       # %

    LPAREN = auto()        # (
    RPAREN = auto()        # )
    LBRACKET = auto()      # [
    RBRACKET = auto()      # ]
    LBRACE = auto()        # {
    RBRACE = auto()        # }

    LANGLE = auto()        # ⟨ or <
    RANGLE = auto()        # ⟩ or >

    COMMA = auto()         # ,
    SEMI = auto()          # ;
    DOT = auto()           # .
    BAR = auto()           # |
    BACKTICK = auto()      # `
    APOSTROPHE = auto()    # '
    AT = auto()            # @
    BANG = auto()          # !
    QUESTION = auto()      # ?
    CARET = auto()         # ^
    TILDE = auto()         # ~
    AMPERSAND = auto()     # &
    DOLLAR = auto()        # $
    HASH = auto()          # #
    BACKSLASH = auto()     # \

    UNDERSCORE = auto()    # _

    # #commands
    CHECK = auto()         # #check
    EVAL = auto()          # #eval
    REDUCE = auto()        # #reduce
    PRINT = auto()         # #print
    HASH_SORRY = auto()    # #sorry
    WIDGET = auto()        # #widget
    GEN_INJECTIVITY = auto()  # #gen_injective_theorems

    # Special
    MOD_DOC = auto()       # Module documentation (/-! ... -/)
    DOC = auto()           # Documentation comment (/-- ... -/)
    LINE_COMMENT = auto()  # Line comment (-- ...)
    BLOCK_COMMENT = auto() # Block comment (/- ... -/)

    WHITESPACE = auto()    # Spaces, tabs, newlines
    NEWLINE = auto()       # Newline
    INDENT = auto()        # Indentation
    DEDENT = auto()        # Dedentation

    EOF = auto()           # End of file


@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    column: int
    raw: str  # Original raw text

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.raw!r}, {self.line}:{self.column})"


class LexerError(Exception):
    pass


class Lexer:
    KEYWORDS = {
        'import': TokenType.IMPORT,
        'open': TokenType.OPEN,
        'namespace': TokenType.NAMESPACE,
        'section': TokenType.SECTION,
        'end': TokenType.END,
        'variable': TokenType.VARIABLE,
        'variables': TokenType.VARIABLES,
        'universe': TokenType.UNIVERSE,
        'universes': TokenType.UNIVERSES,

        'def': TokenType.DEF,
        'theorem': TokenType.THEOREM,
        'lemma': TokenType.LEMMA,
        'example': TokenType.EXAMPLE,
        'axiom': TokenType.AXIOM,
        'opaque': TokenType.OPAQUE,
        'abbrev': TokenType.ABBREV,
        'instance': TokenType.INSTANCE,
        'class': TokenType.CLASS,
        'structure': TokenType.STRUCTURE,
        'inductive': TokenType.INDUCTIVE,
        'coinductive': TokenType.COINDUCTIVE,

        'where': TokenType.WHERE,
        'extends': TokenType.EXTENDS,
        'by': TokenType.BY,
        'have': TokenType.HAVE,
        'let': TokenType.LET,
        'if': TokenType.IF,
        'then': TokenType.THEN,
        'else': TokenType.ELSE,
        'match': TokenType.MATCH,
        'with': TokenType.WITH,
        'forall': TokenType.FORALL,
        'exists': TokenType.EXISTS,
        'fun': TokenType.FUN,
        'assume': TokenType.ASSUME,
        'show': TokenType.SHOW,
        'sorry': TokenType.SORRY,
        'admit': TokenType.ADMIT,

        'set_option': TokenType.SET_OPTION,
        'attribute': TokenType.ATTRIBUTE,
        'local': TokenType.LOCAL,
        'global': TokenType.GLOBAL,
        'scope': TokenType.SCOPE,

        'elab': TokenType.ELAB,
        'macro': TokenType.MACRO,
        'macro_rules': TokenType.MACRO_RULES,
        'syntax': TokenType.SYNTAX,
        'initialize': TokenType.INITIALIZE,
        'add_decl_doc': TokenType.ADD_DECL_DOC,

        'calc': TokenType.CALC,
        'suffices': TokenType.SUFFICES,
        'omit': TokenType.OMIT,
        'include': TokenType.INCLUDE,

        # Notation keywords
        'infix': TokenType.INFIX,
        'infixl': TokenType.INFIXL,
        'infixr': TokenType.INFIXR,
        'prefix': TokenType.PREFIX,
        'postfix': TokenType.POSTFIX,
        'notation': TokenType.NOTATION,
        'scoped': TokenType.SCOPED,
    }

    SPECIAL_COMMANDS = {
        '#align': TokenType.ALIGN,
        '#align_import': TokenType.ALIGN_IMPORT,
        '#noalign': TokenType.NOALIGN,
    }

    UNICODE_OPS = {
        '→': TokenType.ARROW,
        '⇒': TokenType.DARROW,
        '←': TokenType.LARROW,
        '⇐': TokenType.LDARROW,
        '↦': TokenType.MAPSTO,
        'λ': TokenType.LAMBDA,
        '≠': TokenType.NE,
        '≤': TokenType.LE,
        '≥': TokenType.GE,
        '÷': TokenType.DIV,
        '⟨': TokenType.LANGLE,
        '⟩': TokenType.RANGLE,
        '×': TokenType.STAR,   # Product type
        '⊕': TokenType.PLUS,   # Direct sum
        '⊗': TokenType.STAR,   # Tensor product
        '·': TokenType.STAR,   # Center dot (placeholder)
        '¬': TokenType.BANG,   # Negation
        '↔': TokenType.EQ,     # Iff
        '∧': TokenType.AMPERSAND,  # And
        '∨': TokenType.BAR,    # Or
        '⟮': TokenType.LPAREN, # Fancy lparen
        '⟯': TokenType.RPAREN, # Fancy rparen
        '∘': TokenType.STAR,   # Composition
        '≈': TokenType.EQ,     # Approx eq
        '≡': TokenType.EQ,     # Equiv
        '∈': TokenType.MEMBER,     # Element of
        '∉': TokenType.NOT_MEMBER,  # Not element of
        '⊆': TokenType.LE,     # Subset
        '⊂': TokenType.LT,     # Proper subset
        '∪': TokenType.PLUS,   # Union
        '∩': TokenType.STAR,   # Intersection
        '∑': TokenType.IDENT,  # Sum
        '∏': TokenType.IDENT,  # Product
        '√': TokenType.IDENT,  # Sqrt
        '∞': TokenType.IDENT,  # Infinity
        '′': TokenType.APOSTROPHE,  # Prime
        '↑': TokenType.IDENT,  # Up arrow
        '↓': TokenType.IDENT,  # Down arrow
        '↿': TokenType.IDENT,  # Up harpoon
        '⇂': TokenType.IDENT,  # Down harpoon
        '⦃': TokenType.LBRACE, # ⦃ fancy lbrace
        '⦄': TokenType.RBRACE, # ⦄ fancy rbrace
        '⟹': TokenType.ARROW,  # Long double arrow
        '⟸': TokenType.LARROW, # Long double left arrow
        '⟺': TokenType.ARROW,  # Long double double arrow
        '▸': TokenType.GT,     # Rewrite triangle
        '‹': TokenType.LANGLE,  # Single angle
        '›': TokenType.RANGLE,  # Single angle
        '≃': TokenType.EQ,      # Equiv
        '≄': TokenType.NE,      # Not equiv
        '∼': TokenType.TILDE,   # Sim
        '≀': TokenType.STAR,    # Wreath
        '‖': TokenType.BAR,     # Double bar
        '│': TokenType.BAR,     # Box drawings light vertical
        '⁺': TokenType.PLUS,    # Superscript plus
        '⁻': TokenType.MINUS,   # Superscript minus
        'ᵀ': TokenType.IDENT,   # Transpose
        '•': TokenType.STAR,    # Bullet (list item)
        '…': TokenType.IDENT,   # Ellipsis
        '₀': TokenType.IDENT,   # Subscript 0
        '₁': TokenType.IDENT,   # Subscript 1
        '₂': TokenType.IDENT,   # Subscript 2
        '₃': TokenType.IDENT,   # Subscript 3
        '₄': TokenType.IDENT,   # Subscript 4
        '₅': TokenType.IDENT,   # Subscript 5
        '₆': TokenType.IDENT,   # Subscript 6
        '₇': TokenType.IDENT,   # Subscript 7
        '₈': TokenType.IDENT,   # Subscript 8
        '₉': TokenType.IDENT,   # Subscript 9
        'ₙ': TokenType.IDENT,   # Subscript n
        'ₘ': TokenType.IDENT,   # Subscript m
        'ᵢ': TokenType.IDENT,   # Subscript i
        'ⱼ': TokenType.IDENT,   # Subscript j
        'ₖ': TokenType.IDENT,   # Subscript k
        'ˣ': TokenType.IDENT,   # Superscript x
        'ʸ': TokenType.IDENT,   # Superscript y
        'ᶻ': TokenType.IDENT,   # Superscript z
        '⁰': TokenType.IDENT,   # Superscript 0
        '¹': TokenType.IDENT,   # Superscript 1
        '²': TokenType.IDENT,   # Superscript 2
        '³': TokenType.IDENT,   # Superscript 3
        '⁴': TokenType.IDENT,   # Superscript 4
        '⁵': TokenType.IDENT,   # Superscript 5
        '⁶': TokenType.IDENT,   # Superscript 6
        '⁷': TokenType.IDENT,   # Superscript 7
        '⁸': TokenType.IDENT,   # Superscript 8
        '⁹': TokenType.IDENT,   # Superscript 9
        '\u201c': TokenType.IDENT,   # Left double quote
        '\u201d': TokenType.IDENT,   # Right double quote
        '\u2018': TokenType.IDENT,   # Left single quote
        '\u2019': TokenType.IDENT,   # Right single quote
        '\u215f': TokenType.IDENT,   # Fraction 1/
        '\u27f6': TokenType.ARROW,   # Long right arrow
        '\u27f8': TokenType.LDARROW, # Long left double arrow
        '\u27f9': TokenType.DARROW,  # Long right double arrow
        '\u25c1': TokenType.LT,      # White left-pointing triangle
        '\u25b7': TokenType.GT,      # White right-pointing triangle
        '\u21aa': TokenType.ARROW,   # Rightwards arrow with hook
        '\u21d1': TokenType.IDENT,   # Upwards double arrow
        '\u2a06': TokenType.IDENT,   # N-ary square union operator
        '\u2a05': TokenType.IDENT,   # N-ary square intersection operator
        '\u2293': TokenType.IDENT,   # Square cap
        '\u2294': TokenType.IDENT,   # Square cup
        '\u2210': TokenType.IDENT,   # N-ary coproduct
        '\u2211': TokenType.IDENT,   # N-ary summation
        '\u2212': TokenType.MINUS,   # Minus sign
        '\u2213': TokenType.IDENT,   # Minus-or-plus sign
        '\u2214': TokenType.IDENT,   # Dot plus
        '\u22c0': TokenType.IDENT,   # N-ary logical and
        '\u22c1': TokenType.IDENT,   # N-ary logical or
        '\u22c2': TokenType.IDENT,   # N-ary intersection
        '\u22c3': TokenType.IDENT,   # N-ary union
        '\u2a00': TokenType.IDENT,   # N-ary circled dot operator
        '\u2a01': TokenType.IDENT,   # N-ary circled plus operator
        '\u2a02': TokenType.IDENT,   # N-ary circled times operator
        '\u29e8': TokenType.LBRACKET,  # Left square bracket with underbar
        '\u29e9': TokenType.RBRACKET,  # Right square bracket with underbar
        '\u21e8': TokenType.ARROW,   # Rightwards white arrow
        '\u2a7f': TokenType.LE,      # Less-than or slanted equal to with dot inside
        '\u21a9': TokenType.ARROW,   # Leftwards arrow with hook
        '\u21aa': TokenType.ARROW,   # Rightwards arrow with hook
        '\u21d4': TokenType.EQ,      # Left right double arrow (iff)
        '\uffe2': TokenType.BANG,    # Fullwidth not sign
        '\u21a5': TokenType.IDENT,   # Upwards arrow from bar
        '\u21a7': TokenType.IDENT,   # Downwards arrow from bar
        '\u21c4': TokenType.IDENT,   # Rightwards arrow over leftwards arrow
        '\u21c6': TokenType.IDENT,   # Leftwards arrow over rightwards arrow
        '\u21cb': TokenType.IDENT,   # Leftwards harpoon over rightwards harpoon
        '\u21cc': TokenType.IDENT,   # Rightwards harpoon over leftwards harpoon
        '\u21e0': TokenType.IDENT,   # Leftwards dashed arrow
        '\u21e1': TokenType.IDENT,   # Upwards dashed arrow
        '\u21e2': TokenType.IDENT,   # Rightwards dashed arrow
        '\u21e3': TokenType.IDENT,   # Downwards dashed arrow
        '\u21f4': TokenType.IDENT,   # Right arrow with small circle
        '\u21f5': TokenType.IDENT,   # Downwards arrow leftwards of upwards arrow
        '\u21f6': TokenType.IDENT,   # Three rightwards arrows
        '\u21fd': TokenType.LT,      # Leftwards open-headed arrow
        '\u21fe': TokenType.GT,      # Rightwards open-headed arrow
        '\u21ff': TokenType.IDENT,   # Left right open-headed arrow
        '\u2964': TokenType.IDENT,   # Rightwards harpoon with barb upwards to bar
        '\u2962': TokenType.IDENT,   # Leftwards harpoon with barb upwards to bar
        '\u27e6': TokenType.LBRACKET,  # Mathematical left white square bracket
        '\u27e7': TokenType.RBRACKET,  # Mathematical right white square bracket
        '\u27e8': TokenType.LANGLE,    # Mathematical left angle bracket
        '\u27e9': TokenType.RANGLE,    # Mathematical right angle bracket
        '\u27ea': TokenType.LANGLE,    # Mathematical left double angle bracket
        '\u27eb': TokenType.RANGLE,    # Mathematical right double angle bracket
        '\u27ec': TokenType.LBRACKET,  # Mathematical left white tortoise shell bracket
        '\u27ed': TokenType.RBRACKET,  # Mathematical right white tortoise shell bracket
        '\u27ee': TokenType.LPAREN,    # Mathematical left flattened parenthesis
        '\u27ef': TokenType.RPAREN,    # Mathematical right flattened parenthesis
        '\u2980': TokenType.IDENT,     # Triple vertical bar delimiter
        '\u2983': TokenType.LBRACE,    # Left white curly bracket
        '\u2984': TokenType.RBRACE,    # Right white curly bracket
        '\u2985': TokenType.LPAREN,    # Left white parenthesis
        '\u2986': TokenType.RPAREN,    # Right white parenthesis
        '\u2987': TokenType.LPAREN,    # Left tortoise shell bracket
        '\u2988': TokenType.RPAREN,    # Right tortoise shell bracket
        '\u2989': TokenType.LPAREN,    # Left square bracket with tick in top corner
        '\u298a': TokenType.RPAREN,    # Right square bracket with tick in bottom corner
        '\u298b': TokenType.LBRACKET,  # Left square bracket with underbar
        '\u298c': TokenType.RBRACKET,  # Right square bracket with underbar
        '\u298d': TokenType.LBRACKET,  # Left square bracket with tick in top corner
        '\u298e': TokenType.RBRACKET,  # Right square bracket with tick in bottom corner
        '\u298f': TokenType.LBRACKET,  # Left square bracket with tick in bottom corner
        '\u2990': TokenType.RBRACKET,  # Right square bracket with tick in top corner
        '\u2991': TokenType.LANGLE,    # Left angle bracket with dot
        '\u2992': TokenType.RANGLE,    # Right angle bracket with dot
        '\u2993': TokenType.LPAREN,    # Left arc less-than bracket
        '\u2994': TokenType.RPAREN,    # Right arc greater-than bracket
        '\u2995': TokenType.LPAREN,    # Double left arc greater-than bracket
        '\u2996': TokenType.RPAREN,    # Double right arc less-than bracket
        '\u2997': TokenType.LBRACKET,  # Left black tortoise shell bracket
        '\u2998': TokenType.RBRACKET,  # Right black tortoise shell bracket
        '\u29fc': TokenType.LPAREN,    # Left-pointing curved angle bracket
        '\u29fd': TokenType.RPAREN,    # Right-pointing curved angle bracket
        '\u2933': TokenType.ARROW,   # Wave arrow pointing directly right
        '\u2945': TokenType.IDENT,   # Rightwards arrow with plus below
        '\u2a3f': TokenType.IDENT,   # Amalgamation or coproduct
        '\u2a1d': TokenType.IDENT,   # Join
        '\u2a1e': TokenType.IDENT,   # Large left triangle operator
        '\u2a1f': TokenType.IDENT,   # Z notation schema composition
        '\u2a20': TokenType.IDENT,   # Z notation schema piping
        '\u2a21': TokenType.IDENT,   # Z notation schema projection
        '\u2a22': TokenType.IDENT,   # Plus sign with small circle above
        '\u2a23': TokenType.IDENT,   # Plus sign with circumflex accent above
        '\u2a24': TokenType.IDENT,   # Plus sign with tilde above
        '\u2a25': TokenType.IDENT,   # Plus sign with dot below
        '\u2a26': TokenType.IDENT,   # Plus sign with tilde below
        '\u2a27': TokenType.IDENT,   # Plus sign with subscript two
        '\u2a28': TokenType.IDENT,   # Plus sign with black triangle
        '\u2a29': TokenType.IDENT,   # Minus sign with comma above
        '\u2a2a': TokenType.IDENT,   # Minus sign with dot below
        '\u2a2b': TokenType.IDENT,   # Minus sign with falling dots
        '\u2a2c': TokenType.IDENT,   # Minus sign with rising dots
        '\u2a2d': TokenType.IDENT,   # Plus sign in left half circle
        '\u2a2e': TokenType.IDENT,   # Plus sign in right half circle
        '\u2a30': TokenType.IDENT,   # Multiplication sign with dot above
        '\u2a31': TokenType.IDENT,   # Multiplication sign with underbar
        '\u2a32': TokenType.IDENT,   # Semidirect product with bottom closed
        '\u2a33': TokenType.IDENT,   # Smash product
        '\u2a34': TokenType.IDENT,   # Multiplication sign in left half circle
        '\u2a35': TokenType.IDENT,   # Multiplication sign in right half circle
        '\u2a36': TokenType.IDENT,   # Circled multiplication sign with circumflex accent
        '\u2a37': TokenType.IDENT,   # Multiplication sign in double circle
        '\u2a38': TokenType.IDENT,   # Circled division sign
        '\u2a39': TokenType.IDENT,   # Plus sign in triangle
        '\u2a3a': TokenType.IDENT,   # Minus sign in triangle
        '\u2a3b': TokenType.IDENT,   # Multiplication sign in triangle
        '\u2a3c': TokenType.IDENT,   # Interior product
        '\u2a3d': TokenType.IDENT,   # Righthand interior product
        '\u2a3e': TokenType.IDENT,   # Z notation relational composition
        '\u2a40': TokenType.IDENT,   # Intersection with dot
        '\u2a41': TokenType.IDENT,   # Union with minus sign
        '\u2a42': TokenType.IDENT,   # Union with overbar
        '\u2a43': TokenType.IDENT,   # Intersection with overbar
        '\u2a44': TokenType.IDENT,   # Intersection with logical and
        '\u2a45': TokenType.IDENT,   # Union with logical or
        '\u2a46': TokenType.IDENT,   # Union above intersection
        '\u2a47': TokenType.IDENT,   # Intersection above union
        '\u2a48': TokenType.IDENT,   # Union above bar above intersection
        '\u2a49': TokenType.IDENT,   # Intersection above bar above union
        '\u2a4a': TokenType.IDENT,   # Union beside and joined with union
        '\u2a4b': TokenType.IDENT,   # Intersection beside and joined with intersection
        '\u2a4c': TokenType.IDENT,   # Closed union with serifs
        '\u2a4d': TokenType.IDENT,   # Closed intersection with serifs
        '\u2a4e': TokenType.IDENT,   # Double square intersection
        '\u2a4f': TokenType.IDENT,   # Double square union
        '\u2a50': TokenType.IDENT,   # Closed union with serifs and smash product
        '\u2a51': TokenType.IDENT,   # Logical and with dot above
        '\u2a52': TokenType.IDENT,   # Logical or with dot above
        '\u2a53': TokenType.IDENT,   # Double logical and
        '\u2a54': TokenType.IDENT,   # Double logical or
        '\u2a55': TokenType.IDENT,   # Two intersecting logical and
        '\u2a56': TokenType.IDENT,   # Two intersecting logical or
        '\u2a57': TokenType.IDENT,   # Sloping large or
        '\u2a58': TokenType.IDENT,   # Sloping large and
        '\u2a59': TokenType.IDENT,   # Logical or overlapping logical and
        '\u2a5a': TokenType.IDENT,   # Logical and with middle stem
        '\u2a5b': TokenType.IDENT,   # Logical or with middle stem
        '\u2a5c': TokenType.IDENT,   # Logical and with horizontal dash
        '\u2a5d': TokenType.IDENT,   # Logical or with horizontal dash
        '\u2a5e': TokenType.IDENT,   # Logical and with double overbar
        '\u2a5f': TokenType.IDENT,   # Logical and with underbar
        '\u2a60': TokenType.IDENT,   # Logical and with double underbar
        '\u2a61': TokenType.IDENT,   # Logical or with double overbar
        '\u2a62': TokenType.IDENT,   # Logical or with double underbar
        '\u2a63': TokenType.IDENT,   # Logical or with double underbar
        '\u2a64': TokenType.IDENT,   # Z notation domain antirestriction
        '\u2a65': TokenType.IDENT,   # Z notation range antirestriction
        '\u2a66': TokenType.EQ,      # Equals sign with dot below
        '\u2a67': TokenType.EQ,      # Identical with dot above
        '\u2a68': TokenType.EQ,      # Triple horizontal bar with double vertical stroke
        '\u2a69': TokenType.EQ,      # Triple horizontal bar with triple vertical stroke
        '\u2a6a': TokenType.EQ,      # Tilde operator with dot above
        '\u2a6b': TokenType.IDENT,   # Tilde operator with rising dots
        '\u2a6c': TokenType.IDENT,   # Similar minus similar
        '\u2a6d': TokenType.EQ,      # Congruent with dot above
        '\u2a6e': TokenType.IDENT,   # Equals with asterisk
        '\u2a6f': TokenType.IDENT,   # Almost equal to with circumflex accent
        '\u2a70': TokenType.EQ,      # Approximately equal or equal to
        '\u2a71': TokenType.IDENT,   # Equals sign above plus sign
        '\u2a72': TokenType.IDENT,   # Plus sign above equals sign
        '\u2a73': TokenType.EQ,      # Equals sign above tilde operator
        '\u2a74': TokenType.EQ,      # Double colon equal
        '\u2a75': TokenType.EQ,      # Two consecutive equals signs
        '\u2a76': TokenType.EQ,      # Three consecutive equals signs
        '\u2a77': TokenType.IDENT,   # Equals sign with two dots above and two dots below
        '\u2a78': TokenType.EQ,      # Equivalent with four dots above
        '\u2a79': TokenType.LT,      # Less-than with circle inside
        '\u2a7a': TokenType.GT,      # Greater-than with circle inside
        '\u2a7b': TokenType.LT,      # Less-than with question mark above
        '\u2a7c': TokenType.GT,      # Greater-than with question mark above
        '\u2a7d': TokenType.LE,      # Less-than or slanted equal to
        '\u2a7e': TokenType.GE,      # Greater-than or slanted equal to
        '\u2a7f': TokenType.LE,      # Less-than or slanted equal to with dot inside
        '\u2a80': TokenType.GE,      # Greater-than or slanted equal to with dot inside
        '\u2a81': TokenType.LT,      # Less-than or slanted equal to with dot above
        '\u2a82': TokenType.GT,      # Greater-than or slanted equal to with dot above
        '\u2a83': TokenType.LT,      # Less-than or slanted equal to with dot above right
        '\u2a84': TokenType.GT,      # Greater-than or slanted equal to with dot above left
        '\u2a85': TokenType.LT,      # Less-than or approximate
        '\u2a86': TokenType.GT,      # Greater-than or approximate
        '\u2a87': TokenType.LT,      # Less-than and single-line not equal to
        '\u2a88': TokenType.GT,      # Greater-than and single-line not equal to
        '\u2a89': TokenType.LT,      # Less-than and not approximate
        '\u2a8a': TokenType.GT,      # Greater-than and not approximate
        '\u2a8b': TokenType.LT,      # Less-than above double-line equal above greater-than
        '\u2a8c': TokenType.GT,      # Greater-than above double-line equal above less-than
        '\u2a8d': TokenType.LT,      # Less-than above similar or equal
        '\u2a8e': TokenType.GT,      # Greater-than above similar or equal
        '\u2a8f': TokenType.LT,      # Less-than above similar above greater-than
        '\u2a90': TokenType.GT,      # Greater-than above similar above less-than
        '\u2a91': TokenType.LT,      # Less-than above greater-than above double-line equal
        '\u2a92': TokenType.GT,      # Greater-than above less-than above double-line equal
        '\u2a93': TokenType.LT,      # Less-than above slanted equal above greater-than above slanted equal
        '\u2a94': TokenType.GT,      # Greater-than above slanted equal above less-than above slanted equal
        '\u2a95': TokenType.LE,      # Slanted equal to or less-than
        '\u2a96': TokenType.GE,      # Slanted equal to or greater-than
        '\u2a97': TokenType.LE,      # Slanted equal to or less-than with dot inside
        '\u2a98': TokenType.GE,      # Slanted equal to or greater-than with dot inside
        '\u2a99': TokenType.LE,      # Double-line equal to or less-than
        '\u2a9a': TokenType.GE,      # Double-line equal to or greater-than
        '\u2a9b': TokenType.LE,      # Double-line slanted equal to or less-than
        '\u2a9c': TokenType.GE,      # Double-line slanted equal to or greater-than
        '\u2a9d': TokenType.LT,      # Similar or less-than
        '\u2a9e': TokenType.GT,      # Similar or greater-than
        '\u2a9f': TokenType.LT,      # Similar above less-than above equals sign
        '\u2aa0': TokenType.GT,      # Similar above greater-than above equals sign
        '\u2aa1': TokenType.LT,      # Double nested less-than
        '\u2aa2': TokenType.GT,      # Double nested greater-than
        '\u2aa3': TokenType.IDENT,   # Double nested less-than with underbar
        '\u2aa4': TokenType.LT,      # Greater-than overlapping less-than
        '\u2aa5': TokenType.GT,      # Greater-than beside less-than
        '\u2aa6': TokenType.IDENT,   # Less-than closed by curve
        '\u2aa7': TokenType.IDENT,   # Greater-than closed by curve
        '\u2aa8': TokenType.IDENT,   # Less-than closed by curve above slanted equal
        '\u2aa9': TokenType.IDENT,   # Greater-than closed by curve above slanted equal
        '\u2aaa': TokenType.LT,      # Smaller than
        '\u2aab': TokenType.GT,      # Larger than
        '\u2aac': TokenType.LE,      # Smaller than or equal to
        '\u2aad': TokenType.GE,      # Larger than or equal to
        '\u2aae': TokenType.LE,      # Equals sign with bumpy above
        '\u2aaf': TokenType.IDENT,   # Precedes above single-line equals sign
        '\u2ab0': TokenType.IDENT,   # Succeeds above single-line equals sign
        '\u2ab1': TokenType.IDENT,   # Precedes above single-line not equal to
        '\u2ab2': TokenType.IDENT,   # Succeeds above single-line not equal to
        '\u2ab3': TokenType.IDENT,   # Precedes above equals sign
        '\u2ab4': TokenType.IDENT,   # Succeeds above equals sign
        '\u2ab5': TokenType.IDENT,   # Precedes above not equal to
        '\u2ab6': TokenType.IDENT,   # Succeeds above not equal to
        '\u2ab7': TokenType.IDENT,   # Precedes above almost equal to
        '\u2ab8': TokenType.IDENT,   # Succeeds above almost equal to
        '\u2ab9': TokenType.IDENT,   # Precedes above not almost equal to
        '\u2aba': TokenType.IDENT,   # Succeeds above not almost equal to
        '\u2abb': TokenType.IDENT,   # Double precedes
        '\u2abc': TokenType.IDENT,   # Double succeeds
        '\u2abd': TokenType.IDENT,   # Subset with dot
        '\u2abe': TokenType.IDENT,   # Superset with dot
        '\u2abf': TokenType.IDENT,   # Subset with plus sign below
        '\u2ac0': TokenType.IDENT,   # Superset with plus sign below
        '\u2ac1': TokenType.IDENT,   # Subset with multiplication sign below
        '\u2ac2': TokenType.IDENT,   # Superset with multiplication sign below
        '\u2ac3': TokenType.IDENT,   # Subset of or equal to with dot above
        '\u2ac4': TokenType.IDENT,   # Superset of or equal to with dot above
        '\u2ac5': TokenType.LE,      # Subset of above equals sign
        '\u2ac6': TokenType.GE,      # Superset of above equals sign
        '\u2ac7': TokenType.LT,      # Subset of above tilde operator
        '\u2ac8': TokenType.GT,      # Superset of above tilde operator
        '\u2ac9': TokenType.LT,      # Subset of above almost equal to
        '\u2aca': TokenType.GT,      # Superset of above almost equal to
        '\u2acb': TokenType.LT,      # Subset of above not equal to
        '\u2acc': TokenType.GT,      # Superset of above not equal to
        '\u2acd': TokenType.IDENT,   # Square left open box operator
        '\u2ace': TokenType.IDENT,   # Square right open box operator
        '\u2acf': TokenType.LT,      # Closed subset
        '\u2ad0': TokenType.GT,      # Closed superset
        '\u2ad1': TokenType.LE,      # Closed subset or equal to
        '\u2ad2': TokenType.GE,      # Closed superset or equal to
        '\u2ad3': TokenType.LE,      # Subset above superset
        '\u2ad4': TokenType.GE,      # Superset above subset
        '\u2ad5': TokenType.LE,      # Subset above subset
        '\u2ad6': TokenType.GE,      # Superset above superset
        '\u2ad7': TokenType.IDENT,   # Superset beside subset
        '\u2ad8': TokenType.IDENT,   # Superset beside and joined by dash with subset
        '\u2ad9': TokenType.IDENT,   # Element of opening downwards
        '\u2ada': TokenType.IDENT,   # Pitchfork with tee top
        '\u2adb': TokenType.IDENT,   # Transversal intersection
        '\u2adc': TokenType.IDENT,   # Forking
        '\u2add': TokenType.IDENT,   # Nonforking
        '\u2ade': TokenType.IDENT,   # Short left tack
        '\u2adf': TokenType.IDENT,   # Short down tack
        '\u2ae0': TokenType.IDENT,   # Short up tack
        '\u2ae1': TokenType.IDENT,   # Perpendicular with s
        '\u2ae2': TokenType.IDENT,   # Vertical bar triple right turnstile
        '\u2ae3': TokenType.IDENT,   # Double vertical bar left turnstile
        '\u2ae4': TokenType.IDENT,   # Vertical bar double left turnstile
        '\u2ae5': TokenType.IDENT,   # Double vertical bar double left turnstile
        '\u2ae6': TokenType.IDENT,   # Long dash from left member of double vertical
        '\u2ae7': TokenType.IDENT,   # Short down tack with overbar
        '\u2ae8': TokenType.IDENT,   # Short up tack with underbar
        '\u2ae9': TokenType.IDENT,   # Short up tack above short down tack
        '\u2aea': TokenType.IDENT,   # Double down tack
        '\u2aeb': TokenType.IDENT,   # Double up tack
        '\u2aec': TokenType.IDENT,   # Double stroke not sign
        '\u2aed': TokenType.IDENT,   # Reversed double stroke not sign
        '\u2aee': TokenType.IDENT,   # Does not divide with reversed negation slash
        '\u2aef': TokenType.IDENT,   # Vertical line with circle above
        '\u2af0': TokenType.IDENT,   # Vertical line with circle below
        '\u2af1': TokenType.IDENT,   # Down tack with circle below
        '\u2af2': TokenType.IDENT,   # Parallel with horizontal stroke
        '\u2af3': TokenType.IDENT,   # Parallel with tilde operator
        '\u2af4': TokenType.IDENT,   # Triple vertical bar binary relation
        '\u2af5': TokenType.IDENT,   # Triple vertical bar with horizontal stroke
        '\u2af6': TokenType.IDENT,   # Triple colon operator
        '\u2af7': TokenType.IDENT,   # Triple nested less-than
        '\u2af8': TokenType.IDENT,   # Triple nested greater-than
        '\u2af9': TokenType.IDENT,   # Double-line slanted less-than or equal to
        '\u2afa': TokenType.IDENT,   # Double-line slanted greater-than or equal to
        '\u2afb': TokenType.IDENT,   # Triple solidus binary relation
        '\u2afc': TokenType.IDENT,   # Large triple vertical bar operator
        '\u2afd': TokenType.IDENT,   # Double solidus operator
        '\u2afe': TokenType.IDENT,   # White vertical bar
        '\u2aff': TokenType.IDENT,   # N-ary white vertical bar
        '\u2946': TokenType.IDENT,   # Leftwards arrow with plus below
        '\u2940': TokenType.IDENT,   # Anticlockwise gapped circle arrow
        '\u2941': TokenType.IDENT,   # Clockwise gapped circle arrow
        '\u2942': TokenType.ARROW,   # Rightwards arrow with vertical stroke
        '\u2943': TokenType.ARROW,   # Leftwards arrow with vertical stroke
        '\u2944': TokenType.ARROW,   # Leftwards arrow with double vertical stroke
        '\u2947': TokenType.ARROW,   # Rightwards arrow with stroke
        '\u2948': TokenType.ARROW,   # Left right arrow through small circle
        '\u2949': TokenType.ARROW,   # Upwards two-headed arrow from small circle
        '\u294a': TokenType.ARROW,   # Left barb up right barb down harpoon
        '\u294b': TokenType.ARROW,   # Left barb down right barb up harpoon
        '\u294c': TokenType.ARROW,   # Up barb right down barb left harpoon
        '\u294d': TokenType.ARROW,   # Up barb left down barb right harpoon
        '\u294e': TokenType.ARROW,   # Left barb up right barb up harpoon
        '\u294f': TokenType.ARROW,   # Up barb right down barb right harpoon
        '\u2950': TokenType.IDENT,   # Leftwards harpoon with barb down from bar
        '\u2970': TokenType.ARROW,   # Right double arrow with rounded head
        '\u2971': TokenType.ARROW,   # Equals sign above rightwards arrow
        '\u2972': TokenType.ARROW,   # Tilde operator above rightwards arrow
        '\u2973': TokenType.ARROW,   # Leftwards arrow above tilde operator
        '\u2974': TokenType.ARROW,   # Rightwards arrow above tilde operator
        '\u2975': TokenType.ARROW,   # Rightwards arrow above almost equal to
        '\u2976': TokenType.ARROW,   # Less-than above leftwards arrow
        '\u2977': TokenType.ARROW,   # Leftwards arrow through less-than
        '\u2978': TokenType.ARROW,   # Greater-than above rightwards arrow
        '\u2979': TokenType.ARROW,   # Subset above rightwards arrow
        '\u297a': TokenType.ARROW,   # Leftwards arrow through subset
        '\u297b': TokenType.ARROW,   # Superset above leftwards arrow
        '\u297c': TokenType.ARROW,   # Left fish tail
        '\u297d': TokenType.ARROW,   # Right fish tail
        '\u297e': TokenType.IDENT,   # Up fish tail
        '\u297f': TokenType.IDENT,   # Down fish tail
        '\u2900': TokenType.ARROW,   # Rightwards two-headed arrow with vertical stroke
        '\u2901': TokenType.ARROW,   # Rightwards two-headed arrow with double vertical stroke
        '\u2902': TokenType.ARROW,   # Leftwards double arrow with vertical stroke
        '\u2903': TokenType.ARROW,   # Rightwards double arrow with vertical stroke
        '\u2904': TokenType.ARROW,   # Left right double arrow with vertical stroke
        '\u2905': TokenType.ARROW,   # Rightwards two-headed arrow from bar
        '\u2906': TokenType.ARROW,   # Leftwards double arrow from bar
        '\u2907': TokenType.ARROW,   # Rightwards double arrow from bar
        '\u2908': TokenType.ARROW,   # Downwards arrow with horizontal stroke
        '\u2909': TokenType.ARROW,   # Upwards arrow with horizontal stroke
        '\u290a': TokenType.ARROW,   # Upwards triple arrow
        '\u290b': TokenType.ARROW,   # Downwards triple arrow
        '\u290c': TokenType.ARROW,   # Leftwards double dash arrow
        '\u290d': TokenType.ARROW,   # Rightwards double dash arrow
        '\u290e': TokenType.ARROW,   # Leftwards triple dash arrow
        '\u290f': TokenType.ARROW,   # Rightwards triple dash arrow
        '\u2910': TokenType.ARROW,   # Rightwards two-headed triple dash arrow
        '\u2911': TokenType.ARROW,   # Rightwards arrow with dotted stem
        '\u2912': TokenType.ARROW,   # Upwards arrow to bar
        '\u2913': TokenType.ARROW,   # Downwards arrow to bar
        '\u2914': TokenType.ARROW,   # Rightwards arrow with tail with vertical stroke
        '\u2915': TokenType.ARROW,   # Rightwards arrow with tail with double vertical stroke
        '\u2916': TokenType.ARROW,   # Rightwards two-headed arrow with tail
        '\u2917': TokenType.ARROW,   # Rightwards two-headed arrow with tail with vertical stroke
        '\u2918': TokenType.ARROW,   # Rightwards two-headed arrow with tail with double vertical stroke
        '\u2919': TokenType.ARROW,   # Leftwards arrow-tail
        '\u291a': TokenType.ARROW,   # Rightwards arrow-tail
        '\u291b': TokenType.ARROW,   # Leftwards double arrow-tail
        '\u291c': TokenType.ARROW,   # Rightwards double arrow-tail
        '\u291d': TokenType.ARROW,   # Leftwards arrow to black diamond
        '\u291e': TokenType.ARROW,   # Rightwards arrow to black diamond
        '\u291f': TokenType.ARROW,   # Leftwards arrow from bar to black diamond
        '\u2920': TokenType.ARROW,   # Rightwards arrow from bar to black diamond
        '\u2921': TokenType.ARROW,   # North west and south east arrow
        '\u2922': TokenType.ARROW,   # North east and south west arrow
        '\u2923': TokenType.ARROW,   # North west arrow with hook
        '\u2924': TokenType.ARROW,   # North east arrow with hook
        '\u2925': TokenType.ARROW,   # South east arrow with hook
        '\u2926': TokenType.ARROW,   # South west arrow with hook
        '\u2927': TokenType.ARROW,   # North west arrow and north east arrow
        '\u2928': TokenType.ARROW,   # North east arrow and south east arrow
        '\u2929': TokenType.ARROW,   # South east arrow and south west arrow
        '\u292a': TokenType.ARROW,   # South west arrow and north west arrow
        '\u292b': TokenType.ARROW,   # Rising diagonal crossing falling diagonal
        '\u292c': TokenType.ARROW,   # Falling diagonal crossing rising diagonal
        '\u292d': TokenType.ARROW,   # South east arrow crossing north east arrow
        '\u292e': TokenType.ARROW,   # North east arrow crossing south east arrow
        '\u292f': TokenType.ARROW,   # Falling diagonal crossing north east arrow
        '\u2930': TokenType.ARROW,   # Rising diagonal crossing south east arrow
        '\u2931': TokenType.ARROW,   # North east arrow crossing north west arrow
        '\u2932': TokenType.ARROW,   # North west arrow crossing north east arrow
        '\u2934': TokenType.ARROW,   # Arrow pointing rightwards then curving upwards
        '\u2935': TokenType.ARROW,   # Arrow pointing rightwards then curving downwards
        '\u2936': TokenType.ARROW,   # Arrow pointing downwards then curving leftwards
        '\u2937': TokenType.ARROW,   # Arrow pointing downwards then curving rightwards
        '\u2938': TokenType.IDENT,   # Right-side arc clockwise arrow
        '\u2939': TokenType.IDENT,   # Left-side arc anticlockwise arrow
        '\u293a': TokenType.ARROW,   # Top arc anticlockwise arrow
        '\u293b': TokenType.ARROW,   # Bottom arc anticlockwise arrow
        '\u293c': TokenType.ARROW,   # Top arc clockwise arrow with minus
        '\u293d': TokenType.ARROW,   # Top arc anticlockwise arrow with plus
        '\u293e': TokenType.IDENT,   # Lower right semicircular clockwise arrow
        '\u293f': TokenType.IDENT,   # Lower left semicircular anticlockwise arrow
        '\u2940': TokenType.IDENT,   # Anticlockwise closed circle arrow
        '\u2941': TokenType.IDENT,   # Clockwise closed circle arrow
        '\u2951': TokenType.IDENT,   # Upwards harpoon with barb left from bar
        '\u2952': TokenType.IDENT,   # Leftwards harpoon with barb up from bar
        '\u2953': TokenType.IDENT,   # Rightwards harpoon with barb up from bar
        '\u2954': TokenType.IDENT,   # Upwards harpoon with barb right from bar
        '\u2955': TokenType.IDENT,   # Downwards harpoon with barb right from bar
        '\u2956': TokenType.IDENT,   # Leftwards harpoon with barb down above rightwards harpoon with barb up
        '\u2957': TokenType.IDENT,   # Rightwards harpoon with barb down above leftwards harpoon with barb up
        '\u2958': TokenType.IDENT,   # Upwards harpoon with barb left beside downwards harpoon with barb right
        '\u2959': TokenType.IDENT,   # Downwards harpoon with barb left beside upwards harpoon with barb right
        '\u295a': TokenType.IDENT,   # Leftwards harpoon with barb up above leftwards harpoon with barb down
        '\u295b': TokenType.IDENT,   # Upwards harpoon with barb left beside upwards harpoon with barb right
        '\u295c': TokenType.IDENT,   # Rightwards harpoon with barb up above rightwards harpoon with barb down
        '\u295d': TokenType.IDENT,   # Downwards harpoon with barb left beside downwards harpoon with barb right
        '\u295e': TokenType.IDENT,   # Leftwards harpoon with barb up above rightwards harpoon with barb up
        '\u295f': TokenType.IDENT,   # Upwards harpoon with barb left beside upwards harpoon with barb right
        '\u2a2f': TokenType.STAR,    # Vector or cross product
        '\u29f8': TokenType.DIV,     # Big solidus
        '\u2308': TokenType.LBRACKET,  # Left ceiling
        '\u2309': TokenType.RBRACKET,  # Right ceiling
        '\u230a': TokenType.LBRACKET,  # Left floor
        '\u230b': TokenType.RBRACKET,  # Right floor
        '\u208a': TokenType.PLUS,    # Subscript plus
        '\u208b': TokenType.MINUS,   # Subscript minus
        '\u2020': TokenType.IDENT,   # Dagger
        '\u2021': TokenType.IDENT,   # Double dagger
        '\u27c2': TokenType.IDENT,   # Perpendicular
        '\u2720': TokenType.IDENT,   # Maltese cross
        '\u25ef': TokenType.IDENT,   # Large circle
        '\u25b3': TokenType.IDENT,   # White up-pointing triangle
        '\u25b2': TokenType.IDENT,   # Black up-pointing triangle
        '\u25bd': TokenType.IDENT,   # White down-pointing triangle
        '\u25bc': TokenType.IDENT,   # Black down-pointing triangle
        '\u25c0': TokenType.LT,      # Black left-pointing triangle
        '\u25b6': TokenType.GT,      # Black right-pointing triangle
        '\u25b7': TokenType.GT,      # White right-pointing triangle
        '\u25c1': TokenType.LT,      # White left-pointing triangle
        '\u25cb': TokenType.IDENT,   # White circle
        '\u25cf': TokenType.IDENT,   # Black circle
        '\u2605': TokenType.STAR,    # Black star
        '\u2606': TokenType.STAR,    # White star
        '\u2639': TokenType.IDENT,   # White frowning face
        '\u263a': TokenType.IDENT,   # White smiling face
        '\u263b': TokenType.IDENT,   # Black smiling face
        '\u2102': TokenType.IDENT,   # Double-struck capital C
        '\u210d': TokenType.IDENT,   # Double-struck capital H
        '\u2115': TokenType.IDENT,   # Double-struck capital N
        '\u2119': TokenType.IDENT,   # Double-struck capital P
        '\u211a': TokenType.IDENT,   # Double-struck capital Q
        '\u211d': TokenType.IDENT,   # Double-struck capital R
        '\u2124': TokenType.IDENT,   # Double-struck capital Z
        '\u2145': TokenType.IDENT,   # Double-struck italic capital D
        '\u2146': TokenType.IDENT,   # Double-struck italic small d
        '\u2147': TokenType.IDENT,   # Double-struck italic small e
        '\u2148': TokenType.IDENT,   # Double-struck italic small i
        '\u2149': TokenType.IDENT,   # Double-struck italic small j
        '\u2135': TokenType.IDENT,   # Alef symbol
        '\u2136': TokenType.IDENT,   # Bet symbol
        '\u2137': TokenType.IDENT,   # Gimel symbol
        '\u2138': TokenType.IDENT,   # Dalet symbol
        '\u220f': TokenType.IDENT,   # N-ary product
        '\u2210': TokenType.IDENT,   # N-ary coproduct
        '\u2211': TokenType.IDENT,   # N-ary summation
        '\u2213': TokenType.IDENT,   # Minus-or-plus sign
        '\u2214': TokenType.IDENT,   # Dot plus
        '\u2216': TokenType.DIV,     # Set minus
        '\u2217': TokenType.STAR,    # Asterisk operator
        '\u2218': TokenType.IDENT,   # Ring operator
        '\u2219': TokenType.STAR,    # Bullet operator
        '\u221a': TokenType.IDENT,   # Square root
        '\u221b': TokenType.IDENT,   # Cube root
        '\u221c': TokenType.IDENT,   # Fourth root
        '\u221d': TokenType.IDENT,   # Proportional to
        '\u221f': TokenType.IDENT,   # Right angle
        '\u2220': TokenType.IDENT,   # Angle
        '\u2221': TokenType.IDENT,   # Measured angle
        '\u2222': TokenType.IDENT,   # Spherical angle
        '\u2224': TokenType.IDENT,   # Does not divide
        '\u2226': TokenType.IDENT,   # Not parallel to
        '\u2227': TokenType.IDENT,   # Logical and
        '\u2228': TokenType.IDENT,   # Logical or
        '\u2229': TokenType.IDENT,   # Intersection
        '\u222a': TokenType.IDENT,   # Union
        '\u222b': TokenType.IDENT,   # Integral
        '\u222c': TokenType.IDENT,   # Double integral
        '\u222d': TokenType.IDENT,   # Triple integral
        '\u222e': TokenType.IDENT,   # Contour integral
        '\u222f': TokenType.IDENT,   # Surface integral
        '\u2230': TokenType.IDENT,   # Volume integral
        '\u2231': TokenType.IDENT,   # Clockwise integral
        '\u2232': TokenType.IDENT,   # Clockwise contour integral
        '\u2233': TokenType.IDENT,   # Anticlockwise contour integral
        '\u2234': TokenType.IDENT,   # Therefore
        '\u2235': TokenType.IDENT,   # Because
        '\u2236': TokenType.COLON,   # Ratio
        '\u2237': TokenType.COLON,   # Proportion
        '\u2238': TokenType.IDENT,   # Dot minus
        '\u2239': TokenType.IDENT,   # Excess
        '\u223a': TokenType.IDENT,   # Geometric proportion
        '\u223b': TokenType.IDENT,   # Homothetic
        '\u223c': TokenType.TILDE,   # Tilde operator
        '\u223d': TokenType.TILDE,   # Reversed tilde
        '\u223e': TokenType.IDENT,   # Inverted lazy s
        '\u223f': TokenType.IDENT,   # Sine wave
        '\u2240': TokenType.IDENT,   # Wreath product
        '\u2241': TokenType.IDENT,   # Not tilde
        '\u2242': TokenType.IDENT,   # Minus tilde
        '\u2243': TokenType.IDENT,   # Asymptotically equal to
        '\u2244': TokenType.IDENT,   # Not asymptotically equal to
        '\u2245': TokenType.IDENT,   # Approximately equal to
        '\u2246': TokenType.IDENT,   # Approximately but not actually equal to
        '\u2247': TokenType.IDENT,   # Neither approximately nor actually equal to
        '\u2248': TokenType.IDENT,   # Almost equal to
        '\u2249': TokenType.IDENT,   # Not almost equal to
        '\u224a': TokenType.IDENT,   # Almost equal or equal to
        '\u224b': TokenType.IDENT,   # Triple tilde
        '\u224c': TokenType.IDENT,   # All equal to
        '\u224d': TokenType.IDENT,   # Equivalent to
        '\u224e': TokenType.IDENT,   # Geometrically equivalent to
        '\u224f': TokenType.IDENT,   # Difference between
        '\u2250': TokenType.IDENT,   # Approaches the limit
        '\u2251': TokenType.IDENT,   # Geometrically equal to
        '\u2252': TokenType.IDENT,   # Approximately equal to or the image of
        '\u2253': TokenType.IDENT,   # Image of or approximately equal to
        '\u2254': TokenType.COLONEQ,  # Colon equals
        '\u2255': TokenType.COLONEQ,  # Equals colon
        '\u2256': TokenType.IDENT,   # Ring in equal to
        '\u2257': TokenType.IDENT,   # Ring equal to
        '\u2258': TokenType.IDENT,   # Corresponds to
        '\u2259': TokenType.IDENT,   # Estimates
        '\u225a': TokenType.IDENT,   # Equiangular to
        '\u225b': TokenType.IDENT,   # Star equals
        '\u225c': TokenType.IDENT,   # Delta equal to
        '\u225d': TokenType.IDENT,   # Equal to by definition
        '\u225e': TokenType.IDENT,   # Measured by
        '\u225f': TokenType.IDENT,   # Questioned equal to
        '\u2260': TokenType.NE,      # Not equal to
        '\u2261': TokenType.IDENT,   # Identical to
        '\u2262': TokenType.IDENT,   # Not identical to
        '\u2263': TokenType.IDENT,   # Strictly equivalent to
        '\u2264': TokenType.LE,      # Less-than or equal to
        '\u2265': TokenType.GE,      # Greater-than or equal to
        '\u2266': TokenType.LE,      # Less-than over equal to
        '\u2267': TokenType.GE,      # Greater-than over equal to
        '\u2268': TokenType.LT,      # Less-than but not equal to
        '\u2269': TokenType.GT,      # Greater-than but not equal to
        '\u226a': TokenType.LT,      # Much less-than
        '\u226b': TokenType.GT,      # Much greater-than
        '\u226c': TokenType.IDENT,   # Between
        '\u226d': TokenType.IDENT,   # Not equivalent to
        '\u226e': TokenType.LT,      # Not less-than
        '\u226f': TokenType.GT,      # Not greater-than
        '\u2270': TokenType.LE,      # Neither less-than nor equal to
        '\u2271': TokenType.GE,      # Neither greater-than nor equal to
        '\u2272': TokenType.LE,      # Less-than or equivalent to
        '\u2273': TokenType.GE,      # Greater-than or equivalent to
        '\u2274': TokenType.LT,      # Neither less-than nor equivalent to
        '\u2275': TokenType.GT,      # Neither greater-than nor equivalent to
        '\u2276': TokenType.LT,      # Less-than or greater-than
        '\u2277': TokenType.GT,      # Greater-than or less-than
        '\u2278': TokenType.LT,      # Neither less-than nor greater-than
        '\u2279': TokenType.GT,      # Neither greater-than nor less-than
        '\u227a': TokenType.LT,      # Precedes
        '\u227b': TokenType.GT,      # Succeeds
        '\u227c': TokenType.LE,      # Precedes or equal to
        '\u227d': TokenType.GE,      # Succeeds or equal to
        '\u227e': TokenType.LT,      # Precedes or equivalent to
        '\u227f': TokenType.GT,      # Succeeds or equivalent to
        '\u2280': TokenType.LT,      # Does not precede
        '\u2281': TokenType.GT,      # Does not succeed
        '\u2282': TokenType.LT,      # Subset of
        '\u2283': TokenType.GT,      # Superset of
        '\u2284': TokenType.LT,      # Not a subset of
        '\u2285': TokenType.GT,      # Not a superset of
        '\u2286': TokenType.LE,      # Subset of or equal to
        '\u2287': TokenType.GE,      # Superset of or equal to
        '\u2288': TokenType.LE,      # Neither a subset of nor equal to
        '\u2289': TokenType.GE,      # Neither a superset of nor equal to
        '\u228a': TokenType.LE,      # Subset of with not equal to
        '\u228b': TokenType.GE,      # Superset of with not equal to
        '\u228c': TokenType.IDENT,   # Multiset
        '\u228d': TokenType.IDENT,   # Multiset multiplication
        '\u228e': TokenType.IDENT,   # Multiset union
        '\u228f': TokenType.LT,      # Square image of
        '\u2290': TokenType.GT,      # Square original of
        '\u2291': TokenType.LE,      # Square image of or equal to
        '\u2292': TokenType.GE,      # Square original of or equal to
        '\u2293': TokenType.IDENT,   # Square cap
        '\u2294': TokenType.IDENT,   # Square cup
        '\u2295': TokenType.IDENT,   # Circled plus
        '\u2296': TokenType.IDENT,   # Circled minus
        '\u2297': TokenType.IDENT,   # Circled times
        '\u2298': TokenType.IDENT,   # Circled division slash
        '\u2299': TokenType.IDENT,   # Circled dot operator
        '\u229a': TokenType.IDENT,   # Circled ring operator
        '\u229b': TokenType.IDENT,   # Circled asterisk operator
        '\u229c': TokenType.IDENT,   # Circled equals
        '\u229d': TokenType.IDENT,   # Circled dash
        '\u229e': TokenType.IDENT,   # Squared plus
        '\u229f': TokenType.IDENT,   # Squared minus
        '\u22a0': TokenType.IDENT,   # Squared times
        '\u22a1': TokenType.IDENT,   # Squared dot operator
        '\u22a2': TokenType.IDENT,   # Right tack
        '\u22a3': TokenType.IDENT,   # Left tack
        '\u22a4': TokenType.IDENT,   # Down tack
        '\u22a5': TokenType.IDENT,   # Up tack
        '\u22a6': TokenType.IDENT,   # Assertion
        '\u22a7': TokenType.IDENT,   # Models
        '\u22a8': TokenType.IDENT,   # True
        '\u22a9': TokenType.IDENT,   # Forces
        '\u22aa': TokenType.IDENT,   # Triple vertical bar right turnstile
        '\u22ab': TokenType.IDENT,   # Double vertical bar double right turnstile
        '\u22ac': TokenType.IDENT,   # Does not prove
        '\u22ad': TokenType.IDENT,   # Not true
        '\u22ae': TokenType.IDENT,   # Does not force
        '\u22af': TokenType.IDENT,   # Negated double vertical bar double right turnstile
        '\u22b0': TokenType.IDENT,   # Precedes under relation
        '\u22b1': TokenType.IDENT,   # Succeeds under relation
        '\u22b2': TokenType.IDENT,   # Normal subgroup of
        '\u22b3': TokenType.IDENT,   # Contains as normal subgroup
        '\u22b4': TokenType.LE,      # Normal subgroup of or equal to
        '\u22b5': TokenType.GE,      # Contains as normal subgroup or equal to
        '\u22b6': TokenType.IDENT,   # Original of
        '\u22b7': TokenType.IDENT,   # Image of
        '\u22b8': TokenType.IDENT,   # Multimap
        '\u22b9': TokenType.IDENT,   # Hermitian conjugate matrix
        '\u22ba': TokenType.IDENT,   # Intercalate
        '\u22bb': TokenType.IDENT,   # Xor
        '\u22bc': TokenType.IDENT,   # Nand
        '\u22bd': TokenType.IDENT,   # Nor
        '\u22be': TokenType.IDENT,   # Right angle with arc
        '\u22bf': TokenType.IDENT,   # Right triangle
        '\u22c0': TokenType.IDENT,   # N-ary logical and
        '\u22c1': TokenType.IDENT,   # N-ary logical or
        '\u22c2': TokenType.IDENT,   # N-ary intersection
        '\u22c3': TokenType.IDENT,   # N-ary union
        '\u22c4': TokenType.IDENT,   # Diamond operator
        '\u22c5': TokenType.STAR,    # Dot operator
        '\u22c6': TokenType.STAR,    # Star operator
        '\u22c7': TokenType.IDENT,   # Division times
        '\u22c8': TokenType.IDENT,   # Bowtie
        '\u22c9': TokenType.IDENT,   # Left normal factor semidirect product
        '\u22ca': TokenType.IDENT,   # Right normal factor semidirect product
        '\u22cb': TokenType.IDENT,   # Left semidirect product
        '\u22cc': TokenType.IDENT,   # Right semidirect product
        '\u22cd': TokenType.IDENT,   # Reversed tilde equals
        '\u22ce': TokenType.IDENT,   # Curly logical or
        '\u22cf': TokenType.IDENT,   # Curly logical and
        '\u22d0': TokenType.IDENT,   # Double subset
        '\u22d1': TokenType.IDENT,   # Double superset
        '\u22d2': TokenType.IDENT,   # Double intersection
        '\u22d3': TokenType.IDENT,   # Double union
        '\u22d4': TokenType.IDENT,   # Pitchfork
        '\u22d5': TokenType.IDENT,   # Equal and parallel to
        '\u22d6': TokenType.LT,      # Less-than with dot
        '\u22d7': TokenType.GT,      # Greater-than with dot
        '\u22d8': TokenType.LT,      # Very much less-than
        '\u22d9': TokenType.GT,      # Very much greater-than
        '\u22da': TokenType.LE,      # Less-than equal to or greater-than
        '\u22db': TokenType.GE,      # Greater-than equal to or less-than
        '\u22dc': TokenType.LE,      # Equal to or less-than
        '\u22dd': TokenType.GE,      # Equal to or greater-than
        '\u22de': TokenType.LE,      # Equal to or precedes
        '\u22df': TokenType.GE,      # Equal to or succeeds
        '\u22e0': TokenType.IDENT,   # Does not precede or equal
        '\u22e1': TokenType.IDENT,   # Does not succeed or equal
        '\u22e2': TokenType.IDENT,   # Not square image of or equal to
        '\u22e3': TokenType.IDENT,   # Not square original of or equal to
        '\u22e4': TokenType.IDENT,   # Square image of or not equal to
        '\u22e5': TokenType.IDENT,   # Square original of or not equal to
        '\u22e6': TokenType.LT,      # Less-than but not equivalent to
        '\u22e7': TokenType.GT,      # Greater-than but not equivalent to
        '\u22e8': TokenType.LT,      # Precedes but not equivalent to
        '\u22e9': TokenType.GT,      # Succeeds but not equivalent to
        '\u22ea': TokenType.IDENT,   # Not normal subgroup of
        '\u22eb': TokenType.IDENT,   # Does not contain as normal subgroup
        '\u22ec': TokenType.IDENT,   # Not normal subgroup of or equal to
        '\u22ed': TokenType.IDENT,   # Does not contain as normal subgroup or equal
        '\u22ee': TokenType.IDENT,   # Vertical ellipsis
        '\u22ef': TokenType.IDENT,   # Midline horizontal ellipsis
        '\u22f0': TokenType.IDENT,   # Up right diagonal ellipsis
        '\u22f1': TokenType.IDENT,   # Down right diagonal ellipsis
        '\u2300': TokenType.IDENT,   # Diameter sign
        '\u2302': TokenType.IDENT,   # House
        '\u2303': TokenType.IDENT,   # Up arrowhead
        '\u2304': TokenType.IDENT,   # Down arrowhead
        '\u2305': TokenType.IDENT,   # Projective
        '\u2306': TokenType.IDENT,   # Perspective
        '\u2307': TokenType.IDENT,   # Wavy line
        '\u2310': TokenType.IDENT,   # Reversed not sign
        '\u2311': TokenType.IDENT,   # Square lozenge
        '\u2312': TokenType.IDENT,   # Arc
        '\u2313': TokenType.IDENT,   # Segment
        '\u2315': TokenType.IDENT,   # Recorder
        '\u2316': TokenType.IDENT,   # Position indicator
        '\u2317': TokenType.IDENT,   # Viewdata square
        '\u2318': TokenType.IDENT,   # Place of interest sign
        '\u2319': TokenType.IDENT,   # Turned not sign
        '\u231a': TokenType.IDENT,   # Watch
        '\u231b': TokenType.IDENT,   # Hourglass
        '\u2324': TokenType.IDENT,   # Up arrowhead between two horizontal bars
        '\u2325': TokenType.IDENT,   # Option key
        '\u2326': TokenType.IDENT,   # Erase to the right
        '\u2327': TokenType.IDENT,   # X in a rectangle box
        '\u2328': TokenType.IDENT,   # Keyboard
        '\u232b': TokenType.IDENT,   # Erase to the left
        '\u232c': TokenType.IDENT,   # Benzene ring
        '\u237c': TokenType.IDENT,   # Angled dash
        '\u2394': TokenType.IDENT,   # Software-function symbol
        '\u239b': TokenType.IDENT,   # Left parenthesis upper hook
        '\u239c': TokenType.IDENT,   # Left parenthesis extension
        '\u239d': TokenType.IDENT,   # Left parenthesis lower hook
        '\u239e': TokenType.IDENT,   # Right parenthesis upper hook
        '\u239f': TokenType.IDENT,   # Right parenthesis extension
        '\u23a0': TokenType.IDENT,   # Right parenthesis lower hook
        '\u23a1': TokenType.IDENT,   # Left square bracket upper corner
        '\u23a2': TokenType.IDENT,   # Left square bracket extension
        '\u23a3': TokenType.IDENT,   # Left square bracket lower corner
        '\u23a4': TokenType.IDENT,   # Right square bracket upper corner
        '\u23a5': TokenType.IDENT,   # Right square bracket extension
        '\u23a6': TokenType.IDENT,   # Right square bracket lower corner
        '\u23a7': TokenType.IDENT,   # Left curly bracket upper hook
        '\u23a8': TokenType.IDENT,   # Left curly bracket middle piece
        '\u23a9': TokenType.IDENT,   # Left curly bracket lower hook
        '\u23aa': TokenType.IDENT,   # Curly bracket extension
        '\u23ab': TokenType.IDENT,   # Right curly bracket upper hook
        '\u23ac': TokenType.IDENT,   # Right curly bracket middle piece
        '\u23ad': TokenType.IDENT,   # Right curly bracket lower hook
        '\u23ae': TokenType.IDENT,   # Integral extension
        '\u23af': TokenType.IDENT,   # Horizontal line extension
        '\u23b0': TokenType.IDENT,   # Upper left or lower right curly bracket section
        '\u23b1': TokenType.IDENT,   # Upper right or lower left curly bracket section
        '\u23b2': TokenType.IDENT,   # Summation top
        '\u23b3': TokenType.IDENT,   # Summation bottom
        '\u23b4': TokenType.IDENT,   # Top square bracket
        '\u23b5': TokenType.IDENT,   # Bottom square bracket
        '\u23b6': TokenType.IDENT,   # Bottom square bracket over top square bracket
        '\u23b7': TokenType.IDENT,   # Radical symbol bottom
        '\u23b8': TokenType.IDENT,   # Left vertical box line
        '\u23b9': TokenType.IDENT,   # Right vertical box line
        '\u23ba': TokenType.IDENT,   # Horizontal scan line-1
        '\u23bb': TokenType.IDENT,   # Horizontal scan line-3
        '\u23bc': TokenType.IDENT,   # Horizontal scan line-7
        '\u23bd': TokenType.IDENT,   # Horizontal scan line-9
        '\u23be': TokenType.IDENT,   # Dentistry symbol light vertical and top right
        '\u23bf': TokenType.IDENT,   # Dentistry symbol light vertical and bottom right
        '\u23c0': TokenType.IDENT,   # Dentistry symbol light vertical with circle
        '\u23c1': TokenType.IDENT,   # Dentistry symbol light down and horizontal with circle
        '\u23c2': TokenType.IDENT,   # Dentistry symbol light up and horizontal with circle
        '\u23c3': TokenType.IDENT,   # Dentistry symbol light vertical with triangle
        '\u23c4': TokenType.IDENT,   # Dentistry symbol light down and horizontal with triangle
        '\u23c5': TokenType.IDENT,   # Dentistry symbol light up and horizontal with triangle
        '\u23c6': TokenType.IDENT,   # Dentistry symbol light vertical and wave
        '\u23c7': TokenType.IDENT,   # Dentistry symbol light down and horizontal with wave
        '\u23c8': TokenType.IDENT,   # Dentistry symbol light up and horizontal with wave
        '\u23c9': TokenType.IDENT,   # Dentistry symbol light down and horizontal
        '\u23ca': TokenType.IDENT,   # Dentistry symbol light up and horizontal
        '\u23cb': TokenType.IDENT,   # Dentistry symbol light vertical and top left
        '\u23cc': TokenType.IDENT,   # Dentistry symbol light vertical and bottom left
        '\u23cd': TokenType.IDENT,   # Square foot
        '\u23ce': TokenType.IDENT,   # Return symbol
        '\u23cf': TokenType.IDENT,   # Eject symbol
        '\u23d0': TokenType.IDENT,   # Vertical line extension
        '\u23d1': TokenType.IDENT,   # Metrical breve
        '\u23d2': TokenType.IDENT,   # Metrical long over short
        '\u23d3': TokenType.IDENT,   # Metrical short over long
        '\u23d4': TokenType.IDENT,   # Metrical long over two shorts
        '\u23d5': TokenType.IDENT,   # Metrical two shorts over long
        '\u23d6': TokenType.IDENT,   # Metrical two shorts joined
        '\u23d7': TokenType.IDENT,   # Metrical triseme
        '\u23d8': TokenType.IDENT,   # Metrical tetraseme
        '\u23d9': TokenType.IDENT,   # Metrical pentaseme
        '\u23da': TokenType.IDENT,   # Earth ground
        '\u23db': TokenType.IDENT,   # Fuse
        '\u23dc': TokenType.IDENT,   # Top parenthesis
        '\u23dd': TokenType.IDENT,   # Bottom parenthesis
        '\u23de': TokenType.IDENT,   # Top curly bracket
        '\u23df': TokenType.IDENT,   # Bottom curly bracket
        '\u23e0': TokenType.IDENT,   # Top tortoise shell bracket
        '\u23e1': TokenType.IDENT,   # Bottom tortoise shell bracket
        '\u23e2': TokenType.IDENT,   # White trapezium
        '\u23e3': TokenType.IDENT,   # Benzene ring with circle
        '\u23e4': TokenType.IDENT,   # Straightness
        '\u23e5': TokenType.IDENT,   # Flatness
        '\u23e6': TokenType.IDENT,   # Ac current
        '\u23e7': TokenType.IDENT,   # Electrical intersection
        '\u2b1d': TokenType.IDENT,   # Black very small square (⬝)
        '\u2045': TokenType.LBRACKET, # Left square bracket with quill (⁅)
        '\u2046': TokenType.RBRACKET, # Right square bracket with quill (⁆)
        '\u2a0d': TokenType.IDENT,   # Finite part integral (⨍)
        '\u2a0e': TokenType.IDENT,   # Integral with double stroke (⨎)
        '\u2a0f': TokenType.IDENT,   # Integral average with slash (⨏)
        '\u2a10': TokenType.IDENT,   # Circulation function (⨐)
        '\u2a11': TokenType.IDENT,   # Anticlockwise integration (⨑)
        '\u2a12': TokenType.IDENT,   # Line integration with rectangular path (⨒)
        '\u2a13': TokenType.IDENT,   # Line integration with semicircular path (⨓)
        '\u2a14': TokenType.IDENT,   # Line integration with circular path (⨔)
        '\u2a15': TokenType.IDENT,   # Integral around a point operator (⨕)
        '\u2a16': TokenType.IDENT,   # Quaternion integral operator (⨖)
        '\u2a17': TokenType.IDENT,   # Integral with leftwards arrow (⨗)
        '\u2a18': TokenType.IDENT,   # Integral with times sign (⨘)
        '\u2a19': TokenType.IDENT,   # Integral with intersection (⨙)
        '\u2a1a': TokenType.IDENT,   # Integral with union (⨚)
        '\u2a1b': TokenType.IDENT,   # Integral with overbar (⨛)
        '\u2a1c': TokenType.IDENT,   # Integral with underbar (⨜)
        '\u266f': TokenType.IDENT,   # Music sharp sign (♯)
        '\u0302': TokenType.IDENT,   # Combining circumflex accent (̂)
        '\u2197': TokenType.ARROW,   # North east arrow (↗)
        '\u235f': TokenType.IDENT,   # APL circle star (⍟)
        '\u21be': TokenType.IDENT,   # Upwards harpoon with barb rightwards (↾)
        '\u21bf': TokenType.IDENT,   # Upwards harpoon with barb leftwards (↿)
        '\u21c2': TokenType.IDENT,   # Downwards harpoon with barb rightwards (⇂)
        '\u21c3': TokenType.IDENT,   # Downwards harpoon with barb leftwards (⇃)
        '\u25eb': TokenType.IDENT,   # White square with vertical bisecting line (◫)
        '\u25ec': TokenType.IDENT,   # White triangle with vertical bisecting line (◬)
        '\u25ed': TokenType.IDENT,   # White triangle with lower left quadrant (◭)
        '\u25ee': TokenType.IDENT,   # White triangle with lower right quadrant (◮)
        '\u25f0': TokenType.IDENT,   # White square with upper left quadrant (◰)
        '\u25f1': TokenType.IDENT,   # White square with lower left quadrant (◱)
        '\u25f2': TokenType.IDENT,   # White square with lower right quadrant (◲)
        '\u25f3': TokenType.IDENT,   # White square with upper right quadrant (◳)
        '\u25f4': TokenType.IDENT,   # White circle with upper left quadrant (◴)
        '\u25f5': TokenType.IDENT,   # White circle with lower left quadrant (◵)
        '\u25f6': TokenType.IDENT,   # White circle with lower right quadrant (◶)
        '\u25f7': TokenType.IDENT,   # White circle with upper right quadrant (◷)
    }

    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []
        self.indent_stack = [0]

    def error(self, msg: str) -> None:
        raise LexerError(f"{self.line}:{self.column}: {msg}")

    def peek(self, offset: int = 0) -> str:
        pos = self.pos + offset
        if pos < 0 or pos >= len(self.source):
            return '\0'
        return self.source[pos]

    def advance(self) -> str:
        if self.pos >= len(self.source):
            return '\0'
        char = self.source[self.pos]
        self.pos += 1
        if char == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char

    def skip_whitespace(self, track_indent: bool = False) -> Optional[Token]:
        start_line = self.line
        start_col = self.column
        spaces = 0

        while self.peek() in ' \t\r':
            if self.peek() == ' ':
                spaces += 1
            elif self.peek() == '\t':
                spaces += 4
            self.advance()

        if track_indent and self.peek() not in '\n\0' and self.line > start_line:
            # New line with indentation
            current_indent = self.indent_stack[-1]
            if spaces > current_indent:
                self.indent_stack.append(spaces)
                return Token(TokenType.INDENT, '', start_line, start_col, ' ' * spaces)
            elif spaces < current_indent:
                while spaces < self.indent_stack[-1]:
                    self.indent_stack.pop()
                if spaces != self.indent_stack[-1]:
                    self.error("Inconsistent indentation")
                return Token(TokenType.DEDENT, '', start_line, start_col, '')

        return None

    def read_string(self) -> Token:
        start_line = self.line
        start_col = self.column
        raw_chars = [self.advance()]  # Opening "
        result = []

        while self.peek() != '"' and self.peek() != '\0':
            if self.peek() == '\\':
                raw_chars.append(self.advance())
                escape = self.advance()
                raw_chars.append(escape)
                if escape == 'n':
                    result.append('\n')
                elif escape == 't':
                    result.append('\t')
                elif escape == '\\':
                    result.append('\\')
                elif escape == '"':
                    result.append('"')
                elif escape == "'":
                    result.append("'")
                else:
                    result.append(escape)
            else:
                char = self.advance()
                result.append(char)
                raw_chars.append(char)

        if self.peek() != '"':
            self.error("Unterminated string literal")

        raw_chars.append(self.advance())  # Closing "
        raw = ''.join(raw_chars)
        return Token(TokenType.STRING, ''.join(result), start_line, start_col, raw)

    def read_char(self) -> Token:
        start_line = self.line
        start_col = self.column
        raw_chars = [self.advance()]  # Opening '

        if self.peek() == '\\':
            raw_chars.append(self.advance())
            escape = self.advance()
            raw_chars.append(escape)
            if escape == 'n':
                value = '\n'
            elif escape == 't':
                value = '\t'
            elif escape == '\\':
                value = '\\'
            elif escape == "'":
                value = "'"
            else:
                value = escape
        else:
            char = self.advance()
            value = char
            raw_chars.append(char)

        if self.peek() != "'":
            self.error("Unterminated character literal")

        raw_chars.append(self.advance())  # Closing '
        raw = ''.join(raw_chars)
        return Token(TokenType.CHAR, value, start_line, start_col, raw)

    def read_line_comment(self) -> Token:
        start_line = self.line
        start_col = self.column
        result = []

        while self.peek() != '\n' and self.peek() != '\0':
            result.append(self.advance())

        raw = ''.join(result)
        return Token(TokenType.LINE_COMMENT, ''.join(result), start_line, start_col, raw)

    def read_block_comment(self) -> Token:
        start_line = self.line
        start_col = self.column
        result = []

        # Save the start markers for raw
        raw_prefix = '/-'
        depth = 1

        self.advance()  # /
        self.advance()  # -

        while depth > 0 and self.peek() != '\0':
            if self.peek() == '/' and self.peek(1) == '-':
                depth += 1
                result.append(self.advance())
                result.append(self.advance())
            elif self.peek() == '-' and self.peek(1) == '/':
                depth -= 1
                result.append(self.advance())
                result.append(self.advance())
            else:
                result.append(self.advance())

        raw = raw_prefix + ''.join(result)
        content = ''.join(result)[:-2] if result else ''
        return Token(TokenType.BLOCK_COMMENT, content, start_line, start_col, raw)

    def read_doc_comment(self) -> Token:
        start_line = self.line
        start_col = self.column
        result = []

        self.advance()  # /
        self.advance()  # -
        self.advance()  # -

        while self.peek() != '\0':
            if self.peek() == '-' and self.peek(1) == '/' and self.peek(2) != '-':
                result.append(self.advance())
                result.append(self.advance())
                break
            else:
                result.append(self.advance())

        raw = '/-- ' + ''.join(result)
        content = ''.join(result)[:-2] if len(result) >= 2 else ''.join(result)
        return Token(TokenType.DOC, content, start_line, start_col, raw)

    def read_mod_doc(self) -> Token:
        start_line = self.line
        start_col = self.column
        result = []

        self.advance()  # /
        self.advance()  # -
        self.advance()  # !

        depth = 1
        while depth > 0 and self.peek() != '\0':
            if self.peek() == '/' and self.peek(1) == '-':
                depth += 1
                result.append(self.advance())  # /
                result.append(self.advance())  # -
            elif self.peek() == '-' and self.peek(1) == '/':
                depth -= 1
                result.append(self.advance())
                result.append(self.advance())
                break
            else:
                result.append(self.advance())

        raw = '/-!' + ''.join(result)
        content = ''.join(result)[:-2] if len(result) >= 2 else ''.join(result)
        return Token(TokenType.MOD_DOC, content, start_line, start_col, raw)

    def read_number(self) -> Token:
        start_line = self.line
        start_col = self.column
        result = []
        is_float = False

        while self.peek().isdigit():
            result.append(self.advance())

        if self.peek() == '.' and self.peek(1).isdigit():
            is_float = True
            result.append(self.advance())  # .
            while self.peek().isdigit():
                result.append(self.advance())

        if self.peek() in 'eE':
            is_float = True
            result.append(self.advance())
            if self.peek() in '+-':
                result.append(self.advance())
            while self.peek().isdigit():
                result.append(self.advance())

        raw = ''.join(result)
        token_type = TokenType.FLOAT if is_float else TokenType.NAT
        return Token(token_type, raw, start_line, start_col, raw)

    def is_unicode_letter(self, char: str) -> bool:
        """Check if character is a unicode letter suitable for identifiers."""
        if len(char) != 1:
            return False
        code = ord(char)
        # Include Greek letters, math symbols, and common unicode identifiers used in Lean
        return (0x0370 <= code <= 0x03FF or  # Greek
                0x1F00 <= code <= 0x1FFF or  # Extended Greek
                0x2100 <= code <= 0x214F or  # Letterlike Symbols
                0x2200 <= code <= 0x22FF)    # Mathematical Operators (∀, ∃, etc.)

    def is_id_start(self, char: str) -> bool:
        """Check if character can start an identifier."""
        return char.isalpha() or char == '_' or self.is_unicode_letter(char)

    def is_id_continue(self, char: str) -> bool:
        """Check if character can continue an identifier."""
        return (char.isalnum() or char in "_'!?" or
                char == 'ᵀ' or  # Transpose
                self.is_unicode_letter(char))

    def read_identifier(self) -> Token:
        start_line = self.line
        start_col = self.column
        result = []

        # First character must be a valid identifier start
        if self.is_id_start(self.peek()):
            result.append(self.advance())
        else:
            self.error(f"Invalid identifier start character: {self.peek()!r}")

        # Continue reading valid identifier characters
        while self.is_id_continue(self.peek()):
            result.append(self.advance())

        # Handle trailing apostrophes (x', x'', etc.)
        while self.peek() == "'":
            result.append(self.advance())

        raw = ''.join(result)

        if raw == '_':
            return Token(TokenType.UNDERSCORE, raw, start_line, start_col, raw)

        # Check for special commands (starting with #)
        if raw.startswith('#'):
            for cmd, token_type in self.SPECIAL_COMMANDS.items():
                if raw == cmd:
                    return Token(token_type, raw, start_line, start_col, raw)

        # Check for keywords
        token_type = self.KEYWORDS.get(raw, TokenType.IDENT)

        return Token(token_type, raw, start_line, start_col, raw)

    def read_apostrophe_identifier(self) -> Token:
        """Read an identifier that starts with apostrophe (continuation like x', [i]', etc.)."""
        start_line = self.line
        start_col = self.column
        result = []

        # Consume leading apostrophes
        while self.peek() == "'":
            result.append(self.advance())

        # Continue reading valid identifier characters
        while self.is_id_continue(self.peek()):
            result.append(self.advance())

        # Handle trailing apostrophes
        while self.peek() == "'":
            result.append(self.advance())

        raw = ''.join(result)
        return Token(TokenType.IDENT, raw, start_line, start_col, raw)

    def read_name(self) -> Token:
        start_line = self.line
        start_col = self.column
        result = []

        # Name literal like `name or «name with spaces»
        if self.peek() == '`':
            self.advance()
            # In Lean, `( is the start of a syntax quotation, not part of a name
            while self.peek() not in '` \t\n\r\0()[]{}':
                result.append(self.advance())

            content = ''.join(result)
            raw = '`' + content

            if not content:
                return Token(TokenType.BACKTICK, '`', start_line, start_col, '`')

            return Token(TokenType.IDENT, content, start_line, start_col, raw)
        elif self.peek() == '«':
            self.advance()
            while self.peek() != '»' and self.peek() != '\0':
                result.append(self.advance())
            if self.peek() == '»':
                self.advance()
            raw = '«' + ''.join(result) + '»'
            return Token(TokenType.IDENT, ''.join(result), start_line, start_col, raw)

        return self.read_identifier()

    def read_hash_command(self) -> Token:
        """Read #command like #check, #eval, etc."""
        start_line = self.line
        start_col = self.column
        self.advance()  # consume '#'

        # Read the command name
        if not self.peek().isalpha():
            # Just a # followed by non-alpha, treat as HASH token
            return Token(TokenType.HASH, '#', start_line, start_col, '#')

        result = []
        while self.peek().isalnum() or self.peek() == '_':
            result.append(self.advance())

        cmd = ''.join(result)
        raw = '#' + cmd

        # Map known commands
        cmd_map = {
            'check': TokenType.CHECK,
            'eval': TokenType.EVAL,
            'reduce': TokenType.REDUCE,
            'print': TokenType.PRINT,
            'sorry': TokenType.HASH_SORRY,
            'widget': TokenType.WIDGET,
            'gen_injective_theorems': TokenType.GEN_INJECTIVITY,
            'align': TokenType.ALIGN,
            'align_import': TokenType.ALIGN_IMPORT,
            'noalign': TokenType.NOALIGN,
        }

        token_type = cmd_map.get(cmd, TokenType.HASH)
        return Token(token_type, cmd, start_line, start_col, raw)

    def _next_token_inner(self) -> Token:
        # Skip whitespace (but don't track indentation for now)
        indent_token = self.skip_whitespace(track_indent=False)
        if indent_token:
            return indent_token

        start_line = self.line
        start_col = self.column
        char = self.peek()

        if char == '\0':
            return Token(TokenType.EOF, '', start_line, start_col, '')

        if char == '\n':
            self.advance()
            return Token(TokenType.NEWLINE, '\n', start_line, start_col, '\n')

        # Comments and doc comments
        if char == '-' and self.peek(1) == '-':
            return self.read_line_comment()

        if char == '/' and self.peek(1) == '-':
            if self.peek(2) == '!':
                return self.read_mod_doc()
            elif self.peek(2) == '-':
                return self.read_doc_comment()
            else:
                return self.read_block_comment()

        # String literals
        if char == '"':
            return self.read_string()

        # Character literals or identifier continuation (x', appFn!', [i]', '', =' etc.)
        if char == "'":
            # Check if it's part of an identifier
            # In Lean, ' can be: char literal ('a'), identifier suffix (x'), or standalone identifier
            prev = self.peek(-1)
            next_char = self.peek(1)
            next_next = self.peek(2)

            # Check for char literal pattern: 'X' or '\X' where X is any char and closing '
            # Single quote char: ''' (three apostrophes in source)
            is_char_literal = False
            if next_char == "'":
                # Double apostrophe '' - could be empty char (invalid) or start of '''
                if next_next == "'":
                    # Might be ''' (the single quote character literal)
                    is_char_literal = True
            elif next_char == "\\":
                # Escape sequence like '\n', '\t'
                if next_next not in '\0':
                    # Look for closing quote after escape
                    if self.peek(3) == "'":
                        is_char_literal = True
            elif next_char not in '\0':
                # Regular char like 'a', '='
                if next_next == "'":
                    is_char_literal = True

            if is_char_literal:
                return self.read_char()

            # It's an identifier continuation if:
            # - preceded by identifier char or specific symbols
            # - or followed by another '
            if (self.is_id_continue(prev) or
                prev in '])\'' or
                next_char == "'"):
                return self.read_apostrophe_identifier()
            else:
                return self.read_apostrophe_identifier()  # Standalone ' is also an identifier

        # Numbers
        if char.isdigit():
            return self.read_number()

        # Names with backticks or guillemets
        if char in '`«':
            return self.read_name()

        # #commands (#check, #eval, etc.)
        if char == '#':
            return self.read_hash_command()

        # Unicode operators
        if char in self.UNICODE_OPS:
            op = self.advance()
            # Handle ≃*, ≃+, ≃+* as combined operators
            if op == '≃':
                next_char = self.peek()
                if next_char == '*':
                    self.advance()
                    return Token(TokenType.IDENT, '≃*', start_line, start_col, '≃*')
                elif next_char == '+':
                    self.advance()
                    # Check for ≃+*
                    if self.peek() == '*':
                        self.advance()
                        return Token(TokenType.IDENT, '≃+*', start_line, start_col, '≃+*')
                    return Token(TokenType.IDENT, '≃+', start_line, start_col, '≃+')
            # Handle →* as combined operator
            if op == '→':
                if self.peek() == '*':
                    self.advance()
                    return Token(TokenType.IDENT, '→*', start_line, start_col, '→*')
            token_type = self.UNICODE_OPS[op]
            return Token(token_type, op, start_line, start_col, op)

        # Multi-character operators
        two_char = char + self.peek(1)
        if two_char == '->':
            self.advance()
            self.advance()
            return Token(TokenType.ARROW, '->', start_line, start_col, '->')
        if two_char == '=>':
            self.advance()
            self.advance()
            return Token(TokenType.DARROW, '=>', start_line, start_col, '=>')
        if two_char == '<-':
            self.advance()
            self.advance()
            return Token(TokenType.LARROW, '<-', start_line, start_col, '<-')
        if two_char == '<=':
            self.advance()
            self.advance()
            return Token(TokenType.LE, '<=', start_line, start_col, '<=')
        if two_char == '>=':
            self.advance()
            self.advance()
            return Token(TokenType.GE, '>=', start_line, start_col, '>=')
        if two_char == '::':
            self.advance()
            self.advance()
            return Token(TokenType.COLON2, '::', start_line, start_col, '::')
        if two_char == ':=':
            self.advance()
            self.advance()
            return Token(TokenType.COLONEQ, ':=', start_line, start_col, ':=')
        if two_char == '//':
            self.advance()
            self.advance()
            return Token(TokenType.DOUBLE_SLASH, '//', start_line, start_col, '//')

        # Single-character operators
        single_char_ops = {
            '=': TokenType.EQ,
            '<': TokenType.LT,
            '>': TokenType.GT,
            ':': TokenType.COLON,
            '+': TokenType.PLUS,
            '-': TokenType.MINUS,
            '*': TokenType.STAR,
            '/': TokenType.SLASH,
            '%': TokenType.PERCENT,
            '(': TokenType.LPAREN,
            ')': TokenType.RPAREN,
            '[': TokenType.LBRACKET,
            ']': TokenType.RBRACKET,
            '{': TokenType.LBRACE,
            '}': TokenType.RBRACE,
            ',': TokenType.COMMA,
            ';': TokenType.SEMI,
            '.': TokenType.DOT,
            '|': TokenType.BAR,
            '`': TokenType.BACKTICK,
            "'": TokenType.APOSTROPHE,
            '@': TokenType.AT,
            '!': TokenType.BANG,
            '?': TokenType.QUESTION,
            '^': TokenType.CARET,
            '~': TokenType.TILDE,
            '&': TokenType.AMPERSAND,
            '$': TokenType.DOLLAR,
            '\\': TokenType.BACKSLASH,
        }

        if char in single_char_ops:
            self.advance()
            return Token(single_char_ops[char], char, start_line, start_col, char)

        # Identifiers (including keywords and unicode letters)
        if self.is_id_start(char):
            return self.read_identifier()

        # Unknown character
        self.error(f"Unexpected character: {char!r}")
        return Token(TokenType.EOF, '', start_line, start_col, '')  # Never reached

    def next_token(self) -> Token:
        start_pos = self.pos
        token = self._next_token_inner()
        token.raw = self.source[start_pos:self.pos]
        return token

    def tokenize(self) -> List[Token]:
        """Tokenize the entire source code."""
        self.tokens = []
        while True:
            token = self.next_token()
            self.tokens.append(token)
            if token.type == TokenType.EOF:
                break
        return self.tokens

    def __iter__(self) -> Iterator[Token]:
        """Make lexer iterable."""
        if not self.tokens:
            self.tokenize()
        return iter(self.tokens)

