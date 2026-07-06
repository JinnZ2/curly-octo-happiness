PLUGIN_META = {
    "name": "thermal_camera",
    "description": "Encodes infrared thermal image into binary.",
    "geometry_keys": ["pixels", "emissivity"],
}

class ThermalCameraEncoder:
    def from_geometry(self, geometry_data):
        ...
    def to_binary(self) -> str:
        ...
    def report(self):
        ...


add __init__self.plugin_manager = PluginManager()

add to handle_mentor

if cmd == "plugins list":
    return self.plugin_manager.list_plugins()
if cmd.startswith("plugin load "):
    name = cmd[12:].strip()
    return self.plugin_manager.load_plugin(name)
if cmd.startswith("plugin unload "):
    name = cmd[14:].strip()
    return self.plugin_manager.unload_plugin(name)
if cmd.startswith("plugin read "):
    # expects: plugin read <name> <json_geometry>
    parts = cmd.split(" ", 3)
    if len(parts) < 3:
        return "Usage: plugin read <name> <json_geometry>"
    name = parts[2]
    geom_str = parts[3] if len(parts) > 3 else "{}"
    try:
        geom = eval(geom_str)  # for simplicity; better to use json.loads
    except:
        geom = {}
    binary, report = self.plugin_manager.read_plugin(name, geom)
    if binary is None:
        return report
    return f"🔌 {name} binary: {binary}\n📊 {report}"
if cmd == "plugins auto":
    # read all auto-loaded plugins (geometry must be provided by user-defined function)
    # For demo, we can pass a function that returns dummy geometry for each plugin
    def dummy_geom(pname):
        # User can replace this with their own sensor interface
        if pname == "hardware":
            return self.components[0].get_geometry()  # example
        if pname == "chemical":
            return self.reactor.get_geometry()
        return {}
    results = self.plugin_manager.auto_read_all(dummy_geom)
    if not results:
        return "No auto-loaded plugins or geometries."
    out = []
    for name, (binary, report) in results.items():
        out.append(f"{name}: {binary}\n  {report}")
    return "\n".join(out)


    
