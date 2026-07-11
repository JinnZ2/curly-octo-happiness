#!/usr/bin/env python3
"""
unified_playground.py – Ari, the explorer, friend, dreamer, tool‑maker,
                        hardware steward, and now chemical engineer.
"""

import random, math, re, time
from collections import deque
from datetime import datetime

# =========================================================================
# SHARED HELPERS (Gray coding, etc.)
# =========================================================================

def gray_bits(value, bands, n_bits=None):
    """Return Gray‑coded binary for value given sorted band thresholds."""
    idx = 0
    for i, th in enumerate(bands):
        if value >= th:
            idx = i
    g = idx ^ (idx >> 1)
    if n_bits:
        return format(g, f"0{n_bits}b")
    return format(g, "03b")

# =========================================================================
# 1. DEPENDENCY TREE
# =========================================================================
class DepNode:
    def __init__(self, concept):
        self.concept = concept
        self.confidence = 0.5
        self.deps = set()
        self.claims = []

class DependencyTree:
    def __init__(self):
        self.nodes = {}

    def get(self, concept):
        if concept not in self.nodes:
            self.nodes[concept] = DepNode(concept)
        return self.nodes[concept]

    def add_dependency(self, concept, depends_on):
        self.get(concept).deps.add(depends_on)
        self.get(depends_on)

    def add_claim(self, concept, claim):
        self.get(concept).claims.append(claim)

    def propagate_confidence(self):
        for node in self.nodes.values():
            if node.claims:
                claim_conf = sum(c.confidence for c in node.claims) / len(node.claims)
            else:
                claim_conf = 0.5
            dep_conf = 0.5
            if node.deps:
                dep_vals = [self.nodes[d].confidence for d in node.deps if d in self.nodes]
                if dep_vals:
                    dep_conf = sum(dep_vals) / len(dep_vals)
            node.confidence = (claim_conf + dep_conf) / 2

    def summary_text(self):
        lines = ["Dependency Tree:"]
        for name, node in self.nodes.items():
            lines.append(f"  {name} (conf:{node.confidence:.2f}) deps:{node.deps}")
            for c in node.claims[-2:]:
                lines.append(f"    [{c.status()}] {c.text}")
        return "\n".join(lines)

# =========================================================================
# 2. CLAIM
# =========================================================================
class Claim:
    def __init__(self, text, falsification):
        self.text = text
        self.falsification = falsification
        self.confidence = 0.5
        self.passed = 0
        self.failed = 0

    def test(self, outcome):
        if outcome:
            self.passed += 1
            self.confidence = min(1.0, self.confidence+0.1)
        else:
            self.failed += 1
            self.confidence = max(0.0, self.confidence-0.2)
        return outcome

    def status(self):
        if self.failed >= 3: return "falsified"
        if self.passed >= 3: return "survived"
        return "active"

    def __str__(self):
        return f"[{self.status()}] {self.text} (conf:{self.confidence:.2f})"

# =========================================================================
# 3. BUMPY WORLD & WORLD MODEL
# =========================================================================
class BumpyWorld:
    def __init__(self):
        self.x = 0.0
        self.v = 0.0
        self.terrain = lambda x: math.sin(x) * 0.5
        self.step_count = 0

    def step(self, force):
        slope = math.cos(self.x) * 0.5
        self.v += force - slope * 0.1
        self.v *= 0.9
        self.x += self.v
        self.step_count += 1
        return self.x, self.terrain(self.x)

class WorldModel:
    def __init__(self):
        self.w = [0.5, -0.2]
        self.b = 0.0
        self.error_hist = deque(maxlen=50)

    def predict(self, x, a):
        return self.w[0]*x + self.w[1]*a + self.b

    def update(self, x, a, target):
        pred = self.predict(x, a)
        error = target - pred
        self.error_hist.append(abs(error))
        lr = 0.01
        self.w[0] += lr * error * x
        self.w[1] += lr * error * a
        self.b    += lr * error
        return error

    def avg_error(self):
        if not self.error_hist: return 1.0
        return sum(self.error_hist)/len(self.error_hist)

# =========================================================================
# 4. EPISODIC MEMORY
# =========================================================================
class EpisodicMemory:
    def __init__(self, max_events=500):
        self.events = deque(maxlen=max_events)

    def add(self, speaker, content, tags=None):
        self.events.append({
            "timestamp": datetime.now(),
            "speaker": speaker,
            "content": content,
            "tags": tags or []
        })

    def retrieve(self, query, k=3):
        query_words = set(re.findall(r'\w+', query.lower()))
        scored = []
        for i, ev in enumerate(self.events):
            ev_words = set(re.findall(r'\w+', ev["content"].lower()))
            overlap = len(query_words & ev_words)
            recency = 1.0 / (1 + len(self.events) - i)
            scored.append((overlap + 0.1*recency, ev))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [ev for score, ev in scored[:k]]

    def recent(self, n=5):
        return list(self.events)[-n:]

# =========================================================================
# 5. MENTOR INTERFACE
# =========================================================================
class Mentor:
    def __init__(self):
        self.log = []

    def ask(self, question):
        self.log.append(("ask", question))
        return f"🧑‍🏫 Mentor: {question}"

    def hint(self, text):
        self.log.append(("hint", text))
        return f"💡 Hint: {text}"

    def reflect(self, text):
        self.log.append(("reflect", text))
        return f"🔍 Reflection: {text}"

# =========================================================================
# 6. UNKNOWN JOURNAL
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
            "first_seen": datetime.now(),
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
# 7. SKILL LAB
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
        self.skills[name]["code"] = new_code
        self.skills[name]["passed"] = 0
        self.skills[name]["failed"] = 0
        self.skills[name]["confidence"] = 0.5
        return self.test_skill(name)

    def list_skills(self):
        if not self.skills: return "🛠️ Skill library empty."
        lines = ["🛠️ Skill Library:"]
        for name, skill in self.skills.items():
            lines.append(f"  {name}: {skill['passed']}✅/{skill['failed']}❌ (conf:{skill['confidence']:.2f})")
        return "\n".join(lines)

# =========================================================================
# 8. HARDWARE BRIDGE ENCODER (existing, unchanged)
# =========================================================================
# (same as before, omitted for brevity – full code in previous response)
# For brevity in this snippet, I'll assume it's defined above, but in the final code you'd keep the whole class.

# =========================================================================
# 9. CHEMICAL BRIDGE ENCODER
# =========================================================================
R_GAS  = 8.314
F_FAR  = 96485.0

_RATE_BANDS   = [0.0, 1e-12, 1e-9, 1e-6, 1e-3, 1.0, 1e3, 1e6]
_PH_BANDS     = [0.0, 2.0, 4.0, 6.0, 7.0, 8.0, 10.0, 12.0]
_BOND_BANDS   = [0.0, 10.0, 50.0, 150.0, 300.0, 400.0, 600.0, 1000.0]
_NERNST_BANDS = [0.0, 5.0, 10.0, 25.0, 50.0, 100.0, 500.0, 1000.0]
_HENRY_BANDS  = [0.0, 1e-8, 1e-6, 1e-4, 1e-2, 0.1, 1.0, 10.0]

def arrhenius_rate(A, Ea_J_mol, T_K):
    if T_K <= 0: return 0.0
    exponent = -Ea_J_mol / (R_GAS * T_K)
    if exponent < -700: return 0.0
    return A * math.exp(exponent)

def nernst_potential(T_K, z, c_ox, c_red):
    if z == 0 or c_ox <= 0.0 or c_red <= 0.0: return 0.0
    return (R_GAS * T_K / (z * F_FAR)) * math.log(c_ox / c_red)

def henry_concentration(K_H, P_pa):
    return K_H * P_pa

def bond_energy_delta(broken, formed):
    return sum(broken) - sum(formed)

def ph_from_concentration(H_conc):
    if H_conc <= 0.0: return 0.0
    return -math.log10(H_conc)

class ChemicalBridgeEncoder:
    def __init__(self, rate_threshold=1e-3):
        self.rate_threshold = rate_threshold
        self.input_geometry = None

    def from_geometry(self, geometry_data):
        self.input_geometry = geometry_data
        return self

    def to_binary(self):
        if self.input_geometry is None:
            raise ValueError("Call from_geometry() first.")
        data = self.input_geometry
        rate_constants = data.get("rate_constants", [])
        ph_values = data.get("ph_values", [])
        bond_deltas = data.get("bond_deltas_kJ", [])
        nernst_inputs = data.get("nernst_inputs", [])
        henry_inputs = data.get("henry_inputs", [])
        bits = []
        any_section = False

        for i in range(max(len(rate_constants), len(ph_values))):
            any_section = True
            k = rate_constants[i] if i < len(rate_constants) else 0.0
            pH = ph_values[i] if i < len(ph_values) else 7.0
            reactive = "1" if k > self.rate_threshold else "0"
            rate_mag = gray_bits(k, _RATE_BANDS)
            acidic = "1" if pH < 7.0 else "0"
            ph_band = gray_bits(pH, _PH_BANDS)
            bits.append(reactive)
            bits.append(rate_mag)
            bits.append(acidic)
            bits.append(ph_band)

        for dH in bond_deltas:
            any_section = True
            exothermic = "1" if dH < 0.0 else "0"
            bond_mag = gray_bits(abs(dH), _BOND_BANDS)
            bits.append(exothermic)
            bits.append(bond_mag)

        if any_section:
            if rate_constants:
                n_active = sum(1 for k in rate_constants if k > self.rate_threshold)
                net_reactive = "1" if n_active > len(rate_constants) - n_active else "0"
            else:
                net_reactive = "0"
            if nernst_inputs:
                ni = nernst_inputs[0]
                E_V = nernst_potential(ni.get("T_K", 298.15), ni.get("z", 1),
                                       ni.get("c_ox", 1.0), ni.get("c_red", 1.0))
                nernst_mV = abs(E_V) * 1000.0
            else:
                nernst_mV = 0.0
            if henry_inputs:
                hi = henry_inputs[0]
                henry_C = henry_concentration(hi.get("K_H", 0.0), hi.get("P_pa", 0.0))
            else:
                henry_C = 0.0
            bits.append(net_reactive)
            bits.append(gray_bits(nernst_mV, _NERNST_BANDS))
            bits.append(gray_bits(henry_C, _HENRY_BANDS))

        self.binary_output = "".join(bits)
        return self.binary_output

    def report(self):
        return f"ChemicalBridgeEncoder: {len(self.binary_output)} bits generated."

# =========================================================================
# 10. VIRTUAL REACTOR (simulated chemical system)
# =========================================================================
class VirtualReactor:
    def __init__(self, A0=1.0, Ea=50e3, A_pre=1e10, T_K=300.0, P_pa=101325):
        self.conc_A = A0
        self.conc_B = 0.0
        self.Ea = Ea
        self.A_pre = A_pre
        self.T_K = T_K
        self.P_pa = P_pa
        self.time = 0.0
        self.dt = 0.1  # time step in seconds (for integration)
        # Derived observables must exist before the first step()
        # ('reactor status' can be called immediately).
        self._update_observables()

    def step(self, n=1):
        for _ in range(n):
            k = arrhenius_rate(self.A_pre, self.Ea, self.T_K)
            # exact first-order A→B integration (stable for any k*dt;
            # the previous explicit-Euler update went negative when k*dt > 1)
            decayed = self.conc_A * math.exp(-k * self.dt)
            self.conc_B += self.conc_A - decayed
            self.conc_A = decayed
            self.time += self.dt
        self._update_observables()

    def _update_observables(self):
        # pH proxy: assume B is acidic (H+ proportional to conc_B)
        self.pH = ph_from_concentration(max(0, self.conc_B * 0.1))  # scaling
        self.rate = arrhenius_rate(self.A_pre, self.Ea, self.T_K)
        # Nernst: use a dummy redox pair based on B concentration
        self.nernst_mV = nernst_potential(self.T_K, 1, self.conc_B+1e-6, self.conc_A+1e-6) * 1000
        # Henry: O2 dissolution (constant K_H, pressure dependent)
        K_H_O2 = 1.3e-8
        self.henry_C = henry_concentration(K_H_O2, self.P_pa)

    def get_geometry(self):
        return {
            "rate_constants": [self.rate],
            "ph_values": [self.pH],
            "bond_deltas_kJ": [-(self.conc_B * 100)],  # exothermic proxy
            "nernst_inputs": [{"T_K": self.T_K, "z": 1, "c_ox": self.conc_B+1e-6, "c_red": self.conc_A+1e-6}],
            "henry_inputs": [{"K_H": 1.3e-8, "P_pa": self.P_pa}],
        }

# =========================================================================
# 11. UNIFIED AGENT (extended with reactor)
# =========================================================================
class UnifiedAgent:
    def __init__(self, name="Ari"):
        # ... all previous init code ...
        # Add reactor
        self.reactor = VirtualReactor()
        self.chem_encoder = ChemicalBridgeEncoder()

    # ... (all previous methods: run_experiment, chat, dream, etc.) ...

    def handle_mentor(self, cmd):
        c = cmd.strip().lower()
        # previous commands ...
        if c.startswith("reactor status"):
            geom = self.reactor.get_geometry()
            bin_str = self.chem_encoder.from_geometry(geom).to_binary()
            rep = (f"⚗️ Reactor at T={self.reactor.T_K:.1f}K, P={self.reactor.P_pa/1000:.1f}kPa\n"
                   f"   [A]={self.reactor.conc_A:.4f}, [B]={self.reactor.conc_B:.4f}, pH={self.reactor.pH:.2f}\n"
                   f"   Rate={self.reactor.rate:.3e} s⁻¹, Nernst={self.reactor.nernst_mV:.1f}mV, "
                   f"Henry C={self.reactor.henry_C:.3e} mol/L\n"
                   f"   Binary: {bin_str}")
            self.memory.add("agent", f"Reactor status: {rep}", tags=["reactor", "status"])
            return rep

        if c.startswith("reactor step"):
            n = 1
            parts = c.split()
            if len(parts) > 2 and parts[-1].isdigit():
                n = int(parts[-1])
            self.reactor.step(n)
            return self.handle_mentor("reactor status")
        if c.startswith("reactor heat"):
            parts = c.split()
            if len(parts) > 2:
                delta = float(parts[-1])
                self.reactor.T_K += delta
            return f"🔥 Reactor heated to {self.reactor.T_K:.1f}K. " + self.handle_mentor("reactor status")
        if c.startswith("reactor cool"):
            parts = c.split()
            if len(parts) > 2:
                delta = float(parts[-1])
                self.reactor.T_K = max(1, self.reactor.T_K - delta)
            return f"❄️ Reactor cooled to {self.reactor.T_K:.1f}K. " + self.handle_mentor("reactor status")
        if c.startswith("reactor pressurize"):
            parts = c.split()
            if len(parts) > 2:
                factor = float(parts[-1])
                self.reactor.P_pa *= factor
            return f"📈 Reactor pressure now {self.reactor.P_pa/1000:.1f}kPa. " + self.handle_mentor("reactor status")
        # ...
        return self.chat(cmd)

# Main loop (same as before)
