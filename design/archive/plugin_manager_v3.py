# plugin_manager.py (excerpt with new features)

class PluginManager:
    # ... (existing scanning, listing, load/unload) ...

    def init_bands(self, name, samples):
        """Call init_bands on plugin if available."""
        if name in self.plugins:
            inst = self.plugins[name]["instance"]
            if hasattr(inst, "init_bands"):
                inst.init_bands(samples)

    def read_plugin(self, name, state, prev_state=None, cross_signals=None):
        """
        Read a plugin. If plugin supports extended interface, use it;
        otherwise fall back to from_geometry/to_binary.
        """
        if name not in self.plugins:
            return None, f"Plugin '{name}' not found."
        inst = self.plugins[name]["instance"]
        try:
            # Extended interface (priority)
            if hasattr(inst, "to_binary") and "prev_state" in inst.to_binary.__code__.co_varnames:
                binary = inst.to_binary(state, prev_state=prev_state, cross_signals=cross_signals)
                report = inst.report() if hasattr(inst, "report") else ""
                return binary, report
            # Original simple interface
            elif hasattr(inst, "from_geometry") and hasattr(inst, "to_binary"):
                inst.from_geometry(state)
                binary = inst.to_binary()
                report = inst.report() if hasattr(inst, "report") else ""
                return binary, report
            else:
                return None, "Plugin doesn't support reading."
        except Exception as e:
            return None, f"Error: {e}"

    def auto_read_all(self, states: dict, prev_states: dict = None, cross_signals: dict = None):
        """states: dict of plugin_name -> geometry dict. cross_signals: dict of plugin_name -> binary str."""
        results = {}
        for name, state in states.items():
            if name in self.auto_load:
                prev = prev_states.get(name) if prev_states else None
                cross = {k: v for k, v in cross_signals.items() if k != name} if cross_signals else None
                binary, report = self.read_plugin(name, state, prev_state=prev, cross_signals=cross)
                if binary is not None:
                    results[name] = (binary, report)
        return results
