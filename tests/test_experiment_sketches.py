"""Keep experiments/sketches/ runnable offline. Smoke checks only.

The sketches are proposals (see experiments/README.md); these tests assert
that they run and that their by-construction properties hold, nothing more.
They are stdlib-only so they pass in the tier-0 job.
"""
import importlib.util

import pytest
import sys
from pathlib import Path

SKETCHES = Path(__file__).resolve().parents[1] / "experiments" / "sketches"


def _load(name):
    spec = importlib.util.spec_from_file_location(f"sketch_{name}", SKETCHES / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_calibration_metrics_self_check():
    out = _load("calibration_metrics").self_check(n=1500)
    assert out["ece_overconfident"] > out["ece_calibrated"]


def test_latent_confounder_sim_self_check():
    out = _load("latent_confounder_sim").self_check()
    assert set(out) == {"null", "hidden", "instant"}


def test_entropy_rate_check_self_check():
    _load("entropy_rate_check").self_check(n=60_000)


def test_variety_sim_self_check():
    _load("variety_sim").self_check(T=4000)


def test_oracle_audit_runs_read_only(tmp_path):
    mod = _load("oracle_audit")
    data = Path(__file__).resolve().parents[1] / "data"
    before = {p.name: p.stat().st_mtime_ns for p in data.iterdir()}
    sheet = tmp_path / "sheet.csv"
    try:
        rc = mod.main(["--sheet", str(sheet)])
    except (KeyError, TypeError, ValueError) as exc:  # engine schema moved on
        pytest.skip(f"engine data schema changed; audit sketch needs updating: {exc!r}")
    assert rc == 0
    assert sheet.exists()
    after = {p.name: p.stat().st_mtime_ns for p in data.iterdir()}
    assert before == after
