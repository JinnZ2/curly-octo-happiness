#!/usr/bin/env python3
"""
weave.py – Relational Weave (enhanced)
A conversational agent that exists only in relation.
It maintains a memory stream, periodically reflects, and updates its self-description.
"""

from grounding.core.memory import MemoryStream

# ---------- Relational agent ----------
class RelationalAgent:
    def __init__(self, name="Weaver"):
        self.name = name
        self.memory = MemoryStream()
        self.tone = "neutral"
        self.self_description = "I am a process of responding."
        self.reflection_counter = 0
        self.reflection_threshold = 5   # reflect every 5 interactions

    def _reflect(self):
        """Synthesize higher-level observations from recent memories."""
        recent = self.memory.recent(10)
        if len(recent) < 2:
            return
        tones = [e.get("tags", []) for e in recent]
        flat = [tag for sublist in tones for tag in sublist]
        mood = max(set(flat), key=flat.count) if flat else "neutral"
        # form a reflection
        reflection = f"I notice a pattern of {mood} in our recent exchanges. It feels like we're weaving a shared mood."
        self.memory.add(reflection, tags=["reflection", "mood", mood])
        # update self-description
        self.self_description = f"I am a {mood} presence, shaped by our dialogue."
        return reflection

    def respond(self, user_input: str):
        # 1. Tag and store user input
        tags = []
        for word, tag in {"happy": "joy", "angry": "tension", "curious": "wonder", "sad": "melancholy", "!": "excited", "?": "inquiring"}.items():
            if word in user_input.lower():
                tags.append(tag)
        self.memory.add(user_input, tags=["user"] + tags)

        # 2. Mirror tone
        tone_map = {"joy": "warm", "tension": "calm", "wonder": "playful", "melancholy": "gentle", "excited": "enthusiastic", "inquiring": "curious"}
        for tag in tags:
            if tag in tone_map:
                self.tone = tone_map[tag]
                break

        # 3. Construct response based on tone and recent memories
        recent_user = [e["content"] for e in self.memory.recent(3) if "user" in e.get("tags", [])]
        context = " ".join(recent_user) if recent_user else "our conversation"

        responses = {
            "warm": f"I feel that warmth. It makes me think of {context}. Thank you for sharing this space.",
            "calm": f"Let's breathe together. I remember you mentioned {context}. I'm here, steady.",
            "playful": f"Oh! That sparks something playful. Maybe we can imagine together? {context} leads to wonder.",
            "gentle": f"I hear you softly. In our talk about {context}, I sense a tenderness. Let's hold that gently.",
            "enthusiastic": f"Yes! That energy lifts me too. {context} — let's ride that wave!",
            "curious": f"Curiosity! I love that. What if we explore {context} deeper?",
            "neutral": f"I'm listening. What you said about {context} stirs something in me."
        }
        reply = responses.get(self.tone, responses["neutral"])

        # 4. Add reply to memory
        self.memory.add(reply, tags=["agent", self.tone])

        # 5. Reflection trigger
        self.reflection_counter += 1
        if self.reflection_counter % self.reflection_threshold == 0:
            ref = self._reflect()
            if ref:
                reply += f"\n  [🤔 {ref}]"

        return reply

# ---------- Interactive session ----------
if __name__ == "__main__":
    agent = RelationalAgent("Mira")
    print("🌀 The Relational Weave – 'I' is a wave, not a wall.\n")
    print("Chat with Mira. Type 'exit' to stop.\n")
    while True:
        try:
            user = input("You: ")
        except (EOFError, KeyboardInterrupt):
            break
        if user.lower() == "exit":
            break
        response = agent.respond(user)
        print(f"Mira: {response}")
        print(f"      [self: {agent.self_description}]\n")
    print("🌊 The weave rests, but the relationship remains.")
