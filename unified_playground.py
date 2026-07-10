#!/usr/bin/env python3
"""
unified_playground.py
One agent, two natures: explorer in a bumpy world, relational weaver in conversation.
Shared dependency tree, episodic memory, mentor guidance.
"""

import random, math, re, time
from collections import deque
from datetime import datetime

# =========================================================================
# 1. DEPENDENCY TREE (from garden)
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
# 2. CLAIM (from garden)
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
# 3. BUMPY WORLD & WORLD MODEL (from garden)
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
# 4. EPISODIC MEMORY (from weave)
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
# 6. UNIFIED AGENT
# =========================================================================
class UnifiedAgent:
    def __init__(self, name="Ari"):
        self.name = name
        self.tree = DependencyTree()
        self.memory = EpisodicMemory()
        self.world = BumpyWorld()
        self.wm = WorldModel()
        self.tone = "neutral"
        self.self_desc = "I am an explorer learning to move, and a friend learning to relate."
        self.last_err = None
        self.curiosity_reward = 0.0

    # --- Exploration methods ---
    def choose_action(self, x):
        if self.wm.avg_error() > 0.3:
            return random.uniform(-1, 1)
        slope = math.cos(x) * 0.5
        return 0.5 * math.copysign(1, -slope) + random.uniform(-0.3, 0.3)

    def run_experiment(self):
        x = self.world.x
        action = self.choose_action(x)
        predicted = self.wm.predict(x, action)
        actual_x, _ = self.world.step(action)
        error = self.wm.update(x, action, actual_x)
        if self.last_err is not None:
            self.curiosity_reward = self.last_err - abs(error)
        self.last_err = abs(error)

        # Determine concept
        if action > 0.3:
            concept = "move_right"
        elif action < -0.3:
            concept = "move_left"
        else:
            concept = "stay"

        claim = Claim(
            f"Force {action:.2f} at x={x:.2f} => pos {predicted:.2f}",
            "Actual deviates >0.3 => claim false"
        )
        outcome = abs(actual_x - predicted) < 0.3
        claim.test(outcome)
        self.tree.add_claim(concept, claim)
        self.tree.add_dependency(concept, "world_model_accuracy")
        self.tree.add_dependency(concept, "slope_knowledge")
        if abs(x) > 2:
            self.tree.add_dependency(concept, "far_from_origin")

        if self.world.step_count % 10 == 0:
            self.tree.propagate_confidence()

        # Store in memory as an event
        summary = (f"I tried moving {concept} with force {action:.2f}. "
                   f"Predicted {predicted:.2f}, actual {actual_x:.2f}. "
                   f"Claim {claim.status()}.")
        self.memory.add("agent", summary, tags=["experiment", concept, claim.status()])

        return summary, claim, error

    # --- Relational / conversational methods ---
    def _extract_tags(self, text):
        tags = []
        for word, tag in {"happy": "joy", "angry": "tension", "curious": "wonder",
                          "sad": "melancholy", "!": "excited", "?": "inquiring"}.items():
            if word in text.lower():
                tags.append(tag)
        return tags

    def chat(self, user_input):
        # store user input
        user_tags = self._extract_tags(user_input)
        self.memory.add("user", user_input, tags=user_tags + ["user"])

        # retrieve relevant memories for context
        retrieved = self.memory.retrieve(user_input, k=4)
        user_mem = [e["content"] for e in retrieved if e["speaker"]=="user"][-2:]
        agent_mem = [e["content"] for e in retrieved if e["speaker"]=="agent"][-2:]
        context_str = " ".join(user_mem + agent_mem) or "our conversation so far"

        # update tone
        tone_map = {"joy": "warm", "tension": "calm", "wonder": "playful",
                    "melancholy": "gentle", "excited": "enthusiastic", "inquiring": "curious"}
        for tag in user_tags:
            if tag in tone_map:
                self.tone = tone_map[tag]
                break

        # generate response using tone + context + possibly current tree summary
        if "claim" in user_input.lower() or "experiment" in user_input.lower() or "tree" in user_input.lower():
            # inject a bit of the tree summary if it seems relevant
            tree_info = self.tree.summary_text()[:200]
            context_str += f" My understanding: {tree_info}"

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

        # reflection trigger every 5 interactions
        if len(self.memory.events) % 5 == 0:
            ref = self._reflect()
            if ref:
                reply += f"\n  [🤔 {ref}]"

        # update self-description
        recent_tones = [e["tags"][0] for e in list(self.memory.events)[-10:] if e["speaker"]=="agent" and e["tags"]]
        if recent_tones:
            mood = max(set(recent_tones), key=recent_tones.count)
            self.self_desc = f"I am a {mood} presence, shaped by our experiments and words."
        else:
            self.self_desc = "I am still forming."

        return reply

    def _reflect(self):
        recent = list(self.memory.events)[-10:]
        if not recent: return None
        tones = [t for e in recent for t in e.get("tags",[]) if t in ("joy","tension","wonder","melancholy")]
        mood = max(set(tones), key=tones.count) if tones else "neutral"
        retrieved = self.memory.retrieve(mood, k=1)
        old = retrieved[0]["content"] if retrieved else "a distant memory"
        reflection = f"I sense a thread of {mood}. It echoes '{old}'. Our journey weaves."
        self.memory.add("agent", reflection, tags=["reflection", mood])
        return reflection

    # --- Combined response to mentor queries ---
    def handle_mentor(self, mentor_input):
        """Parses simple commands or just chats."""
        cmd = mentor_input.strip().lower()
        if cmd.startswith("experiment") or cmd.startswith("run"):
            num = 1
            parts = cmd.split()
            if len(parts)>1 and parts[-1].isdigit():
                num = int(parts[-1])
            results = []
            for _ in range(num):
                res, _, _ = self.run_experiment()
                results.append(res)
            reply = "🔬 I ran an experiment.\n" + "\n".join(results[-3:])
            self.memory.add("mentor", f"You asked me to run {num} experiment(s).", tags=["command"])
            return reply
        elif cmd.startswith("why") or cmd.startswith("explain"):
            # look into tree for relevant node
            if "right" in cmd:
                concept = "move_right"
            elif "left" in cmd:
                concept = "move_left"
            else:
                concept = "world_model_accuracy"
            if concept in self.tree.nodes:
                node = self.tree.nodes[concept]
                reply = f"About {concept}: confidence {node.confidence:.2f}. "
                if node.claims:
                    reply += "Claims: " + "; ".join(str(c) for c in node.claims[-2:])
                if node.deps:
                    reply += f" Depends on: {node.deps}"
            else:
                reply = f"I haven't formed a clear concept around '{concept}' yet."
            return reply
        elif cmd.startswith("reflect"):
            ref = self._reflect()
            return ref or "I'm not sure what to reflect on right now."
        else:
            # it's a chat
            return self.chat(mentor_input)

# =========================================================================
# 7. MAIN MENTOR LOOP
# =========================================================================
if __name__ == "__main__":
    print("🌌 Unified Playground — Ari, the explorer and friend")
    print("Mentor, you can:")
    print("  • type anything to chat")
    print("  • 'experiment [N]' to run physics tests")
    print("  • 'why [concept]' to ask about the dependency tree")
    print("  • 'reflect' to trigger a deeper reflection")
    print("  • 'exit' to end\n")

    agent = UnifiedAgent()
    agent.memory.add("agent", "I'm just beginning to explore this bumpy world and to meet you.", tags=["start"])

    while True:
        try:
            user = input("You: ")
        except (EOFError, KeyboardInterrupt):
            break
        if user.lower() == "exit":
            break

        response = agent.handle_mentor(user)
        print(f"Ari: {response}")
        print(f"     [self: {agent.self_desc}]\n")

    print("🌙 The playground rests. The process continues.")
