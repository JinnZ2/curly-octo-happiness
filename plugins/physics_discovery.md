> **Integration target:** `unified_playground.py` → `UnifiedAgent` (`__init__` / `handle_mentor`). This file is a wiring snippet, not a standalone module.

if cmd.startswith("discover from "):
    # discover from <stream_name> [optional description]
    parts = cmd.split(" ", 3)   # ["discover", "from", stream, description?]
    stream = parts[2] if len(parts) > 2 else "unknown_stream"
    desc = parts[3] if len(parts) > 3 else ""
    return self.discovery_plugin.run_full_discovery(stream, desc)

if cmd.startswith("ingest "):
    # ingest <stream_name> <value>
    parts = cmd.split()
    if len(parts) < 3:
        return "Usage: ingest <stream_name> <value>"
    stream = parts[1]
    value = float(parts[2])
    self.discovery_plugin.ingest(stream, value)
    return f"📥 Ingested {value} into '{stream}'."

if cmd == "check novelty":
    results = []
    for stream in self.discovery_plugin.data_buffers:
        score, _ = self.discovery_plugin.check_for_novelty(stream)
        results.append(f"  {stream}: novelty={score:.2f}")
    return "Novelty scores:\n" + "\n".join(results) if results else "No data streams yet."

    autonomous loop:

    # After physics / hardware steps:
if self.discovery_plugin:
    for stream_name in self.discovery_plugin.data_buffers:
        novelty, _ = self.discovery_plugin.check_for_novelty(stream_name)
        if novelty > self.discovery_plugin.novelty_threshold:
            # auto‑discover
            result = self.discovery_plugin.run_full_discovery(stream_name, "auto‑detected")
            self.memory.add("agent", result, tags=["auto_discovery"])

            
