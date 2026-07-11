import os
import importlib
import sys
from collections import OrderedDict

class PluginManager:
    def __init__(self, plugin_dir="plugins"):
        self.plugin_dir = plugin_dir
        self.plugins = OrderedDict()  # name -> {"module": module, "encoder": instance, "meta": PLUGIN_META}
        self.auto_load = set()        # names of plugins to auto-encode each step
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
                    if hasattr(module, "PLUGIN_META") and hasattr(module, module.PLUGIN_META.get("encoder_class", f"{mod_name.capitalize()}Encoder")):
                        meta = module.PLUGIN_META
                        enc_class = getattr(module, meta.get("encoder_class", f"{mod_name.capitalize()}Encoder"))
                        encoder = enc_class()  # assumes no-arg constructor; could pass config
                        self.plugins[meta["name"]] = {
                            "module": module,
                            "encoder": encoder,
                            "meta": meta,
                        }
                        print(f"🧩 Loaded plugin: {meta['name']}")
                except Exception as e:
                    print(f"⚠️ Failed to load plugin '{fname}': {e}")

    def list_plugins(self):
        if not self.plugins:
            return "No plugins found."
        lines = ["🧩 Available Plugins:"]
        for name, info in self.plugins.items():
            lines.append(f"  - {name}: {info['meta']['description']}")
        return "\n".join(lines)

    def load_plugin(self, name):
        if name not in self.plugins:
            return f"❌ Plugin '{name}' not found."
        self.auto_load.add(name)
        return f"✅ Plugin '{name}' loaded and set to auto-read."

    def unload_plugin(self, name):
        self.auto_load.discard(name)
        return f"⬅️ Plugin '{name}' removed from auto-read."

    def read_plugin(self, name, geometry_data):
        if name not in self.plugins:
            return None, f"❌ Plugin '{name}' not found."
        try:
            enc = self.plugins[name]["encoder"]
            enc.from_geometry(geometry_data)
            binary = enc.to_binary()
            report = enc.report() if hasattr(enc, "report") else ""
            return binary, report
        except Exception as e:
            return None, f"⚠️ Error reading plugin '{name}': {e}"

    def auto_read_all(self, geometry_provider):
        """Call this every cycle to get all auto-loaded plugin data."""
        results = {}
        for name in self.auto_load:
            geom = geometry_provider(name)   # user-defined function that returns geometry dict for a given plugin
            if geom:
                binary, report = self.read_plugin(name, geom)
                if binary:
                    results[name] = (binary, report)
        return results
