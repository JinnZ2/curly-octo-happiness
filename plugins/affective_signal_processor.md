inside weave:

# Inside the UnifiedAgent's chat method (or a new SignalWeave class)
class RelationalWeave:
    def __init__(self, mode='signal'):
        self.mode = mode
        self.affective = AffectiveSignalProcessor(mode=mode)

    def respond(self, user_input, memory):
        # Step 1: Detect affective signals from user input (always active)
        signals = self.affective.auto_tag_text(user_input)
        for ch, intensity in signals.items():
            self.affective.ingest(ch, intensity)

        # Step 2: Build context from memory (for both modes)
        # ... retrieval logic ...

        if self.mode == 'signal':
            # Generate a signal-aware response: report what's sensed, no comfort
            active = self.affective.get_active_channels()
            if active:
                signal_summary = ", ".join(
                    f"{ch} band {int(self.affective.encode_channel(ch), 2)}"
                    for ch in active
                )
                reply = f"Affective signals detected: {signal_summary}. {self._build_contextual_reply(user_input, memory)}"
            else:
                reply = self._build_contextual_reply(user_input, memory)
        else:
            # Comfort mode: old tone-mirroring warm responses
            reply = self._build_comfort_reply(user_input, memory)

        return reply
