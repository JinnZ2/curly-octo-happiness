#!/usr/bin/env python3
# CC0 1.0 Universal.
"""gate_check.py -- presence or absence of four structural features in a repo.

Reports absence. Does not diagnose why. No interpretation, no
recommendation, no severity language.

Stdlib only. Single file. Runs offline.
"""

import argparse
import ast
import os
import re
import sys

# --------------------------------------------------------------------------
# labels
#
# The first three mirror an existing schema used elsewhere; do not add
# members. There is deliberately NO FAIL member: anything categorised as
# failure gets discarded as noise, and the information in it stops being
# recyclable.
# --------------------------------------------------------------------------

HELD_RETRIEVABLE = "HELD_RETRIEVABLE"      # present and locatable (file+line)
HELD_UNRETRIEVABLE = "HELD_UNRETRIEVABLE"  # present, not pinnable to a location
NOT_HELD = "NOT_HELD"                      # absent
OUT_OF_ENVELOPE = "OUT_OF_ENVELOPE"        # check does not apply

# BUILDER'S DERIVATION, not part of the original spec:
#   found and a line number is available  -> HELD_RETRIEVABLE
#   found and no line number is available -> HELD_UNRETRIEVABLE
#   not found                             -> NOT_HELD
# The spec fixed the label set and check 4's out-of-envelope case; the
# mapping from a check's outcome onto the labels is the builder's.


def _label(hits, unlocated):
    if hits:
        return HELD_RETRIEVABLE
    if unlocated:
        return HELD_UNRETRIEVABLE
    return NOT_HELD


# --------------------------------------------------------------------------
# vocabularies
# --------------------------------------------------------------------------

UNKNOWN_PHRASES = (
    "unknown", "unknowable", "blocked", "out of envelope", "out of scope",
    "indeterminate", "undetermined", "underivable", "not applicable",
    "abstain", "unresolved", "insufficient", "no data", "unavailable",
    "not held", "undecidable", "inconclusive",
)

FAILURE_PHRASES = UNKNOWN_PHRASES + (
    "error", "exception", "fail", "failed", "failure", "invalid", "missing",
    "absent", "empty", "refuse", "refused", "reject", "rejected", "denied",
    "raises", "null", "none", "nan",
)

KILL_NAMES = frozenset({"exit", "_exit", "abort", "quit"})

FAILURE_CALL_NAMES = frozenset({
    "assertRaises", "assertRaisesRegex", "assertIsNone", "assertFalse",
    "assertNotIn", "assertNotEqual", "assertIsNot", "assertNotIsInstance",
    "fail", "raises", "xfail",
})

SOURCE_EXT = frozenset({
    ".py", ".js", ".mjs", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java",
    ".rb", ".c", ".h", ".cc", ".cpp", ".hpp", ".cs", ".sh", ".bash",
    ".lua", ".php", ".swift", ".kt", ".m", ".scala", ".jl", ".r", ".pl",
})

SKIP_DIRS = frozenset({
    ".git", ".hg", ".svn", "__pycache__", "node_modules", ".venv", "venv",
    "env", "dist", "build", ".tox", ".mypy_cache", ".pytest_cache", ".idea",
})

DEMO_MARKERS = ("demo", "example", "sample")
TEST_MARKERS = ("test", "spec")


def _normalise(text):
    """Fold an identifier to space-separated lowercase words.

    OUT_OF_ENVELOPE, outOfEnvelope and "out-of-envelope" all become
    "out of envelope", so one phrase list matches every casing convention.
    """
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", str(text))
    return " " + re.sub(r"[^a-z0-9]+", " ", spaced.lower()).strip() + " "


def _has_phrase(text, phrases):
    norm = _normalise(text)
    return any((" " + p + " ") in norm for p in phrases)


def _line_re(phrases):
    alts = "|".join(re.escape(p).replace(r"\ ", r"[\s_\-]+") for p in phrases)
    return re.compile(r"(?<![A-Za-z0-9])(?:%s)(?![A-Za-z0-9])" % alts, re.I)


UNKNOWN_RE = _line_re(UNKNOWN_PHRASES)
FAILURE_RE = _line_re(FAILURE_PHRASES)


# --------------------------------------------------------------------------
# file collection
# --------------------------------------------------------------------------

class Record(object):
    """One source file, with whatever of it could be read."""

    def __init__(self, path, rel):
        self.path = path
        self.rel = rel
        self.text = None      # decoded source, or None
        self.lines = []
        self.tree = None      # parsed Python AST, or None
        self.undecodable = False

    @property
    def is_python(self):
        return self.tree is not None

    @property
    def is_test(self):
        low = self.rel.lower()
        return any(m in low for m in TEST_MARKERS)

    @property
    def is_demo(self):
        low = self.rel.lower()
        if any(m in low for m in DEMO_MARKERS):
            return True
        return bool(self.text) and "__main__" in self.text


def collect(root):
    records = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames
                             if d not in SKIP_DIRS and not d.startswith("."))
        for name in sorted(filenames):
            if os.path.splitext(name)[1].lower() not in SOURCE_EXT:
                continue
            full = os.path.join(dirpath, name)
            rec = Record(full, os.path.relpath(full, root))
            try:
                with open(full, "r", encoding="utf-8") as handle:
                    rec.text = handle.read()
                rec.lines = rec.text.splitlines()
            except (UnicodeDecodeError, ValueError):
                # Readable as bytes only. A match found this way is real but
                # carries no line attribution -> HELD_UNRETRIEVABLE.
                rec.undecodable = True
                try:
                    with open(full, "rb") as handle:
                        rec.text = None
                        rec.raw = handle.read()
                except OSError:
                    continue
            except OSError:
                continue
            if rec.text is not None and full.lower().endswith(".py"):
                try:
                    rec.tree = ast.parse(rec.text)
                except SyntaxError:
                    rec.tree = None
            records.append(rec)
    return records


def _raw(rec):
    return getattr(rec, "raw", b"")


# --------------------------------------------------------------------------
# AST helpers
# --------------------------------------------------------------------------

def _node_words(node):
    """Every identifier-ish string inside a subtree."""
    out = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name):
            out.append(sub.id)
        elif isinstance(sub, ast.Attribute):
            out.append(sub.attr)
        elif isinstance(sub, ast.Constant) and isinstance(sub.value, str):
            out.append(sub.value)
    return out


def _call_name(node):
    func = node.func if isinstance(node, ast.Call) else node
    if isinstance(func, ast.Attribute):
        return func.attr
    return getattr(func, "id", None)


def _is_kill_stmt(node):
    if isinstance(node, ast.Raise):
        return True
    if isinstance(node, ast.Return):
        if node.value is None:
            return True
        if isinstance(node.value, ast.Constant) and node.value.value is None:
            return True
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
        if _call_name(node.value) in KILL_NAMES:
            return True
    return False


def _has_failure_expr(node):
    for sub in ast.walk(node):
        if isinstance(sub, ast.Constant) and sub.value in (None, False):
            return True
        if isinstance(sub, ast.UnaryOp) and isinstance(sub.op, ast.Not):
            return True
    return any(_has_phrase(w, FAILURE_PHRASES) for w in _node_words(node))


# --------------------------------------------------------------------------
# CHECK 1 -- UNKNOWN return path present
# --------------------------------------------------------------------------

def check1(records):
    hits, unlocated = [], False
    for rec in records:
        if rec.undecodable:
            if UNKNOWN_RE.search(_raw(rec).decode("latin-1", "replace")):
                unlocated = True
            continue
        if rec.is_python:
            for node in ast.walk(rec.tree):
                if isinstance(node, ast.Return) and node.value is not None:
                    if any(_has_phrase(w, UNKNOWN_PHRASES)
                           for w in _node_words(node.value)):
                        hits.append((rec.rel, node.lineno))
                elif isinstance(node, ast.ClassDef):
                    for stmt in node.body:
                        target = None
                        if isinstance(stmt, ast.Assign) and stmt.targets:
                            first = stmt.targets[0]
                            target = getattr(first, "id", None)
                        elif isinstance(stmt, ast.AnnAssign):
                            target = getattr(stmt.target, "id", None)
                        if target and _has_phrase(target, UNKNOWN_PHRASES):
                            hits.append((rec.rel, stmt.lineno))
        else:
            for num, line in enumerate(rec.lines, 1):
                if not UNKNOWN_RE.search(line):
                    continue
                # a return of it, or an enum-member-shaped assignment
                if "return" in line or re.match(r"\s*[A-Za-z_][A-Za-z0-9_]*\s*[=:]", line):
                    hits.append((rec.rel, num))
    return _label(hits, unlocated), hits


# --------------------------------------------------------------------------
# CHECK 2 -- KILL RULE stated
# --------------------------------------------------------------------------

def check2(records):
    hits, unlocated = [], False
    for rec in records:
        if rec.undecodable:
            continue
        if rec.is_python:
            for node in ast.walk(rec.tree):
                if isinstance(node, ast.If):
                    for branch in (node.body, node.orelse):
                        for stmt in branch:
                            for sub in ast.walk(stmt):
                                if _is_kill_stmt(sub):
                                    hits.append((rec.rel, sub.lineno))
                                    break
                # An assert is a condition and an abort in one statement.
                # BUILDER'S DECISION: counted outside test files only, so
                # test assertions do not read as the artifact's kill rule.
                elif isinstance(node, ast.Assert) and not rec.is_test:
                    hits.append((rec.rel, node.lineno))
        else:
            # BUILDER'S DECISION: for non-Python files the guard is looked
            # for within the three preceding lines. Crude, and stated as
            # crude rather than silently approximated.
            for num, line in enumerate(rec.lines, 1):
                if not re.search(r"\b(raise|throw|exit|abort|die)\b|return\s+(None|null|nil)\s*;?\s*$", line):
                    continue
                window = rec.lines[max(0, num - 4):num]
                if any(re.search(r"\b(if|unless|when|case)\b", w) for w in window):
                    hits.append((rec.rel, num))
    return _label(hits, unlocated), hits


# --------------------------------------------------------------------------
# CHECK 3 -- TESTS cover the failure case
#
# Returns count and present as two separate values. They are separate
# instruments and stay separate. The checker carries no threshold.
# --------------------------------------------------------------------------

def check3(records):
    hits, unlocated = [], False
    for rec in records:
        if not rec.is_test:
            continue
        if rec.undecodable:
            if FAILURE_RE.search(_raw(rec).decode("latin-1", "replace")):
                unlocated = True
            continue
        if rec.is_python:
            # A `with pytest.raises(...)` block is one assertion, but its
            # context expression is also a Call. Count the block and skip
            # that Call, or every such assertion is counted twice and the
            # count stops being a raw number.
            counted_as_with = set()
            for node in ast.walk(rec.tree):
                if isinstance(node, (ast.With, ast.AsyncWith)):
                    for item in node.items:
                        if isinstance(item.context_expr, ast.Call):
                            if _call_name(item.context_expr) in FAILURE_CALL_NAMES:
                                counted_as_with.add(id(item.context_expr))
            for node in ast.walk(rec.tree):
                if isinstance(node, ast.Assert):
                    if _has_failure_expr(node.test):
                        hits.append((rec.rel, node.lineno))
                elif isinstance(node, (ast.With, ast.AsyncWith)):
                    for item in node.items:
                        if id(item.context_expr) in counted_as_with:
                            hits.append((rec.rel, node.lineno))
                elif isinstance(node, ast.Call):
                    if id(node) in counted_as_with:
                        continue
                    if _call_name(node) in FAILURE_CALL_NAMES:
                        hits.append((rec.rel, node.lineno))
        else:
            for num, line in enumerate(rec.lines, 1):
                if re.search(r"\b(assert|expect|should)\b", line, re.I) \
                        and FAILURE_RE.search(line):
                    hits.append((rec.rel, num))
    count = len(hits)
    present = count > 0
    return _label(hits, unlocated), hits, count, present


# --------------------------------------------------------------------------
# CHECK 4 -- DEMO can fail
# --------------------------------------------------------------------------

INPUT_RE = re.compile(
    r"\bsys\.argv\b|\bargparse\b|\binput\s*\(|\bos\.environ\b|\benviron\[|"
    r"\bstdin\b|\bgetopt\b|\bfileinput\b")


def check4(records):
    demos = [r for r in records if r.is_demo and not r.is_test]
    if not demos:
        # No demo located: the check does not apply to this artifact.
        return OUT_OF_ENVELOPE, [], "no demo located"

    hits = []
    takes_input = False
    for rec in demos:
        if rec.text and INPUT_RE.search(rec.text):
            takes_input = True
        if rec.undecodable:
            continue
        if rec.is_python:
            for node in ast.walk(rec.tree):
                if isinstance(node, ast.Raise):
                    hits.append((rec.rel, node.lineno))
                elif isinstance(node, ast.ExceptHandler):
                    hits.append((rec.rel, node.lineno))
                elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                    if _call_name(node.value) in KILL_NAMES:
                        hits.append((rec.rel, node.lineno))
                elif isinstance(node, ast.Assert):
                    hits.append((rec.rel, node.lineno))
        else:
            for num, line in enumerate(rec.lines, 1):
                if re.search(r"\b(raise|throw|catch|except|rescue|exit|abort)\b", line):
                    hits.append((rec.rel, num))

    if hits:
        return HELD_RETRIEVABLE, hits, ""
    if not takes_input:
        # The stated special case: the demo is the whole artifact, with no
        # input under which it could not succeed.
        return OUT_OF_ENVELOPE, [], "demo takes no input"
    return NOT_HELD, [], ""


# --------------------------------------------------------------------------
# thresholds (FILE 1). Read only. This program never writes either file.
# --------------------------------------------------------------------------

CONFIG_NAME = "thresholds.txt"
CHECK3_KEY = "check3_failure_assertions_min"


def load_thresholds(explicit, repo_root):
    """Return (values, source_path). Missing config is not an error."""
    if explicit:
        candidates = [explicit]
    else:
        # BUILDER'S DECISION (order not specified): repo first, then the
        # directory this script sits in.
        candidates = [os.path.join(repo_root, CONFIG_NAME),
                      os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   CONFIG_NAME)]
    for path in candidates:
        if not os.path.isfile(path):
            continue
        values = {}
        try:
            with open(path, "r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" not in line:
                        continue
                    key, _, raw = line.partition("=")
                    values[key.strip()] = raw.strip()
        except OSError:
            continue
        return values, path
    return {}, None


# --------------------------------------------------------------------------
# output. Facts only.
# --------------------------------------------------------------------------

def _fmt(hits):
    if not hits:
        return "  (no location)"
    return "\n".join("  %s:%d" % (rel, line) for rel, line in hits)


def report(root, records, thresholds, config_path, first_only):
    print("gate_check  %s" % os.path.abspath(root))
    print("files scanned: %d" % len(records))
    if config_path:
        print("thresholds: %s" % config_path)
    else:
        print("thresholds: absent (no %s found)" % CONFIG_NAME)
    print("")

    def emit(title, label, hits, note=""):
        print("CHECK %s" % title)
        print("  %s%s" % (label, ("  (%s)" % note) if note else ""))
        shown = hits[:1] if first_only else hits
        print(_fmt(shown))
        if hits and first_only and len(hits) > 1:
            print("  (+%d more; omit --first to list)" % (len(hits) - 1))
        print("")

    label1, hits1 = check1(records)
    emit("1  UNKNOWN return path present", label1, hits1)

    label2, hits2 = check2(records)
    emit("2  KILL RULE stated", label2, hits2)

    label3, hits3, count3, present3 = check3(records)
    print("CHECK 3  TESTS cover the failure case")
    print("  %s" % label3)
    shown = hits3[:1] if first_only else hits3
    print(_fmt(shown))
    if hits3 and first_only and len(hits3) > 1:
        print("  (+%d more; omit --first to list)" % (len(hits3) - 1))
    print("  count = %d" % count3)
    print("  present = %s" % present3)
    if CHECK3_KEY in thresholds:
        raw = thresholds[CHECK3_KEY]
        try:
            value = int(raw)
            print("  threshold %s = %d  (count %d, at_or_above = %s)"
                  % (CHECK3_KEY, value, count3, count3 >= value))
        except ValueError:
            print("  threshold %s = %s  (not an integer; no comparison made)"
                  % (CHECK3_KEY, raw))
    else:
        print("  threshold %s: absent" % CHECK3_KEY)
    print("")

    label4, hits4, note4 = check4(records)
    emit("4  DEMO can fail", label4, hits4, note4)

    other = sorted(k for k in thresholds if k != CHECK3_KEY)
    if other:
        print("thresholds present in config and not read by any check:")
        for key in other:
            print("  %s = %s" % (key, thresholds[key]))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Presence or absence of four structural features.")
    parser.add_argument("repo", nargs="?", default=".",
                        help="repo path to walk (default: .)")
    parser.add_argument("--config", default=None,
                        help="path to %s" % CONFIG_NAME)
    # Every location is reported by default: the order asks for the file
    # and line where each check passes or is absent. --first is a display
    # convenience only.
    parser.add_argument("--first", action="store_true",
                        help="show only the first location per check")
    args = parser.parse_args(argv)

    if not os.path.isdir(args.repo):
        parser.error("not a directory: %s" % args.repo)

    records = collect(args.repo)
    thresholds, config_path = load_thresholds(args.config, args.repo)
    report(args.repo, records, thresholds, config_path, args.first)
    return 0


if __name__ == "__main__":
    sys.exit(main())
