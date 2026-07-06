def geom_provider(name):
    if name == "em_field":
        # read from real solver or return None
        return None
    if name == "light":
        # read from camera/photodetector simulation
        return {
            "polarization": ["V", "H"],
            "spectrum_nm": [500.0, 600.0],
            "interference_intensity": [0.7, 0.3],
            "photon_spin": ["R", "L"],
        }
    return None
