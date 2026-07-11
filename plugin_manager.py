"""plugin_manager.py — the single, consolidated plugin manager.

Merges the three historical versions (now in design/archive/):
  v1: encoder_class + from_geometry()/to_binary()/report()
  v2: class_name + process(geometry) adapter path
  v3: init_bands() + extended to_binary(state, prev_state, cross_signals)

Plugins are modules in `plugin_dir` exposing a PLUGIN_META dict with at
least {"name", "description"} and a "class_name" key (legacy
"encoder_class" also accepted). Plugins whose class needs constructor
arguments (services like harmony_field or vector_pole) are registered
un-instantiated; obtain them with get_service(name, *args).
"""

import importlib
import inspect
import os
import sys
from typing import Callable, Dict, Optional, Tuple


class PluginManager:
    def __init__(self, plugin_dir="plugins"):
        self.plugin_dir = plugin_dir
        self.plugins = {}          # name -> {"module", "class", "instance", "meta", "kind"}
        self.auto_load = set()     # names of plugins to auto-read each cycle
        self._scan()

    def _scan(self):
        if not os.path.isdir(self.plugin_dir):
            os.makedirs(self.plugin_dir, exist_ok=True)
            return
        if self.plugin_dir not in sys.path:
            sys.path.insert(0, self.plugin_dir)
        for fname in sorted(os.listdir(self.plugin_dir)):
            if not fname.endswith(".py") or fname.startswith("__"):
                continue
            mod_name = fname[:-3]
            try:
                module = importlib.import_module(mod_name)
                if not hasattr(module, "PLUGIN_META"):
                    continue
                meta = module.PLUGIN_META
                class_name = meta.get("class_name") or meta.get("encoder_class") \
                    or f"{mod_name.capitalize()}Plugin"
                plugin_class = getattr(module, class_name)
                try:
                    instance = plugin_class()
                    kind = meta.get("kind", "encoder")
                except TypeError:
                    # Needs constructor args: register as a service, build lazily.
                    instance = None
                    kind = "service"
                entry = {
                    "module": module,
                    "class": plugin_class,
                    "instance": instance,
                    "meta": meta,
                    "kind": kind,
                }
                self.plugins[meta["name"]] = entry
                # Also register under the module name so lookups by filename
                # work when PLUGIN_META["name"] differs (e.g. emf -> emf_sensor).
                self.plugins.setdefault(mod_name, entry)
                suffix = " (service — use get_service)" if instance is None else ""
                print(f"🧩 Loaded plugin: {meta['name']}{suffix}")
            except Exception as e:
                print(f"⚠️ Skipping '{fname}': {e}")

    # ------------------------------------------------------------------
    # Lookup / lifecycle
    # ------------------------------------------------------------------
    def get_service(self, name, *args, **kwargs):
        """Return the plugin instance, instantiating services on first use
        with the supplied constructor arguments."""
        if name not in self.plugins:
            return None
        entry = self.plugins[name]
        if entry["instance"] is None:
            entry["instance"] = entry["class"](*args, **kwargs)
        return entry["instance"]

    def list_plugins(self) -> str:
        if not self.plugins:
            return "No plugins found."
        lines = ["🧩 Available Plugins:"]
        seen = set()
        for name, info in self.plugins.items():
            if id(info) in seen:
                continue  # skip module-name aliases
            seen.add(id(info))
            tag = " [service]" if info["kind"] == "service" else ""
            lines.append(f"  - {info['meta']['name']}{tag}: {info['meta']['description']}")
        return "\n".join(lines)

    def load_plugin(self, name: str) -> str:
        if name not in self.plugins:
            return f"❌ Plugin '{name}' not found."
        self.auto_load.add(name)
        return f"✅ Plugin '{name}' loaded and will auto-read."

    def unload_plugin(self, name: str) -> str:
        self.auto_load.discard(name)
        return f"⬅️ Plugin '{name}' removed from auto-read."

    def init_bands(self, name, samples):
        """Call init_bands on a plugin if it supports adaptive banding."""
        if name in self.plugins:
            inst = self.get_service(name)
            if inst is not None and hasattr(inst, "init_bands"):
                inst.init_bands(samples)

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------
    def read_plugin(self, name: str, state: dict, prev_state=None,
                    cross_signals=None) -> Tuple[Optional[str], Optional[str]]:
        """Return (binary_str, report_str) or (None, error). Tries, in order:
        extended to_binary(state, prev_state, cross_signals), process(state),
        then from_geometry(state)/to_binary()."""
        if name not in self.plugins:
            return None, f"❌ Plugin '{name}' not found."
        entry = self.plugins[name]
        if entry["instance"] is None:
            return None, f"⚠️ '{name}' is a service; instantiate it with get_service()."
        inst = entry["instance"]
        try:
            if hasattr(inst, "to_binary"):
                params = inspect.signature(inst.to_binary).parameters
                if "prev_state" in params:
                    binary = inst.to_binary(state, prev_state=prev_state,
                                            cross_signals=cross_signals)
                    return binary, self._report(inst)
            if hasattr(inst, "process"):
                result = inst.process(state)
                return result.get("binary"), result.get("report", "")
            if hasattr(inst, "from_geometry") and hasattr(inst, "to_binary"):
                inst.from_geometry(state)
                return inst.to_binary(), self._report(inst)
            return None, "⚠️ Plugin doesn't support read operation."
        except Exception as e:
            return None, f"⚠️ Error: {e}"

    @staticmethod
    def _report(inst) -> str:
        return inst.report() if hasattr(inst, "report") else ""

    def auto_read_all(self, source, prev_states: dict = None,
                      cross_signals: dict = None) -> Dict[str, tuple]:
        """Read every auto-loaded plugin.

        `source` is either a callable name -> geometry dict (v1/v2 style) or
        a dict of plugin_name -> state (v3 style)."""
        results = {}
        if callable(source):
            items = ((name, source(name)) for name in self.auto_load)
        else:
            items = ((name, state) for name, state in source.items()
                     if name in self.auto_load)
        for name, state in items:
            if state is None:
                continue
            prev = prev_states.get(name) if prev_states else None
            cross = ({k: v for k, v in cross_signals.items() if k != name}
                     if cross_signals else None)
            binary, report = self.read_plugin(name, state, prev_state=prev,
                                              cross_signals=cross)
            if binary:
                results[name] = (binary, report)
        return results
