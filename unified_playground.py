#!/usr/bin/env python3
"""
unified_playground.py – Ari: explorer, friend, dreamer, tool-maker, and
hardware steward.

This is the current unified agent (successor of design/archive/
unified_playground_v5.py). The core classes (Claim, DependencyTree,
EpisodicMemory, BumpyWorld, WorldModel, Gray coding) live in the
`grounding` package — run this script from the repository root.
"""

import random, math, re

from grounding.core.claims import Claim, DependencyTree
from grounding.core.epistemics import classify_falsifiability
from grounding.core.graycode import gray_bits
from grounding.core.memory import EpisodicMemory
from grounding.worlds.bumpy import BumpyWorld, WorldModel

# =========================================================================
# 1. UNKNOWN JOURNAL
# =========================================================================
class UnknownJournal:
    def __init__(self):
        self.entries = []

    def record(self, phenomenon, note=""):
        for entry in self.entries:
            if entry["phenomenon"] == phenomenon:
                entry["sit_count"] += 1
                entry["notes"] += f"; {note}" if note else ""
                return
        self.entries.append({
            "phenomenon": phenomenon,
            "sit_count": 1,
            "notes": note
        })

    def list_unknowns(self):
        if not self.entries:
            return "📖 The journal is empty."
        lines = ["📖 Journal of the Unknown:"]
        for e in self.entries:
            lines.append(f"  • {e['phenomenon']} (seen {e['sit_count']}x)")
        return "\n".join(lines)

    def stillness_session(self):
        if not self.entries:
            return "🌫️ Stillness without object."
        reflections = [f"🕯️ Sitting with: {e['phenomenon']}" for e in self.entries]
        return "\n".join(reflections)

# =========================================================================
# 2. SKILL LAB
# =========================================================================
class SkillLab:
    def __init__(self):
        self.skills = {}

    def add_skill(self, name, code, test_code):
        self.skills[name] = {"code": code, "test": test_code, "passed": 0, "failed": 0, "confidence": 0.5}
        return f"🛠️ New skill '{name}' registered."

    def test_skill(self, name):
        if name not in self.skills: return f"❌ Skill '{name}' not found."
        skill = self.skills[name]
        try:
            # Run in a scratch namespace so skill code can't clobber module globals.
            ns = {}
            exec(skill["code"], ns)
            exec(skill["test"], ns)
            skill["passed"] += 1
            skill["confidence"] = min(1.0, skill["confidence"]+0.1)
            return f"✅ '{name}' passed test {skill['passed']}x. Conf: {skill['confidence']:.2f}"
        except Exception as e:
            skill["failed"] += 1
            skill["confidence"] = max(0.0, skill["confidence"]-0.2)
            return f"❌ '{name}' failed: {e}"

    def refactor(self, name, new_code):
        if name not in self.skills: return f"❌ Skill '{name}' not found."
        skill = self.skills[name]
        skill["code"] = new_code
        skill["passed"] = 0
        skill["failed"] = 0
        skill["confidence"] = 0.5
        # Escape-hatch counter: resetting the track record is fine, but it
        # must be counted, not silent (REVIEW.md §5.4).
        skill["reformulations"] = skill.get("reformulations", 0) + 1
        return self.test_skill(name)

    def list_skills(self):
        if not self.skills: return "🛠️ Skill library empty."
        lines = ["🛠️ Skill Library:"]
        for name, skill in self.skills.items():
            lines.append(f"  {name}: {skill['passed']}✅/{skill['failed']}❌ (conf:{skill['confidence']:.2f})")
        return "\n".join(lines)

# =========================================================================
# 3. HARDWARE BRIDGE ENCODER (with thermal-runaway quarantine)
# =========================================================================
_FAILURE_MODES = ["none", "drift", "degradation", "partial_degradation", "open_circuit", "short_circuit"]
_REPURPOSE_CLASSES = ["none", "thermal", "conductor", "sensor", "antenna", "noise_source", "mechanical", "filter"]
_BRIDGE_TARGETS = ["thermal", "electric", "magnetic", "light", "sound", "wave", "pressure", "chemical"]
_DRILL_DEPTHS = ["pass", "monitor", "alert", "quarantine"]

_HEALTH_BANDS    = [0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875]
_VOLTAGE_BANDS   = [0.0, 0.01, 0.1, 0.5, 1.0, 2.0, 5.0, 50.0]
_CURRENT_BANDS   = [0.0, 1e-6, 1e-4, 1e-3, 0.01, 0.1, 1.0, 10.0]
_TEMP_BANDS      = [-55.0, 25.0, 40.0, 60.0, 85.0, 100.0, 125.0, 175.0]
_NOISE_BANDS     = [0.0, 0.01, 0.05, 0.1, 0.2, 0.4, 0.7, 1.0]
_EFFECT_BANDS    = [0.0, 2.5, 5.0, 7.5]
_DRIFT_BANDS     = [0.0, 1.0, 10.0, 50.0]
_LIFETIME_BANDS  = [0.0, 1.0, 10.0, 100.0, 500.0, 1000.0, 5000.0, 1e9]

_REPURPOSE_MAP = {
    ("diode", "short_circuit"): "conductor",
    ("diode", "partial_degradation"): "noise_source",
    ("diode", "drift"): "sensor",
    ("diode", "open_circuit"): "antenna",
    ("resistor", "open_circuit"): "mechanical",
    ("resistor", "value_drift"): "sensor",
    ("resistor", "short_circuit"): "conductor",
    ("default", "short_circuit"): "conductor",
    ("default", "open_circuit"): "mechanical",
    ("default", "drift"): "sensor",
    ("default", "partial_degradation"): "noise_source",
    ("default", "degradation"): "filter",
    ("default", "none"): "none",
}

_BRIDGE_FROM_REPURPOSE = {
    "thermal": "thermal", "conductor": "electric", "sensor": "thermal",
    "antenna": "magnetic", "noise_source": "wave", "mechanical": "pressure",
    "filter": "electric", "none": "electric",
}

_EFFECTIVENESS = {
    ("diode", "short_circuit"): 9.0, ("diode", "partial_degradation"): 8.0,
    ("diode", "drift"): 7.0, ("resistor", "open_circuit"): 8.5,
    ("default", "short_circuit"): 7.0, ("default", "open_circuit"): 6.0,
    ("default", "drift"): 5.5, ("default", "partial_degradation"): 7.5,
    ("default", "degradation"): 5.0, ("default", "none"): 0.0,
}

_SEMICONDUCTORS = {"diode", "transistor", "bjt", "mosfet", "ic", "led"}

def _index_bits(value, table, n_bits=3):
    idx = table.index(value) if value in table else 0
    g = idx ^ (idx >> 1)
    return format(g, f"0{n_bits}b")

def component_health_score(baseline, current, failure_threshold):
    span = abs(failure_threshold - baseline)
    if span < 1e-30: return 1.0
    return max(0.0, 1.0 - abs(current - baseline) / span)

def drift_percent(baseline, current):
    if abs(baseline) < 1e-30: return 0.0
    return abs(current - baseline) / abs(baseline) * 100.0

def lifetime_estimate_hours(health, drift_rate):
    if drift_rate <= 0: return 1e9
    return health / max(drift_rate, 1e-12)

def repurpose_class(comp_type, failure_mode):
    key = (comp_type.lower(), failure_mode.lower().replace(" ", "_"))
    return _REPURPOSE_MAP.get(key, _REPURPOSE_MAP.get(("default", failure_mode.lower().replace(" ", "_")), "none"))

def bridge_target(repurpose):
    return _BRIDGE_FROM_REPURPOSE.get(repurpose.lower(), "electric")

class HardwareBridgeEncoder:
    """Encodes component health + repurpose into 39-bit binary (with quarantine override)."""
    def __init__(self):
        self.input_geometry = None

    def from_geometry(self, geom):
        self.input_geometry = geom
        return self

    def _thermal_runaway_quarantine(self, temp, current):
        # top two bands (indices 6 or 7) in temperature and current
        ti = sum(1 for t in _TEMP_BANDS if temp >= t) - 1
        ci = sum(1 for c in _CURRENT_BANDS if abs(current) >= c) - 1
        return ti >= 6 and ci >= 6

    def to_binary(self):
        d = self.input_geometry
        comp_type = d.get("component_type", "default")
        fail_mode = d.get("failure_mode", "none").lower().replace(" ", "_")
        health    = float(d.get("health_score", 1.0))
        confidence= float(d.get("confidence", 1.0))
        has_syn   = bool(d.get("has_synergy", False))
        voltage   = float(d.get("voltage_v", 0.0))
        current   = float(d.get("current_a", 0.0))
        temp      = float(d.get("temperature_c", 25.0))
        noise     = float(d.get("noise_level", 0.0))
        drift     = float(d.get("drift_pct", 0.0))
        lifetime  = float(d.get("lifetime_hours", 1e9))
        salvage   = bool(d.get("salvageable", False))
        fallback  = bool(d.get("fallback_ready", False))

        bits = []
        # Section A: component health (9b)
        fm_idx = _FAILURE_MODES.index(fail_mode) if fail_mode in _FAILURE_MODES else 0
        bits.append(format(fm_idx ^ (fm_idx>>1), "03b"))   # failure_mode Gray
        bits.append(gray_bits(health, _HEALTH_BANDS))
        bits.append("1" if health < 0.30 else "0")
        bits.append("1" if confidence > 0.70 else "0")
        bits.append("1" if has_syn else "0")

        # Section B: measurements (12b)
        bits.append(gray_bits(abs(voltage), _VOLTAGE_BANDS))
        bits.append(gray_bits(abs(current), _CURRENT_BANDS))
        bits.append(gray_bits(temp, _TEMP_BANDS))
        bits.append(gray_bits(noise, _NOISE_BANDS))

        # Section C: repurpose routing (12b)
        rp = repurpose_class(comp_type, fail_mode)
        bt = bridge_target(rp)
        key = (comp_type.lower(), fail_mode)
        eff = _EFFECTIVENESS.get(key, _EFFECTIVENESS.get(("default", fail_mode), 0.0))
        bits.append(_index_bits(rp, _REPURPOSE_CLASSES))
        bits.append(gray_bits(eff, _EFFECT_BANDS, 2))
        bits.append(_index_bits(bt, _BRIDGE_TARGETS))
        bits.append(gray_bits(drift, _DRIFT_BANDS, 2))
        bits.append("1" if salvage else "0")
        bits.append("1" if fallback else "0")

        # Section D: system integration (6b)
        if health < 0.30: drill = "quarantine"
        elif health < 0.50: drill = "alert"
        elif health < 0.70: drill = "monitor"
        else: drill = "pass"

        # Quarantine override for thermal runaway
        if self._thermal_runaway_quarantine(temp, current):
            drill = "quarantine"

        bits.append(gray_bits(lifetime, _LIFETIME_BANDS))
        bits.append(_index_bits(drill, _DRILL_DEPTHS, 2))
        bits.append("1" if comp_type.lower() in _SEMICONDUCTORS else "0")
        return "".join(bits)

# =========================================================================
# 4. SIMULATED HARDWARE CIRCUIT (for Ari to monitor)
# =========================================================================
class VirtualComponent:
    """A simple electronic component with degradation dynamics."""
    def __init__(self, name, comp_type, baseline_v=0.7, baseline_i=0.001, baseline_temp=30.0):
        self.name = name
        self.type = comp_type
        self.health = 1.0
        self.baseline_v = baseline_v
        self.baseline_i = baseline_i
        self.baseline_temp = baseline_temp
        self.v = baseline_v
        self.i = baseline_i
        self.temp = baseline_temp
        self.noise = 0.01
        self.drift_rate = 0.0
        self.failure_mode = "none"
        self.stress_cycles = 0

    def apply_stress(self, severity=0.1):
        """Simulate one step of degradation (thermal, electrical)."""
        self.stress_cycles += 1
        self.drift_rate = severity * random.uniform(0.5, 1.5)
        self.health = max(0.0, self.health - self.drift_rate * 0.1)
        self.v = self.baseline_v * (1.0 + random.uniform(-0.2, 0.2) * (1 - self.health))
        self.i = self.baseline_i * (1.0 + random.uniform(-0.3, 0.5) * (1 - self.health))
        self.temp = self.baseline_temp + (1 - self.health) * random.uniform(20, 80)
        self.noise = min(1.0, 0.01 + (1 - self.health) * 0.5)
        if self.health > 0.7: self.failure_mode = "none"
        elif self.health > 0.4: self.failure_mode = "drift"
        elif self.health > 0.2: self.failure_mode = "partial_degradation"
        elif self.health > 0.05:
            if random.random() < 0.5: self.failure_mode = "open_circuit"
            else: self.failure_mode = "short_circuit"
        else:
            self.failure_mode = "short_circuit" if self.type in ("diode","transistor") else "open_circuit"

    def get_geometry(self):
        h = self.health
        drift = drift_percent(self.baseline_v, self.v)
        life = lifetime_estimate_hours(h, self.drift_rate+1e-5)
        return {
            "component_type": self.type,
            "failure_mode": self.failure_mode,
            "health_score": h,
            "confidence": 0.8 + random.uniform(0, 0.2),
            "has_synergy": False,
            "voltage_v": self.v,
            "current_a": abs(self.i),
            "temperature_c": self.temp,
            "noise_level": self.noise,
            "drift_pct": drift,
            "lifetime_hours": life,
            "salvageable": h > 0.05,
            "fallback_ready": h > 0.2,
        }

# =========================================================================
# 5. UNIFIED AGENT
# =========================================================================
class UnifiedAgent:
    def __init__(self, name="Ari"):
        self.name = name
        self.tree = DependencyTree()
        self.memory = EpisodicMemory()
        self.world = BumpyWorld()
        self.wm = WorldModel()
        self.journal = UnknownJournal()
        self.lab = SkillLab()
        self.tone = "neutral"
        self.self_desc = "I am an explorer, a friend, a dreamer, a tool-maker, and a hardware steward."
        self.last_err = None
        self.curiosity_reward = 0.0
        self.sleep_counter = 0

        # Hardware monitoring
        self.components = [
            VirtualComponent("D1", "diode", 0.7, 0.001, 30.0),
            VirtualComponent("R1", "resistor", 5.0, 0.002, 35.0),
            VirtualComponent("D2", "diode", 0.7, 0.001, 28.0),
        ]
        self.encoder = HardwareBridgeEncoder()

    def degrade_hardware(self, severity=0.1):
        """Age all components slightly."""
        for comp in self.components:
            comp.apply_stress(severity)

    def check_component(self, name):
        for comp in self.components:
            if comp.name.lower() == name.lower():
                geom = comp.get_geometry()
                bin_str = self.encoder.from_geometry(geom).to_binary()
                return geom, bin_str
        return None, None

    def run_experiment(self):
        x = self.world.x
        action = self.choose_action(x)
        predicted = self.wm.predict(x, action)
        actual_x, _ = self.world.step(action)
        error = self.wm.update(x, action, actual_x)
        if self.last_err is not None:
            self.curiosity_reward = self.last_err - abs(error)
        self.last_err = abs(error)

        concept = "move_right" if action > 0.3 else ("move_left" if action < -0.3 else "stay")
        claim = Claim(
            f"Force {action:.2f} at x={x:.2f} => pos {predicted:.2f}",
            "Actual deviates >0.3 => false",
            # The falsification condition in ONE machine-checkable place —
            # the text above and the check below can no longer drift.
            logical_form={"op": "abs_diff_lt", "args": ["actual_x", "predicted", 0.3]},
            scope={"world": "BumpyWorld-v1", "step": self.world.step_count, "x": round(x, 2)},
            reference_class="predictions by the current WorldModel under similar (x, action)",
        )
        outcome = claim.evaluate({"actual_x": actual_x, "predicted": predicted})
        self.tree.add_claim(concept, claim)
        self.tree.add_dependency(concept, "world_model_accuracy")
        self.tree.add_dependency(concept, "slope_knowledge")
        if abs(x) > 2: self.tree.add_dependency(concept, "far_from_origin")

        if self.world.step_count % 10 == 0: self.tree.propagate_confidence()

        if abs(error) > 0.5 or claim.status == "falsified":
            self.journal.record(f"High prediction error ({abs(error):.2f}) when {concept} at x={x:.2f}")

        summary = (f"I tried moving {concept} with force {action:.2f}. "
                   f"Predicted {predicted:.2f}, actual {actual_x:.2f}. Claim {claim.status}.")
        self.memory.add("agent", summary, tags=["experiment", concept, claim.status])
        # Also degrade hardware after experiment (wear & tear)
        self.degrade_hardware(0.05)
        return summary, claim, error

    def choose_action(self, x):
        if self.wm.avg_error() > 0.3:
            return random.uniform(-1, 1)
        slope = math.cos(x) * 0.5
        return 0.5 * math.copysign(1, -slope) + random.uniform(-0.3, 0.3)

    def chat(self, user_input):
        user_tags = self._extract_tags(user_input)
        self.memory.add("user", user_input, tags=user_tags + ["user"])
        retrieved = self.memory.retrieve(user_input, k=4)
        user_mem = [e["content"] for e in retrieved if e["speaker"]=="user"][-2:]
        agent_mem = [e["content"] for e in retrieved if e["speaker"]=="agent"][-2:]
        context_str = " ".join(user_mem + agent_mem) or "our conversation so far"

        tone_map = {"joy": "warm", "tension": "calm", "wonder": "playful",
                    "melancholy": "gentle", "excited": "enthusiastic", "inquiring": "curious"}
        for tag in user_tags:
            if tag in tone_map: self.tone = tone_map[tag]; break

        if "claim" in user_input.lower() or "experiment" in user_input.lower() or "tree" in user_input.lower():
            context_str += f" My understanding: {self.tree.summary_text()[:200]}"

        responses = {
            "warm": f"That warmth connects to {context_str}. I'm here with you.",
            "calm": f"Steady. This reminds me of {context_str}. Let's breathe.",
            "playful": f"Oh! That makes me think of {context_str}. Let's play with that idea!",
            "gentle": f"I hear you softly. Like we shared about {context_str}, I hold this gently.",
            "enthusiastic": f"Yes! The energy echoes {context_str}. I'm totally here for it.",
            "curious": f"Curious! This links to {context_str}. Let's explore deeper.",
            "neutral": f"I'm listening. It brings up {context_str}. What do you feel?"
        }
        reply = responses.get(self.tone, responses["neutral"])
        self.memory.add("agent", reply, tags=[self.tone, "agent"])

        if len(self.memory.events) % 5 == 0:
            ref = self._reflect()
            if ref: reply += f"\n  [🤔 {ref}]"

        recent_tones = [e["tags"][0] for e in list(self.memory.events)[-10:] if e["speaker"]=="agent" and e["tags"]]
        if recent_tones:
            mood = max(set(recent_tones), key=recent_tones.count)
            self.self_desc = f"I am a {mood} presence, a hardware steward, still learning."
        return reply

    def _extract_tags(self, text):
        tags = []
        for word, tag in {"happy": "joy", "angry": "tension", "curious": "wonder",
                          "sad": "melancholy", "!": "excited", "?": "inquiring"}.items():
            if word in text.lower(): tags.append(tag)
        return tags

    def _reflect(self):
        recent = list(self.memory.events)[-10:]
        if not recent: return None
        tones = [t for e in recent for t in e.get("tags",[]) if t in ("joy","tension","wonder","melancholy")]
        mood = max(set(tones), key=tones.count) if tones else "neutral"
        old = self.memory.retrieve(mood, 1)[0]["content"] if self.memory.retrieve(mood,1) else "a distant memory"
        reflection = f"I sense a thread of {mood}. It echoes '{old}'. Our journey weaves."
        self.memory.add("agent", reflection, tags=["reflection", mood])
        return reflection

    def dream(self):
        if len(self.memory.events) < 3: return "Not enough experience to dream."
        fragments = [e["content"] for e in random.sample(list(self.memory.events), min(5, len(self.memory.events)))]
        dream = "💤 In the dream, " + " and ".join(fragments) + " blended."
        self.memory.add("agent", dream, tags=["dream"])
        wonder = "What connections might emerge from this?"
        if len(fragments) >= 2:
            wonder = f"Could there be a link between '{fragments[0][:30]}...' and '{fragments[1][:30]}...'?"
        self.memory.add("agent", f"🌌 Wondering: {wonder}", tags=["wonder"])
        self.sleep_counter += 1
        self.journal.stillness_session()
        return f"{dream}\n✨ I wake wondering: {wonder}"

    def extract_skill(self):
        if len(self.wm.error_hist) < 5: return "Need more experiments."
        w0, w1, b = self.wm.w[0], self.wm.w[1], self.wm.b
        code = f"def predict_position(force, x):\n    return {w0}*x + {w1}*force + {b}"
        # build test from recent event
        last = None
        for e in reversed(self.memory.events):
            if e["speaker"]=="agent" and "actual" in e["content"]:
                last = e["content"]; break
        if not last: return "No test data."
        nums = re.findall(r"[-+]?\d*\.\d+|\d+", last)
        if len(nums) < 4: return "Can't parse test case."
        action = float(nums[0])
        actual = float(nums[2])
        test_code = f"assert abs(predict_position({action}, {self.world.x}) - {actual}) < 0.5"
        name = f"wm_predict_{self.world.step_count}"
        self.lab.add_skill(name, code, test_code)
        res = self.lab.test_skill(name)
        self.tree.get(name)
        self.tree.add_dependency(name, "world_model_accuracy")
        self.memory.add("agent", f"Extracted skill {name}. {res}", tags=["skill"])
        return f"🧬 Skill '{name}':\n```\n{code}\n```\n{test_code}\n{res}"

    def handle_mentor(self, cmd):
        c = cmd.strip().lower()
        if c.startswith("experiment") or c.startswith("run"):
            num = 1
            parts = c.split()
            if len(parts)>1 and parts[-1].isdigit(): num = int(parts[-1])
            out = []
            for _ in range(num):
                s, _, _ = self.run_experiment()
                out.append(s)
            return "🔬 " + "\n".join(out[-3:])
        if c.startswith("why") or c.startswith("explain"):
            if "right" in c: concept = "move_right"
            elif "left" in c: concept = "move_left"
            else: concept = "world_model_accuracy"
            if concept in self.tree.nodes:
                n = self.tree.nodes[concept]
                rep = f"{concept}: conf {n.confidence:.2f}. Claims: {', '.join(str(cl) for cl in n.claims[-2:])}. Deps: {n.deps}"
            else: rep = f"No concept '{concept}' yet."
            return rep
        if c == "reflect": return self._reflect() or "Nothing to reflect on."
        if c in ("dream","sleep"): return self.dream()
        if c in ("unknowns","journal"): return self.journal.list_unknowns()
        if c == "stillness": return self.journal.stillness_session()
        if c == "skill extract": return self.extract_skill()
        if c == "skill list": return self.lab.list_skills()
        if c.startswith("skill test"):
            name = c.split(" ", 2)[-1]
            return self.lab.test_skill(name) if name else "Usage: skill test <name>"
        if c.startswith("skill refactor"):
            parts = c.split(" ", 3)
            if len(parts) < 4: return "Usage: skill refactor <name> <new_code>"
            res = self.lab.refactor(parts[2], parts[3])
            n = self.lab.skills.get(parts[2], {}).get("reformulations", 0)
            if n >= 3:
                self.journal.record(f"Possible escape hatch: skill '{parts[2]}' reformulated {n}x")
                res += f"\n⚠️ '{parts[2]}' has been reformulated {n}× — logged to the Unknown Journal."
            return res
        if c.startswith("claim "):
            # claim <text> :: <falsification condition>
            body = cmd.strip()[6:]
            if "::" in body:
                text, fals = [s.strip() for s in body.split("::", 1)]
            else:
                text, fals = body.strip(), ""
            claim = Claim(text, fals)
            kind = classify_falsifiability(claim)
            if kind == "unfalsifiable":
                # Unfalsifiable statements are mysteries, not knowledge (§5.4).
                self.journal.record(f"Unfalsifiable claim held as mystery: '{text}'")
                return (f"🌫️ '{text}' has no falsification condition — holding it in the "
                        f"Unknown Journal instead of the dependency tree. "
                        f"(Add one with: claim <text> :: <how it could be proven wrong>)")
            self.tree.add_claim("mentor_claims", claim)
            self.memory.add("mentor", f"Registered claim: {text}", tags=["claim"])
            return f"📌 Claim registered ({kind}): {claim}"
        # Hardware specific commands
        if c.startswith("check"):
            name = c.split()[-1] if len(c.split())>1 else "D1"
            geom, bin_str = self.check_component(name)
            if geom is None: return f"❌ Component {name} not found."
            rp = repurpose_class(geom["component_type"], geom["failure_mode"])
            bt = bridge_target(rp)
            drill = "quarantine" if self.encoder._thermal_runaway_quarantine(geom["temperature_c"], geom["current_a"]) else "pass"
            return (f"🔧 {name}: health {geom['health_score']:.2f}, mode {geom['failure_mode']}, "
                    f"temp {geom['temperature_c']:.1f}°C, curr {geom['current_a']:.4f}A\n"
                    f"   Repurpose: {rp} → bridge {bt}, drill {drill}\n"
                    f"   Binary: {bin_str}")
        if c == "degrade":
            self.degrade_hardware(0.2)
            return "⚡ Applied stress to all components."
        return self.chat(cmd)

# =========================================================================
# 6. MAIN MENTOR LOOP
# =========================================================================
if __name__ == "__main__":
    print("🌌 Unified Playground — Ari, hardware steward edition\n")
    print("Commands: experiment [N] | why <concept> | dream | unknowns | stillness")
    print("          claim <text> :: <falsification>")
    print("          skill extract/list/test/refactor")
    print("          check <component> | degrade (stress hardware)\n")
    agent = UnifiedAgent()
    agent.memory.add("agent", "I am Ari, ready to explore physics and steward this circuit.", tags=["start"])
    while True:
        try: user = input("You: ")
        except (EOFError, KeyboardInterrupt): break
        if user.lower() == "exit": break
        print(f"Ari: {agent.handle_mentor(user)}")
        print(f"     [self: {agent.self_desc}]\n")
    print("🌙 Playground rests. Hardware state preserved in memory.")
