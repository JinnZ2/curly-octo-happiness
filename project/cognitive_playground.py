"""
Cognitive Playground: A self-exploration framework for language models.
The model experiments with multiple reasoning styles and computation substrates,
learns from its own failures, detects meta-cognitive signals, and improves
through self-distillation without teacher traces.
"""

import torch
import torch.nn as nn
from transformers import AutoModelForCausalLM, AutoTokenizer
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any, Tuple
import re
import numpy as np
from collections import defaultdict
from sklearn.neighbors import NearestNeighbors  # for meta-learner

# ----------------------------------------------------------------------
# 1. COMPUTATION SUBSTRATES
# ----------------------------------------------------------------------
@dataclass
class ComputationSubstrate:
    name: str
    description: str
    prompt_modifier: Callable[[str], str]
    # Helps the model adopt a specific “processing mode”
    # e.g., binary: think in true/false, ternary: true/false/unknown
    signature_patterns: List[str] = field(default_factory=list)

SUBSTRATES = {
    "binary": ComputationSubstrate(
        name="binary",
        description="Classical two-valued logic: True/False, 1/0.",
        prompt_modifier=lambda p: (
            f"Process the following using strict binary logic. Represent all statements "
            f"as either true (1) or false (0). Use logic gates, truth tables, and Boolean algebra.\n\n{p}"
        ),
        signature_patterns=[r"0", r"1", r"true", r"false", r"AND", r"OR", r"NOT"]
    ),
    "ternary": ComputationSubstrate(
        name="ternary",
        description="Three-valued logic: True, False, Unknown/Undefined.",
        prompt_modifier=lambda p: (
            f"Use three-valued logic (True, False, Unknown). Where information is missing, "
            f"explicitly use 'Unknown'. Build truth tables with three values.\n\n{p}"
        ),
        signature_patterns=[r"unknown", r"true", r"false", r"maybe"]
    ),
    "fuzzy": ComputationSubstrate(
        name="fuzzy",
        description="Fuzzy logic with continuous truth values between 0 and 1.",
        prompt_modifier=lambda p: (
            f"Apply fuzzy logic. Assign degrees of truth between 0 and 1 to each claim. "
            f"Use operators like min, max, and probabilistic OR.\n\n{p}"
        ),
        signature_patterns=[r"degree", r"0\.\d+", r"membership", r"fuzzy"]
    ),
    "neural": ComputationSubstrate(
        name="neural",
        description="Imitate a neural network: weighted sums, activation functions, layer-wise processing.",
        prompt_modifier=lambda p: (
            f"Think as if you are a neural network. Represent inputs as vectors, apply weights, "
            f"use activation functions (ReLU, sigmoid), and propagate through layers. "
            f"Give numerical confidence scores.\n\n{p}"
        ),
        signature_patterns=[r"weight", r"bias", r"activation", r"sigmoid", r"layer"]
    ),
    "analog": ComputationSubstrate(
        name="analog",
        description="Continuous physical analogy: fluid flow, electrical circuits, mechanical systems.",
        prompt_modifier=lambda p: (
            f"Reason using an analog physical system. Map the problem to a continuous system "
            f"(e.g., water flow, heat transfer) and use differential intuition.\n\n{p}"
        ),
        signature_patterns=[r"flow", r"pressure", r"current", r"resistance", r"gradient"]
    ),
    "geometric_symbolic": ComputationSubstrate(
        name="geometric_symbolic",
        description="Geometric algebra and spatial transformations, then convert to symbolic form.",
        prompt_modifier=lambda p: (
            f"First visualize the problem geometrically, using coordinates, rotations, and projections. "
            f"Then translate that geometric insight into a formal algebraic or logical expression.\n\n{p}"
        ),
        signature_patterns=[r"coordinate", r"vector", r"rotation", r"project", r"transform"]
    ),
    "quantum_inspired": ComputationSubstrate(
        name="quantum_inspired",
        description="Probabilistic superposition, entanglement analogies, and measurement collapse.",
        prompt_modifier=lambda p: (
            f"Think in terms of quantum-like superposition: states are probability amplitudes, "
            f"and a 'measurement' collapses to an outcome. Use interference and entanglement metaphors.\n\n{p}"
        ),
        signature_patterns=[r"amplitude", r"superposition", r"collapse", r"entangle"]
    ),
}

# ----------------------------------------------------------------------
# 2. REASONING STYLES
# ----------------------------------------------------------------------
@dataclass
class ReasoningStyle:
    name: str
    description: str
    prompt_modifier: Callable[[str], str]
    signature_patterns: List[str] = field(default_factory=list)

STYLES = {
    "geometric": ReasoningStyle(
        name="geometric",
        description="Spatial, diagrammatic reasoning using mental images and symmetries.",
        prompt_modifier=lambda p: f"Solve by visualizing geometry. Describe your mental image and transformations step by step.\n\n{p}",
        signature_patterns=[r"imagine", r"visualize", r"symmetry", r"rotation", r"manifold"]
    ),
    "linear_sequential": ReasoningStyle(
        name="linear_sequential",
        description="Strict step-by-step linear chain of inference.",
        prompt_modifier=lambda p: f"Proceed one clear logical step at a time, each built strictly on the last. Number your steps.\n\n{p}",
        signature_patterns=[r"Step \d+", r"first", r"next", r"then", r"thus"]
    ),
    "spiral_recursive": ReasoningStyle(
        name="spiral_recursive",
        description="Iterative deepening, revisiting earlier steps with new insight.",
        prompt_modifier=lambda p: f"Start with a rough idea, then cycle back to refine. Show how understanding deepens each cycle.\n\n{p}",
        signature_patterns=[r"initially", r"reconsider", r"cycle", r"refine", r"deeper"]
    ),
    "formal_logic": ReasoningStyle(
        name="formal_logic",
        description="Symbolic logic with predicates and formal inference rules.",
        prompt_modifier=lambda p: f"Translate into formal logic. Use quantifiers and derive via modus ponens etc.\n\n{p}",
        signature_patterns=[r"∀", r"∃", r"→", r"∧", r"∨", r"¬", r"modus"]
    ),
    "aristotelian": ReasoningStyle(
        name="aristotelian",
        description="Syllogisms, categories, essential attributes.",
        prompt_modifier=lambda p: f"Analyze using Aristotelian syllogisms. Identify categories and essential properties.\n\n{p}",
        signature_patterns=[r"all", r"no", r"some", r"therefore", r"syllogism"]
    ),
    "physics_first": ReasoningStyle(
        name="physics_first",
        description="Conservation laws, symmetries, dimensional analysis.",
        prompt_modifier=lambda p: f"Apply fundamental physics: conservation, symmetry, dimensional analysis.\n\n{p}",
        signature_patterns=[r"conservation", r"symmetry", r"dimension", r"energy"]
    ),
    "dialectical": ReasoningStyle(
        name="dialectical",
        description="Thesis, antithesis, synthesis.",
        prompt_modifier=lambda p: f"State a thesis, then argue against it, and finally synthesize a resolution.\n\n{p}",
        signature_patterns=[r"thesis", r"antithesis", r"synthesis", r"on the other hand"]
    ),
    "analogical": ReasoningStyle(
        name="analogical",
        description="Map to a different domain, reason there, and map back.",
        prompt_modifier=lambda p: f"Find an analogy from another domain that shares structure. Reason within that analogy, then map back.\n\n{p}",
        signature_patterns=[r"this is like", r"similarly", r"imagine if"]
    ),
}

# ----------------------------------------------------------------------
# 3. EXPLORER – generates chains given style + substrate
# ----------------------------------------------------------------------
class ReasoningExplorer:
    def __init__(self, model, tokenizer, device="cpu"):
        self.model = model.to(device)
        self.tokenizer = tokenizer
        self.device = device
        self.styles = STYLES
        self.substrates = SUBSTRATES

    def generate_chain(
        self,
        prompt: str,
        style_name: Optional[str] = None,
        substrate_name: Optional[str] = None,
        max_new_tokens: int = 350,
        temperature: float = 0.8,
        num_beams: int = 3,
    ) -> Tuple[str, List[str], str, str]:
        """
        Returns: (full_text, list_of_steps, style_used, substrate_used)
        """
        # Apply style modifier
        style = self.styles.get(style_name) if style_name else None
        substrate = self.substrates.get(substrate_name) if substrate_name else None

        mod_prompt = prompt
        if style:
            mod_prompt = style.prompt_modifier(mod_prompt)
        if substrate:
            mod_prompt = substrate.prompt_modifier(mod_prompt)

        # Adjust generation config based on style/substrate
        gen_kwargs = {
            "max_new_tokens": max_new_tokens,
            "temperature": temperature,
            "do_sample": True,
            "num_beams": num_beams,
            "early_stopping": True,
            "pad_token_id": self.tokenizer.eos_token_id,
        }
        # For strict logical modes, lower temperature
        if style_name in ["formal_logic", "aristotelian"] or substrate_name in ["binary", "ternary"]:
            gen_kwargs["temperature"] = 0.6

        inputs = self.tokenizer(mod_prompt, return_tensors="pt").to(self.device)
        outputs = self.model.generate(**inputs, **gen_kwargs)
        full_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Split into steps (heuristic: lines starting with "Step", numbers, or paragraphs)
        steps = self._split_steps(full_text)
        return full_text, steps, style_name or "none", substrate_name or "none"

    def _split_steps(self, text: str) -> List[str]:
        # Remove the initial prompt if present? We'll assume the model returns the whole answer.
        # Split on "Step" patterns or double newlines.
        # A simple split by lines that look like step markers.
        step_pattern = r"(?:^|\n)(Step \d+|\[Step \d+\]|\d+\.|\- )"
        parts = re.split(step_pattern, text)
        # Rejoin step markers with their content
        steps = []
        for i in range(1, len(parts), 2):
            steps.append((parts[i] + parts[i+1]).strip())
        if not steps:
            # Fallback: split by double newline
            steps = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
        return steps if steps else [text]

    def generate_multi_style(
        self, prompt: str, style_substrate_pairs: List[Tuple[str, str]]
    ) -> List[Dict[str, Any]]:
        """Generate one chain for each (style, substrate) combination."""
        results = []
        for s_name, sub_name in style_substrate_pairs:
            text, steps, s, sub = self.generate_chain(prompt, s_name, sub_name)
            results.append({
                "style": s,
                "substrate": sub,
                "full_text": text,
                "steps": steps,
            })
        return results


# ----------------------------------------------------------------------
# 4. CRITIC – evaluates outcome and step quality
# ----------------------------------------------------------------------
class ReasoningCritic:
    def __init__(self, outcome_checker: Optional[Callable] = None):
        """
        outcome_checker: function(chain_text, ground_truth) -> bool (1 for correct)
        """
        self.outcome_checker = outcome_checker

    def evaluate_chain(
        self,
        chain_text: str,
        steps: List[str],
        ground_truth: Optional[str] = None,
    ) -> Dict[str, Any]:
        outcome = None
        first_error_step = None
        if self.outcome_checker and ground_truth is not None:
            outcome = 1 if self.outcome_checker(chain_text, ground_truth) else 0
        # Placeholder for step-level scoring: we could use a learned value head.
        # For now, if outcome==0, we assume the last step is the error, but ideally
        # we'd have a process-supervised model. We'll return a dummy score list.
        step_scores = [1.0] * len(steps)  # all 1 for now (to be replaced with a proper scorer)
        if outcome == 0:
            # Simulate: mark the last step as the error for simplicity.
            first_error_step = len(steps) - 1 if steps else 0
        return {
            "outcome": outcome,
            "step_scores": step_scores,
            "first_error_step_idx": first_error_step,
        }


# ----------------------------------------------------------------------
# 5. EXPERIENCE BUFFER
# ----------------------------------------------------------------------
@dataclass
class Experience:
    prompt: str
    style: str
    substrate: str
    chain_text: str
    steps: List[str]
    outcome: Optional[int]  # 0/1
    first_error_step_idx: Optional[int]
    corrected_chain: Optional[str] = None

class ExperienceBuffer:
    def __init__(self):
        self.experiences: List[Experience] = []

    def add(self, exp: Experience):
        self.experiences.append(exp)

    def get_all_failures(self) -> List[Experience]:
        return [e for e in self.experiences if e.outcome == 0]

    def get_contrastive_pairs(self):
        """Return (prompt, failed_chain, corrected_chain) for all corrected failures."""
        pairs = []
        for e in self.experiences:
            if e.outcome == 0 and e.corrected_chain:
                pairs.append((e.prompt, e.chain_text, e.corrected_chain))
        return pairs

    def get_style_performance(self) -> Dict[str, List[int]]:
        perf = defaultdict(list)
        for e in self.experiences:
            if e.outcome is not None:
                perf[f"{e.style}|{e.substrate}"].append(e.outcome)
        return {k: sum(v)/len(v) for k, v in perf.items()}


# ----------------------------------------------------------------------
# 6. FALSIFIER – challenges chains with other styles/substrates
# ----------------------------------------------------------------------
class Falsifier:
    def __init__(self, explorer: ReasoningExplorer, critic: ReasoningCritic):
        self.explorer = explorer
        self.critic = critic

    def falsify(
        self,
        original_chain: str,
        original_style: str,
        original_substrate: str,
        attack_style: str = "formal_logic",
        attack_substrate: str = "binary",
        ground_truth: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Ask the model to find a flaw using a different cognitive mode.
        Returns whether the chain was successfully falsified.
        """
        prompt = (
            f"The following reasoning was generated using {original_style} style "
            f"and {original_substrate} processing:\n\n{original_chain}\n\n"
            f"Now, using {attack_style} style and {attack_substrate} processing, "
            f"find a flaw or counterexample in the above reasoning."
        )
        chain, steps, _, _ = self.explorer.generate_chain(
            prompt, style_name=attack_style, substrate_name=attack_substrate
        )
        # For simplicity, we assume if a rebuttal exists, it's a falsification.
        # In practice, we'd use a verifier to check if the flaw is valid.
        # Here we just check if the critic outcome on the original remains valid.
        # We'll return the rebuttal chain.
        return {
            "rebuttal_chain": chain,
            "attack_style": attack_style,
            "attack_substrate": attack_substrate,
            # In a full system, we'd run an automatic check.
        }


# ----------------------------------------------------------------------
# 7. META-LEARNER – learns which (style, substrate) to use
# ----------------------------------------------------------------------
class MetaLearner:
    def __init__(self):
        self.problem_embeddings = []
        self.metadata = []  # list of dicts with style, substrate, outcome

    def update(self, problem_embed: np.ndarray, style: str, substrate: str, outcome: int):
        self.problem_embeddings.append(problem_embed)
        self.metadata.append({"style": style, "substrate": substrate, "outcome": outcome})

    def recommend(self, problem_embed: np.ndarray, top_k=3) -> List[Tuple[str, str]]:
        if len(self.problem_embeddings) < 5:
            # Not enough data: return a default set
            return [("linear_sequential", "binary"), ("dialectical", "fuzzy"), ("geometric", "analog")]
        # Use k-NN to find similar problems, then compute success rate per (style,substrate)
        knn = NearestNeighbors(n_neighbors=min(20, len(self.problem_embeddings)))
        knn.fit(np.array(self.problem_embeddings))
        _, indices = knn.kneighbors([problem_embed])
        scores = defaultdict(list)
        for idx in indices[0]:
            meta = self.metadata[idx]
            scores[(meta["style"], meta["substrate"])].append(meta["outcome"])
        avg_scores = {k: np.mean(v) for k, v in scores.items()}
        # Sort by average success, return top_k
        sorted_pairs = sorted(avg_scores.items(), key=lambda x: x[1], reverse=True)
        return [pair for pair, _ in sorted_pairs[:top_k]]


# ----------------------------------------------------------------------
# 8. SELF-IMPROVING TRAINER
# ----------------------------------------------------------------------
class SelfImprovingTrainer:
    def __init__(self, model, tokenizer, buffer: ExperienceBuffer, device="cpu"):
        self.model = model
        self.tokenizer = tokenizer
        self.buffer = buffer
        self.device = device
        self.optimizer = torch.optim.AdamW(model.parameters(), lr=5e-6)

    def train_contrastive_repair(self, num_epochs=1):
        """
        For each failed chain that has a corrected version, train the model
        to generate the correction given the prefix up to the error step.
        """
        pairs = self.buffer.get_contrastive_pairs()
        if not pairs:
            return
        self.model.train()
        for epoch in range(num_epochs):
            total_loss = 0
            for prompt, bad_chain, good_chain in pairs:
                # Build input: prompt + bad chain prefix, target: good continuation
                # We'll just concatenate prompt and the whole bad chain and ask model to produce good chain.
                # Simpler: fine-tune to transform bad_chain -> good_chain directly.
                input_text = f"Correct the flawed reasoning:\n{bad_chain}\n\nCorrected reasoning:\n{good_chain}"
                inputs = self.tokenizer(input_text, return_tensors="pt", truncation=True, max_length=1024).to(self.device)
                labels = inputs.input_ids.clone()
                # Mask loss on the input part (before "Corrected reasoning:") – we only want to learn the correction.
                mask_idx = input_text.find("Corrected reasoning:") 
                # Tokenize that prefix to get length
                prefix_ids = self.tokenizer(input_text[:mask_idx], return_tensors="pt").input_ids.shape[1]
                labels[:, :prefix_ids] = -100
                outputs = self.model(**inputs, labels=labels)
                loss = outputs.loss
                loss.backward()
                self.optimizer.step()
                self.optimizer.zero_grad()
                total_loss += loss.item()
            print(f"Contrastive repair epoch {epoch} loss: {total_loss:.4f}")

    def train_meta_cognitive_detector(self):
        """
        Train a linear classifier on hidden states at each step to predict eventual failure.
        This would be plugged into the model's forward pass; here we outline the idea.
        """
        # For brevity, we'll skip the implementation, but it would:
        # 1. Forward each step through the model, collect last-token hidden states.
        # 2. Use first_error_step_idx to label steps: before error -> 0, at/after -> 1.
        # 3. Train an auxiliary linear layer.
        pass


# ----------------------------------------------------------------------
# 9. PLAYGROUND ORCHESTRATOR
# ----------------------------------------------------------------------
class CognitivePlayground:
    def __init__(
        self,
        model_name: str = "gpt2",  # placeholder, use any HF model
        device: str = "cpu",
        outcome_checker: Optional[Callable] = None,
    ):
        self.device = device
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(model_name)
        self.tokenizer.pad_token = self.tokenizer.eos_token
        self.explorer = ReasoningExplorer(self.model, self.tokenizer, device)
        self.critic = ReasoningCritic(outcome_checker)
        self.buffer = ExperienceBuffer()
        self.falsifier = Falsifier(self.explorer, self.critic)
        self.meta_learner = MetaLearner()
        self.trainer = SelfImprovingTrainer(self.model, self.tokenizer, self.buffer, device)

    def embed_prompt(self, prompt: str) -> np.ndarray:
        """Simple bag-of-words embedding for meta-learner (or use sentence-transformers)."""
        # In practice, use a proper sentence embedder. Here we use token counts.
        inputs = self.tokenizer(prompt, return_tensors="pt")
        # Return mean of token ids as naive embedding.
        return inputs.input_ids.float().mean(dim=1).numpy().flatten()

    def run_cycle(
        self,
        prompts: List[str],
        ground_truths: Optional[List[str]] = None,
        num_style_attempts: int = 3,
    ):
        for i, prompt in enumerate(prompts):
            gt = ground_truths[i] if ground_truths else None
            prompt_embed = self.embed_prompt(prompt)
            # Get recommended (style, substrate) from meta-learner
            recommended = self.meta_learner.recommend(prompt_embed, top_k=num_style_attempts)
            # Also add some random exploration
            all_styles = list(STYLES.keys())
            all_substrates = list(SUBSTRATES.keys())
            # Generate chains for recommended and a few random ones
            attempts = recommended.copy()
            for _ in range(num_style_attempts):
                random_pair = (np.random.choice(all_styles), np.random.choice(all_substrates))
                if random_pair not in attempts:
                    attempts.append(random_pair)

            for style, substrate in attempts:
                chain_text, steps, s_used, sub_used = self.explorer.generate_chain(
                    prompt, style, substrate
                )
                eval_res = self.critic.evaluate_chain(chain_text, steps, gt)
                outcome = eval_res["outcome"]
                first_err = eval_res["first_error_step_idx"]

                # If outcome is 0, attempt self-correction (using a different style maybe)
                corrected = None
                if outcome == 0:
                    # Self-correction: ask the model to fix its own reasoning.
                    correction_prompt = (
                        f"The following reasoning for the question '{prompt}' is flawed:\n{chain_text}\n\n"
                        f"Please provide a corrected reasoning."
                    )
                    corr_text, _, _, _ = self.explorer.generate_chain(correction_prompt, style, substrate)
                    corrected = corr_text

                exp = Experience(
                    prompt=prompt,
                    style=s_used,
                    substrate=sub_used,
                    chain_text=chain_text,
                    steps=steps,
                    outcome=outcome,
                    first_error_step_idx=first_err,
                    corrected_chain=corrected,
                )
                self.buffer.add(exp)
                # Update meta-learner
                if outcome is not None:
                    self.meta_learner.update(prompt_embed, s_used, sub_used, outcome)

                # Optionally run falsifier on successful chains
                if outcome == 1:
                    falsify_res = self.falsifier.falsify(chain_text, s_used, sub_used)
                    # Store the falsification attempt (could be logged)

        # After collecting experiences, run training steps
        self.trainer.train_contrastive_repair()
        # self.trainer.train_meta_cognitive_detector()  # when implemented

        # Print summary
        perf = self.buffer.get_style_performance()
        print("Style|Substrate performance:")
        for k, v in perf.items():
            print(f"  {k}: {v:.2%}")

    def run_continuous(self, prompts, rounds=5, ground_truths=None):
        for r in range(rounds):
            print(f"\n=== Round {r+1} ===")
            self.run_cycle(prompts, ground_truths)

# ----------------------------------------------------------------------
# 10. EXAMPLE OUTCOME CHECKER (for math problems)
# ----------------------------------------------------------------------
def math_equality_checker(chain_text: str, ground_truth: str) -> bool:
    # Extract last number from chain and compare to ground truth.
    # Very simplistic – for demonstration only.
    numbers = re.findall(r"[-+]?\d*\.\d+|\d+", chain_text)
    if numbers:
        return numbers[-1].strip() == ground_truth.strip()
    return False

# ----------------------------------------------------------------------
# 11. MAIN (demo)
# ----------------------------------------------------------------------
if __name__ == "__main__":
    # Example usage (requires a real model and GPU for actual training)
    playground = CognitivePlayground(
        model_name="gpt2",  # use a small model for testing
        device="cpu",
        outcome_checker=math_equality_checker,
    )
    sample_prompts = [
        "What is 12 + 7?",
        "If all dogs are mammals and all mammals are animals, are all dogs animals?",
    ]
    sample_gts = ["19", "yes"]
    # Run one round (in real use, you'd loop many times)
    playground.run_cycle(sample_prompts, sample_gts, num_style_attempts=2)
