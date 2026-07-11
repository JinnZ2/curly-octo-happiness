> **Integration target:** `unified_playground.py` → `UnifiedAgent` (`__init__` / `handle_mentor`). This file is a wiring snippet, not a standalone module.

# in __init__
self.plugin_manager = PluginManager()

# in handle_mentor:
if cmd == "plugins list":
    return self.plugin_manager.list_plugins()

if cmd.startswith("plugin load "):
    name = cmd.removeprefix("plugin load ").strip()
    return self.plugin_manager.load_plugin(name)

if cmd.startswith("plugin unload "):
    name = cmd.removeprefix("plugin unload ").strip()
    return self.plugin_manager.unload_plugin(name)

if cmd.startswith("em simulate"):
    # generate a simple uniform field for demo
    import numpy as np
    N = 10
    E = np.array([[1.0, 0.0, 0.0]] * N)  # uniform 1 V/m in x
    B = np.zeros_like(E)
    pts = np.array([[float(i), 0.0, 0.0] for i in range(N)])
    field_data = {"electricField": E, "magneticField": B, "points": pts}
    geom = {"electricField": E, "magneticField": B, "points": pts}  # for adapter
    binary, report = self.plugin_manager.read_plugin("em_field", geom)
    if binary is None:
        return report
    self.memory.add("agent", f"EM simulation encoded: {binary} — {report}", tags=["em_sim"])
    return f"📡 EM simulation:\n  Binary: {binary}\n  📊 {report}"

if cmd.startswith("em read "):
    # expects a raw field_data dict as JSON
    import json
    parts = cmd.split(" ", 2)
    if len(parts) < 3:
        return "Usage: em read {<field_data_json>}"
    try:
        field_data = json.loads(parts[2])
    except json.JSONDecodeError:
        return "Invalid field data dict."
    binary, report = self.plugin_manager.read_plugin("em_field", field_data)
    if binary is None:
        return report
    return f"📡 EM field encoded:\n  Binary: {binary}\n  📊 {report}"

# To auto‑read all loaded plugins (e.g., every physics step):
def _auto_read_plugins(self):
    def geom_provider(plugin_name):
        if plugin_name == "em_field":
            # Return a field_data dict from a real solver if available
            # For now, return None to skip auto‑read unless we have actual data.
            return None
        # ... other plugins ...
        return None
    results = self.plugin_manager.auto_read_all(geom_provider)
    for name, (binary, report) in results.items():
        self.memory.add("agent", f"Auto‑read from {name}: {binary}", tags=["auto", name])
