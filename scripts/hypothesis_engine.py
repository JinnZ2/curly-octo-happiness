#!/usr/bin/env python3
"""Hypothesis Engine — an autonomous, deterministic research pipeline.

Explores free scholarly APIs, stakes each finding as a falsifiable Claim in the
repo's epistemic machinery, tests claims by cross-source verification,
reformulates failures (counting escape hatches), scans for hidden variables in
the residuals, and consolidates surviving claims into hypothesis drafts.

Stdlib only and no LLM in the loop, so it runs free on a GitHub runner and
produces the same output for the same inputs. Design doc:
`design/hypothesis_engine.md`.

    python scripts/hypothesis_engine.py --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime
from math import log2
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from xml.etree import ElementTree

# The engine stakes claims in the repo's own machinery rather than carrying a
# second copy of it (see CLAUDE.md: grounding/ is the canonical home).
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from grounding.core.claims import Claim as _RepoClaim
    from grounding.core.claims import DependencyTree as _RepoTree
    from grounding.core.epistemics import classify_falsifiability
except ImportError as exc:  # pragma: no cover - only if run outside the repo
    raise SystemExit(
        "hypothesis_engine must run from inside curly-octo-happiness "
        f"(cannot import the grounding package: {exc})")

try:
    from grounding.core.memory import EpisodicMemory
except ImportError:  # pragma: no cover
    EpisodicMemory = None

USER_AGENT = "curly-octo-happiness-hypothesis-engine/1.0 (+https://github.com/JinnZ2/curly-octo-happiness)"
TIMEOUT = 20
DEFAULT_SLEEP = 1.0

# Stage 6 gates, mirroring modules/hnd.py.
RESIDUAL_THRESHOLD = 0.1
CORRELATION_THRESHOLD = 0.5
# A residual that barely moves cannot be explained by anything; correlating it
# reads noise as signal. Same discipline as the BET spread guard in dormancy.py.
RESIDUAL_SPREAD_FLOOR = 0.05
# Pearson r on three points is not evidence, whatever its magnitude.
MIN_BUCKETS = 4
# A residual built from a prior nobody tested is not a measurement. Beta(1,1)
# carries zero Fisher information about the world, so a topic must have at least
# this many standing test outcomes before its residuals mean anything at all.
MIN_STANDING_TESTS = 8
# Above this, a candidate is indistinguishable from the clock and no amount of
# data separates the two; refusing is the only honest verdict (Reichenbach).
COLLINEAR_WITH_CLOCK = 0.98
# Floor on Kish's effective sample size, *calibrated* rather than chosen: see
# `calibrate_scan`, which measures the scan's false-positive rate on synthetic
# null corpora and returns the loosest floor that holds a 5% rate. Without any
# floor the scan fired on 36% of corpora containing no driver at all -- the
# same lesson damage.py records for CUSUM, that a criterion sound in theory has
# to have its operating characteristic measured on the data it will see.
#
# The measurement also corrected a guess. 6.0 looked right by eye, being where
# the false-positive rate first rounds to zero, but it costs 20 points of power
# for nothing. Over 4000 trials per point: 5.0 gives 3.65% false positives (95%
# upper bound 4.28%) at 58.1% power, against 0.4% and 38.6% at 6.0. A gate
# tightened past its target is not safer, only deafer.
#
# Read the power figure before trusting any suggestion this scan makes: at
# corpus sizes the engine actually sees it misses roughly two drivers in five.
# That is an argument for the epsilon-machine criterion, not for loosening this.
MIN_EFFECTIVE_SAMPLE = 5.0
# Reported as a measured cross-check on the MDL gate, not gated on.
PERMUTATIONS = 2000
SIGNIFICANCE = 0.05
PERMUTATION_SEED = 20260817

# Stage 7: a topic needs this many surviving claims to be worth drafting.
NEW_HYPOTHESIS_MIN_CLAIMS = 3
NEW_HYPOTHESIS_MARKER = "NEW HYPOTHESIS"


# ---------------------------------------------------------------------------
# small utilities
# ---------------------------------------------------------------------------

def read_jsonl(path) -> List[dict]:
    """Read a JSON-lines file; a missing file is an empty log, not an error."""
    path = Path(path)
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def append_jsonl(path, rows: Iterable[dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "topic"


def _digest(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def pearson(x: Sequence[float], y: Sequence[float]) -> float:
    """Pearson r, the same formulation modules/hnd.py uses. 0.0 when undefined."""
    if len(x) != len(y) or len(x) < 2:
        return 0.0
    n = len(x)
    sum_x, sum_y = sum(x), sum(y)
    sum_x2 = sum(v * v for v in x)
    sum_y2 = sum(v * v for v in y)
    sum_xy = sum(a * b for a, b in zip(x, y))
    numerator = n * sum_xy - sum_x * sum_y
    denominator = ((n * sum_x2 - sum_x ** 2) * (n * sum_y2 - sum_y ** 2)) ** 0.5
    if denominator == 0:
        return 0.0
    return numerator / denominator


def parse_date(value: str) -> Optional[date]:
    """Parse the date formats the three APIs hand back. None when unparseable."""
    if not value:
        return None
    text = str(value)[:10]
    for fmt, width in (("%Y-%m-%d", 10), ("%Y-%m", 7), ("%Y", 4)):
        try:
            return datetime.strptime(text[:width], fmt).date()
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# findings
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    """One scholarly record, from one source, for one topic."""

    source: str
    title: str
    url: str
    date: str
    topic: str
    abstract: str = ""

    @property
    def hash(self) -> str:
        """Dedup key. Title and url are what identify a record across runs."""
        return _digest(self.source, self.title, self.url)

    def to_dict(self) -> dict:
        row = {"source": self.source, "title": self.title, "url": self.url,
               "date": self.date, "topic": self.topic, "abstract": self.abstract}
        row["hash"] = self.hash
        return row

    @classmethod
    def from_dict(cls, row: dict) -> "Finding":
        return cls(source=row.get("source", ""), title=row.get("title", ""),
                   url=row.get("url", ""), date=row.get("date", ""),
                   topic=row.get("topic", ""), abstract=row.get("abstract", ""))


# ---------------------------------------------------------------------------
# claims
# ---------------------------------------------------------------------------

@dataclass
class Claim(_RepoClaim):
    """A repo Claim that remembers where it came from and what tested it.

    `id` is derived once from the claim's opening content and then stays put --
    reformulation rewrites the text but must not change the claim's identity,
    or its track record would silently fork.
    """

    source_url: Optional[str] = None
    id: str = ""
    tested_against: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.id:
            scope = json.dumps(self.scope or {}, sort_keys=True)
            self.id = _digest(self.text, self.falsification, scope)[:16]

    @property
    def topic(self) -> str:
        return (self.scope or {}).get("topic", "unscoped")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "falsification": self.falsification,
            "confidence": self.confidence,
            "passed": self.passed,
            "failed": self.failed,
            "scope": self.scope,
            "reference_class": self.reference_class,
            "reformulation_count": self.reformulation_count,
            "meta_flags": list(self.meta_flags),
            "source_url": self.source_url,
            "tested_against": list(self.tested_against),
            "status": self.status,
            "beta_confidence": round(self.beta_confidence, 4),
        }

    @classmethod
    def from_dict(cls, row: dict) -> "Claim":
        return cls(
            text=row["text"],
            falsification=row.get("falsification", ""),
            confidence=row.get("confidence", 0.5),
            passed=row.get("passed", 0),
            failed=row.get("failed", 0),
            scope=row.get("scope"),
            reference_class=row.get("reference_class"),
            reformulation_count=row.get("reformulation_count", 0),
            meta_flags=list(row.get("meta_flags", [])),
            source_url=row.get("source_url"),
            id=row.get("id", ""),
            tested_against=list(row.get("tested_against", [])),
        )


class DependencyTree:
    """Claim registry for the engine, backed by the repo's dependency tree.

    `claims` is the engine's flat id -> Claim index; `tree` is the repo
    `DependencyTree` the claims are actually staked in, one concept node per
    topic, so confidence propagation and the revolutionary-claim flag come from
    the repo's machinery rather than a reimplementation of it.
    """

    def __init__(self) -> None:
        self.claims: Dict[str, Claim] = {}
        self.tree = _RepoTree()

    def add_claim(self, claim: Claim) -> Claim:
        self.claims[claim.id] = claim
        self.tree.add_claim(claim.topic, claim)
        return claim

    def remove(self, claim: Claim) -> None:
        self.claims.pop(claim.id, None)
        node = self.tree.nodes.get(claim.topic)
        if node is not None:
            node.claims = [c for c in node.claims if getattr(c, "id", None) != claim.id]

    def by_topic(self) -> Dict[str, List[Claim]]:
        grouped: Dict[str, List[Claim]] = {}
        for claim in self.claims.values():
            grouped.setdefault(claim.topic, []).append(claim)
        return grouped

    def propagate(self) -> None:
        self.tree.propagate_confidence()


def save_tree(tree: DependencyTree, path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"saved_at": datetime.now().isoformat(timespec="seconds"),
               "claims": [c.to_dict() for c in tree.claims.values()]}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def load_tree(path) -> DependencyTree:
    """Reload the persisted tree; a missing file just means a fresh start."""
    tree = DependencyTree()
    path = Path(path)
    if not path.exists():
        return tree
    payload = json.loads(path.read_text(encoding="utf-8"))
    for row in payload.get("claims", []):
        tree.add_claim(Claim.from_dict(row))
    return tree


# ---------------------------------------------------------------------------
# text heuristics
# ---------------------------------------------------------------------------

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
    "have", "in", "is", "it", "its", "of", "on", "or", "our", "that", "the",
    "their", "there", "these", "this", "to", "was", "we", "were", "when",
    "which", "with", "results", "result", "study", "paper", "show", "shows",
    "showed", "using", "used", "can", "may", "also", "than", "then", "they",
}

HEDGE_MARKERS = (
    "might", "perhaps", "may remain", "could perhaps", "in some sense",
    "we believe", "elusive", "do not commit", "arguably", "conceivably",
    "it is possible that", "seems to suggest",
)

CORROBORATION_MARKERS = (
    "confirm", "confirms", "confirmed", "validate", "validates", "validating",
    "replicate", "replicates", "replicated", "replication", "corroborate",
    "corroborates", "consistent", "reproduce", "reproduces", "reproducible",
    "support", "supports",
)

CONTRADICTION_MARKERS = (
    "fail", "fails", "failed", "cannot", "no effect", "does not", "do not",
    "contradict", "contradicts", "refute", "refutes", "underperform",
    "underperforms", "inconsistent", "unreliable", "not reproducible",
)

# A measurable anchor: a number, a percentage, or an explicit inequality. A
# claim without one has nothing a replication could disagree with.
MEASURABLE = re.compile(r"(\d+(?:\.\d+)?\s*%|\b\d+(?:\.\d+)?\b|[<>≥≤]=?)")


def _tokens(text: str) -> set:
    """Content words, crudely singularised so 'agent'/'agents' match."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    out = set()
    for word in words:
        if word in STOPWORDS or len(word) < 3:
            continue
        if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
            word = word[:-1]
        out.add(word)
    return out


def _count_markers(text: str, markers: Sequence[str]) -> int:
    lowered = text.lower()
    return sum(lowered.count(marker) for marker in markers)


def corroboration(claim_text: str, other_text: str, min_overlap: int = 2) -> int:
    """Does `other_text` corroborate (+1), contradict (-1), or ignore (0) the claim?

    Two gates. First topical overlap -- unrelated work is no evidence either
    way, however confidently it is worded. Then the balance of corroboration
    against contradiction markers. Equal counts return 0: agreement with no
    explicit signal is not replication, and the design doc is blunt that this
    oracle is weak evidence.
    """
    shared = _tokens(claim_text) & _tokens(other_text)
    if len(shared) < min_overlap:
        return 0
    positive = _count_markers(other_text, CORROBORATION_MARKERS)
    negative = _count_markers(other_text, CONTRADICTION_MARKERS)
    if negative > positive:
        return -1
    if positive > negative:
        return 1
    return 0


def first_sentence(text: str, limit: int = 320) -> str:
    text = " ".join((text or "").split())
    if not text:
        return ""
    match = re.search(r"(?<=[.!?])\s", text)
    sentence = text[:match.start() + 1] if match else text
    return sentence[:limit].strip()


def distill_claim(finding: Finding) -> Tuple[str, str, str]:
    """Turn a finding into (claim text, falsification condition, reference class).

    Template-distilled, per the design doc's stated limitation. The one piece of
    judgement is the falsification condition: it is built from the measurable
    anchor in the abstract, and when there is no anchor -- or the abstract is
    hedged past the point of commitment -- it comes back empty, which
    `classify_falsifiability` reads as unfalsifiable and routes to the unknown
    journal rather than the tree.
    """
    claim_text = (f"On topic {finding.topic}, {finding.title} reports: "
                  f"{first_sentence(finding.abstract) or 'no abstract available'}")
    reference_class = f"{finding.source} records on '{finding.topic}'"

    body = finding.abstract or ""
    anchors = MEASURABLE.findall(body)
    hedges = _count_markers(body, HEDGE_MARKERS)

    if not body or not anchors:
        return claim_text, "", reference_class
    if hedges >= 2:
        # Hedged past commitment: the text states no condition it would fail.
        return claim_text, "", reference_class

    quantity = anchors[0].strip()
    falsification = (f"An independent source on '{finding.topic}' reports the "
                     f"opposite effect, or fails to reproduce the stated "
                     f"{quantity} result")
    return claim_text, falsification, reference_class


# ---------------------------------------------------------------------------
# stage 1 — explore
# ---------------------------------------------------------------------------

def _fetch(url: str) -> Optional[bytes]:
    """One network read. Every failure is logged and the run continues."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.read()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        print(f"  ! fetch failed ({exc}): {url}", file=sys.stderr)
        return None


def fetch_arxiv(query: str, topic: str, limit: int) -> List[Finding]:
    url = ("http://export.arxiv.org/api/query?"
           + urllib.parse.urlencode({"search_query": f"all:{query}",
                                     "start": 0, "max_results": limit}))
    raw = _fetch(url)
    if not raw:
        return []
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    try:
        root = ElementTree.fromstring(raw)
    except ElementTree.ParseError as exc:
        print(f"  ! arxiv parse failed: {exc}", file=sys.stderr)
        return []
    findings = []
    for entry in root.findall("atom:entry", ns):
        title = (entry.findtext("atom:title", "", ns) or "").strip()
        summary = (entry.findtext("atom:summary", "", ns) or "").strip()
        link = (entry.findtext("atom:id", "", ns) or "").strip()
        published = (entry.findtext("atom:published", "", ns) or "")[:10]
        if title:
            findings.append(Finding("arxiv", " ".join(title.split()), link,
                                    published, topic, " ".join(summary.split())))
    return findings


def fetch_semantic_scholar(query: str, topic: str, limit: int) -> List[Finding]:
    url = ("https://api.semanticscholar.org/graph/v1/paper/search?"
           + urllib.parse.urlencode({"query": query, "limit": limit,
                                     "fields": "title,abstract,url,year"}))
    raw = _fetch(url)
    if not raw:
        return []
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"  ! semantic_scholar parse failed: {exc}", file=sys.stderr)
        return []
    findings = []
    for paper in payload.get("data", []) or []:
        title = (paper.get("title") or "").strip()
        if not title:
            continue
        year = paper.get("year")
        findings.append(Finding("semantic_scholar", title,
                                paper.get("url") or "",
                                f"{year}-01-01" if year else "",
                                topic, (paper.get("abstract") or "").strip()))
    return findings


def fetch_crossref(query: str, topic: str, limit: int) -> List[Finding]:
    url = ("https://api.crossref.org/works?"
           + urllib.parse.urlencode({"query": query, "rows": limit}))
    raw = _fetch(url)
    if not raw:
        return []
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"  ! crossref parse failed: {exc}", file=sys.stderr)
        return []
    findings = []
    for item in payload.get("message", {}).get("items", []) or []:
        titles = item.get("title") or []
        if not titles:
            continue
        parts = (item.get("issued", {}).get("date-parts") or [[]])[0]
        issued = "-".join(f"{p:02d}" if i else str(p) for i, p in enumerate(parts))
        abstract = re.sub(r"<[^>]+>", " ", item.get("abstract") or "")
        findings.append(Finding("crossref", " ".join(titles[0].split()),
                                item.get("URL") or "", issued, topic,
                                " ".join(abstract.split())))
    return findings


FETCHERS = {
    "arxiv": fetch_arxiv,
    "semantic_scholar": fetch_semantic_scholar,
    "crossref": fetch_crossref,
}


def stage_explore(topics: List[dict], max_per_topic: int = 10,
                  dry_run: bool = False, sample_path=None,
                  sleep: float = DEFAULT_SLEEP) -> List[Finding]:
    """Collect findings for every topic. Offline in dry-run mode."""
    if dry_run:
        return _load_sample(topics, max_per_topic, sample_path)

    findings: List[Finding] = []
    for topic in topics:
        name = topic["name"]
        for query in topic.get("queries", []):
            for source in topic.get("sources", []):
                fetcher = FETCHERS.get(source)
                if fetcher is None:
                    print(f"  ! unknown source {source!r}, skipping", file=sys.stderr)
                    continue
                got = fetcher(query, name, max_per_topic)
                print(f"  {source:17} {len(got):3d} for {query!r}")
                findings.extend(got)
                if sleep:
                    time.sleep(sleep)
    return findings


def _load_sample(topics: List[dict], max_per_topic: int, sample_path) -> List[Finding]:
    path = Path(sample_path or REPO_ROOT / "scripts" / "sample_findings.json")
    rows = json.loads(path.read_text(encoding="utf-8"))
    wanted = {t["name"] for t in topics}
    per_topic: Dict[str, int] = {}
    findings = []
    for row in rows:
        finding = Finding.from_dict(row)
        if wanted and finding.topic not in wanted:
            continue
        if per_topic.get(finding.topic, 0) >= max_per_topic:
            continue
        per_topic[finding.topic] = per_topic.get(finding.topic, 0) + 1
        findings.append(finding)
    return findings


# ---------------------------------------------------------------------------
# stage 2 — log
# ---------------------------------------------------------------------------

def stage_log(findings: List[Finding], log_path) -> Tuple[List[Finding], int]:
    """Append unseen findings to the log. Returns (new findings, skipped count)."""
    log_path = Path(log_path)
    seen = {row.get("hash") for row in read_jsonl(log_path)}
    new, skipped = [], 0
    for finding in findings:
        if finding.hash in seen:
            skipped += 1
            continue
        seen.add(finding.hash)
        new.append(finding)
    if new:
        append_jsonl(log_path, [f.to_dict() for f in new])
        _remember(new, log_path.parent / "episodic_memory.json")
    return new, skipped


def _remember(findings: List[Finding], memory_path: Path) -> None:
    """Persist findings as episodic memory events.

    The repo's EpisodicMemory is an in-process deque, so it cannot carry state
    between weekly runs on a fresh runner; the JSON index is what actually
    persists. When the class is importable it still runs, so the engine's
    memories are shaped exactly like the agents'.
    """
    events = []
    if memory_path.exists():
        try:
            events = json.loads(memory_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            events = []

    memory = EpisodicMemory() if EpisodicMemory is not None else None
    for finding in findings:
        content = f"[{finding.source}] {finding.title}"
        if memory is not None:
            memory.add("engine", content, tags=["finding", finding.topic])
        events.append({"speaker": "engine", "content": content,
                       "tags": ["finding", finding.topic],
                       "url": finding.url, "date": finding.date})

    memory_path.parent.mkdir(parents=True, exist_ok=True)
    memory_path.write_text(json.dumps(events[-2000:], indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# stage 3 — claim
# ---------------------------------------------------------------------------

def stage_claim(findings: List[Finding], tree: DependencyTree,
                unknown_path) -> Tuple[List[Claim], int]:
    """Distil findings into claims; route the unfalsifiable ones aside.

    Unfalsifiable content is preserved in the unknown journal, never dropped:
    a mystery is not a refutation.
    """
    made: List[Claim] = []
    unknown_rows: List[dict] = []

    for finding in findings:
        text, falsification, reference_class = distill_claim(finding)
        claim = Claim(
            text=text,
            falsification=falsification,
            scope={"topic": finding.topic, "source": finding.source,
                   "date": finding.date},
            reference_class=reference_class,
            source_url=finding.url,
        )
        if classify_falsifiability(claim) == "unfalsifiable":
            unknown_rows.append({
                "flag": "unfalsifiable",
                "topic": finding.topic,
                "text": text,
                "reason": "no measurable falsification condition in the abstract",
                "source": finding.source,
                "url": finding.url,
                "logged_at": datetime.now().isoformat(timespec="seconds"),
            })
            continue
        tree.add_claim(claim)
        made.append(claim)

    if unknown_rows:
        append_jsonl(unknown_path, unknown_rows)
    return made, len(unknown_rows)


# ---------------------------------------------------------------------------
# stage 4 — test
# ---------------------------------------------------------------------------

def stage_test(tree: DependencyTree, findings: Sequence) -> Dict[str, int]:
    """Test staked claims against every *other* source on the same topic.

    With no world to poke, cross-source verification is the only oracle
    available: an independent record that corroborates raises confidence, one
    that contradicts lowers it. Each (claim, finding) pair is used once and
    remembered, so re-running the engine on the same corpus does not
    re-litigate settled evidence.
    """
    rows = [f if isinstance(f, dict) else f.to_dict() for f in findings]
    stats = {"passed": 0, "failed": 0, "skipped": 0}

    for claim in tree.claims.values():
        for row in rows:
            if row.get("topic") != claim.topic:
                continue
            if row.get("url") and row.get("url") == claim.source_url:
                continue  # a paper cannot corroborate itself
            key = row.get("hash") or _digest(row.get("source", ""),
                                             row.get("title", ""),
                                             row.get("url", ""))
            if key in claim.tested_against:
                continue
            verdict = corroboration(claim.text, row.get("abstract", "") or "")
            if verdict == 0:
                stats["skipped"] += 1
                continue
            claim.tested_against.append(key)
            claim.test(verdict > 0)
            stats["passed" if verdict > 0 else "failed"] += 1
    return stats


# ---------------------------------------------------------------------------
# stage 5 — modify
# ---------------------------------------------------------------------------

def stage_modify(tree: DependencyTree, unknown_path, reform_path) -> Dict[str, int]:
    """Reformulate falsified claims, and escape-hatch the serial offenders.

    A falsified claim gets one narrowed restatement per run. The third
    reformulation is the tell -- a claim being endlessly patched to survive is
    not being tested -- so it leaves the tree for the unknown journal.
    """
    stats = {"reformulated": 0, "escape_hatched": 0}
    reform_rows: List[dict] = []
    unknown_rows: List[dict] = []

    for claim in list(tree.claims.values()):
        if claim.status != "falsified":
            continue

        restriction = f"restricted after failure #{claim.reformulation_count + 1}"
        scope = dict(claim.scope or {})
        scope["restrictions"] = list(scope.get("restrictions", [])) + [restriction]
        claim.scope = scope
        claim.reformulate(
            text=f"{claim.text} (scope narrowed: {restriction})",
            falsification=claim.falsification)
        stats["reformulated"] += 1
        reform_rows.append({
            "claim_id": claim.id,
            "reformulation_count": claim.reformulation_count,
            "text": claim.text,
            "topic": claim.topic,
            "logged_at": datetime.now().isoformat(timespec="seconds"),
        })

        if claim.escape_hatch_suspected:
            tree.remove(claim)
            stats["escape_hatched"] += 1
            unknown_rows.append({
                "flag": "escape-hatch",
                "topic": claim.topic,
                "text": claim.text,
                "reason": (f"reformulated {claim.reformulation_count}x without "
                           "surviving a test"),
                "claim_id": claim.id,
                "url": claim.source_url,
                "logged_at": datetime.now().isoformat(timespec="seconds"),
            })

    if reform_rows:
        append_jsonl(reform_path, reform_rows)
    if unknown_rows:
        append_jsonl(unknown_path, unknown_rows)
    return stats


# ---------------------------------------------------------------------------
# stage 6 — hidden variables
# ---------------------------------------------------------------------------

class TimeGrid:
    """Equal-width time buckets shared by the residuals and every candidate.

    The point of the grid is that bucket *i* means the same interval on both
    sides of the correlation. Without it the only thing lining a residual up
    with a candidate value is list position -- claim-stake order against
    chronological order -- and those two orderings are unrelated.
    """

    def __init__(self, start: date, span_days: int, n_buckets: int) -> None:
        self.start = start
        self.span_days = span_days
        self.n_buckets = n_buckets

    @classmethod
    def over(cls, dates: Sequence[date], n_buckets: int) -> Optional["TimeGrid"]:
        if len(dates) < 2 or n_buckets < 2:
            return None
        start, end = min(dates), max(dates)
        span = (end - start).days
        if span <= 0:
            return None
        return cls(start, span, n_buckets)

    def index(self, when: date) -> int:
        offset = (when - self.start).days
        return max(0, min(self.n_buckets - 1,
                          int(offset / self.span_days * self.n_buckets)))

    def bucket(self, dated: Iterable[Tuple[date, Any]]) -> List[List[Any]]:
        out: List[List[Any]] = [[] for _ in range(self.n_buckets)]
        for when, item in dated:
            out[self.index(when)].append(item)
        return out


def candidate_series(rows: List[dict], grid: TimeGrid) -> List[Tuple[str, List[float]]]:
    """Exogenous series the residuals can be correlated against.

    One summary statistic per bucket of `grid`. These stand in for the
    environmental time series modules/hnd.py correlates against.
    """
    dated = [(parse_date(r.get("date", "")), r) for r in rows]
    buckets = grid.bucket((d, r) for d, r in dated if d is not None)
    volume = [float(len(b)) for b in buckets]
    diversity = [float(len({r.get("source", "") for r in b})) for b in buckets]
    return [("findings_volume", volume), ("source_diversity", diversity)]


def beta_precision(passed: int, failed: int) -> float:
    """Inverse variance of a claim's Beta(1+p, 1+f) posterior: its weight.

    Var = theta(1-theta)/(a+b+1), so the precision rises linearly with the
    number of tests behind the claim -- the Fisher information of a binomial
    proportion. This is the whole reason an unweighted mean was wrong: an
    untested claim and a claim tested twenty times to a dead heat both report
    `beta_confidence` 0.5, and only the variance tells them apart (1/12 against
    1/172). Weighting by precision is the minimum-variance combination of
    measurements -- Gauss-Markov -- and it makes an untested claim contribute
    almost nothing without needing a rule that says so.
    """
    a, b = 1 + passed, 1 + failed
    return (a + b) ** 2 * (a + b + 1) / (a * b)


def weighted_pearson(x: Sequence[float], y: Sequence[float],
                     w: Sequence[float]) -> float:
    """Pearson r with per-observation weights. 0.0 when undefined."""
    if not (len(x) == len(y) == len(w)) or len(x) < 2 or sum(w) <= 0:
        return 0.0
    total = sum(w)
    mx = sum(a * wi for a, wi in zip(x, w)) / total
    my = sum(b * wi for b, wi in zip(y, w)) / total
    cov = sum(wi * (a - mx) * (b - my) for a, b, wi in zip(x, y, w))
    vx = sum(wi * (a - mx) ** 2 for a, wi in zip(x, w))
    vy = sum(wi * (b - my) ** 2 for b, wi in zip(y, w))
    denominator = (vx * vy) ** 0.5
    if denominator <= 0:
        return 0.0
    return max(-1.0, min(1.0, cov / denominator))


def weighted_partial(x: Sequence[float], y: Sequence[float], z: Sequence[float],
                     w: Sequence[float]) -> Optional[float]:
    """r(x, y | z): the correlation left once z explains what it can.

    Here z is the clock. Both candidates are functions of elapsed time -- the
    literature thickens -- and so is accumulated evidence, so a raw correlation
    between them is Reichenbach's common cause rather than a driver. Measured on
    the live corpus, `findings_volume` correlates with time at 0.876 on its own.

    Returns None when the candidate is collinear with the clock: there is then
    no variation left to attribute, and "cannot tell" is the honest answer
    rather than a number.
    """
    rxy = weighted_pearson(x, y, w)
    rxz = weighted_pearson(x, z, w)
    ryz = weighted_pearson(y, z, w)
    if abs(rxz) > COLLINEAR_WITH_CLOCK:
        return None
    denominator = ((1 - rxz ** 2) * (1 - ryz ** 2)) ** 0.5
    if denominator < 1e-12:
        return None
    return max(-1.0, min(1.0, (rxy - rxz * ryz) / denominator))


def effective_sample_size(w: Sequence[float]) -> float:
    """Kish's n_eff = (sum w)^2 / sum w^2.

    How many equally-informative observations the weighted set is worth. Seven
    claims of which three were never tested are not seven observations, and the
    description-length gate below is charged against this rather than the raw
    bucket count.
    """
    squares = sum(v * v for v in w)
    return (sum(w) ** 2 / squares) if squares > 0 else 0.0


def description_length_gain(r: Optional[float], n: float, k: int = 1) -> float:
    """Bits saved by keeping a predictor, minus the bits it costs to state it.

    Rissanen's MDL in its Schwarz/BIC form: coding the residual under a linear
    model with correlation r saves -(n/2) log2(1-r^2) bits, and naming the
    parameter costs (k/2) log2(n). Positive means the candidate pays for
    itself. This replaces a 0.05 significance convention with a quantity that
    has units, and it tightens on its own as n falls -- |r| must clear 0.49 at
    seven observations but only 0.21 at a hundred.

    Worth stating plainly: MDL alone would *not* have caught the first live
    run's false positive (it scores +2.3 bits). The alignment, the precision
    weighting and the clock are what reject it; MDL's contribution is removing
    the arbitrary threshold, not doing the rejecting.
    """
    if r is None or n <= 1:
        return 0.0
    # A perfect fit saves unboundedly many bits in the limit; clamp rather than
    # zero it, since returning 0.0 here would read "worthless" for the one case
    # that is worth the most.
    rho = min(abs(r), 1.0 - 1e-12)
    return -(n / 2) * log2(1 - rho * rho) - (k / 2) * log2(n)


def permutation_p(x: Sequence[float], y: Sequence[float], observed: float,
                  trials: int = PERMUTATIONS,
                  seed: int = PERMUTATION_SEED) -> float:
    """Two-sided p for |r| under random re-pairing, by permutation.

    The bucket counts here are single digits, where the asymptotic t-test on r
    is not trustworthy; permuting the pairing measures the null directly. The
    add-one form keeps p strictly positive, and the seed keeps a committed
    digest reproducible.
    """
    rng = random.Random(seed)
    shuffled = list(y)
    target = abs(observed) - 1e-12
    hits = 0
    for _ in range(trials):
        rng.shuffle(shuffled)
        if abs(pearson(x, shuffled)) >= target:
            hits += 1
    return (hits + 1) / (trials + 1)


def stage_hidden(tree: DependencyTree, findings: Sequence, hidden_path,
                 residual_threshold: float = RESIDUAL_THRESHOLD,
                 correlation_threshold: float = CORRELATION_THRESHOLD,
                 significance: float = SIGNIFICANCE,
                 min_effective: float = MIN_EFFECTIVE_SAMPLE,
                 permutations: int = PERMUTATIONS) -> List[dict]:
    """Scan claim residuals for unmodelled drivers, mirroring modules/hnd.py.

    The residual of a claim is how far its calibrated posterior sits from
    "no idea": `beta_confidence - 0.5`. Signed, because the direction is the
    evidence -- a topic whose claims drift confident as the literature thickens
    is telling you something a topic with random scatter is not.

    Each claim is placed in real time by the finding it was staked from, and
    residuals are combined per bucket, so a correlation is between two things
    measured over the same interval.

    Every gate here is a quantity rather than a convention. A claim is weighted
    by the precision of its own posterior, so evidence-free claims fall out of
    the average on their own (`beta_precision`); a topic must carry standing
    test outcomes at all, because a residual built from an untouched prior is
    not a measurement; the candidate is judged on what it explains *after the
    clock* has explained what it can, since the literature thickening drives
    both sides; and it is kept only if it pays for itself in bits
    (`description_length_gain`) charged against Kish's effective sample size
    rather than the raw bucket count.

    Replayed against the first live run, every topic is now refused and each
    gate earns its keep on a different one. The topic that produced the
    reported `source_diversity` driver kept its evidence (51 standing tests)
    but its seven claims fall into *two* occupied buckets, so there were never
    seven observations to correlate. The two topics reformulation had reset are
    stopped earlier, by the standing-evidence floor. Nothing survives to reach
    the clock test on this corpus, which is the honest outcome for 136 papers.
    """
    rows = [f if isinstance(f, dict) else f.to_dict() for f in findings]
    when_by_url = {}
    for row in rows:
        parsed = parse_date(row.get("date", ""))
        if parsed is not None and row.get("url"):
            when_by_url[row["url"]] = parsed
    suggestions: List[dict] = []

    for topic, claims in sorted(tree.by_topic().items()):
        dated_claims = [(when_by_url[c.source_url], c) for c in claims
                        if c.source_url in when_by_url]
        if len(dated_claims) < MIN_BUCKETS:
            continue
        # Absolute information floor. Weighting sorts out which claims matter
        # relative to each other; it cannot rescue a topic where every claim is
        # an untested prior, because then the weights are merely equal.
        standing = sum(c.passed + c.failed for _, c in dated_claims)
        if standing < MIN_STANDING_TESTS:
            continue

        topic_rows = [r for r in rows if r.get("topic") in (topic, None)] or rows
        topic_dates = [d for d in (parse_date(r.get("date", "")) for r in topic_rows)
                       if d is not None]
        grid = TimeGrid.over(topic_dates, len(dated_claims))
        if grid is None:
            continue

        # Residuals onto the same grid, then keep only the buckets that carry a
        # claim -- and drop those buckets from every candidate too, so both
        # sides stay aligned on the interval rather than on list position.
        binned = grid.bucket(
            (d, (c.beta_confidence - 0.5, beta_precision(c.passed, c.failed)))
            for d, c in dated_claims)
        occupied = [i for i, b in enumerate(binned) if b]
        if len(occupied) < MIN_BUCKETS:
            continue
        # Information adds, so a bucket's weight is the total precision in it
        # and its residual is the precision-weighted mean of its claims.
        residuals, weights = [], []
        for i in occupied:
            total = sum(w for _, w in binned[i])
            residuals.append(sum(v * w for v, w in binned[i]) / total)
            weights.append(total)
        clock = [float(i) for i in occupied]

        mean_abs = sum(abs(r) for r in residuals) / len(residuals)
        if mean_abs < residual_threshold:
            continue
        spread = max(residuals) - min(residuals)
        if spread < RESIDUAL_SPREAD_FLOOR:
            continue
        n_eff = effective_sample_size(weights)
        if n_eff < min_effective:
            continue

        candidates = candidate_series(topic_rows, grid)
        # MDL charges for the search as well as the fit: naming which of the
        # candidates won costs log2(m) bits. Dropping this when the permutation
        # test's Bonferroni correction was replaced left the scan taking the
        # best of several shots for free.
        search_cost = log2(len(candidates)) if len(candidates) > 1 else 0.0
        for name, full_series in candidates:
            series = [full_series[i] for i in occupied]
            r = weighted_pearson(series, residuals, weights)
            if abs(r) <= correlation_threshold:
                continue
            partial = weighted_partial(series, residuals, clock, weights)
            if partial is None:
                continue          # indistinguishable from the clock
            # k=2, not 1: the clock is a fitted term in this model too, and
            # charging for only the candidate understates what was spent.
            gain = description_length_gain(partial, n_eff, k=2) - search_cost
            if gain <= 0:
                continue
            p = (permutation_p(series, residuals, partial, trials=permutations)
                 if permutations > 0 else None)
            suggestions.append({
                "type": "hidden_variable_suggestion",
                "topic": topic,
                "candidate": name,
                "correlation": round(r, 4),
                "partial_correlation": round(partial, 4),
                "description_length_gain_bits": round(gain, 3),
                "p_value": round(p, 5) if p is not None else None,
                "effective_sample_size": round(n_eff, 2),
                "standing_tests": standing,
                "mean_abs_residual": round(mean_abs, 4),
                "residual_spread": round(spread, 4),
                "n_buckets": len(occupied),
                "n_claims": len(dated_claims),
                "evidence": (f"claim residuals on '{topic}' track {name} "
                             f"(r={r:.2f}, {partial:+.2f} once the clock is "
                             f"accounted for) and it pays for itself by "
                             f"{gain:.1f} bits over {n_eff:.1f} effective "
                             f"observations from {standing} standing tests"),
                "logged_at": datetime.now().isoformat(timespec="seconds"),
            })

    if suggestions and hidden_path is not None:
        append_jsonl(hidden_path, suggestions)
    return suggestions


# ---------------------------------------------------------------------------
# stage 6 — calibration
#
# The scan's gates are only worth what its measured error rates say they are.
# This mirrors `SequentialDamageDetector.calibrate_from` in grounding/core/
# damage.py: build streams whose truth is known, run the real detector over
# them, and set the threshold from what comes back rather than from what the
# derivation promised.
# ---------------------------------------------------------------------------

CALIBRATION_SEED = 20260818


def synthetic_topic(rng: random.Random, n_claims: int = 8, *,
                    driver: bool = False, topic: str = "t",
                    spikes: Sequence[int] = (3, 7, 11)) -> Tuple[Any, List[dict]]:
    """A corpus whose truth is known, for measuring the scan against.

    With `driver=False` the evidence on each claim is independent of everything
    else, so any suggestion the scan returns is a false positive by
    construction. With `driver=True` publication volume spikes in `spikes` and
    the well-corroborated claims sit on those spikes -- an association that is
    genuinely there and, because it is not monotone in time, one that survives
    the clock control rather than being manufactured by it.
    """
    tree = DependencyTree()
    findings: List[dict] = []
    for i in range(n_claims):
        month = rng.randint(1, 12)
        if not driver:
            passed, failed = rng.randint(0, 10), rng.randint(0, 10)
        elif month in spikes:
            passed, failed = rng.randint(7, 10), rng.randint(0, 2)
        else:
            passed, failed = rng.randint(0, 2), rng.randint(7, 10)
        url = f"https://example.invalid/{topic}/{i}"
        tree.add_claim(Claim(text=f"synthetic claim {i}", falsification="x",
                             passed=passed, failed=failed,
                             scope={"topic": topic}, source_url=url))
        findings.append({"date": f"2024-{month:02d}-{rng.randint(1, 28):02d}",
                         "topic": topic, "url": url,
                         "source": rng.choice(["arxiv", "crossref"])})
    padded = spikes if driver else range(1, 13)
    for month in padded:
        for k in range(8 if driver else 2):
            findings.append({"date": f"2024-{month:02d}-15", "topic": topic,
                             "url": f"https://example.invalid/pad/{month}/{k}",
                             "source": rng.choice(["arxiv", "crossref"])})
    return tree, findings


def wilson_upper(successes: int, trials: int, z: float = 1.96) -> float:
    """Upper bound of the Wilson score interval for a binomial rate.

    A measured false-positive rate is itself an estimate: 300 trials of a true
    4% rate return anything from 2% to 7% depending on the seed, so calibrating
    against the point estimate promises a rate the next sample can break. The
    bound is what the promise should be made on -- and unlike the normal
    approximation it stays sane when zero events are observed, which is the
    common case at a high floor.
    """
    if trials <= 0:
        return 1.0
    p = successes / trials
    z2 = z * z
    denominator = 1 + z2 / trials
    center = (p + z2 / (2 * trials)) / denominator
    half = z * ((p * (1 - p) / trials + z2 / (4 * trials * trials)) ** 0.5) / denominator
    return min(1.0, center + half)


def scan_operating_characteristic(min_effective: float, *, trials: int = 300,
                                  n_claims: int = 8, seed: int = CALIBRATION_SEED
                                  ) -> Dict[str, float]:
    """Measure (false positive rate, power) of the scan at one n_eff floor.

    Both halves matter and they trade against each other: a floor high enough
    to silence every null corpus also silences most real drivers, and a scan
    that never fires is not thereby correct.
    """
    rates: Dict[str, float] = {}
    for label, driver in (("false_positive_rate", False), ("power", True)):
        rng = random.Random(seed)
        fired = 0
        for _ in range(trials):
            tree, findings = synthetic_topic(
                rng, n_claims=n_claims + (4 if driver else 0), driver=driver)
            if _scan_topics(tree, findings, min_effective):
                fired += 1
        rates[label] = fired / trials
        if not driver:
            rates["false_positive_upper"] = wilson_upper(fired, trials)
    rates["min_effective"] = min_effective
    rates["trials"] = trials
    return rates


def _scan_topics(tree, findings, min_effective: float) -> List[dict]:
    """stage_hidden with no logging and no permutation diagnostic.

    Calibration runs the scan tens of thousands of times, so it skips both the
    write and the 2000-permutation cross-check. Neither is a gate, so what is
    measured here is exactly what production decides on.
    """
    return stage_hidden(tree, findings, None, min_effective=min_effective,
                        permutations=0)


def calibrate_scan(target_false_positive: float = 0.05,
                   floors: Sequence[float] = (0.0, 3.0, 4.0, 5.0, 5.5, 6.0,
                                              6.5, 7.0, 8.0),
                   trials: int = 800, n_claims: int = 8,
                   seed: int = CALIBRATION_SEED) -> Dict[str, Any]:
    """Smallest n_eff floor whose *measured* false-positive rate meets target.

    Smallest, not safest: every increment of the floor costs power, so the
    honest choice is the loosest gate that still holds the promise. The whole
    curve is returned with it, because a floor picked without its power cost in
    view is how a detector ends up sound and useless at the same time.

    Raises when no floor in the grid reaches the target -- that means the scan
    cannot make the promise on corpora this size, which is a fact to report
    rather than a threshold to keep raising.
    """
    # Enough trials to resolve the rate being promised: fewer than ~10 expected
    # events and the estimate is noise. damage.py refuses short samples for the
    # same reason.
    needed = int(10 / target_false_positive) if target_false_positive > 0 else 0
    if target_false_positive > 0 and trials < needed:
        raise ValueError(
            f"{trials} trials cannot resolve a {target_false_positive:.0%} rate; "
            f"need ~{needed} so the measurement sees ten false alarms")

    curve = [scan_operating_characteristic(floor, trials=trials,
                                           n_claims=n_claims, seed=seed)
             for floor in floors]
    # Judge on the confidence bound, not the point estimate: the floor has to
    # hold the promise on the next sample too, not merely on this one.
    passing = [row for row in curve
               if row["false_positive_upper"] <= target_false_positive]
    if not passing:
        best = min(curve, key=lambda row: row["false_positive_upper"])
        raise ValueError(
            f"no floor in {list(floors)} holds a {target_false_positive:.0%} "
            f"false-positive rate on {n_claims}-claim corpora; the best bound is "
            f"{best['false_positive_upper']:.1%} at n_eff >= {best['min_effective']}")
    chosen = min(passing, key=lambda row: row["min_effective"])
    return {
        "min_effective": chosen["min_effective"],
        "false_positive_rate": chosen["false_positive_rate"],
        "false_positive_upper": chosen["false_positive_upper"],
        "power": chosen["power"],
        "trials": trials,
        "target_false_positive": target_false_positive,
        "shipped_default": MIN_EFFECTIVE_SAMPLE,
        "curve": curve,
    }


def _report_calibration(trials: int) -> int:
    """Print stage 6's measured operating characteristic. Behind --calibrate."""
    print(f"stage 6 operating characteristic ({trials} trials per point)\n")
    print(f"{'n_eff floor':>12} {'false pos':>10} {'95% upper':>10} {'power':>8}")
    try:
        result = calibrate_scan(trials=trials)
    except ValueError as exc:
        print(f"  calibration failed: {exc}")
        return 1
    for row in result["curve"]:
        mark = "  <- calibrated" if row["min_effective"] == result["min_effective"] else ""
        print(f"{row['min_effective']:12.1f} {row['false_positive_rate']:9.2%} "
              f"{row['false_positive_upper']:9.2%} {row['power']:7.1%}{mark}")
    print()
    print(f"  loosest floor holding a {result['target_false_positive']:.0%} rate: "
          f"n_eff >= {result['min_effective']}")
    print(f"  power there: {result['power']:.1%} -- roughly "
          f"{1 - result['power']:.0%} of real drivers are missed")
    if result["min_effective"] != result["shipped_default"]:
        print(f"  NOTE: the module ships {result['shipped_default']}; "
              f"this measurement says {result['min_effective']}")
    return 0


def retract(hidden_path, topic: str, candidate: str, reason: str,
            superseded_by: str = "") -> dict:
    """Withdraw a logged suggestion by *appending*, never by deleting.

    Landauer again, from the direction dormancy.py already argues it: erasure
    is the irreversible operation, computation is not. Deleting the record
    destroys the fact that the engine ever made the error, which is precisely
    the information that makes the correction auditable -- and it is the one
    bit a reader most needs, because a log that silently loses its mistakes
    cannot be distinguished from one that never made any. A retraction keeps
    both states recoverable, so nothing is erased and nothing is hidden. It is
    the same discipline as the reformulation counter: the escape hatch is
    counted rather than closed.
    """
    row = {
        "type": "retraction",
        "topic": topic,
        "candidate": candidate,
        "reason": reason,
        "superseded_by": superseded_by,
        "logged_at": datetime.now().isoformat(timespec="seconds"),
    }
    append_jsonl(hidden_path, [row])
    return row


def standing_suggestions(rows: Sequence[dict]) -> List[dict]:
    """The suggestions in a hidden-variable log that have not been retracted."""
    withdrawn = {(r.get("topic"), r.get("candidate")) for r in rows
                 if r.get("type") == "retraction"}
    return [r for r in rows
            if r.get("type") == "hidden_variable_suggestion"
            and (r.get("topic"), r.get("candidate")) not in withdrawn]


# ---------------------------------------------------------------------------
# stage 7 — consolidate
# ---------------------------------------------------------------------------

def stage_consolidate(tree: DependencyTree, topics: List[dict], unknown_path,
                      hidden_path, hypotheses_dir) -> Dict[str, Any]:
    """Write one hypothesis draft per topic, regenerated from the live tree."""
    hypotheses_dir = Path(hypotheses_dir)
    hypotheses_dir.mkdir(parents=True, exist_ok=True)

    unknowns = read_jsonl(unknown_path)
    # Retracted suggestions stay in the log but must not reach a draft.
    hidden = standing_suggestions(read_jsonl(hidden_path))
    grouped = tree.by_topic()
    tree.propagate()

    names = [t["name"] for t in topics] or sorted(grouped)
    written, new_hypotheses = [], []

    for name in names:
        claims = grouped.get(name, [])
        surviving = [c for c in claims if c.status == "survived"]
        refuted = [c for c in claims if c.status == "falsified"]
        active = [c for c in claims if c.status == "active"]
        topic_unknowns = [u for u in unknowns if u.get("topic") == name]
        topic_hidden = [h for h in hidden if h.get("topic") == name]
        if not (claims or topic_unknowns or topic_hidden):
            continue  # a configured topic that found nothing gets no draft

        node = tree.tree.nodes.get(name)
        confidence = node.confidence if node else 0.5
        if len(surviving) >= NEW_HYPOTHESIS_MIN_CLAIMS:
            new_hypotheses.append(name)

        path = hypotheses_dir / f"{slugify(name)}.md"
        path.write_text(_hypothesis_markdown(
            name, confidence, surviving, refuted, active,
            topic_hidden, topic_unknowns), encoding="utf-8")
        written.append(path)

    return {
        "hypothesis_files": len(written),
        "paths": [str(p) for p in written],
        "new_hypotheses": new_hypotheses,
    }


def _claim_lines(claims: List[Claim]) -> List[str]:
    if not claims:
        return ["_none_"]
    lines = []
    for claim in sorted(claims, key=lambda c: (-c.beta_confidence, c.text)):
        lines.append(f"- **{claim.text}**")
        lines.append(f"  - falsification: {claim.falsification}")
        lines.append(f"  - record: {claim.passed} passed / {claim.failed} failed, "
                     f"beta-confidence {claim.beta_confidence:.2f}")
        if claim.source_url:
            lines.append(f"  - source: {claim.source_url}")
        if claim.reformulation_count:
            lines.append(f"  - reformulated {claim.reformulation_count}x")
        for flag in claim.meta_flags:
            lines.append(f"  - flag: {flag}")
    return lines


def _hypothesis_markdown(topic: str, confidence: float, surviving: List[Claim],
                         refuted: List[Claim], active: List[Claim],
                         hidden: List[dict], unknowns: List[dict]) -> str:
    stamp = date.today().isoformat()
    lines = [
        f"# Hypothesis draft — {topic}",
        "",
        f"_Regenerated {stamp} by `scripts/hypothesis_engine.py`. "
        f"Node confidence {confidence:.2f}; "
        f"{len(surviving)} surviving / {len(active)} active / "
        f"{len(refuted)} refuted claims._",
        "",
        "Cross-source corroboration is weak evidence — corroboration is not "
        "replication. Treat this as a starting point for human review, not a "
        "finding.",
        "",
        "## Supporting claims",
        "",
    ]
    lines += _claim_lines(surviving + active)
    lines += ["", "## Contradicted/refuted claims", ""]
    lines += _claim_lines(refuted)
    lines += ["", "## Hidden-variable suspects", ""]
    if hidden:
        for row in hidden:
            lines.append(f"- {row.get('evidence', row.get('candidate', 'unknown'))}")
    else:
        lines.append("_none_")
    lines += ["", "## Open unknowns", ""]
    if unknowns:
        for row in unknowns:
            lines.append(f"- [{row.get('flag', 'unknown')}] {row.get('text', '')}")
            if row.get("reason"):
                lines.append(f"  - {row['reason']}")
    else:
        lines.append("_none_")
    lines.append("")
    return "\n".join(lines)


def write_report(path, stats: Dict[str, Any]) -> str:
    """Render the run report; the NEW HYPOTHESIS marker is the workflow's cue."""
    lines = [
        f"# Hypothesis engine report — {date.today().isoformat()}",
        "",
        f"- findings seen: {stats['found']} ({stats['new']} new, "
        f"{stats['skipped']} already logged)",
        f"- claims staked: {stats['claims']} ({stats['unknown']} routed to the "
        "unknown journal as unfalsifiable)",
        f"- tests: {stats['test']['passed']} corroborated / "
        f"{stats['test']['failed']} contradicted / "
        f"{stats['test']['skipped']} no signal",
        f"- reformulations: {stats['modify']['reformulated']} "
        f"({stats['modify']['escape_hatched']} escape-hatched out of the tree)",
        # Reformulating resets a claim's track record, so the test counts above
        # are the run's activity, not the tree's standing evidence. Stating both
        # keeps a digest from reading as better-supported than it is.
        f"- claims carrying evidence after reformulation: "
        f"{stats.get('evidenced', 0)}/{stats.get('tree_size', 0)}",
        f"- hidden-variable suggestions: {len(stats['hidden'])}",
        f"- hypothesis drafts written: {stats['consolidate']['hypothesis_files']}",
        "",
    ]
    for row in stats["hidden"]:
        lines.append(f"- hidden variable: {row['evidence']}")
    if stats["hidden"]:
        lines.append("")

    new = stats["consolidate"]["new_hypotheses"]
    if new:
        lines.append(f"## {NEW_HYPOTHESIS_MARKER}")
        lines.append("")
        lines.append(f"{NEW_HYPOTHESIS_MIN_CLAIMS}+ surviving claims on:")
        for name in new:
            lines.append(f"- {name} → `hypotheses/{slugify(name)}.md`")
        lines.append("")

    report = "\n".join(lines)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def load_config(path) -> List[dict]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    topics = payload.get("topics", [])
    if not topics:
        raise SystemExit(f"no topics in {path}")
    return topics


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default=str(REPO_ROOT / "config" / "topics.json"))
    parser.add_argument("--dry-run", action="store_true",
                        help="skip all network access and use the sample findings")
    parser.add_argument("--max-per-topic", type=int, default=10,
                        help="cap results per query per source")
    parser.add_argument("--data-dir", default=str(REPO_ROOT / "data"))
    parser.add_argument("--hypotheses-dir", default=str(REPO_ROOT / "hypotheses"))
    parser.add_argument("--sample", default=str(REPO_ROOT / "scripts" / "sample_findings.json"))
    parser.add_argument("--calibrate", action="store_true",
                        help="measure stage 6's false-positive rate and power "
                             "on synthetic corpora, then exit")
    parser.add_argument("--calibration-trials", type=int, default=4000)
    args = parser.parse_args(argv)

    if args.calibrate:
        return _report_calibration(args.calibration_trials)

    data_dir = Path(args.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    log_path = data_dir / "findings_log.jsonl"
    unknown_path = data_dir / "unknown_journal.jsonl"
    reform_path = data_dir / "reformulations.jsonl"
    hidden_path = data_dir / "hidden_variables.jsonl"
    tree_path = data_dir / "claim_tree.json"

    topics = load_config(args.config)

    print("1. explore")
    findings = stage_explore(topics, max_per_topic=args.max_per_topic,
                             dry_run=args.dry_run, sample_path=args.sample,
                             sleep=0.0 if args.dry_run else DEFAULT_SLEEP)

    print("2. log")
    new, skipped = stage_log(findings, log_path)
    print(f"   {len(new)} new, {skipped} already logged")

    tree = load_tree(tree_path)

    print("3. claim")
    made, unknown_count = stage_claim(new, tree, unknown_path)
    print(f"   {len(made)} staked, {unknown_count} unfalsifiable")

    print("4. test")
    test_stats = stage_test(tree, read_jsonl(log_path))
    print(f"   {test_stats['passed']} corroborated, {test_stats['failed']} contradicted")

    print("5. modify")
    modify_stats = stage_modify(tree, unknown_path, reform_path)
    print(f"   {modify_stats['reformulated']} reformulated, "
          f"{modify_stats['escape_hatched']} escape-hatched")

    print("6. hidden")
    hidden = stage_hidden(tree, read_jsonl(log_path), hidden_path)
    print(f"   {len(hidden)} suggestions")

    print("7. consolidate")
    consolidated = stage_consolidate(tree, topics, unknown_path, hidden_path,
                                     args.hypotheses_dir)
    save_tree(tree, tree_path)

    report = write_report(data_dir / "engine_report.md", {
        "found": len(findings), "new": len(new), "skipped": skipped,
        "claims": len(made), "unknown": unknown_count,
        "test": test_stats, "modify": modify_stats, "hidden": hidden,
        "consolidate": consolidated,
        "evidenced": sum(1 for c in tree.claims.values() if c.passed or c.failed),
        "tree_size": len(tree.claims),
    })
    print()
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
