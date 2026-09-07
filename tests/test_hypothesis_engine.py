"""Offline tests for scripts/hypothesis_engine.py (dry-run / sample data only)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import hypothesis_engine as he  # noqa: E402

SAMPLE = Path(__file__).resolve().parent.parent / "scripts" / "sample_findings.json"


@pytest.fixture()
def topics():
    return [
        {"name": "calibration and falsifiability of LLM agents",
         "queries": ["calibration"], "sources": []},
        {"name": "hidden variable detection / causal discovery from residuals",
         "queries": ["residual"], "sources": []},
    ]


@pytest.fixture()
def workspace(tmp_path):
    (tmp_path / "data").mkdir()
    return tmp_path


def run_explore(topics):
    return he.stage_explore(topics, max_per_topic=5, dry_run=True, sample_path=SAMPLE)


def test_explore_dry_run_uses_sample(topics):
    findings = run_explore(topics)
    assert len(findings) == 5
    assert {f.topic for f in findings} == {t["name"] for t in topics}


def test_dedup_idempotency(topics, workspace):
    log_path = workspace / "data" / "findings_log.jsonl"
    findings = run_explore(topics)
    new1, skipped1 = he.stage_log(findings, log_path)
    assert len(new1) == 5 and skipped1 == 0
    # second run with identical findings changes nothing
    new2, skipped2 = he.stage_log(run_explore(topics), log_path)
    assert new2 == [] and skipped2 == 5
    assert len(he.read_jsonl(log_path)) == 5


def test_claim_creation_and_falsifiability_routing(topics, workspace):
    log_path = workspace / "data" / "findings_log.jsonl"
    unknown = workspace / "data" / "unknown_journal.jsonl"
    new, _ = he.stage_log(run_explore(topics), log_path)
    tree = he.DependencyTree()
    made, unknown_count = he.stage_claim(new, tree, unknown)
    # the hedged "might/perhaps" sample entry routes to unknown journal
    assert unknown_count == 1
    assert len(made) == 4
    rows = he.read_jsonl(unknown)
    assert rows[0]["flag"] == "unfalsifiable"
    for c in made:
        assert c.falsification
        assert c.scope["topic"]


def test_reformulation_escape_hatch(workspace):
    unknown = workspace / "data" / "unknown_journal.jsonl"
    reform = workspace / "data" / "reformulations.jsonl"
    tree = he.DependencyTree()
    claim = he.Claim(text="test claim", falsification="replication contradicts",
                     scope={"topic": "t"})
    tree.add_claim(claim)
    for i in range(3):
        claim.failed = 3  # force falsified
        stats = he.stage_modify(tree, unknown, reform)
    assert stats["escape_hatched"] == 1
    assert claim.reformulation_count == 3
    assert claim.id not in tree.claims
    rows = he.read_jsonl(unknown)
    assert rows[-1]["flag"] == "escape-hatch"


def dated_topic(tree, evidence, *, topic="t", extra_findings=()):
    """Stake one claim per (month, passed, failed), each joined to its finding.

    Claims are placed in time by the finding they came from -- `source_url` on
    the claim against `url` on the finding -- which is the only thing that makes
    a residual and a candidate series comparable bucket by bucket.
    """
    findings = []
    for month, passed, failed in evidence:
        url = f"https://example.org/{topic}/{month}"
        tree.add_claim(he.Claim(text=f"claim {url}", falsification="x",
                                passed=passed, failed=failed,
                                scope={"topic": topic}, source_url=url))
        findings.append({"date": f"2024-{month:02d}-01", "topic": topic,
                         "source": "arxiv", "url": url})
    return findings + list(extra_findings)


def spiky_topic(tree, *, spikes=(3, 6), months=range(1, 8)):
    """A candidate that deviates from trend, with residuals following it.

    Publication volume spikes in `spikes` and the claims staked there are the
    well-corroborated ones. Neither series is monotone, so the association
    survives conditioning on the clock -- which is what distinguishes a driver
    from two things that both simply grow over time.
    """
    evidence = [(m, 8, 1) if m in spikes else (m, 1, 8) for m in months]
    findings = dated_topic(tree, evidence)
    findings += [{"date": f"2024-{m:02d}-01", "topic": "t", "source": "crossref",
                  "url": f"https://example.org/pad/{m}/{k}"}
                 for m in spikes for k in range(8)]
    return findings


def test_hidden_variable_scan_triggers(workspace):
    """Confidence tracking publication rate rather than evidence."""
    hidden = workspace / "data" / "hidden_variables.jsonl"
    tree = he.DependencyTree()
    findings = spiky_topic(tree)

    suggestions = he.stage_hidden(tree, findings, hidden)
    assert suggestions, "expected a suggestion when a candidate really tracks"
    assert all(s["type"] == "hidden_variable_suggestion" for s in suggestions)
    assert any(s["candidate"] == "findings_volume" for s in suggestions)
    for s in suggestions:
        # It has to survive the clock and pay for itself in bits.
        assert abs(s["partial_correlation"]) > he.CORRELATION_THRESHOLD
        assert s["description_length_gain_bits"] > 0
        assert s["n_buckets"] >= he.MIN_BUCKETS
        assert s["standing_tests"] >= he.MIN_STANDING_TESTS
    assert he.read_jsonl(hidden)


def test_a_candidate_that_is_just_the_clock_is_refused(workspace):
    """Reichenbach: two things that both grow with time are not cause and effect.

    Measured on the live corpus, `findings_volume` correlates with elapsed time
    at r=0.876 all by itself. Accumulating evidence also drifts with time, so a
    raw correlation between them is guaranteed and means nothing.
    """
    hidden = workspace / "data" / "hidden_variables.jsonl"
    tree = he.DependencyTree()
    # Residual climbs monotonically; so does the volume of findings.
    findings = dated_topic(tree, [
        (1, 1, 8), (2, 2, 7), (3, 4, 6), (4, 6, 4), (5, 7, 2), (6, 8, 1)])
    findings += [{"date": f"2024-{m:02d}-01", "topic": "t", "source": "crossref",
                  "url": f"https://example.org/pad/{m}/{k}"}
                 for m in range(1, 7) for k in range(m)]
    assert he.stage_hidden(tree, findings, hidden) == []


def test_untested_claims_carry_no_information_however_many_there_are(workspace):
    """Beta(1,1) is a prior, not a measurement.

    This is the live run's false positive at its root: reformulation had reset
    all seven claims, so every residual was the prior mean. Weighting alone
    cannot catch it -- equally uninformative claims get equal weights -- so the
    scan needs an absolute floor on standing evidence.
    """
    hidden = workspace / "data" / "hidden_variables.jsonl"
    tree = he.DependencyTree()
    findings = spiky_topic(tree)
    for claim in tree.claims.values():          # wipe the evidence, keep the shape
        claim.passed = claim.failed = 0
    assert he.stage_hidden(tree, findings, hidden) == []


def test_evidence_free_claims_are_down_weighted_not_counted(workspace):
    """An untested claim should dilute the effective sample size, not the signal."""
    hidden = workspace / "data" / "hidden_variables.jsonl"
    tree = he.DependencyTree()
    findings = spiky_topic(tree, months=range(1, 11))
    full = he.stage_hidden(tree, findings, hidden)
    assert full, "expected the driver to be found with all claims tested"

    tree2 = he.DependencyTree()
    findings2 = spiky_topic(tree2, months=range(1, 11))
    for i, claim in enumerate(tree2.claims.values()):
        if i % 3 == 0 and claim.passed < claim.failed:   # untest some weak ones
            claim.passed = claim.failed = 0
    diluted = he.stage_hidden(tree2, findings2, hidden)
    assert diluted, "the real driver should still show through"
    assert (diluted[0]["effective_sample_size"]
            < full[0]["effective_sample_size"]), "n_eff must fall"


def test_hidden_variable_scan_no_trigger_without_a_correlated_candidate(workspace):
    """Large residuals alone are not a hidden variable; something must track them."""
    hidden = workspace / "data" / "hidden_variables.jsonl"
    tree = he.DependencyTree()
    # Residuals alternate +/-0.36: way past the magnitude gate, but no candidate
    # series correlates with a period-2 sawtooth, so nothing is suggested.
    findings = dated_topic(tree, [
        (1, 5, 0), (3, 0, 5), (5, 5, 0), (7, 0, 5), (9, 5, 0), (11, 0, 5)])
    assert he.stage_hidden(tree, findings, hidden) == []


def test_hidden_variable_scan_no_trigger_on_flat(workspace):
    hidden = workspace / "data" / "hidden_variables.jsonl"
    tree = he.DependencyTree()
    findings = dated_topic(tree, [(m, 1, 1) for m in (1, 3, 5, 7, 9)])
    suggestions = he.stage_hidden(tree, findings, hidden)
    assert suggestions == []  # mean|residual| = |0.5-0.5| = 0 < 0.1


def test_a_residual_that_barely_moves_explains_nothing(workspace):
    """The first live run's false positive, pinned.

    Seven claims whose residuals spanned 0.097 were reported as tracking
    `source_diversity` at r=-0.72. On that few near-constant points |r|>0.5 is
    reached by 46% of random orderings, so magnitude alone cannot be the gate.
    """
    hidden = workspace / "data" / "hidden_variables.jsonl"
    tree = he.DependencyTree()
    # beta_confidence ~0.78-0.87: a large mean residual that hardly varies.
    findings = dated_topic(tree, [
        (1, 7, 2), (2, 8, 2), (3, 7, 2), (4, 6, 2), (5, 6, 2), (6, 6, 2), (7, 7, 2)])
    suggestions = he.stage_hidden(tree, findings, hidden)
    assert suggestions == []


def test_claims_are_correlated_in_time_not_in_stake_order(workspace):
    """Reordering how claims were staked must not change the finding.

    The residual series and the candidate series used to be zipped by list
    position -- claim-stake order against chronological order -- so the same
    data gave a different answer depending on the order the API happened to
    return it in.
    """
    hidden = workspace / "data" / "hidden_variables.jsonl"
    spikes, months = (3, 6), range(1, 8)
    evidence = [(m, 8, 1) if m in spikes else (m, 1, 8) for m in months]
    padding = [{"date": f"2024-{m:02d}-01", "topic": "t", "source": "crossref",
                "url": f"https://example.org/pad/{m}/{k}"}
               for m in spikes for k in range(8)]

    def scan(order):
        tree = he.DependencyTree()
        findings = dated_topic(tree, [evidence[i] for i in order],
                               extra_findings=padding)
        return he.stage_hidden(tree, findings, hidden)

    forward = scan(range(len(evidence)))
    backward = scan(range(len(evidence) - 1, -1, -1))
    shuffled = scan([3, 0, 5, 1, 4, 2])

    assert forward, "expected the correlation to be found at all"
    key = lambda rows: sorted((s["candidate"], s["correlation"]) for s in rows)
    assert key(forward) == key(backward) == key(shuffled)


# --- the topic clock: telling "found nothing" from "could not look" ---------

def test_a_clock_derives_when_the_topic_supports_one():
    """shelf_life = tau / |coupling|, per JinnZ2/Simulators claim-record."""
    tree = he.DependencyTree()
    findings = spiky_topic(tree, months=range(1, 11))
    clock = {c.topic: c for c in he.topic_clocks(tree, findings)}["t"]
    assert clock.state == he.DERIVED and clock.resolvable
    assert clock.shelf_life_years == pytest.approx(
        clock.tau_years / abs(clock.coupling), rel=1e-9)


def test_a_topic_with_too_few_claims_is_underivable_not_empty():
    """The distinction the whole clock exists for."""
    tree = he.DependencyTree()
    findings = dated_topic(tree, [(1, 5, 1), (4, 4, 2)])
    clock = {c.topic: c for c in he.topic_clocks(tree, findings)}["t"]
    assert clock.state == he.UNDERIVABLE
    assert not clock.resolvable and "cannot support an elasticity" in clock.reason


def test_insensitive_residuals_name_the_term_that_failed():
    """Zero elasticity is not 'stable forever'; it is 'this term bounds nothing'."""
    tree = he.DependencyTree()
    # Every claim carries the same residual, so it cannot vary with volume.
    findings = dated_topic(tree, [(m, 6, 2) for m in (1, 3, 5, 7, 9, 11)])
    clock = {c.topic: c for c in he.topic_clocks(tree, findings)}["t"]
    assert clock.state == he.UNBOUNDED_BY_THIS_TERM
    assert clock.tau_years is not None      # tau was derivable; the coupling was not
    assert clock.shelf_life_years is None


def test_untested_claims_leave_the_clock_underivable():
    """Residual-free claims sit exactly at the prior, so no elasticity exists."""
    tree = he.DependencyTree()
    findings = spiky_topic(tree, months=range(1, 11))
    for claim in tree.claims.values():
        claim.passed = claim.failed = 0
    clock = {c.topic: c for c in he.topic_clocks(tree, findings)}["t"]
    assert clock.state == he.UNDERIVABLE


def test_a_null_scan_on_a_derived_clock_is_a_real_negative():
    """Both halves together: searchable, searched, nothing found."""
    tree = he.DependencyTree()
    # A resolvable topic whose residuals track nothing in particular.
    findings = dated_topic(tree, [
        (1, 6, 2), (3, 2, 6), (5, 5, 3), (7, 3, 5), (9, 6, 2), (11, 2, 6)])
    clock = {c.topic: c for c in he.topic_clocks(tree, findings)}["t"]
    suggestions = he.stage_hidden(tree, findings, None)
    assert suggestions == []
    # The clock is what licenses reading that empty list as evidence.
    assert clock.state in (he.DERIVED, he.UNBOUNDED_BY_THIS_TERM)


# --- stage 6's operating characteristic, measured rather than assumed --------

def test_the_scan_holds_its_false_positive_rate_on_null_corpora():
    """A detector is worth what its measured error rate says, not its derivation.

    Every gate in stage 6 is principled and the scan still fired on 36% of
    corpora containing no driver at all, before the n_eff floor was calibrated.
    This is the same discipline damage.py records for CUSUM, where a designed
    ARL0 of 1000 delivered an empirical 7.8.
    """
    rates = he.scan_operating_characteristic(he.MIN_EFFECTIVE_SAMPLE, trials=250)
    # The bound, not the point estimate: 250 trials of a true 3% rate return
    # anything from 1% to 6% by seed, so asserting the estimate would be flaky
    # in exactly the way this whole exercise is about.
    assert rates["false_positive_upper"] <= 0.08


def test_the_scan_can_still_find_a_driver_that_is_really_there():
    """The other half: a gate tightened past its target is deaf, not safe."""
    rates = he.scan_operating_characteristic(he.MIN_EFFECTIVE_SAMPLE, trials=250)
    assert rates["power"] > 0.4


def test_removing_the_floor_lets_the_null_corpora_through():
    """Pins *why* the floor is there: without it the rate is indefensible."""
    rates = he.scan_operating_characteristic(0.0, trials=250)
    assert rates["false_positive_rate"] > 0.10


def test_raising_the_floor_trades_power_monotonically():
    loose = he.scan_operating_characteristic(4.0, trials=250)
    tight = he.scan_operating_characteristic(8.0, trials=250)
    assert tight["false_positive_rate"] < loose["false_positive_rate"]
    assert tight["power"] < loose["power"]


def test_calibration_refuses_a_target_it_cannot_reach():
    """No floor can make a small corpus safe; say so instead of raising it."""
    # Floors 0 and 3 measure ~20% and ~18%; no bound of theirs reaches 2%.
    with pytest.raises(ValueError) as excinfo:
        he.calibrate_scan(target_false_positive=0.02, floors=(0.0, 3.0),
                          trials=500)
    assert "no floor" in str(excinfo.value)


def test_calibration_refuses_too_few_trials_to_resolve_the_rate():
    """Estimating a 5% rate off 20 draws is not a measurement."""
    with pytest.raises(ValueError) as excinfo:
        he.calibrate_scan(target_false_positive=0.05, trials=20)
    assert "cannot resolve" in str(excinfo.value)


def test_the_shipped_default_is_what_calibration_returns():
    """The constant in the module must be the measured one, not a leftover."""
    result = he.calibrate_scan(trials=800)
    assert result["min_effective"] == he.MIN_EFFECTIVE_SAMPLE
    assert result["false_positive_upper"] <= result["target_false_positive"]


def test_a_retraction_withdraws_without_erasing(workspace):
    """Landauer: erasure is the irreversible operation, so retract by appending.

    Deleting the record would destroy the fact that the engine ever made the
    error -- the one thing a reader most needs in order to trust the log at all.
    """
    hidden = workspace / "data" / "hidden_variables.jsonl"
    tree = he.DependencyTree()
    findings = spiky_topic(tree)
    suggestions = he.stage_hidden(tree, findings, hidden)
    assert suggestions and he.standing_suggestions(he.read_jsonl(hidden))

    he.retract(hidden, topic="t", candidate=suggestions[0]["candidate"],
               reason="confounded with the clock", superseded_by="abc123")

    rows = he.read_jsonl(hidden)
    # The original record is still there, and still says what it said.
    assert any(r["type"] == "hidden_variable_suggestion" for r in rows)
    assert any(r["type"] == "retraction" for r in rows)
    # But it no longer stands, so nothing downstream may cite it.
    assert not any(s["candidate"] == suggestions[0]["candidate"]
                   for s in he.standing_suggestions(rows))


def test_consolidation_writes_hypothesis_md(topics, workspace):
    log_path = workspace / "data" / "findings_log.jsonl"
    unknown = workspace / "data" / "unknown_journal.jsonl"
    hidden = workspace / "data" / "hidden_variables.jsonl"
    new, _ = he.stage_log(run_explore(topics), log_path)
    tree = he.DependencyTree()
    he.stage_claim(new, tree, unknown)
    result = he.stage_consolidate(tree, topics, unknown, hidden,
                                  workspace / "hypotheses")
    files = list((workspace / "hypotheses").glob("*.md"))
    assert files and result["hypothesis_files"] == len(files)
    body = files[0].read_text()
    for section in ("## Supporting claims", "## Contradicted/refuted claims",
                    "## Hidden-variable suspects", "## Open unknowns"):
        assert section in body


def test_claim_tree_save_load_roundtrip(tmp_path):
    tree = he.DependencyTree()
    tree.add_claim(he.Claim(text="a", falsification="f", passed=2, failed=1,
                            scope={"topic": "t"}, source_url="http://x"))
    tree.add_claim(he.Claim(text="b", falsification="f2", reformulation_count=1,
                            scope={"topic": "u", "restrictions": ["narrow"]}))
    path = tmp_path / "claim_tree.json"
    he.save_tree(tree, path)
    loaded = he.load_tree(path)
    assert set(loaded.claims) == set(tree.claims)
    a = next(c for c in loaded.claims.values() if c.text == "a")
    assert (a.passed, a.failed, a.source_url) == (2, 1, "http://x")
    b = next(c for c in loaded.claims.values() if c.text == "b")
    assert b.reformulation_count == 1
    # missing file -> fresh tree
    assert len(he.load_tree(tmp_path / "nope.json").claims) == 0


def test_corroboration_heuristic():
    pos = "We demonstrate that calibration improves accuracy by 18% on agent benchmarks"
    cor = "We confirm and validate that calibration improves accuracy on agent benchmarks"
    con = "Calibration fails to improve accuracy and agents underperform benchmarks"
    unrel = "Quantum chromodynamics lattice results for meson spectra"
    assert he.corroboration(pos, cor) == 1
    assert he.corroboration(pos, con) == -1
    assert he.corroboration(pos, unrel) == 0


def test_full_dry_run_main(topics, workspace, monkeypatch):
    cfg = workspace / "topics.json"
    cfg.write_text(json.dumps({"topics": topics}))
    rc = he.main(["--config", str(cfg), "--dry-run", "--max-per-topic", "3",
                  "--data-dir", str(workspace / "data"),
                  "--hypotheses-dir", str(workspace / "hypotheses"),
                  "--sample", str(SAMPLE)])
    assert rc == 0
    assert (workspace / "data" / "engine_report.md").exists()
    assert (workspace / "data" / "claim_tree.json").exists()
    # idempotent second run: no new findings
    rc = he.main(["--config", str(cfg), "--dry-run",
                  "--data-dir", str(workspace / "data"),
                  "--hypotheses-dir", str(workspace / "hypotheses"),
                  "--sample", str(SAMPLE)])
    assert rc == 0
    assert len(he.read_jsonl(workspace / "data" / "findings_log.jsonl")) == 5


# ---------------------------------------------------------------------------
# Network layer: retry/backoff and the Semantic Scholar key. No sockets are
# opened; urlopen is replaced with a scripted double.
# ---------------------------------------------------------------------------

import io
import urllib.error
from email.message import Message


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def _http_error(url, code, retry_after=None):
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = str(retry_after)
    return urllib.error.HTTPError(url, code, f"HTTP {code}", headers, io.BytesIO(b""))


def _script_urlopen(monkeypatch, outcomes):
    """Each call pops the next outcome: an Exception is raised, bytes are served.
    Returns the list of Request objects seen, for header assertions."""
    seen = []
    queue = list(outcomes)

    def fake_urlopen(request, timeout=None):
        seen.append(request)
        nxt = queue.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return _Response(nxt)

    monkeypatch.setattr(he.urllib.request, "urlopen", fake_urlopen)
    return seen


S2_URL = "https://api.semanticscholar.org/graph/v1/paper/search?query=x"
ARXIV_URL = "http://export.arxiv.org/api/query?search_query=all:x"


def test_fetch_retries_429_then_succeeds(monkeypatch):
    seen = _script_urlopen(monkeypatch, [_http_error(S2_URL, 429), b'{"data": []}'])
    slept = []
    out = he._fetch(S2_URL, backoff=(2.0, 4.0), sleep=slept.append)
    assert out == b'{"data": []}'
    assert len(seen) == 2
    assert slept == [2.0]


def test_fetch_gives_up_after_backoff_exhausted(monkeypatch):
    seen = _script_urlopen(monkeypatch, [_http_error(S2_URL, 429)] * 4)
    slept = []
    out = he._fetch(S2_URL, backoff=(1.0, 2.0, 3.0), sleep=slept.append)
    assert out is None
    assert len(seen) == 4            # 1 try + 3 retries
    assert slept == [1.0, 2.0, 3.0]  # the schedule, in order


def test_fetch_does_not_retry_permanent_errors(monkeypatch):
    seen = _script_urlopen(monkeypatch, [_http_error(S2_URL, 404)])
    slept = []
    assert he._fetch(S2_URL, sleep=slept.append) is None
    assert len(seen) == 1 and slept == []


def test_fetch_honours_retry_after_within_cap(monkeypatch):
    _script_urlopen(monkeypatch, [_http_error(S2_URL, 429, retry_after=5),
                                  _http_error(S2_URL, 429, retry_after=9999),
                                  b"ok"])
    slept = []
    assert he._fetch(S2_URL, backoff=(1.0, 1.0), sleep=slept.append) == b"ok"
    assert slept == [5.0, he.RETRY_AFTER_CAP]


def test_s2_api_key_sent_only_to_semantic_scholar(monkeypatch):
    monkeypatch.setenv(he.S2_API_KEY_ENV, "secret-key")
    seen = _script_urlopen(monkeypatch, [b"a", b"b"])
    he._fetch(S2_URL)
    he._fetch(ARXIV_URL)
    assert seen[0].get_header("X-api-key") == "secret-key"
    assert seen[1].get_header("X-api-key") is None
    assert seen[1].get_header("User-agent") == he.USER_AGENT


def test_no_api_key_header_without_env(monkeypatch):
    monkeypatch.delenv(he.S2_API_KEY_ENV, raising=False)
    seen = _script_urlopen(monkeypatch, [b"a"])
    he._fetch(S2_URL)
    assert seen[0].get_header("X-api-key") is None


# ---------------------------------------------------------------------------
# stage 3/4 quality gates -- each test pins a failure the live corpus produced
# ---------------------------------------------------------------------------

def test_the_verdict_depends_on_the_claim_being_tested():
    """The bug: `corroboration` read only the *other* abstract.

    On the 2026-09-07 corpus all 52 abstracts that issued a verdict handed the
    identical one to every claim they were paired with, so each topic's claims
    converged on a single score and the ranking carried no information. An
    oracle whose output never varies with its first argument is measuring the
    prose of the second.
    """
    other = ("Calibration fails on agent benchmarks. "
             "Separately, we confirm the lattice spectra of mesons.")
    about_calibration = "On topic x, P reports: calibration on agent benchmarks"
    about_mesons = "On topic x, Q reports: lattice meson spectra results"
    assert he.corroboration(about_calibration, other) == -1
    assert he.corroboration(about_mesons, other) == 1


def test_markers_are_read_only_where_the_shared_subject_is_discussed():
    claim = "On topic x, P reports: abstention improves reliability"
    # The contradiction sits in a sentence about something else entirely.
    other = ("Abstention improves reliability and we validate this. "
             "Our unrelated tokenizer fails and does not converge.")
    assert he.corroboration(claim, other) == 1


def test_topic_words_are_not_evidence_of_agreement():
    """Topic vocabulary is shared by construction, so it cannot testify."""
    topic = "hidden variable detection / causal discovery from residuals"
    claim = f"On topic {topic}, P reports: transformer residual gating"
    other = "We confirm a hidden variable detection result for causal discovery"
    # Overlap is entirely topic words -> nothing claim-specific is shared.
    assert he.shared_subject(claim, other, topic) == set()
    assert he.corroboration(claim, other, topic=topic) == 0


def test_information_gate_refuses_agreement_on_ubiquitous_words():
    claim = "On topic x, P reports: the model improves accuracy"
    other = "We confirm the model improves accuracy"
    everywhere = ["the model improves accuracy"] * 40
    idf = he.idf_map(everywhere)
    # Every shared word appears in every document, so the overlap is worth ~0
    # bits and buys no testimony however positively the other text is worded.
    assert he.corroboration(claim, other, idf=idf) == 0


@pytest.mark.parametrize("body,expected", [
    ("accuracy improves by 18% on the benchmark", "18%"),
    ("accuracy reaches 96.15% on the test set", "96.15%"),
    # identifiers, not results -- each produced a live falsification condition
    ("energy distance defined in Szekely and Rizzo (2013)", ""),
    ("evaluated on the SQuAD 2.0 reading comprehension benchmark", ""),
    ("we report OOD@10 across four vendors", ""),
    ("System 1 and System 2 for embodied reasoning", ""),
    ("the entropy rate of English, after Shannon 1951", ""),
])
def test_result_anchor_takes_measurements_and_declines_identifiers(body, expected):
    assert he.result_anchor(body) == expected


def test_a_percentage_outranks_a_bare_number():
    body = "we ran 3 seeds and accuracy improved by 12% overall"
    assert he.result_anchor(body) == "12%"


def test_off_topic_retrieval_is_refused_by_phrase_not_by_keyword():
    """The leak: three de novo protein-binder papers were staked as
    hidden-variable-detection claims, matching on *latent* (a product name) and
    *discovery* (drug discovery), and became that topic's top three claims."""
    phrases = he.topic_phrases(
        "hidden variable detection / causal discovery from residuals",
        ["hidden confounder detection model residuals",
         "causal discovery latent variables time series"])
    leak = ("Latent-X: An Atom-level Frontier Model for De Novo Protein Binder "
            "Design. Traditional drug discovery relies on screening millions of "
            "candidate molecules with low success rates.")
    real = ("Detecting hidden confounding in observational data using multiple "
            "environments. A common assumption in causal inference is that "
            "there is no hidden confounding.")
    assert not he.in_scope(leak, phrases)
    assert he.in_scope(real, phrases)


def test_scope_refusals_are_journalled_not_dropped(workspace):
    unknown = workspace / "data" / "unknown_journal.jsonl"
    tree = he.DependencyTree()
    finding = he.Finding(source="arxiv", title="Latent-X: De Novo Protein Binder",
                         url="http://x", date="2026-01-01",
                         topic="hidden variable detection / causal discovery from residuals",
                         abstract="Drug discovery screens millions of molecules, 12% succeed.")
    phrases = {finding.topic: he.topic_phrases(finding.topic,
                                               ["causal discovery latent variables"])}
    made, count = he.stage_claim([finding], tree, unknown, scope_phrases=phrases)
    assert made == [] and count == 1
    row = he.read_jsonl(unknown)[0]
    assert row["flag"] == "off-scope"
    assert row["url"] == "http://x"


def test_scope_gate_is_opt_in():
    """Callers that pass no phrases keep the previous staking behaviour."""
    tree = he.DependencyTree()
    finding = he.Finding(source="arxiv", title="Anything At All", url="http://y",
                         date="2026-01-01", topic="some topic",
                         abstract="Accuracy improves by 9% over the baseline.")
    made, count = he.stage_claim([finding], tree, Path("/dev/null"))
    assert len(made) == 1 and count == 0


def test_corroboration_calibration_returns_the_shipped_default():
    corpus = []
    for i in range(12):
        corpus.append({"topic": "alpha", "url": f"a{i}", "title": f"alpha {i}",
                       "abstract": f"confounder adjustment sensitivity {i} "
                                   f"confirms the estimator is consistent"})
        corpus.append({"topic": "beta", "url": f"b{i}", "title": f"beta {i}",
                       "abstract": f"galactic rotation photometry {i} "
                                   f"confirms the profile is consistent"})
    out = he.calibrate_corroboration(corpus, target_false_testimony=0.05)
    assert out["false_testimony_upper"] <= 0.05
    # loosest gate meeting the target, not the tightest available
    assert out["min_bits"] <= min(r["min_bits"] for r in out["curve"]
                                  if r["false_testimony_upper"] <= 0.05)


def test_calibration_refuses_a_target_it_cannot_hold():
    corpus = [{"topic": "alpha", "url": f"u{i}", "title": "t",
               "abstract": "confirms consistent supports validated result"}
              for i in range(8)]
    with pytest.raises(ValueError):
        he.calibrate_corroboration(corpus, target_false_testimony=0.0,
                                   grids=(0.0, 1.0))
