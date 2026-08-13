import pytest

np = pytest.importorskip("numpy")


def test_plugin_manager_scan_and_paths():
    from plugin_manager import PluginManager
    pm = PluginManager("plugins")
    names = {v["meta"]["name"] for v in pm.plugins.values()}
    for expected in ("magnetic", "light", "emf_sensor", "harmony_field",
                     "gravitational", "felt_service"):
        assert expected in names
    # module-name alias (§1.12): emf.py registers as both emf and emf_sensor
    assert pm.plugins["emf"] is pm.plugins["emf_sensor"]
    # service path (§3.23): felt_service instantiates lazily and computes
    svc = pm.get_service("felt_service")
    assert 0.0 <= svc.compute(0.9, 0.9, 5.0) <= 1.0


def test_magnetic_bands_differentiate():
    import magnetic
    m = magnetic.MagneticPlugin()
    low = m.to_binary({"B_vec": [0.05, 0, 0]})
    high = m.to_binary({"B_vec": [1.5, 0, 0]})
    assert low[:3] != high[:3]   # was constant before the _gray_bits fix (§1.1)


def test_light_bridge_encodes():
    import light_bridge
    lp = light_bridge.LightPlugin()
    bits = lp.from_geometry({
        "polarization": ["V", "H"],
        "spectrum_nm": [500.0, 600.0],
        "interference_intensity": [0.7, 0.3],
        "photon_spin": ["R", "L"],
    }).to_binary()
    assert set(bits) <= {"0", "1"} and len(bits) == 2 * 8 + 7


def test_harmony_field_geometry_and_velocities():
    import harmony_field_engine as hfe
    eng = hfe.HarmonyFieldEngine()
    assert len(np.unique(eng.rest_vertices, axis=0)) == 30
    eng.apply_force(5, np.array([0.3, 0.0, 0.0]))
    _, vel, disp = eng.step()
    assert vel > 0 and disp > 0   # velocities were always 0 before §3.11


def test_gravitational_merger_at_peak_only():
    import gravitational
    g = gravitational.GravitationalPlugin()
    g.to_binary({"strain": 1e-21, "frequency": 100})
    rising = g.to_binary({"strain": 5e-21, "frequency": 200},
                         prev_state={"strain": 1e-21, "frequency": 100})
    peak = g.to_binary({"strain": 2e-21, "frequency": 300},
                       prev_state={"strain": 5e-21, "frequency": 200})
    assert rising[23] == "0" and peak[23] == "1"


class _StubManager:
    """Minimal plugin_manager stand-in exposing one encoder's band thresholds."""

    def __init__(self, bands):
        instance = type("Enc", (), {"bands_magnitude": bands})()
        self.plugins = {"enc": {"instance": instance}}


def test_variety_alarm_fires_when_the_bands_cannot_keep_up():
    """Ashby wiring: in-range data the encoder can no longer tell apart."""
    import physics_discovery

    plugin = physics_discovery.PhysicsDiscoveryPlugin()
    # Two thresholds spanning the whole range: the data is comfortably in range
    # but every value lands in the same band, so one codeword answers all of it.
    plugin.plugin_manager = _StubManager([0.0, 100.0])
    for i in range(60):
        plugin.ingest("seismo", i * 0.05)

    status = plugin.variety_status("seismo")
    assert status["distinct_disturbances"] > 10   # the world presents many states
    assert status["distinct_responses"] == 1      # the encoder sees one
    assert status["response_variety"] == 0.0
    assert status["margin"] < 0                   # V(R) < V(D): Ashby violated
    assert status["uncontrolled_variety"] > 0
    assert status["alarm"]

    # A finely banded encoder over the same range keeps its margin.
    plugin.plugin_manager = _StubManager([i * 0.05 for i in range(60)])
    assert not plugin.variety_status("seismo")["alarm"]


def test_variety_status_needs_a_populated_buffer():
    import physics_discovery

    plugin = physics_discovery.PhysicsDiscoveryPlugin()
    plugin.plugin_manager = _StubManager([0.0, 1.0])
    assert plugin.variety_status("nothing_here") is None
    for i in range(5):
        plugin.ingest("short", i)
    assert plugin.variety_status("short") is None


def test_discovery_trigger_modes():
    import physics_discovery

    plugin = physics_discovery.PhysicsDiscoveryPlugin()
    # Values sit inside the known range, so novelty stays low, but the single
    # band means the encoder cannot distinguish them: variety alarm only.
    plugin.plugin_manager = _StubManager([0.0, 10.0])
    for i in range(60):
        plugin.ingest("seismo", i * 0.1)

    novelty, _ = plugin.check_for_novelty("seismo")
    assert novelty < plugin.novelty_threshold
    assert "no action" in plugin.run_full_discovery("seismo", trigger="novelty")

    with pytest.raises(ValueError):
        plugin.run_full_discovery("seismo", trigger="vibes")

    # The variety trigger reaches the encoder-creation path instead of bailing
    # out; with no meta_encoder wired up it fails there, which is the proof it
    # got past the gate.
    with pytest.raises(AttributeError):
        plugin.run_full_discovery("seismo", trigger="variety")


def test_affective_gray_decode():
    import affective_signal_processor as asp
    a = asp.AffectiveSignalProcessor()
    a.ingest("curiosity", 0.8)
    assert "band 6" in a.report()   # Gray '101' decoded to 6, not 5 (§3.22)
