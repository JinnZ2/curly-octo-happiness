> **Integration target:** `unified_playground.py` → `UnifiedAgent` (`__init__` / `handle_mentor`). This file is a wiring snippet, not a standalone module.

if cmd.startswith("create encoder"):
    parts = cmd.split(" ", 2)
    if len(parts) < 3:
        return "Usage: create encoder <name> <description> <primary_key> <bands_json>"
    # Parse a JSON string with name, description, primary_key, bands
    # For simplicity, we'll take a dict literal
    config_str = parts[2]
    config = eval(config_str)  # careful: use json.loads in practice
    name = config["name"]
    desc = config["description"]
    primary = config["primary_key"]
    bands = config["magnitude_bands"]
    delta_bands = config.get("delta_bands", None)
    result = self.meta_encoder.create_encoder(name, desc, primary, bands, delta_bands)
    # Hot-load it
    load_result = self.meta_encoder.load_new_encoder(name, self.plugin_manager)
    return f"{result}\n{load_result}"

if cmd.startswith("test new encoder"):
    # test the newly created encoder with sample data
    parts = cmd.split(" ", 3)
    if len(parts) < 4:
        return "Usage: test new encoder <name> <sample_geometry_json>"
    name = parts[3].strip()
    geom = json.loads(parts[4]) if len(parts)>4 else {}
    binary, report = self.plugin_manager.read_plugin(name, geom)
    return f"🔌 {name} binary: {binary}\n📊 {report}"
