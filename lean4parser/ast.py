# ast.py
"""
Lean 4 AST Nodes - Simplified version with raw expressions.
"""
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, fields
from typing import List, Optional, Union, Dict


class ASTNode(ABC):
    """Base class for all AST nodes."""
    @abstractmethod
    def to_source(self) -> str:
        pass

    def lstrip_until_next_line(self, text):
        return re.sub(r'^[ ]*\n', '', text)

    def __str__(self) -> str:
        return self.to_source()

    def to_tree(self, indent: str = "", is_last: bool = True, max_depth: int = 10, current_depth: int = 0) -> str:
        marker = ("└── " if is_last else "├── ") if current_depth > 0 else ""
        res = f"{indent}{marker}{self.__class__.__name__}\n"
        if current_depth >= max_depth:
            if fields(self):
                res = res.rstrip() + " (...)\n"
            return res
        new_indent = indent + (("    " if is_last else "│   ") if current_depth > 0 else "")
        relevant_fields = []
        for f in fields(self):
            val = getattr(self, f.name)
            if val is not None and val != [] and val != {}:
                relevant_fields.append((f.name, val))
        for i, (label, value) in enumerate(relevant_fields):
            last_field = (i == len(relevant_fields) - 1)
            field_marker = "└── " if last_field else "├── "
            if isinstance(value, ASTNode):
                res += f"{new_indent}{field_marker}{label}:\n"
                child_indent = new_indent + ("    " if last_field else "│   ")
                res += value.to_tree(child_indent, True, max_depth, current_depth + 1)
            elif isinstance(value, list):
                res += f"{new_indent}{field_marker}{label}\n"
                list_indent = new_indent + ("    " if last_field else "│   ")
                if current_depth + 1 >= max_depth and value:
                    res += f"{list_indent}└── ...\n"
                    continue
                for j, item in enumerate(value):
                    last_item = (j == len(value) - 1)
                    if isinstance(item, ASTNode):
                        res += item.to_tree(list_indent, last_item, max_depth, current_depth + 2)
                    else:
                        item_marker = "└── " if last_item else "├── "
                        res += f"{list_indent}{item_marker}{repr(item)}\n"
            elif isinstance(value, dict):
                res += f"{new_indent}{field_marker}{label}\n"
                dict_indent = new_indent + ("    " if last_field else "│   ")
                if current_depth + 1 >= max_depth and value:
                    res += f"{dict_indent}└── ...\n"
                    continue
                items = list(value.items())
                for j, (k, v) in enumerate(items):
                    last_item = (j == len(items) - 1)
                    item_marker = "└── " if last_item else "├── "
                    res += f"{dict_indent}{item_marker}{k} → {v}\n"
            else:
                res += f"{new_indent}{field_marker}{label}: {repr(value)}\n"
        return res


@dataclass
class Modifier(ASTNode):
    """
    Represents a modifier.
    Pattern: (private|protected|noncomputable|partial|unsafe|mutual)
    Examples:
    - from ProverBench-15
    ```lean
    noncomputable
    ```
    - from MathOlympiadBench-105
    ```lean
    local
    ```
    """
    name: str

    def to_source(self) -> str:
        return self.name


@dataclass
class IgnoredContent(ASTNode):
    """
    Represents content ignored by the parser (e.g., after #exit).
    """
    content: str

    def to_source(self) -> str:
        return self.content

@dataclass
class RawExpr(ASTNode):
    """
    Represents a raw expression.
    Pattern: .*
    Examples:
    - from MiniF2F-1
    ```lean
    ℝ
    ```
    - from ProofNet-157
    ```lean
    ∃ ( x : I ) , f x = x
    ```
    - from PutnamBench-144
    ```lean
    Set ℝ → ( ℝ → ℝ ) → Prop
    ```
    - from PutnamBench-672
    ```lean
    IsGreatest 
     { r : ℝ | ∃ g : ℕ → ℕ , ( ∀ n : ℕ , 0 < n → 0 < g n ) ∧ 
     ∀ n : ℕ , 0 < n → ( ( g ( g n ) : ℝ ) ^ r ) ≤ ( g ( n + 1 ) : ℝ ) - ( g n : ℝ ) } 
     ( ( 1 / 4 ) : ℝ )
    ```
    """
    content: str

    def to_source(self) -> str:
        return self.content


@dataclass
class Comment(ASTNode):
    """
    Represents a comment.
    Pattern: /-.*-/ or --.*
    Examples:
    - from ProverBench-16
    ```lean
    /-
    All prime divisors of a number of the form n^8 - n^4 + 1, where n is a natural number,
    are of the form 24k + 1, where k is a natural number.
    -/
    ```
    - from ProverBench-148
    ```lean
    /-
    Let $f(x) = x^2 + 1$ be a polynomial over the finite field $\mathbb{Z}_2$. Then $f(x)$ has exactly one zero in $\mathbb{Z}_2$, namely $x = 1$.
    -/
    ```
    - from ProverBench-270
    ```lean
    -- Define the open interval (-1, 1)
    ```
    - from PutnamBench-672
    ```lean
    -- 1 / 4
    ```
    """
    content: str
    is_block: bool = False
    is_doc: bool = False
    is_mod_doc: bool = False

    def to_source(self) -> str:
        if self.is_mod_doc:
            return f"/-!{self.content}-/"
        elif self.is_doc:
            return f"/--{self.content}-/"
        elif self.is_block:
            return f"/-{self.content}-/"
        else:
            return f"{self.content}"


@dataclass
class Import(ASTNode):
    """
    Represents an import statement.
    Pattern: import (runtime )?<module>
    Examples:
    - from MiniF2F-1
    ```lean
    import Mathlib
    ```
    - from MiniF2F-1
    ```lean
    import Aesop
    ```
    - from ProverBench-145
    ```lean
    import Mathlib.Data.Real.Basic
    ```
    """
    module: str
    runtime: bool = False

    def to_source(self) -> str:
        if self.runtime:
            return f"import runtime {self.module}"
        return f"import {self.module}"


@dataclass
class Open(ASTNode):
    """
    Represents an open statement.
    Pattern: open (scoped )?<namespaces> (hiding <hiding>)? (renaming <renaming>)?
    Examples:
    - from ProverBench-35
    ```lean
    open Int
    ```
    - from PutnamBench-34
    ```lean
    open Set MvPolynomial
    ```
    - from PutnamBench-670
    ```lean
    open BigOperators Finset Matrix
    ```
    - from PutnamBench-352
    ```lean
    open Classical Polynomial Filter Topology Real Set Nat List
    ```
    """
    namespaces: List[str]
    hiding: Optional[List[str]] = None
    renaming: Optional[Dict[str, str]] = None
    abbrev: bool = False
    is_scoped: bool = False
    explicit: Optional[List[str]] = None

    def to_source(self) -> str:
        result = "open"
        if self.is_scoped:
            result += " scoped"
        result += ' ' + ' '.join(self.namespaces)
        if self.explicit:
            result += f" ({''.join(self.explicit)})"
        if self.abbrev:
            result += " abbrev"
        if self.hiding:
            result += f" hiding {''.join(self.hiding)}"
        if self.renaming:
            renames = ' '.join(f"{old} → {new}" for old, new in self.renaming.items())
            result += f" renaming {renames}"
        return result


@dataclass
class SetOption(ASTNode):
    """
    Represents a set_option statement.
    Pattern: set_option <name> <value>
    Examples:
    - from MiniF2F-1
    ```lean
    set_option maxHeartbeats 0
    ```
    - from PutnamBench-82
    ```lean
    set_option synthInstance.maxSize 127
    ```
    """
    name: str
    value: Union[bool, int, str]

    def to_source(self) -> str:
        if isinstance(self.value, bool):
            val_str = "true" if self.value else "false"
        else:
            val_str = str(self.value)
        return f"set_option {self.name} {val_str}"


@dataclass
class Align(ASTNode):
    """
    Represents an #align statement.
    Pattern: #align <old_name> <new_name>
    """
    old_name: str
    new_name: str

    def to_source(self) -> str:
        return f"#align {self.old_name} {self.new_name}"


@dataclass
class AlignImport(ASTNode):
    """
    Represents an #align_import statement.
    Pattern: #align_import <module> from "<source>"
    """
    module: str
    source: str

    def to_source(self) -> str:
        return f'#align_import {self.module} from "{self.source}"'


@dataclass
class NoAlign(ASTNode):
    """
    Represents a #noalign statement.
    Pattern: #noalign <name>
    """
    name: str

    def to_source(self) -> str:
        return f"#noalign {self.name}"


@dataclass
class Binder(ASTNode):
    """
    Represents a binder.
    Pattern: (<names> : <type>) or {<names> : <type>} or [<names> : <type>]
    Examples:
    - from MathOlympiadBench-157
    ```lean
    {x}
    ```
    - from MathOlympiadBench-57
    ```lean
    (hf : P a f)
    ```
    - from PutnamBench-277
    ```lean
    (f : Set . Ioi ( 0 : ℝ ) → Set . Ioi ( 0 : ℝ ))
    ```
    - from PutnamBench-390
    ```lean
    (F1 F2 U V A B C D P Q : EuclideanSpace ℝ ( Fin 2 ))
    ```
    """
    names: List[str]
    type: Optional[RawExpr] = None
    is_implicit: bool = False
    is_strict_implicit: bool = False
    is_inst_implicit: bool = False
    default_value: Optional[RawExpr] = None
    has_parens: bool = True

    def to_source(self) -> str:
        names_str = ' '.join(self.names)
        type_str = f" :{self.type.to_source()}" if self.type else ""
        if self.default_value:
            type_str += f" := {self.default_value.to_source()}"

        if self.is_inst_implicit and names_str == "_" and self.default_value is None:
            return f"[{self.type.to_source()}]"
        elif self.is_inst_implicit:
            return f"[{names_str}{type_str}]"
        elif self.is_strict_implicit:
            return f"⦃{names_str}{type_str}⦄"
        elif self.is_implicit:
            return f"{{{names_str}{type_str}}}"

        if not self.has_parens:
            return f"{names_str}{type_str}"
        return f"({names_str}{type_str})"


@dataclass
class Variable(ASTNode):
    """
    Represents a variable statement.
    Pattern: variable <binders>
    Examples:
    - from ProverBench-16
    ```lean
    variable (n : ℕ)
    ```
    - from ProverBench-224
    ```lean
    variable (x y : ℝ)
    ```
    - from ProverBench-119
    ```lean
    variable {k : ℕ} (x y : EuclideanSpace ℝ ( Fin k ))
    ```
    - from ProverBench-70
    ```lean
    variable {a b c x y z : ℝ} (ha : 0 < a) (hb : 0 < b) (hc : 0 < c) (hx : 0 < x) (hy : 0 < y) (hz : 0 < z)
    ```
    """
    binders: List[Binder]

    def to_source(self) -> str:
        return f"variable {' '.join(b.to_source() for b in self.binders)}"


@dataclass
class Universe(ASTNode):
    """
    Represents a universe statement.
    Pattern: universe <names>
    Examples:
    - from ProverBench-114
    ```lean
    universe u
    ```
    """
    names: List[str]

    def to_source(self) -> str:
        return f"universe {' '.join(self.names)}"


@dataclass
class Attribute(ASTNode):
    """
    Represents an attribute.
    Pattern: [<name> <args>]
    Examples:
    - from MathOlympiadBench-128
    ```lean
    [mk_iff]
    ```
    - from MathOlympiadBench-277
    ```lean
    [ext]
    ```
    - from MathOlympiadBench-157
    ```lean
    [mk_iff isGood_iff']
    ```
    - from MathOlympiadBench-160
    ```lean
    [local instance]
    ```
    """
    name: str
    args: Optional[List[str]] = None
    priority: Optional[int] = None

    def to_source(self) -> str:
        if self.priority is not None:
            return f"[{self.name} {self.priority}]"
        if self.args:
            return f"[{self.name} {' '.join(self.args)}]"
        return f"[{self.name}]"


@dataclass
class AttributeDeclaration(ASTNode):
    """
    Represents an attribute declaration.
    Pattern: attribute [[<attributes>]] <names>
    Examples:
    - from MathOlympiadBench-160
    ```lean
    attribute [local instance] FiniteDimensional.of_fact_finrank_eq_two
    ```
    """
    attributes: List[Attribute]
    names: List[str]
    modifiers: List[Modifier] = field(default_factory=list)

    def to_source(self) -> str:
        attrs_str = ''.join(a.to_source() for a in self.attributes)
        mod_str = ' '.join(m.to_source() for m in self.modifiers) + ' ' if self.modifiers else ""
        return f"attribute {mod_str}{attrs_str} {' '.join(self.names)}" 


@dataclass
class Elab(ASTNode):
    """
    Represents an elab statement.
    Pattern: elab <head> <args> => <body>
    """
    head: Optional[str] = None
    args: List[str] = None
    body: Optional[str] = None
    modifiers: List[Modifier] = field(default_factory=list)

    def to_source(self) -> str:
        mod_str = ' '.join(m.to_source() for m in self.modifiers) + ' ' if self.modifiers else ""
        result = f"{mod_str}elab"
        if self.head:
            result += f" {self.head}"
        if self.args:
            result += f" {' '.join(self.args)}"
        if self.body:
            result += f" => {self.body}"
        return result


@dataclass
class Macro(ASTNode):
    """
    Represents a macro statement.
    Pattern: macro <head> <args> => <body>
    """
    head: Optional[str] = None
    args: List[str] = None
    body: Optional[str] = None
    modifiers: List[Modifier] = field(default_factory=list)

    def to_source(self) -> str:
        mod_str = ' '.join(m.to_source() for m in self.modifiers) + ' ' if self.modifiers else ""
        result = f"{mod_str}macro"
        if self.head:
            result += f" {self.head}"
        if self.args:
            result += f" {' '.join(self.args)}"
        if self.body:
            result += f" => {self.body}"
        return result


@dataclass
class Syntax(ASTNode):
    """
    Represents a syntax statement.
    Pattern: syntax <head> <args> : <category> => <body>
    """
    head: Optional[str] = None
    args: List[str] = None
    precedence: Optional[int] = None
    category: Optional[str] = None
    body: Optional[str] = None
    modifiers: List[Modifier] = field(default_factory=list)

    def to_source(self) -> str:
        mod_str = ' '.join(m.to_source() for m in self.modifiers) + ' ' if self.modifiers else ""
        result = f"{mod_str}syntax"
        if self.head:
            result += f" {self.head}"
        if self.args:
            result += f" {' '.join(self.args)}"
        if self.category:
            result += f" : {self.category}"
        if self.body:
            result += f" => {self.body}"
        return result


@dataclass
class NotationDecl(ASTNode):
    """
    Represents a notation declaration.
    Pattern: (notation|infix|prefix|postfix) <pattern> => <body>
    Examples:
    - from MathOlympiadBench-45
    ```lean
    notation "ℝ+" => PosReal
    ```
    - from MathOlympiadBench-101
    ```lean
    notation "ℤ>0" => PosInt
    ```
    - from MathOlympiadBench-105
    ```lean
    local infixl:80 " ⋆ " => star
    ```
    """
    kind: str
    precedence: Optional[Union[int, str]] = None
    pattern: Optional[str] = None
    body: Optional[str] = None
    modifiers: List[Modifier] = field(default_factory=list)

    def to_source(self) -> str:
        result = ""
        if self.modifiers:
            result += ' '.join(m.to_source() for m in self.modifiers) + ' '
        result += self.kind
        if self.precedence is not None:
            result += f":{self.precedence}"
        if self.pattern:
            # Pattern already includes quotes from parser, just add a space
            result += f' {self.pattern}'
        if self.body:
            result += f" => {self.body}"
        return result


@dataclass
class MacroRules(ASTNode):
    """
    Represents a macro_rules statement.
    Pattern: macro_rules <args> | <rules>
    """
    precedence: Optional[int] = None
    args: List[str] = field(default_factory=list)
    rules: List[str] = field(default_factory=list)
    modifiers: List[Modifier] = field(default_factory=list)

    def to_source(self) -> str:
        mod_str = ' '.join(m.to_source() for m in self.modifiers) + ' ' if self.modifiers else ""
        result = f"{mod_str}macro_rules"
        if self.precedence is not None:
            result += f" {self.precedence}"
        if self.args:
            result += f" {' '.join(self.args)}"
        for rule in self.rules:
            result += f"\n | {rule}"
        return result


@dataclass
class RegisterOption(ASTNode):
    """
    Represents a register_option statement.
    Pattern: register_option <name> : <type> := <body>
    """
    name: str
    type_expr: Optional[str] = None
    body: Optional[str] = None
    doc: Optional[str] = None

    def to_source(self) -> str:
        result = ""
        if self.doc:
            result += f"/--{self.doc}-/\n"
        result += f"register_option {self.name}"
        if self.type_expr:
            result += f" : {self.type_expr}"
        if self.body:
            result += f" {self.body}"
        return result

@dataclass
class Initialize(ASTNode):
    """
    Represents an initialize statement.
    Pattern: initialize <target> [: <type>] [:= | ←] <body>
    """
    target: Optional[str] = None
    type_expr: Optional[str] = None
    assign_token: Optional[str] = None
    body: Optional[str] = None

    def to_source(self) -> str:
        result = "initialize"
        if self.target:
            result += f" {self.target}"
        if self.type_expr:
            result += f" : {self.type_expr}"
        if self.assign_token and self.body:
            result += f" {self.assign_token} {self.body}"
        elif self.body:
            result += f" {self.body}"
        return result


@dataclass
class AddDeclDoc(ASTNode):
    """
    Represents an add_decl_doc statement.
    Pattern: add_decl_doc <decl_name>
    """
    decl_name: str

    def to_source(self) -> str:
        return f"add_decl_doc {self.decl_name}"



    def to_source(self) -> str:
        if self.body:
            body_src = self.body.to_source() if isinstance(self.body, ASTNode) else str(self.body)
            # If body already starts with the kind, don't repeat it
            if body_src.startswith(self.kind):
                return f"local {body_src}"
            # If body starts with : (precedence), no space after kind
            if body_src.startswith(':'):
                return f"local {self.kind}{body_src}"
            return f"local {self.kind} {body_src}"
        return f"local {self.kind}"


@dataclass
class Definition(ASTNode):
    """
    Represents a definition (def, theorem, etc.
    Pattern: (def|theorem|lemma|abbrev|example|opaque|axiom) <name> <binders> : <type> := <body>
    Examples:
    - from ProverBench-42
    ```lean
    axiom infinitelyManyPrimesOfForm4kPlus1 : ∃ ( infinitelyMany : ℕ → Prop ) , ∀ n : ℕ , infinitelyMany n → ∃ p : ℕ , Nat . Prime p ∧ p % 4 = 1
    ```
    - from PutnamBench-646
    ```lean
    abbrev putnam_1988_b2_solution : Prop :=
      True
    ```
    - from ProverBench-51
    ```lean
    theorem prime_remainder_theorem (p : ℕ) (hp : Prime p) : 
     let N :=
      ( range ( p - 1 ) ) . prod ( λ k => k ^ 2 + 1 ) ; 
     if p % 4 = 3 then N % p = 4 else N % p = 0 := by sorry
    ```
    - from MathOlympiadBench-160
    ```lean
    theorem imo2019_p2 [Fact ( finrank ℝ V = 2 )] (A B C A₁ B₁ P Q P₁ Q₁ : Pt) (affine_independent_ABC : AffineIndependent ℝ ! [ A , B , C ]) (wbtw_B_A₁_C : Wbtw ℝ B A₁ C) (wbtw_A_B₁_C : Wbtw ℝ A B₁ C) (wbtw_A_P_A₁ : Wbtw ℝ A P A₁) (wbtw_B_Q_B₁ : Wbtw ℝ B Q B₁) (PQ_parallel_AB : line [ ℝ , P , Q ] ∥ line [ ℝ , A , B ]) (P_ne_Q : P ≠ Q) (sbtw_P_B₁_P₁ : Sbtw ℝ P B₁ P₁) (angle_PP₁C_eq_angle_BAC : ∠ P P₁ C = ∠ B A C) (C_ne_P₁ : C ≠ P₁) (sbtw_Q_A₁_Q₁ : Sbtw ℝ Q A₁ Q₁) (angle_CQ₁Q_eq_angle_CBA : ∠ C Q₁ Q = ∠ C B A) (C_ne_Q₁ : C ≠ Q₁) : 
     Concyclic ( { P , Q , P₁ , Q₁ } : Set Pt ) :=
      by sorry
    ```
    """
    doc: Optional[str] = None
    has_at: bool = False  # For @[attribute] syntax
    kind: str = "def" 
    name: str = "name"
    binders: List[Binder] = field(default_factory=list)
    type: Optional[RawExpr] = None
    body: Optional[RawExpr] = None
    attributes: List[Attribute] = field(default_factory=list)
    modifiers: List[Modifier] = field(default_factory=list)
    has_coloneq: bool = False

    def attrs_to_source(self) -> str:
        if self.attributes:
            attr_str = ' '.join(a.to_source() for a in self.attributes)
            if self.has_at:
                # Already includes brackets from Attribute.to_source(), just add @
                return f"@{attr_str}\n"
            return attr_str + '\n'
        return ""

    def doc_to_source(self) -> str:
        if self.doc:
            return f"/--{self.doc}-/\n"
        return ""

    def to_source(self) -> str:
        binders_str = ' '.join(b.to_source() for b in self.binders)
        type_str = f" :{self.type.to_source()}" if self.type else ""

        body_str = ""
        if self.body:
            body_content = self.body.to_source().lstrip()
            if self.has_coloneq:
                body_str = f" :=\n{self.lstrip_until_next_line(self.body.to_source())}"
            elif body_content.startswith('|'):
                body_str = f"\n{self.lstrip_until_next_line(self.body.to_source())}"
            elif body_content.startswith('where'):
                body_str = f"\n{self.lstrip_until_next_line(self.body.to_source())}"
            else:
                body_str = f" :=\n{self.lstrip_until_next_line(self.body.to_source())}"

        mod_str = ' '.join(m.to_source() for m in self.modifiers) + ' ' if self.modifiers else ""

        result = self.doc_to_source() + self.attrs_to_source()
        result += f"{mod_str}{self.kind} {self.name}"
        if binders_str:
            result += f" {binders_str}"
        result += f"{type_str}{body_str}"
        return result.rstrip()


@dataclass
class Instance(ASTNode):
    """
    Represents an instance declaration.
    Pattern: instance <name> <binders> : <type> := <body>
    Examples:
    - from ProverBench-148
    ```lean
    instance : Semiring Z2 := inferInstanceAs ( Semiring ( ZMod 2 ) ) 
     
     -- Define the polynomial f(x) = x^2 + 1 over Z_2
    ```
    - from MathOlympiadBench-349
    ```lean
    instance [Add G] : FunLike ( InfectiousFun G ) G G where
      coe f := f . toFun
      coe_injective' f g h := by rwa [ InfectiousFun . mk . injEq ]
    ```
    - from MathOlympiadBench-255
    ```lean
    noncomputable instance IsMSequence.instDecidablePred [DecidableEq I] [DecidableEq Λ] : 
     DecidablePred ( IsMSequence I Λ ) := by 
     unfold IsMSequence ; infer_instance
    ```
    - from MathOlympiadBench-27
    ```lean
    instance {k : ℕ} (α : Type *) [Fintype α] [DecidableEq α] : 
     Fintype ( fiber α k ) := by unfold fiber ; infer_instance
    ```
    """
    name: str
    type: RawExpr
    binders: List[Binder] = field(default_factory=list)
    fields: List[tuple] = field(default_factory=list)  # (name, value) value is RawExpr
    attributes: List[Attribute] = field(default_factory=list)
    doc: Optional[str] = None
    is_priority: Optional[str] = None

    modifiers: List[Modifier] = field(default_factory=list)

    def attrs_to_source(self) -> str:
        if self.attributes:
            return ' '.join(a.to_source() for a in self.attributes) + '\n'
        return ""

    def doc_to_source(self) -> str:
        if self.doc:
            return f"/--{self.doc}-/\n"
        return ""

    def get_modifiers_source(self) -> str:
        if not self.modifiers:
            return ""
        return ' '.join(m.to_source() for m in self.modifiers) + ' '

    def to_source(self) -> str:
        priority_str = f" {self.is_priority}" if self.is_priority else ""
        name_str = f" {self.name}" if self.name else ""
        binders_str = ' '.join(b.to_source() for b in self.binders)

        result = self.doc_to_source() + self.attrs_to_source()
        result += f"{self.get_modifiers_source()}instance{priority_str}{name_str}"
        if binders_str:
            result += f" {binders_str}"
        if self.type:
            result += f" : {self.type.to_source()}"

        if self.fields:
            result += " where"
            for field in self.fields:
                if len(field) == 3:
                    name, binders, value = field
                    binders_str = ' '.join(b.to_source().strip() for b in binders)
                    if binders_str:
                        result += f"\n  {name} {binders_str} := {value.to_source()}"
                    else:
                        result += f"\n  {name} := {value.to_source()}"
                else:
                    name, value = field
                    result += f"\n  {name} := {value.to_source()}"

        return result


@dataclass
class ClassField(ASTNode):
    """
    Represents a class field.
    Pattern: <name> <binders> : <type>
    Examples:
    - from MathOlympiadBench-350
    ```lean
    add_mem : ∀ { v w } , v ∈ S → w ∈ S → v + w ∈ S
    ```
    - from MathOlympiadBench-360
    ```lean
    a_pos : 0 < a
    ```
    - from MathOlympiadBench-360
    ```lean
    c_pos : 0 < c
    ```
    - from MathOlympiadBench-360
    ```lean
    spec : ( ( a * b : ℕ ) : ℚ ) / ( a + b : ℕ ) + ( c * d : ℕ ) / ( c + d : ℕ ) 
     = ( a + b : ℕ ) * ( c + d : ℕ ) / ( a + b + c + d : ℕ )
    ```
    """
    name: str
    type: RawExpr
    binders: List[Binder] = field(default_factory=list)
    doc: Optional[str] = None

    def to_source(self) -> str:
        doc_str = f"/--{self.doc}-/ " if self.doc else ""
        binders_str = ' '.join(b.to_source() for b in self.binders)
        if binders_str:
            return f"{doc_str}{self.name} {binders_str} : {self.type.to_source()}"
        return f"{doc_str}{self.name} : {self.type.to_source()}"


@dataclass
class Class(ASTNode):
    """
    Represents a class declaration.
    Pattern: class <name> <binders> : <type> extends <extends> where <fields>
    Examples:
    - from MathOlympiadBench-306
    ```lean
    class CancelCommDistribMonoid (M) extends CancelCommMonoid M, Distrib M
    ```
    - from MathOlympiadBench-350
    ```lean
    class IsAddSupClosed {m : ℕ} (S : Set ( Fin m → ℤ )) : Prop where
      add_mem : ∀ { v w } , v ∈ S → w ∈ S → v + w ∈ S
      sup_mem : ∀ { v w } , v ∈ S → w ∈ S → v ⊔ w ∈ S
    ```
    """
    name: str
    binders: List[Binder] = field(default_factory=list)
    type: Optional[RawExpr] = None
    extends: List[RawExpr] = field(default_factory=list)
    fields: List[ClassField] = field(default_factory=list)
    attributes: List[Attribute] = field(default_factory=list)
    doc: Optional[str] = None
    has_where: bool = True
    deriving: List[str] = field(default_factory=list)

    modifiers: List[Modifier] = field(default_factory=list)

    def attrs_to_source(self) -> str:
        if self.attributes:
            return ' '.join(a.to_source() for a in self.attributes) + '\n'
        return ""

    def doc_to_source(self) -> str:
        if self.doc:
            return f"/--{self.doc}-/\n"
        return ""

    def get_modifiers_source(self) -> str:
        if not self.modifiers:
            return ""
        return ' '.join(m.to_source() for m in self.modifiers) + ' '

    def to_source(self) -> str:
        binders_str = ' '.join(b.to_source() for b in self.binders)
        type_str = f" : {self.type.to_source()}" if self.type else ""
        extends_str = f" extends {', '.join(e.to_source() for e in self.extends)}" if self.extends else ""

        result = self.doc_to_source() + self.attrs_to_source()
        result += f"{self.get_modifiers_source()}class {self.name}"
        if binders_str:
            result += f" {binders_str}"
        result += type_str
        result += extends_str
        if self.has_where:
            result += " where"

        for field in self.fields:
            result += f"\n  {field.to_source()}"
        if self.deriving:
            result += f"\n  deriving {', '.join(self.deriving)}"

        return result


@dataclass
class StructureField(ASTNode):
    """
    Represents a structure field.
    Pattern: <name> <binders> : <type> := <default>
    Examples:
    - from MathOlympiadBench-4
    ```lean
    s : Multiset ℕ
    ```
    - from MathOlympiadBench-257
    ```lean
    side_x : x ≤ y + z
    ```
    - from MathOlympiadBench-353
    ```lean
    x : ℕ → F
    ```
    - from MathOlympiadBench-343
    ```lean
    colour_symm (x y : V) : colour x y = colour y x
    ```
    """
    name: str
    type: RawExpr
    binders: List[Binder] = field(default_factory=list)
    default: Optional[RawExpr] = None
    doc: Optional[str] = None
    is_binder: bool = False
    implicit_names: List[str] = field(default_factory=list)

    def to_source(self) -> str:
        doc_str = f"/--{self.doc}-/\n  " if self.doc else ""
        default_str = f" := {self.default.to_source()}" if self.default else ""
        # Handle implicit names (params without brackets like `x y : Type`)
        implicit_str = ' '.join(self.implicit_names) + ' ' if self.implicit_names else ""
        if self.type is None:
            return f"{doc_str}{self.name}{default_str}"
        if self.is_binder:
            return f"{doc_str}({self.name} : {self.type.to_source()}){default_str}"
        if self.binders:
            binders_str = ' '.join(b.to_source() for b in self.binders)
            return f"{doc_str}{self.name} {binders_str} : {self.type.to_source()}{default_str}"
        return f"{doc_str}{self.name} {implicit_str}: {self.type.to_source()}{default_str}"


@dataclass
class Structure(ASTNode):
    """
    Represents a structure declaration.
    Pattern: structure <name> (<binders>)* (: <type>)* (extends <extends>)* (where <fields>)*
    Examples:
    - from MathOlympiadBench-5
    ```lean
    structure Coords where
      (row : ℕ)
      (col : ℕ)
    ```
    - from MathOlympiadBench-320
    ```lean
    structure SpecialTuple (n : ℕ) where
      toFun : Fin n . pred . succ → ℤ
      jump_shift : Fin n . pred . succ → Fin n . pred . succ
      jump_shift_spec : ∀ i , ( n : ℤ ) ∣ ∑ j ∈ Ico i . 1 ( i . 1 + ( ( jump_shift i ) . 1 + 1 ) ) , toFun j
    ```
    - from MathOlympiadBench-31
    ```lean
    structure IsGood (f : ℝ ≥ 0 → ℝ ≥ 0) : Prop where
      map_add_rev x y : f ( x * f y ) * f y = f ( x + y )
      map_two : f 2 = 0
      map_ne_zero : ∀ x < 2 , f x ≠ 0
    ```
    - from MathOlympiadBench-315
    ```lean
    @[ext]
    structure CentralInvolutive (R : Type *) [Ring R] where
      val : R
      val_mul_self_eq_one : val * val = 1
      val_mul_comm (x : R) : x * val = val * x
    ```
    """
    name: str
    binders: List[Binder] = field(default_factory=list)
    type: Optional[RawExpr] = None
    extends: List[RawExpr] = field(default_factory=list)
    ctor_name: Optional[str] = None
    fields: List[StructureField] = field(default_factory=list)
    attributes: List[Attribute] = field(default_factory=list)
    doc: Optional[str] = None
    has_where: bool = True
    deriving: List[str] = field(default_factory=list)

    modifiers: List[Modifier] = field(default_factory=list)
    has_at: bool = False  # For @[attribute] syntax

    def attrs_to_source(self) -> str:
        if self.attributes:
            # When has_at is True, the attributes already include the @ prefix
            # and we shouldn't add extra brackets
            attr_str = ' '.join(a.to_source() for a in self.attributes)
            if self.has_at:
                # Already includes brackets from Attribute.to_source(), just add @
                return f"@{attr_str}\n"
            return attr_str + '\n'
        return ""

    def doc_to_source(self) -> str:
        if self.doc:
            return f"/--{self.doc}-/\n"
        return ""

    def get_modifiers_source(self) -> str:
        if not self.modifiers:
            return ""
        return ' '.join(m.to_source() for m in self.modifiers) + ' '

    def to_source(self) -> str:
        binders_str = ' '.join(b.to_source() for b in self.binders)
        type_str = f" : {self.type.to_source()}" if self.type else ""
        extends_str = f" extends {', '.join(e.to_source() for e in self.extends)}" if self.extends else ""
        ctor_str = f" ::\n  mk ::" if self.ctor_name else ""

        result = self.doc_to_source() + self.attrs_to_source()
        result += f"{self.get_modifiers_source()}structure {self.name}"
        if binders_str:
            result += f" {binders_str}"
        result += f"{type_str}{extends_str}"
        if self.has_where:
            result += " where"
        result += ctor_str

        for field in self.fields:
            result += f"\n  {field.to_source()}"
        if self.deriving:
            result += f"\n  deriving {', '.join(self.deriving)}"

        return result


@dataclass
class InductiveCtor(ASTNode):
    """
    Represents an inductive constructor.
    Pattern: | <name> <binders> : <type>
    Examples:
    - from MathOlympiadBench-21
    ```lean
    | AlwaysTrue : SolutionData
    ```
    - from MathOlympiadBench-110
    ```lean
    | BaseCase (b : Blackboard n) : 
     valid_moves a n ⟨ b , . Bob ⟩ = ∅ → BobCanForceEnd a n ⟨ b , . Bob ⟩
    ```
    - from MathOlympiadBench-110
    ```lean
    | BobTurn (b : Blackboard n) (m : State n) : 
     ( m ∈ valid_moves a n ⟨ b , . Bob ⟩ ) → BobCanForceEnd a n m → 
     BobCanForceEnd a n ⟨ b , . Bob ⟩
    ```
    - from MathOlympiadBench-270
    ```lean
    /-- Solutions that are indicator functions on submonoids of `R`. -/ | indicator (A : Set R) (_ : ∀ m n , m * n ∈ A ↔ m ∈ A ∧ n ∈ A) (C : S) (_ : ⌈ C ⌉ = 1) : 
     IsAnswer ( fun x ↦ if x ∈ A then C else 0 )
    ```
    """
    name: str
    binders: List[Binder] = field(default_factory=list)
    type: Optional[RawExpr] = None
    doc: Optional[str] = None

    def to_source(self) -> str:
        doc_str = f"/--{self.doc}-/ " if self.doc else ""
        binders_str = ' '.join(b.to_source() for b in self.binders)
        type_str = f" : {self.type.to_source()}" if self.type else ""
        if binders_str:
            return f"{doc_str}| {self.name} {binders_str}{type_str}"
        return f"{doc_str}| {self.name}{type_str}"


@dataclass
class Inductive(ASTNode):
    """
    Represents an inductive declaration.
    Pattern: inductive <name> <binders> : <type> where <ctors>
    Examples:
    - from MathOlympiadBench-21
    ```lean
    inductive SolutionData where
    | AlwaysTrue : SolutionData
    | Counterexample : ℕ → SolutionData
    ```
    - from MathOlympiadBench-43
    ```lean
    inductive Color : Type where
    | red : Color
    | blue : Color
    deriving DecidableEq, Fintype
    ```
    - from PutnamBench-663
    ```lean
    inductive HasWinningStrategy (n : ℕ) : List ( GameString n ) → Prop where
    | win (play : List ( GameString n )) (s : GameString n) : 
     IsValidGamePlay ( play + + [ s ] ) → 
     ( ∀ s' , IsValidGamePlay ( play + + [ s , s' ] ) → HasWinningStrategy n ( play + + [ s , s' ] ) ) → 
     HasWinningStrategy n play
    ```
    - from MathOlympiadBench-284
    ```lean
    inductive BinOpClosure {α : Type *} (op : α → α → α) (P : α → Prop) : α → Prop where
    | ofMem {a} (h : P a) : BinOpClosure op P a
    | ofOp {a b} (ha : BinOpClosure op P a) (hb : BinOpClosure op P b) : BinOpClosure op P ( op a b )
    ```
    """
    name: str
    binders: List[Binder] = field(default_factory=list)
    type: Optional[RawExpr] = None
    ctors: List[InductiveCtor] = field(default_factory=list)
    ctor_style: Optional[str] = None
    attributes: List[Attribute] = field(default_factory=list)
    doc: Optional[str] = None
    deriving: List[str] = field(default_factory=list)

    modifiers: List[Modifier] = field(default_factory=list)

    def attrs_to_source(self) -> str:
        if self.attributes:
            return ' '.join(a.to_source() for a in self.attributes) + '\n'
        return ""

    def doc_to_source(self) -> str:
        if self.doc:
            return f"/--{self.doc}-/\n"
        return ""

    def get_modifiers_source(self) -> str:
        if not self.modifiers:
            return ""
        return ' '.join(m.to_source() for m in self.modifiers) + ' '

    def to_source(self) -> str:
        binders_str = ' '.join(b.to_source() for b in self.binders)
        type_str = f" : {self.type.to_source()}" if self.type else ""

        result = self.doc_to_source() + self.attrs_to_source()
        result += f"{self.get_modifiers_source()}inductive {self.name}"
        if binders_str:
            result += f" {binders_str}"
        result += f"{type_str}"

        if self.ctor_style:
            result += f" {self.ctor_style}"

        if self.ctors:
            for ctor in self.ctors:
                result += f"\n{ctor.to_source()}"

        if self.deriving:
            result += f"\nderiving {', '.join(self.deriving)}"

        return result


@dataclass
class Mutual(ASTNode):
    """
    Represents a mutual block.
    Pattern: mutual <body> end
    """
    body: List[ASTNode] = field(default_factory=list)
    modifiers: List[Modifier] = field(default_factory=list)

    def to_source(self) -> str:
        mod_str = ' '.join(m.to_source() for m in self.modifiers) + ' ' if self.modifiers else ""
        body_str = '\n\n'.join(item.to_source() for item in self.body)
        return f"{mod_str}mutual\n\n{body_str}\n\nend"


@dataclass
class Namespace(ASTNode):
    """
    Represents a namespace block.
    Pattern: namespace <name> <body> end <name>
    """
    name: str
    body: List[ASTNode] = field(default_factory=list)
    has_end: bool = True

    def to_source(self) -> str:
        body_str = '\n\n'.join(item.to_source() for item in self.body)
        if self.has_end:
            return f"namespace {self.name}\n\n{body_str}\n\nend {self.name}"
        else:
            return f"namespace {self.name}\n\n{body_str}"


@dataclass
class Section(ASTNode):
    """
    Represents a section block.
    Pattern: section <name> <body> end <name>
    """
    name: Optional[str] = None
    body: List[ASTNode] = field(default_factory=list)
    modifiers: List[Modifier] = field(default_factory=list)
    has_end: bool = True

    def to_source(self) -> str:
        name_str = f" {self.name}" if self.name else ""
        modifier_str = ' '.join(m.to_source() for m in self.modifiers) + ' ' if self.modifiers else ""
        body_str = '\n\n'.join(item.to_source() for item in self.body)
        if self.has_end:
            end_str = f" end {self.name}" if self.name else " end"
        else:
            end_str = ""
        return f"{modifier_str}section{name_str}\n\n{body_str}\n\n{end_str}"


@dataclass
class Include(ASTNode):
    """
    Represents an include statement.
    Pattern: include <names>
    """
    names: List[str]

    def to_source(self) -> str:
        return f"include {' '.join(self.names)}"


@dataclass
class Omit(ASTNode):
    """
    Represents an omit statement.
    Pattern: omit <names>
    """
    names: List[str]

    def to_source(self) -> str:
        return f"omit {' '.join(self.names)}"


@dataclass
class Notation(ASTNode):
    """
    Represents a notation statement.
    Pattern: notation "<pattern>" => <value>
    """
    pattern: str
    value: RawExpr
    precedence: Optional[int] = None

    def to_source(self) -> str:
        prec_str = f" : {self.precedence}" if self.precedence else ""
        return f'notation{prec_str} "{self.pattern}" => {self.value.to_source()}'


@dataclass
class Infix(ASTNode):
    """
    Represents an infix statement.
    Pattern: infix "<op>" => <func>
    """
    op: str
    func: str
    precedence: int

    def to_source(self) -> str:
        return f'infix:{self.precedence} "{self.op}" => {self.func}'


@dataclass
class Prefix(ASTNode):
    """
    Represents a prefix statement.
    Pattern: prefix "<op>" => <func>
    """
    op: str
    func: str
    precedence: int

    def to_source(self) -> str:
        return f'prefix:{self.precedence} "{self.op}" => {self.func}'


@dataclass
class Postfix(ASTNode):
    """
    Represents a postfix statement.
    Pattern: postfix "<op>" => <func>
    """
    op: str
    func: str
    precedence: int

    def to_source(self) -> str:
        return f'postfix:{self.precedence} "{self.op}" => {self.func}'


@dataclass
class Module(ASTNode):
    """
    Represents a Lean module (file).
    Pattern: <body>
    """
    header_comments: List[Comment] = field(default_factory=list)
    body: List[ASTNode] = field(default_factory=list)

    def to_source(self) -> str:
        parts = []

        for c in self.header_comments:
            parts.append(c.to_source())

        for i, item in enumerate(self.body):
            if i > 0:
                if not isinstance(self.body[i-1], Comment) or isinstance(item, (Definition, Instance, Structure)):
                    parts.append("")
            parts.append(item.to_source())

        return '\n'.join(parts)


@dataclass
class LibraryNote(ASTNode):
    """
    Represents a library_note statement.
    Pattern: library_note "<name>" / "<content>"
    """
    name: str
    content: str

    def to_source(self) -> str:
        return f'library_note "{self.name}"/"{self.content}"'


@dataclass
class Derive(ASTNode):
    """
    Represents a deriving instance statement.
    Pattern: deriving instance <handlers> for <type>
    """
    handlers: List[str]
    type: RawExpr

    def to_source(self) -> str:
        return f"deriving instance {', '.join(self.handlers)} for {self.type.to_source()}"


@dataclass
class HashCommand(ASTNode):
    """
    Represents a #command statement like #check, #eval, #reduce, #print.
    Pattern: #<command> <expr>
    Examples:
    - #check Nat
    - #eval 2 + 2
    - #reduce (fun x => x + 1) 3
    - #print Nat
    """
    command: str  # check, eval, reduce, print, etc.
    expr: Optional[RawExpr] = None

    def to_source(self) -> str:
        if self.expr:
            return f"#{self.command} {self.expr.to_source()}"
        return f"#{self.command}"


@dataclass
class AssertNotExists(ASTNode):
    """
    Represents an assert_not_exists statement.
    Pattern: assert_not_exists <name>
    """
    name: str

    def to_source(self) -> str:
        return f"assert_not_exists {self.name}"