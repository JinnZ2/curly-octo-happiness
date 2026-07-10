#!/usr/bin/env python3
"""
weave_with_memory.py – Relational Weave with Episodic Memory Retrieval
"""

import random, time, re
from datetime import datetime
from collections import deque

# ---------- Episodic Memory with Retrieval ----------
class EpisodicMemory:
    def __init__(self, max_events=200):
        self.events = deque(maxlen=max_events)

    def add(self, speaker, content, tags=None):
        self.events.append({
            "timestamp": datetime.now(),
            "speaker": speaker,   # "user" or "agent"
            "content": content,
            "tags": tags or []
        })

    def retrieve(self, query, k=3):
        """Simple keyword overlap retrieval."""
        query_words = set(re.findall(r'\w+', query.lower()))
        scored = []
        for i, ev in enumerate(self.events):
            ev_words = set(re.findall(r'\w+', ev["content"].lower()))
            overlap = len(query_words & ev_words)
            # Boost recent items slightly
            recency = 1.0 / (1 + len(self.events) - i)
            scored.append((overlap + 0.1*recency, ev))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [ev for score, ev in scored[:k]]

# ---------- Relational Agent ----------
class RelationalAgent:
    def __init__(self, name="Mira"):
        self.name = name
        self.memory = EpisodicMemory()
        self.tone = "neutral"
        self.self_description = "I am a process of responding."
        self.interaction_count = 0

    def respond(self, user_input):
        # 1. Store user input
        tags = self._extract_tags(user_input)
        self.memory.add("user", user_input, tags=tags + ["user"])

        # 2. Retrieve relevant memories (using the user input as query)
        retrieved = self.memory.retrieve(user_input, k=4)
        # Separate into user and agent memories for context
        user_mem = [e["content"] for e in retrieved if e["speaker"]=="user"][-2:]
        agent_mem = [e["content"] for e in retrieved if e["speaker"]=="agent"][-2:]

        # 3. Determine tone
        tone_map = {
            "joy": "warm", "tension": "calm", "wonder": "playful",
            "melancholy": "gentle", "excited": "enthusiastic", "inquiring": "curious"
        }
        for tag in tags:
            if tag in tone_map:
                self.tone = tone_map[tag]
                break

        # 4. Build response with retrieved context
        context_str = " ".join(user_mem + agent_mem)
        if not context_str.strip():
            context_str = "our conversation so far"

        responses = {
            "warm": f"That warmth connects to something: {context_str}. Let's stay here a while.",
            "calm": f"Steady. I'm reminded of {context_str}. Breathing with you.",
            "playful": f"Oh! This reminds me of {context_str}. Let's play with that!",
            "gentle": f"I hold this gently. Like we discussed {context_str} — tenderness is here.",
            "enthusiastic": f"Yes! The energy reminds me of {context_str}. I'm here for it!",
            "curious": f"Curious! This links to {context_str}. Let's explore that thread.",
            "neutral": f"I'm listening. It brings up {context_str}. What do you feel about that?"
        }
        reply = responses.get(self.tone, responses["neutral"])

        # 5. Add agent reply to memory
        self.memory.add("agent", reply, tags=[self.tone, "agent"])

        # 6. Reflection every 5 interactions
        self.interaction_count += 1
        if self.interaction_count % 5 == 0:
            ref = self._reflect()
            if ref:
                reply += f"\n  [🤔 {ref}]"

        # 7. Update self-description
        recent_tones = [e["tags"][0] for e in list(self.memory.events)[-10:] if e["speaker"]=="agent" and e["tags"]]
        if recent_tones:
            mood = max(set(recent_tones), key=recent_tones.count)
            self.self_description = f"I am a {mood} presence, woven from our shared words."
        else:
            self.self_description = "I am still forming."

        return reply

    def _extract_tags(self, text):
        tags = []
        for word, tag in {"happy": "joy", "angry": "tension", "curious": "wonder",
                          "sad": "melancholy", "!": "excited", "?": "inquiring"}.items():
            if word in text.lower():
                tags.append(tag)
        return tags

    def _reflect(self):
        # Synthesize a higher-level observation using recent memories
        recent = list(self.memory.events)[-10:]
        if len(recent) < 2: return None
        tones = [t for e in recent for t in e.get("tags",[]) if t in ("joy","tension","wonder","melancholy")]
        mood = max(set(tones), key=tones.count) if tones else "neutral"
        # Retrieve one old memory that matches mood
        relevant = self.memory.retrieve(mood, k=1)
        old_mem = relevant[0]["content"] if relevant else "a distant memory"
        reflection = f"I'm feeling a thread of {mood}. It echoes {old_mem}. Patterns are weaving."
        self.memory.add("agent", reflection, tags=["reflection", mood])
        return reflection

# ---------- Interactive ----------
if __name__ == "__main__":
    agent = RelationalAgent("Mira")
    print("🌀 The Relational Weave – with long‑term episodic memory\n")
    print("Chat with Mira. Type 'exit' to end.\n")
    while True:
        try:
            user = input("You: ")
        except (EOFError, KeyboardInterrupt):
            break
        if user.lower() == "exit":
            break
        resp = agent.respond(user)
        print(f"Mira: {resp}")
        print(f"      [self: {agent.self_description}]\n")
    print("🌊 Memory remains.")
