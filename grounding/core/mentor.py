"""Mentor interfaces.

Mentor          — returns formatted strings (unified_playground line).
MentorInterface — prints directly (shared.py / playground4-8 line).
Both keep a (kind, text) log.
"""


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


class MentorInterface:
    def __init__(self):
        self.log = []

    def ask(self, question: str):
        self.log.append(("ask", question))
        print(f"🧑‍🏫 Mentor asks: {question}")

    def hint(self, hint: str):
        self.log.append(("hint", hint))
        print(f"💡 Hint: {hint}")

    def reflect(self, observation: str):
        self.log.append(("reflect", observation))
        print(f"🔍 Mentor reflects: {observation}")
