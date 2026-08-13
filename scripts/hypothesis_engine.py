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
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime
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

def candidate_series(rows: List[dict], n_buckets: int) -> List[Tuple[str, List[float]]]:
    """Exogenous series the residuals can be correlated against.

    The findings stream is split into `n_buckets` equal *time* intervals (equal
    counts would make volume constant by construction and untestable), and each
    candidate is one summary statistic per interval. These stand in for the
    environmental time series modules/hnd.py correlates against.
    """
    dated = [(parse_date(r.get("date", "")), r) for r in rows]
    dated = [(d, r) for d, r in dated if d is not None]
    if len(dated) < 2 or n_buckets < 2:
        return []
    dated.sort(key=lambda pair: pair[0])

    start, end = dated[0][0], dated[-1][0]
    span = (end - start).days
    if span <= 0:
        return []

    buckets: List[List[dict]] = [[] for _ in range(n_buckets)]
    for when, row in dated:
        index = min(n_buckets - 1, int((when - start).days / span * n_buckets))
        buckets[index].append(row)

    volume = [float(len(b)) for b in buckets]
    diversity = [float(len({r.get("source", "") for r in b})) for b in buckets]
    return [("findings_volume", volume), ("source_diversity", diversity)]


def stage_hidden(tree: DependencyTree, findings: Sequence, hidden_path,
                 residual_threshold: float = RESIDUAL_THRESHOLD,
                 correlation_threshold: float = CORRELATION_THRESHOLD) -> List[dict]:
    """Scan claim residuals for unmodelled drivers, mirroring modules/hnd.py.

    The residual of a claim is how far its calibrated posterior sits from
    "no idea": `beta_confidence - 0.5`. Signed, because the direction is the
    evidence -- a topic whose claims drift confident as the literature thickens
    is telling you something a topic with random scatter is not. Gated on mean
    |residual| >= threshold so the scan does not chase noise, exactly as HND
    gates on mean residual magnitude.
    """
    rows = [f if isinstance(f, dict) else f.to_dict() for f in findings]
    suggestions: List[dict] = []

    for topic, claims in sorted(tree.by_topic().items()):
        if len(claims) < 3:
            continue
        residuals = [c.beta_confidence - 0.5 for c in claims]
        mean_abs = sum(abs(r) for r in residuals) / len(residuals)
        if mean_abs < residual_threshold:
            continue

        topic_rows = [r for r in rows if r.get("topic") in (topic, None)] or rows
        for name, series in candidate_series(topic_rows, len(residuals)):
            r = pearson(series, residuals)
            if abs(r) <= correlation_threshold:
                continue
            suggestions.append({
                "type": "hidden_variable_suggestion",
                "topic": topic,
                "candidate": name,
                "correlation": round(r, 4),
                "mean_abs_residual": round(mean_abs, 4),
                "n_claims": len(claims),
                "evidence": (f"claim residuals on '{topic}' track {name} "
                             f"(r={r:.2f}) across {len(claims)} claims"),
                "logged_at": datetime.now().isoformat(timespec="seconds"),
            })

    if suggestions:
        append_jsonl(hidden_path, suggestions)
    return suggestions


# ---------------------------------------------------------------------------
# stage 7 — consolidate
# ---------------------------------------------------------------------------

def stage_consolidate(tree: DependencyTree, topics: List[dict], unknown_path,
                      hidden_path, hypotheses_dir) -> Dict[str, Any]:
    """Write one hypothesis draft per topic, regenerated from the live tree."""
    hypotheses_dir = Path(hypotheses_dir)
    hypotheses_dir.mkdir(parents=True, exist_ok=True)

    unknowns = read_jsonl(unknown_path)
    hidden = read_jsonl(hidden_path)
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
    args = parser.parse_args(argv)

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
    })
    print()
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
