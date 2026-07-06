#!/usr/bin/env python3
"""Skill Lab – an agent that writes, tests, and refactors its own tools."""
import ast, textwrap, sys, io
from shared import DependencyTree

class SkillLab:
    def __init__(self, tree: DependencyTree):
        self.skills = {}      # name -> (code, tests)
        self.tree = tree

    def propose_skill(self, name: str, code: str, test_code: str):
        """Write a small function and its test."""
        self.skills[name] = {"code": code, "test": test_code, "passed": 0, "failed": 0}
        self.tree.add_node(name)
        self._run_tests(name)

    def _run_tests(self, name: str):
        skill = self.skills[name]
        try:
            exec(skill["code"], globals())
            exec(skill["test"], globals())
            skill["passed"] += 1
            print(f"✅ {name} passed tests.")
            self.tree.nodes[name].confidence = 0.9
        except Exception as e:
            skill["failed"] += 1
            print(f"❌ {name} failed: {e}")
            self.tree.nodes[name].confidence = 0.3

    def refactor(self, name: str, new_code: str):
        if name in self.skills:
            self.skills[name]["code"] = new_code
            self._run_tests(name)
        else:
            print("Skill not found.")

    def summary(self):
        for name, skill in self.skills.items():
            print(f"{name}: {skill['passed']} passes, {skill['failed']} fails")

if __name__ == "__main__":
    tree = DependencyTree()
    lab = SkillLab(tree)
    lab.propose_skill(
        "add_two",
        "def add_two(x): return x+2",
        "assert add_two(3) == 5, 'Should be 5'"
    )
    lab.propose_skill(
        "multiply_three",
        "def multiply_three(x): return x*3",
        "assert multiply_three(3) == 9"
    )
    lab.refactor("add_two", "def add_two(x): return x+3")
    lab.summary()
    print(tree.summary())
