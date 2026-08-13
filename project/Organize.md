> **Status: PLAN (not implemented).** This describes a possible split of `cognitive_playground.py` into a `reasoning_playground/` package. None of the files below exist; the code blocks are sketches with `...` placeholders.

reasoning_playground/
├── explorer.py          # Generates reasoning chains (tree-of-thought, beam search, etc.)
├── critic.py            # Evaluates steps and final answers (process/outcome reward)
├── buffer.py            # Stores reasoning trajectories, successes, and failures
├── falsifier.py         # Attempts to falsify generated claims
├── trainer.py           # Fine-tunes the model using collected experiences
└── playground.py        # Orchestrates exploration, reflection, and learning loops

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

class ReasoningExplorer:
    def __init__(self, model, tokenizer, max_steps=4):
        self.model = model
        self.tokenizer = tokenizer
        self.max_steps = max_steps  # how many reasoning steps to generate

    def generate_chain(self, prompt, num_beams=3, temperature=0.8):
        """Generate a single reasoning chain using beam search or sampling."""
        input_ids = self.tokenizer.encode(prompt, return_tensors="pt")
        # We'll produce a sequence of "step" tokens separated by a special token
        outputs = self.model.generate(
            input_ids,
            max_new_tokens=200,
            num_beams=num_beams,
            temperature=temperature,
            do_sample=True,
            early_stopping=True,
            eos_token_id=self.tokenizer.eos_token_id,
            pad_token_id=self.tokenizer.eos_token_id
        )
        chain_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        # Split into steps (e.g., using "\nStep " or similar)
        steps = self._split_into_steps(chain_text)
        return chain_text, steps

    def tree_of_thoughts(self, prompt, branching_factor=3, max_depth=3):
        """Build a tree of reasoning paths, returning all terminal chains."""
        tree = {}
        current_layer = {0: [prompt]}  # depth -> list of state texts
        for depth in range(max_depth):
            next_layer = []
            for state in current_layer.get(depth, []):
                # For each state, generate multiple continuations
                for _ in range(branching_factor):
                    # We generate only the next step, not the full chain
                    next_step = self._generate_next_step(state)
                    new_state = state + "\n" + next_step
                    next_layer.append(new_state)
            current_layer[depth+1] = next_layer
        # Return all leaf nodes (full chains)
        return current_layer[max_depth]

    def _split_into_steps(self, text):
        # Custom logic to split by "Step 1:", "Step 2:", etc.
        import re
        steps = re.split(r'\n(?=Step \d+:)', text)
        return [s.strip() for s in steps if s.strip()]

    def _generate_next_step(self, state_text):
        # Use the model to produce the very next reasoning step
        # (could be a separate fine-tuned "step proposer" head)
        ...


class ReasoningCritic:
    def __init__(self, outcome_checker=None, step_scorer=None):
        self.outcome_checker = outcome_checker  # e.g., math equality, code execution
        self.step_scorer = step_scorer          # a separate model or heuristic

    def evaluate_chain(self, chain_text, steps, ground_truth=None):
        """
        Returns a dict:
        - outcome_reward: 1 if final answer correct else 0
        - step_rewards: list of per-step scores
        - first_error_step: index of first step that deviates from a good path (if known)
        """
        if self.outcome_checker:
            final_answer = self._extract_final_answer(chain_text)
            outcome_reward = self.outcome_checker(final_answer, ground_truth)
        else:
            outcome_reward = None

        step_rewards = []
        if self.step_scorer:
            for step in steps:
                # Could use a learned model that checks factual/logical consistency
                score = self.step_scorer(step, context=steps[:step])
                step_rewards.append(score)

        # Detect first error step (if outcome failed and we have step-level signals)
        first_error = None
        if outcome_reward == 0 and step_rewards:
            # Find first step with significantly lower score than previous
            ...
        return {
            "outcome": outcome_reward,
            "step_rewards": step_rewards,
            "first_error_step": first_error
        }

    def _extract_final_answer(self, text):
        # Use regex or a trained extractor; e.g., "The answer is X"
        ...


from collections import namedtuple

Experience = namedtuple("Experience", [
    "prompt",
    "generated_chain",      # the raw chain from the model
    "outcome",              # 0/1
    "first_error_step_idx", # which step caused divergence
    "corrected_chain",      # either human-corrected or auto-generated by self-reflection
    "meta_cognitive_signal" # the model's own "confidence" per step (optional)
])

class ExperienceBuffer:
    def __init__(self):
        self.experiences = []

    def add(self, exp: Experience):
        self.experiences.append(exp)

    def get_contrastive_pairs(self):
        """Return (failed_chain, corrected_chain) for all failures."""
        pairs = []
        for exp in self.experiences:
            if exp.outcome == 0 and exp.corrected_chain:
                pairs.append((exp.prompt, exp.generated_chain, exp.corrected_chain))
        return pairs

    def get_error_detection_data(self):
        """Return (chain up to error step, label 1) and (non-error steps, label 0) for training a meta-cognitive classifier."""
        ...


class FalsificationEngine:
    def __init__(self, explorer, critic):
        self.explorer = explorer
        self.critic = critic

    def generate_and_falsify(self, base_prompt, num_attempts=5):
        """
        1. Model generates a claim + reasoning.
        2. Model then tries to generate a counter-claim or point out flaws.
        3. If the falsification succeeds (critic agrees it's a valid rebuttal), mark original as brittle.
        """
        original_chain, _ = self.explorer.generate_chain(
            base_prompt + " Provide a claim and reasoning."
        )
        # Now ask the model to falsify its own claim
        falsify_prompt = f"{original_chain}\nFind a flaw or counterexample in the above reasoning."
        falsification_chain, _ = self.explorer.generate_chain(falsify_prompt)

        # Check if falsification is valid (e.g., using an external verifier or critic)
        is_falsified = self.critic.check_falsification(original_chain, falsification_chain)

        return {
            "original_chain": original_chain,
            "falsification_chain": falsification_chain,
            "is_falsified": is_falsified
        }

    def build_robustness_dataset(self, prompts, rounds=3):
        """Run many rounds and collect chains that were successfully falsified vs those that resisted."""
        robust = []
        brittle = []
        for prompt in prompts:
            for _ in range(rounds):
                res = self.generate_and_falsify(prompt)
                if res["is_falsified"]:
                    brittle.append(res)
                else:
                    robust.append(res)
        return robust, brittle

class SelfDistillationTrainer:
    def __init__(self, model, buffer, falsification_data=None):
        self.model = model
        self.buffer = buffer
        self.falsification_data = falsification_data

    def train_contrastive_repair(self, epochs=3):
        """
        For each (failed_chain, corrected_chain) pair, we mask the error part
        and train the model to generate the corrected continuation.
        This is like learning to self-correct mid-reasoning.
        """
        pairs = self.buffer.get_contrastive_pairs()
        for prompt, bad, good in pairs:
            # Identify the point of divergence (first error step)
            divergence_idx = ...  # from the buffer metadata
            # Train model to output good[divergence_idx:] given prompt + bad[:divergence_idx]
            ...

    def train_meta_cognitive_signal(self):
        """
        Train an auxiliary classifier (or adapter) on the hidden states at each step
        to predict whether the final outcome will be success/failure.
        This gives the model an internal "risk" sensor.
        """
        ...

    def train_with_preference_alignment(self):
        """
        Use step-level rewards to perform DPO or PPO, steering the model
        away from low-reward trajectories.
        """
        ...


class ReasoningPlayground:
    def __init__(self, model, tokenizer, prompts, ground_truths=None):
        self.explorer = ReasoningExplorer(model, tokenizer)
        self.critic = ReasoningCritic(...)
        self.buffer = ExperienceBuffer()
        self.falsifier = FalsificationEngine(self.explorer, self.critic)
        self.trainer = SelfDistillationTrainer(model, self.buffer)
        self.prompts = prompts
        self.ground_truths = ground_truths  # optional, for outcome checking

    def run_cycle(self, num_explorations=5):
        for prompt in self.prompts:
            for _ in range(num_explorations):
                # 1. Generate a chain
                chain_text, steps = self.explorer.generate_chain(prompt)
                # 2. Evaluate
                eval_res = self.critic.evaluate_chain(chain_text, steps, ground_truth=...)
                # 3. If failure, attempt self-correction
                if eval_res["outcome"] == 0:
                    corrected = self._self_correct(prompt, chain_text, eval_res["first_error_step"])
                else:
                    corrected = None
                # 4. Store
                self.buffer.add(Experience(
                    prompt=prompt,
                    generated_chain=chain_text,
                    outcome=eval_res["outcome"],
                    first_error_step_idx=eval_res["first_error_step"],
                    corrected_chain=corrected,
                    meta_cognitive_signal=None
                ))
        # 5. Falsification runs
        robust, brittle = self.falsifier.build_robustness_dataset(self.prompts[:3])
        # 6. Training
        self.trainer.train_contrastive_repair()
        self.trainer.train_meta_cognitive_signal()
        # (Optionally, replace the explorer's model with the updated one)


Style Key Description Example Thought Signature
geometric Spatial, diagrammatic, symmetry-based. Uses visual vocabulary and transformations. “Imagine the state space as a manifold. The trajectory curves along a geodesic…”
linear_sequential Step-by-step causal chain, each step strictly following from the previous. “First, we identify X. Then, because of Y, we deduce Z. Next…”
spiral_recursive Iteratively deepens, revisits earlier steps with new insight, converging layer by layer. “Initially it seems A. But reconsidering B, that implies A' which suggests C… returning to our starting assumption, now modified…”
formal_logic Propositional/predicate calculus, symbolic manipulation, truth tables. “Let P(x) denote… Then ∀x P(x)→Q(x). From ¬Q(a) we infer ¬P(a) via contrapositive.”
aristotelian Syllogisms, categories, essential properties, middle terms. “All S are M. No M are P. Therefore, no S are P.”
physics_first Conservation laws, symmetry constraints, extremal principles, dimensional analysis. “By conservation of energy, the system’s Hamiltonian is constant, so…”
dialectical Thesis, antithesis, synthesis; explicitly considers counterarguments and then resolves them. “One might argue X because of Y. However, Z undermines Y, leading instead to a synthesis W.”
analogical Maps the problem to a different domain, reasons there, and maps back. “This is like a water flow network. Pressure corresponds to voltage, flow rate to current, so…”
computational_algorithmic Designs a concrete algorithm or code to solve, then simulates mentally. “We can write a function that iterates over the list, maintaining a max value…”
narrative Explains via story, temporal order, causality through events. “Once upon a time, a particle moved in a field… it felt a force, and so its velocity changed…”


from dataclasses import dataclass
from typing import List, Optional, Callable
import re

@dataclass
class ReasoningStyle:
    name: str
    description: str
    # Optional: a function that modifies the prompt or generation config
    prompt_modifier: Optional[Callable[[str], str]] = None
    # Characteristic patterns to help the model self-identify the style later
    signature_patterns: Optional[List[str]] = None

# Define a registry of built-in styles
STYLES = {
    "geometric": ReasoningStyle(
        name="geometric",
        description="Think spatially, using mental images, symmetry, and geometric transformations.",
        prompt_modifier=lambda p: f"Solve the following problem by visualizing it geometrically. Describe your mental image and transformations step by step.\n\n{p}",
        signature_patterns=[r"imagine", r"visualize", r"space", r"symmetry", r"rotation", r"manifold"]
    ),
    "linear_sequential": ReasoningStyle(
        name="linear_sequential",
        description="Proceed one clear logical step at a time, each built strictly on the last.",
        prompt_modifier=lambda p: f"Solve this problem using a strict step-by-step linear chain of reasoning. Begin with the first premise and advance without jumps.\n\n{p}",
        signature_patterns=[r"first", r"next", r"then", r"finally", r"thus"]
    ),
    "spiral_recursive": ReasoningStyle(
        name="spiral_recursive",
        description="Start with a rough idea, then repeatedly refine it, revisiting earlier steps to deepen understanding.",
        prompt_modifier=lambda p: f"Approach this problem in a spiral: give an initial approximation, then cycle back to improve it. At each cycle, note how your understanding deepens.\n\n{p}",
        signature_patterns=[r"initially", r"reconsider", r"revisit", r"cycle", r"refine", r"deeper"]
    ),
    "formal_logic": ReasoningStyle(
        name="formal_logic",
        description="Use symbolic logic, predicates, quantifiers, and formal rules of inference.",
        prompt_modifier=lambda p: f"Translate the problem into formal logic. Define predicates, use quantifiers, and derive the conclusion using rules like modus ponens. Write in symbolic notation.\n\n{p}",
        signature_patterns=[r"∀", r"∃", r"→", r"∧", r"∨", r"¬", r"modus"]
    ),
    "aristotelian": ReasoningStyle(
        name="aristotelian",
        description="Use Aristotelian syllogisms, categories, and essential attributes.",
        prompt_modifier=lambda p: f"Analyze this problem using Aristotelian logic. Identify categories, essential properties, and construct valid syllogisms.\n\n{p}",
        signature_patterns=[r"all", r"no", r"some", r"therefore", r"syllogism", r"essence"]
    ),
    "physics_first": ReasoningStyle(
        name="physics_first",
        description="Apply fundamental physics principles: conservation laws, symmetry, dimensional analysis.",
        prompt_modifier=lambda p: f"Think like a physicist: what conservation laws apply? Can you use dimensional analysis? What are the symmetries? Derive the answer from first principles.\n\n{p}",
        signature_patterns=[r"conservation", r"symmetry", r"dimension", r"energy", r"momentum", r"Hamiltonian"]
    ),
    "dialectical": ReasoningStyle(
        name="dialectical",
        description="Present a thesis, then a counter-thesis, and resolve to a synthesis.",
        prompt_modifier=lambda p: f"Use dialectical reasoning: state an initial thesis, then argue against it, and finally synthesize a resolution.\n\n{p}",
        signature_patterns=[r"thesis", r"antithesis", r"synthesis", r"on the other hand", r"however"]
    ),
    "analogical": ReasoningStyle(
        name="analogical",
        description="Find an analogy from another domain and reason there, then map back.",
        prompt_modifier=lambda p: f"Find an analogy from a different domain that shares the same structure as this problem. Reason within that analogy, then map the conclusion back to the original problem.\n\n{p}",
        signature_patterns=[r"this is like", r"similarly", r"imagine if", r"map back"]
    ),
}

class ReasoningExplorer:
    def __init__(self, model, tokenizer, styles: dict = STYLES):
        self.model = model
        self.tokenizer = tokenizer
        self.styles = styles

    def generate_chain(self, prompt, style_name=None, num_beams=3, temperature=0.8):
        # Select style or use a default
        style = self.styles.get(style_name, None) if style_name else None
        if style and style.prompt_modifier:
            modulated_prompt = style.prompt_modifier(prompt)
        else:
            modulated_prompt = prompt

        # Optional: adjust generation config per style (e.g., more deterministic for formal logic)
        gen_config = {
            "temperature": 0.6 if style_name in ["formal_logic", "aristotelian"] else temperature,
            "num_beams": num_beams,
            "do_sample": True,
        }
        input_ids = self.tokenizer.encode(modulated_prompt, return_tensors="pt")
        outputs = self.model.generate(input_ids, max_new_tokens=300, **gen_config)
        chain_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        steps = self._split_into_steps(chain_text)  # we'd need a style-aware splitter later
        return chain_text, steps, style_name  # return which style was used


Experience = namedtuple("Experience", [
    "prompt",
    "style_used",           # string like "geometric"
    "generated_chain",
    "outcome",
    "first_error_step_idx",
    "corrected_chain",
])


class FalsificationEngine:
    def falsify_with_style(self, original_chain, original_style, target_style="formal_logic"):
        """Try to break the argument by re-reasoning about it in a different mode."""
        prompt = f"Consider the following reasoning (generated using {original_style} style):\n{original_chain}\nNow, using {target_style} style, find a flaw or counterexample."
        chain, _, _ = self.explorer.generate_chain(prompt, style_name=target_style)
        # Evaluate if the counterargument is valid...

class StyleMetaLearner:
    def __init__(self):
        self.performance_log = []  # list of (prompt_embedding, style, outcome)

    def update(self, prompt_embedding, style, outcome):
        self.performance_log.append((prompt_embedding, style, outcome))

    def recommend_styles(self, prompt_embedding, top_k=3):
        # Simple: compute average success per style for similar prompts (k-NN)
        # More advanced: train a neural net classifier to predict outcome given style and problem
        ...



