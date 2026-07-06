handle_mentor:

if cmd == "mag init":
    # Provide some sample data for band initialization
    samples = [
        {"B_vec": [0.1, 0.0, 0.0], "B_mag": 0.1},
        {"B_vec": [0.15, 0.02, 0.0], "B_mag": 0.151},
        {"B_vec": [0.09, -0.01, 0.0], "B_mag": 0.0905},
        {"B_vec": [0.2, 0.0, 0.0], "B_mag": 0.2},
        {"B_vec": [0.12, 0.03, 0.0], "B_mag": 0.1237},
        # ... more samples ...
    ]
    self.plugin_manager.init_bands("magnetic", samples)
    return "🧲 Magnetic bands initialized."

if cmd.startswith("mag read "):
    # Parse B_vec as e.g., "0.2,0.1,0.3"
    parts = cmd[9:].strip().split()
    B_vec = [float(x) for x in parts[0].split(",")]
    state = {"B_vec": B_vec}
    # Provide prev_state and cross_signals if needed
    prev = self.last_mag_state  # store previously
    cross = {}
    # If EM plugin is loaded and has last binary
    if "em_field" in self.plugin_manager.auto_load:
        cross["em_field"] = self.last_em_binary or "0000"
    binary, report = self.plugin_manager.read_plugin("magnetic", state, prev_state=prev, cross_signals=cross)
    self.last_mag_state = state
    self.memory.add("agent", f"Magnetic reading: {binary} — {report}", tags=["magnetic"])
    return f"🧲 Magnetic encoding:\n  Binary: {binary}\n  📊 {report}"

if cmd == "em simulate":
    # (existing EM simulation, store its binary)
    # ... after encoding, set self.last_em_binary = binary
