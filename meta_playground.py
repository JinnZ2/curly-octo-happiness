#!/usr/bin/env python3
"""meta_playground.py – The full ecosystem in a daily cycle."""

import random, time
from shared import DependencyTree, SharedMemory, MentorInterface

# Import all playground modules
# (playgrounds 1-3 and 7 live in files that predate the playgroundN_* naming)
from claim_falsification_garden import CuriosityAgent, MiniWorld
from relational_weave import RelationalAgent
from initiation_loop import InitiatingAgent
from playground4_distributed import DistributedAgent
from playground5_dream import Dreamer
from playground6_unknown import UnknownJournal
import self_modeling_explorer
from playground8_skill_lab import SkillLab

# Quick wrappers for those that don't already have a run function
def run_garden_cycle(tree, mem, mentor):
    # simplified garden step
    agent = CuriosityAgent("GardenAgent")
    world = MiniWorld()
    claim = agent.make_claim("moving right is safe", "if I hit a wall, it's false")
    outcome = world.move("right")
    agent.test_claim(claim, outcome)
    tree.add_claim("movement_right_safety", claim)
    mem.add({"playground": "garden", "claim": claim.text, "outcome": outcome})
    print(f"🌱 Garden: {claim}")

def run_weave_interaction(tree, mem, mentor):
    # quick relational weave snippet
    agent = RelationalAgent()
    response = agent.respond("I'm feeling curious today.")
    mem.add({"playground": "weave", "response": response, "tone": agent.state['tone']})
    print(f"🌀 Weave: {response}")

def run_initiation_phase(tree, mem, mentor):
    agent = InitiatingAgent()
    agent.observe("the world is bumpy")
    wonder = agent.initiate()
    mem.add({"playground": "initiation", "wonder": wonder})
    print(f"🌌 Initiation: {wonder}")

def run_self_model_step(tree, mem):
    # short burst of the self-modeling explorer (playground 7)
    final_x, self_err, _ = self_modeling_explorer.run(steps=20)
    mem.add({"playground": "self_model", "final_pos": final_x, "self_error": self_err})
    print(f"🌀 Self-model: 20 steps, final pos {final_x:.2f}, self-err {self_err:.3f}")

# Main daily loop
if __name__ == "__main__":
    tree = DependencyTree()
    mem = SharedMemory()
    mentor = MentorInterface()
    dreamer = Dreamer(mem)
    journal = UnknownJournal(mentor)
    lab = SkillLab(tree)

    print("🌅 A new day in the AI Playground Ecosystem.\n")

    # Morning exploration
    run_garden_cycle(tree, mem, mentor)
    run_self_model_step(tree, mem)   # from playground7, add a step
    run_initiation_phase(tree, mem, mentor)

    # Midday relationship weaving
    run_weave_interaction(tree, mem, mentor)
    dist_agent = DistributedAgent(tree, mem)
    dist_agent.trace_action("combined_exploration")

    # Afternoon skill building
    lab.propose_skill("increment", "def increment(x): return x+1", "assert increment(3)==4")
    mem.add({"playground": "skill_lab", "skill": "increment", "status": "passed"})

    # Evening stillness and unknowns
    journal.encounter("why the agent's confidence sometimes drops without a clear reason")
    journal.stillness_session()

    # Night: dream and calibrate
    print("\n🌜 Night falls. The system dreams...")
    for _ in range(2):
        print(dreamer.sleep())
    tree.recalibrate()
    print(tree.summary())

    print("\n🌄 The day ends. The playground rests, but the process continues.")
