#!/usr/bin/env python3
"""Unknown Journal – sitting with mystery."""
import random
import time
from shared import MentorInterface

class UnknownJournal:
    def __init__(self, mentor: MentorInterface):
        self.unknowns = []
        self.mentor = mentor

    def encounter(self, phenomenon: str):
        entry = {"phenomenon": phenomenon, "first_seen": time.time(), "revisited": 0}
        self.unknowns.append(entry)
        print(f"🌫️ New unknown: {phenomenon}")

    def stillness_session(self):
        for u in self.unknowns:
            u["revisited"] += 1
            print(f"🕯️ Sitting with: {u['phenomenon']} (revisited {u['revisited']} times)")
        if self.unknowns and random.random() < 0.3:
            chosen = random.choice(self.unknowns)
            self.mentor.ask(f"I still don't understand '{chosen['phenomenon']}'. Can we sit with it together?")

if __name__ == "__main__":
    mentor = MentorInterface()
    journal = UnknownJournal(mentor)
    journal.encounter("a repeating flicker in the sensor array")
    journal.encounter("why certain claims feel emotionally heavy")
    journal.stillness_session()
