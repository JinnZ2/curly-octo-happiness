import os, sys, importlib
from typing import Dict, Any, Optional, Callable

class PluginManager:
    def __init__(self, plugin_dir="plugins"):
        self.plugin_dir = plugin_dir
        self.plugins = {}          # name -> {"module": module, "instance": obj, "meta": PLUGIN_META}
        self.auto_load = set()     # names of plugins to auto-read each cycle
        self._scan()

    def _scan(self):
        if not os.path.isdir(self.plugin_dir):
            os.makedirs(self.plugin_dir, exist_ok=True)
            return
        sys.path.insert(0, self.plugin_dir)
        for fname in os.listdir(self.plugin_dir):
            if fname.endswith(".py") and not fname.startswith("__"):
                mod_name = fname[:-3]
                try:
                    module = importlib.import_module(mod_name)
                    if not hasattr(module, "PLUGIN_META"):
                        continue
                    meta = module.PLUGIN_META
                    class_name = meta.get("class_name", f"{mod_name.capitalize()}Plugin")
                    plugin_class = getattr(module, class_name)
                    instance = plugin_class()
                    self.plugins[meta["name"]] = {
                        "module": module,
                        "instance": instance,
                        "meta": meta,
                    }
                    print(f"🧩 Loaded plugin: {meta['name']}")
                except Exception as e:
                    print(f"⚠️ Skipping '{fname}': {e}")

    def list_plugins(self) -> str:
        if not self.plugins:
            return "No plugins found."
        lines = ["🧩 Available Plugins:"]
        for name, info in self.plugins.items():
            lines.append(f"  - {name}: {info['meta']['description']}")
        return "\n".join(lines)

    def load_plugin(self, name: str) -> str:
        if name not in self.plugins:
            return f"❌ Plugin '{name}' not found."
        self.auto_load.add(name)
        return f"✅ Plugin '{name}' loaded and will auto‑read."

    def unload_plugin(self, name: str) -> str:
        self.auto_load.discard(name)
        return f"⬅️ Plugin '{name}' removed from auto‑read."

    def read_plugin(self, name: str, geometry: dict) -> tuple[Optional[str], Optional[str]]:
        """Return (binary_str, report_str) or (None, error)."""
        if name not in self.plugins:
            return None, f"❌ Plugin '{name}' not found."
        inst = self.plugins[name]["instance"]
        try:
            if hasattr(inst, "process"):
                # Adapter path
                result = inst.process(geometry)
                return result.get("binary"), result.get("report", "")
            elif hasattr(inst, "from_geometry") and hasattr(inst, "to_binary"):
                # Simple encoder path
                inst.from_geometry(geometry)
                return inst.to_binary(), getattr(inst, "report", lambda: "")()
            else:
                return None, "⚠️ Plugin doesn't support read operation."
        except Exception as e:
            return None, f"⚠️ Error: {e}"

    def auto_read_all(self, geometry_provider: Callable[[str], Optional[dict]]) -> Dict[str, tuple]:
        """Call this each cycle to get all auto-loaded plugin data."""
        results = {}
        for name in self.auto_load:
            geom = geometry_provider(name)
            if geom is not None:
                binary, report = self.read_plugin(name, geom)
                if binary:
                    results[name] = (binary, report)
        return results
