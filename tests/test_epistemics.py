import pytest

from grounding.core.claims import Claim, DependencyTree
from grounding.core.epistemics import (check_geometry_units, check_with_z3,
                                       classify_falsifiability,
                                       evaluate_logical_form)


# ---------------------------------------------------------------------------
# §5.1 — logical forms
# ---------------------------------------------------------------------------

def test_logical_form_evaluation():
    form = {"op": "abs_diff_lt", "args": ["actual", "predicted", 0.3]}
    assert evaluate_logical_form(form, {"actual": 1.0, "predicted": 1.1})
    assert not evaluate_logical_form(form, {"actual": 1.0, "predicted": 2.0})


def test_logical_form_unbound_variable():
    with pytest.raises(ValueError, match="unbound"):
        evaluate_logical_form({"op": "lt", "args": ["a", 1]}, {})


def test_logical_form_unknown_op():
    with pytest.raises(ValueError, match="unknown"):
        evaluate_logical_form({"op": "implies", "args": [1, 2]}, {})


def test_claim_evaluate_single_source_of_truth():
    c = Claim("pos within 0.3", "deviates > 0.3",
              logical_form={"op": "abs_diff_lt", "args": ["actual", "predicted", 0.3]})
    assert c.evaluate({"actual": 0.0, "predicted": 0.1}) is True
    assert c.evaluate({"actual": 0.0, "predicted": 5.0}) is False
    assert c.passed == 1 and c.failed == 1


def test_claim_evaluate_refutation_test_takes_priority():
    c = Claim("x", "y", refutation_test=lambda obs: obs["broke"])
    assert c.evaluate({"broke": False}) is True
    assert c.evaluate({"broke": True}) is False


def test_claim_evaluate_returns_none_without_condition():
    assert Claim("x", "y").evaluate({}) is None


def test_z3_check_graceful():
    form = {"op": "abs_diff_lt", "args": ["a", "b", 0.3]}
    verdict = check_with_z3(form, {"a": 1.0, "b": 1.1})
    # z3 is an optional dependency: either a real verdict or "unavailable".
    assert verdict in ("consistent", "falsified", "unavailable")
    if verdict != "unavailable":
        assert check_with_z3(form, {"a": 1.0, "b": 9.0}) == "falsified"


# ---------------------------------------------------------------------------
# §5.2 — units and meta-grounding
# ---------------------------------------------------------------------------

def test_unit_range_warnings():
    warnings = check_geometry_units({
        "temperature_c": -400.0,        # below absolute zero
        "voltage_v": 5.0,               # fine
        "T_K": -10.0,                   # negative kelvin
        "component_type": "diode",      # non-numeric: ignored
        "ph_values": [7.0],             # no unit suffix: ignored
    })
    assert len(warnings) == 2
    assert any("temperature_c" in w for w in warnings)
    assert any("T_K" in w for w in warnings)


def test_unit_check_lists():
    assert check_geometry_units({"spectrum_nm": [500.0, -3.0]})  # negative wavelength


def test_meta_grounding_flag():
    t = DependencyTree()
    t.get("physics").confidence = 0.95
    ordinary = Claim("small tweak", "fails a measurement")
    t.add_claim("physics", ordinary)
    assert ordinary.meta_flags == []

    revolutionary = Claim("physics is wrong", "any confirmation", confidence=0.1)
    t.add_claim("physics", revolutionary)
    assert any("revolutionary" in f for f in revolutionary.meta_flags)


# ---------------------------------------------------------------------------
# §5.3 — scope and reference class
# ---------------------------------------------------------------------------

def test_scoped_claim_fields():
    c = Claim("force moves ball", "ball stays put",
              scope={"world": "BumpyWorld-v1", "step": 12},
              reference_class="WorldModel predictions at similar (x, action)")
    assert c.scope["world"] == "BumpyWorld-v1"
    assert "WorldModel" in c.reference_class


# ---------------------------------------------------------------------------
# §5.4 — falsifiability classifier and escape hatch
# ---------------------------------------------------------------------------

def test_falsifiability_classifier():
    machine = Claim("x", "y", logical_form={"op": "lt", "args": ["a", 1]})
    textual = Claim("water boils at 100C", "thermometer reads differently at boil")
    vague = Claim("everything is connected", "none")
    empty = Claim("the vibe is off", "")
    assert classify_falsifiability(machine) == "machine-checkable"
    assert classify_falsifiability(textual) == "falsifiable"
    assert classify_falsifiability(vague) == "unfalsifiable"
    assert classify_falsifiability(empty) == "unfalsifiable"
    assert machine.falsifiable and textual.falsifiable
    assert not vague.falsifiable


def test_escape_hatch_counter():
    c = Claim("the market will crash", "it doesn't crash by friday")
    for _ in range(3):
        c.test(False)
    assert c.status == "falsified"
    suspicious = c.reformulate(falsification="it doesn't crash by NEXT friday")
    assert not suspicious and c.status == "active"      # record reset, counted
    c.reformulate()
    suspicious = c.reformulate()
    assert suspicious and c.escape_hatch_suspected
    assert any("escape-hatch" in f for f in c.meta_flags)


# ---------------------------------------------------------------------------
# §5.5 — calibrated confidence and external knowledge bases
# ---------------------------------------------------------------------------

def test_beta_confidence():
    c = Claim("x", "y")
    assert c.beta_confidence == 0.5                     # Beta(1,1) prior
    for _ in range(8):
        c.test(True)
    for _ in range(2):
        c.test(False)
    assert abs(c.beta_confidence - 9 / 12) < 1e-9       # Beta(9,3) mean
    assert 0.0 < c.beta_confidence < 1.0


def test_fdm_loads_knowledge_from_json():
    networkx = pytest.importorskip("networkx")  # noqa: F841 (modules dir needs it)
    import os
    from fdm import FractalDependencyMapper
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fdm = FractalDependencyMapper.from_json(
        os.path.join(root, "data", "chemical_plant_kb.json"),
        os.path.join(root, "data", "primitive_roots.json"))
    tree = fdm.trace("Fresnel_Lens")
    assert tree.max_depth > 0
    assert "SOIL" in tree.primitive_roots


def test_plugin_manager_unit_checks():
    pytest.importorskip("numpy")
    from plugin_manager import PluginManager
    pm = PluginManager("plugins", unit_checks=True)
    _, report = pm.read_plugin("magnetic", {"B_vec": [0.5, 0, 0]})
    assert "units" not in report                        # nothing suspicious
    binary, report = pm.read_plugin("light", {
        "polarization": ["V"], "spectrum_nm": [-500.0],
        "interference_intensity": [0.7], "photon_spin": ["R"]})
    assert binary is not None
    assert "spectrum_nm" in report and "units" in report
