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


def test_affective_gray_decode():
    import affective_signal_processor as asp
    a = asp.AffectiveSignalProcessor()
    a.ingest("curiosity", 0.8)
    assert "band 6" in a.report()   # Gray '101' decoded to 6, not 5 (§3.22)
