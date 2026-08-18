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
