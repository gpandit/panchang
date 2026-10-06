"""S0-06 source boundary check. Run: python3 tools/check_contract_authority.py

Dependency-free and offline. Checks Python import ASTs and source tokens for the
web/admin/temple-admin (TS/JS), iOS (Swift), and Android (Kotlin) clients.
This is a conservative source guard, not a typechecker or a data-flow proof.
"""

from __future__ import annotations

import argparse
import ast
import io
import re
import sys
import tokenize
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {
    ".git", ".opencode", ".omnirush", ".venv", "node_modules", "build", "dist",
    ".next", ".gradle", "__pycache__", "tmp-panchang", "generated", "docs", "__tests__",
}
SOURCE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".swift", ".kt"}
CLIENT_SUFFIXES = SOURCE_SUFFIXES - {".py"}
CLIENT_ROOTS = ("apps/web/src", "apps/admin/src", "apps/temple-admin/src",
                "apps/ios/ThePandit/Sources", "apps/android/app/src/main")
EPHEMERIS = re.compile(r"^(?:swisseph|pyswisseph)(?:\.|$)", re.I)
JS_IMPORT = re.compile(
    r"\b(?:from\s*|import\s*\(?|require\s*\()\s*['\"](?:swisseph|pyswisseph)(?:/[^'\"]*)?['\"]",
    re.I,
)
NATIVE_IMPORT = re.compile(r"\bimport\s+(?:swisseph|pyswisseph)(?:\b|\.)", re.I)
DOMAIN = r"(?:tithi|nakshatra|yoga|karana|paksha|muhurat|ayanamsa|sunrise|sunset|moonrise|" \
         r"lunarMonth|panchang|price|subtotal|totalPrice|totalAmount|commission|tax|payout|" \
         r"quote|refund|bookingAmount|amountMinor|feeMinor|entitlement)"
CALCULATOR = re.compile(
    rf"\b(?:calc(?:ulate)?|compute|derive|resolve)\w*{DOMAIN}\w*\s*\(", re.I,
)
DOMAIN_MATH = re.compile(
    rf"\b\w*{DOMAIN}\w*\b\s*(?:\?\.|\.)?\s*(?:\+|\-|\*|/|%)\s*"
    rf"(?:\d|\b[a-zA-Z_$])|(?:\d|\b[a-zA-Z_$]\w*)\s*(?:\+|\-|\*|/|%)\s*"
    rf"\b\w*{DOMAIN}\w*\b", re.I,
)
DOMAIN_ASSIGN_MATH = re.compile(
    rf"\b(?:const|let|var|val)\s+\w*{DOMAIN}\w*\s*(?::[^=\n]+)?="
    r"[^;\n]*\b[a-zA-Z_$]\w*\s*(?:\+|\-|\*|/|%)\s*\b[a-zA-Z_$0-9]\w*", re.I,
)
# State-machine changes belong to the gateway; assignment to a client-side
# booking/payout field is suspicious even without arithmetic.
STATE_WRITE = re.compile(r"\b(?:booking|payout)\w*\s*(?:\?\.)?\.\s*(?:state|status)\s*=(?!=)", re.I)
TIER_DECISION = re.compile(
    r"\b(?:canBook|canCheckout|isEntitled|hasEntitlement|eligibleForCheckout)\w*\s*="
    r"[^;\n]*\b(?:tier|subscription|entitlement)\b[^;\n]*(?:===?|!==?|>=?|<=?)|"
    r"\b(?:canBook|canCheckout|isEntitled|hasEntitlement|eligibleForCheckout)\w*\s*="
    r"[^;\n]*(?:===?|!==?|>=?|<=?)[^;\n]*\b(?:tier|subscription|entitlement)\b", re.I,
)


@dataclass(frozen=True, order=True)
class Violation:
    path: str
    line: int
    rule: str
    detail: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.rule}: {self.detail}"


def _source_files(root: Path):
    """Walk source, excluding generated/vendor/worktree artifacts (not docs)."""
    import os

    for directory, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
        for filename in sorted(files):
            path = Path(directory) / filename
            if path.suffix in SOURCE_SUFFIXES and not (
                path.suffix in CLIENT_SUFFIXES and (".test." in filename or ".spec." in filename)
            ):
                yield path


def _is_client(relative: str) -> bool:
    return any(relative.startswith(prefix + "/") for prefix in CLIENT_ROOTS)


def check_python(source: str, relative: str) -> list[Violation]:
    """AST rather than grep: docstrings, comments and text are not imports."""
    try:
        tree = ast.parse(source, filename=relative)
    except SyntaxError:
        # A Python 3.11 host cannot parse the repository's Python 3.12 PEP 695
        # generic classes. Tokenize imports instead; the project typecheck owns
        # syntax validation. Ignore docstrings/comments, including fake imports.
        return _check_python_tokens(source, relative)
    allowed = relative.startswith("services/panchang/")
    violations = []
    for node in ast.walk(tree):
        modules: list[str] = []
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            modules = [node.module or ""]
        elif isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant):
            fn = node.func
            if (isinstance(fn, ast.Name) and fn.id == "__import__") or (
                isinstance(fn, ast.Attribute) and fn.attr == "import_module"
                and isinstance(fn.value, ast.Name) and fn.value.id == "importlib"
            ):
                modules = [node.args[0].value] if isinstance(node.args[0].value, str) else []
        if not allowed:
            for module in modules:
                if EPHEMERIS.match(module):
                    violations.append(Violation(relative, node.lineno, "ephemeris-boundary", module))
    return violations


def _check_python_tokens(source: str, relative: str) -> list[Violation]:
    if relative.startswith("services/panchang/"):
        return []
    tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    violations = []
    for i, token in enumerate(tokens):
        if token.type != tokenize.NAME:
            continue
        if token.string == "from":
            # Only the module after `from` counts, not an imported symbol.
            following = next((part for part in tokens[i + 1:]
                              if part.type not in {tokenize.NL, tokenize.COMMENT}), None)
            if following and following.type == tokenize.NAME and EPHEMERIS.match(following.string):
                violations.append(Violation(relative, token.start[0],
                                            "ephemeris-boundary", following.string))
        elif token.string == "import" and not any(
            part.string == "from" for part in tokens[max(0, i - 5):i]
            if part.start[0] == token.start[0]
        ):
            # Covers `import foo, swisseph`; comments/strings cannot match.
            until = next((j for j in range(i + 1, len(tokens))
                          if tokens[j].type in {tokenize.NEWLINE, tokenize.ENDMARKER}), len(tokens))
            for part in tokens[i + 1:until]:
                if part.type == tokenize.NAME and EPHEMERIS.match(part.string):
                    violations.append(Violation(relative, token.start[0],
                                                "ephemeris-boundary", part.string))
        if token.string == "__import__" or token.string == "import_module":
            if i + 2 < len(tokens) and tokens[i + 1].string == "(":
                value = tokens[i + 2]
                if value.type == tokenize.STRING:
                    try:
                        module = ast.literal_eval(value.string)
                    except (ValueError, SyntaxError):
                        continue
                    if isinstance(module, str) and EPHEMERIS.match(module):
                        violations.append(Violation(relative, token.start[0],
                                                    "ephemeris-boundary", module))
    return violations


def mask_comments_and_strings(source: str) -> str:
    """Keep offsets/newlines; erase comments and literals for source-pattern checks.

    Handles //, #, /* */, JS backticks and quoted strings in our client languages.
    Regexes with // inside strings and documentation do not trigger guards.
    """
    out = list(source)
    i = 0
    while i < len(source):
        start = i
        if source.startswith("//", i) or source[i] == "#":
            i = source.find("\n", i)
            if i == -1:
                i = len(source)
        elif source.startswith("/*", i):
            end = source.find("*/", i + 2)
            i = len(source) if end == -1 else end + 2
        elif source[i] in "\"'`":
            quote = source[i]
            if source.startswith(quote * 3, i):
                end = source.find(quote * 3, i + 3)
                i = len(source) if end == -1 else end + 3
            else:
                i += 1
                while i < len(source):
                    if source[i] == "\\":
                        i += 2
                    elif source[i] == quote:
                        i += 1
                        break
                    else:
                        i += 1
        else:
            i += 1
            continue
        for index in range(start, min(i, len(source))):
            if source[index] != "\n":
                out[index] = " "
    return "".join(out)


def check_client(source: str, relative: str) -> list[Violation]:
    if not _is_client(relative) or Path(relative).suffix not in CLIENT_SUFFIXES:
        return []
    masked = mask_comments_and_strings(source)
    violations = []
    # Import literals must remain visible; find these in original text, then
    # require that their import/require token is not in a comment or string.
    imports = JS_IMPORT if Path(relative).suffix in {".ts", ".tsx", ".js", ".jsx"} else NATIVE_IMPORT
    for match in imports.finditer(source):
        if masked[match.start():match.start() + 6].strip():
            violations.append(Violation(relative, source.count("\n", 0, match.start()) + 1,
                                        "ephemeris-boundary", "client ephemeris import"))
    for rule, pattern in (("client-calculation", CALCULATOR), ("client-arithmetic", DOMAIN_MATH),
                          ("client-arithmetic", DOMAIN_ASSIGN_MATH),
                          ("client-state", STATE_WRITE), ("client-entitlement", TIER_DECISION)):
        for match in pattern.finditer(masked):
            violations.append(Violation(relative, masked.count("\n", 0, match.start()) + 1,
                                        rule, source[match.start():match.end()].strip()))
    # A named assignment may also contain a domain operand: one diagnostic
    # per line/rule is enough to direct the reviewer to the source expression.
    return list({(v.path, v.line, v.rule): v for v in violations}.values())


def scan(root: Path = ROOT) -> list[Violation]:
    violations = []
    for path in _source_files(root):
        relative = path.relative_to(root).as_posix()
        source = path.read_text(encoding="utf-8")
        if path.suffix == ".py":
            violations.extend(check_python(source, relative))
        else:
            violations.extend(check_client(source, relative))
    return sorted(violations)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root")
    args = parser.parse_args()
    violations = scan(args.root.resolve())
    for violation in violations:
        print(violation)
    if violations:
        print(f"S0-06 authority check failed: {len(violations)} violation(s)", file=sys.stderr)
        return 1
    print("S0-06 authority check passed (ephemeris boundary and client authority)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
