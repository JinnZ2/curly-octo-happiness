# hnd.py
"""
Hidden Node Detector (HND) v1.0

Analyzes residuals between predicted and observed outputs to
identify unmodeled variables, phantom causalities, and hidden buffers.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
import json
import os
import sys

# The ε-machine acceptance test lives in the shared core package. modules/ is
# not a package and is normally run with its own directory as CWD, so reach the
# repository root the same way project/ does before importing.
try:
    from grounding.core.epsilon_machine import (
        equalized_history_length, reconstruct, symbolize)
except ImportError:  # pragma: no cover - depends on how the script was launched
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from grounding.core.epsilon_machine import (
        equalized_history_length, reconstruct, symbolize)

@dataclass
class HiddenNodeSuggestion:
    """A potential new node to add to the model."""
    name: str
    confidence: float  # 0.0 - 1.0
    reason: str
    evidence: str
    category: str  # "causal", "correlational", "buffer"
    diagnostics: Dict[str, Any] = field(default_factory=dict)

class HiddenNodeDetector:
    """Detects hidden nodes from model residuals."""

    def __init__(self, model: Dict, environment: Dict):
        """
        Args:
            model: {
                "nodes": [...],
                "dependencies": {...},
                "predicted_outputs": [...]
            }
            environment: {
                "variables": {...},
                "time_series": {...}
            }
        """
        self.model = model
        self.environment = environment
        self.suggestions: List[HiddenNodeSuggestion] = []
        self.rejected: List[HiddenNodeSuggestion] = []
        self.unverified: List[HiddenNodeSuggestion] = []

    def scan(self, residuals: List[float], threshold: float = 0.1,
             acceptance: str = "correlation") -> List[HiddenNodeSuggestion]:
        """
        Scan for hidden nodes.

        Args:
            residuals: List of (predicted - actual) values
            threshold: Minimum residual magnitude to trigger detection
            acceptance: how a candidate earns its place in the model.
                "correlation" (default) keeps the historical behaviour: the
                per-detector correlation thresholds are the whole test.
                "epsilon_machine" treats those thresholds as a cheap candidate
                *generator* and then applies the acceptance criterion of
                `accept_by_epsilon_machine` -- a candidate is kept only if
                conditioning on it makes the residual stream both simpler and
                less surprising. Rejected candidates land in `self.rejected`;
                candidates the criterion could not test (too little data) stay
                in the returned list and are noted in `self.unverified`.
        """
        self.suggestions = []
        self.rejected = []
        self.unverified = []
        avg_residual = sum(abs(r) for r in residuals) / len(residuals) if residuals else 0

        if avg_residual < threshold:
            return []  # Model is performing well

        # Method 1: Residual Gradient (unmodeled loss)
        self._detect_residual_gradient(residuals)

        # Method 2: Phantom Causality (ghost mediator)
        self._detect_phantom_causality()

        # Method 3: Negative Space (hidden buffer)
        self._detect_hidden_buffer()

        if acceptance == "epsilon_machine":
            self._apply_epsilon_machine_acceptance(residuals)
        elif acceptance != "correlation":
            raise ValueError(f"unknown acceptance mode: {acceptance!r}")

        return self.suggestions

    # ------------------------------------------------------------------
    # ε-machine acceptance (Crutchfield minimality, via CSSR-style states)
    # ------------------------------------------------------------------

    # Samples needed per history cell before the reconstruction is worth
    # believing. Below roughly this density the state estimates are noise:
    # on a synthetic driver+echo benchmark the criterion separated them 6/20
    # times at 60 samples and 19/20 at 300, so refusing to answer is the honest
    # move -- an untestable claim goes to the unknowns, not into the model.
    MIN_SAMPLES_PER_HISTORY = 15

    def accept_by_epsilon_machine(self, residuals: List[float], var_name: str,
                                  n_bands: int = 4, max_history: int = 2,
                                  margin: float = 0.02) -> Tuple[bool, Dict[str, Any]]:
        """Does conditioning on `var_name` earn a place in the model?

        Reconstructs causal states for the residual stream twice: once from the
        residual's own past, once from the past augmented with the candidate
        variable. The candidate is accepted iff *both* statistical complexity
        C_mu and entropy rate h_mu fall by at least `margin` bits.

        Requiring both is the point. A genuinely explanatory variable collapses
        causal states -- the residual's own long history had been acting as a
        proxy for it -- so memory and surprise drop together. An irrelevant
        variable also lowers the measured h_mu on finite data, by shattering
        histories into rare states that each look deterministic, but it pays
        for that with a sharp *rise* in C_mu. The complexity term is what makes
        this a test rather than a ratchet.

        The augmented machine gets a shorter history budget so that both
        machines search history spaces of the same size (see
        `equalized_history_length`); without that correction the finite-sample
        inflation of C_mu sinks genuine drivers along with the spurious ones.

        Returns (accepted, diagnostics).
        """
        series = self.environment.get("time_series", {}).get(var_name)
        if not series or len(series) != len(residuals) or len(residuals) < 8:
            return False, {"acceptance": "skipped", "why": "series unusable or too short"}

        residual_symbols = symbolize(residuals, n_bands=n_bands)
        candidate_symbols = symbolize(series, n_bands=n_bands)
        augmented = list(zip(residual_symbols, candidate_symbols))

        needed = self.MIN_SAMPLES_PER_HISTORY * len(set(residual_symbols)) ** max_history
        if len(residuals) < needed:
            return False, {
                "acceptance": "skipped",
                "why": (f"{len(residuals)} samples cannot support "
                        f"{len(set(residual_symbols))}^{max_history} histories; "
                        f"need ~{needed}"),
                "samples": len(residuals),
                "samples_needed": needed,
            }

        augmented_history = equalized_history_length(
            len(set(residual_symbols)), len(set(augmented)), max_history)

        before = reconstruct(residual_symbols, max_history=max_history)
        after = reconstruct(residual_symbols, augmented, max_history=augmented_history)

        d_c = before.statistical_complexity - after.statistical_complexity
        d_h = before.entropy_rate - after.entropy_rate
        accepted = d_c >= margin and d_h >= margin

        return accepted, {
            "acceptance": "accepted" if accepted else "rejected",
            "c_mu_before": round(before.statistical_complexity, 4),
            "c_mu_after": round(after.statistical_complexity, 4),
            "h_mu_before": round(before.entropy_rate, 4),
            "h_mu_after": round(after.entropy_rate, 4),
            "delta_c_mu": round(d_c, 4),
            "delta_h_mu": round(d_h, 4),
            "states_before": before.n_states,
            "states_after": after.n_states,
            "history_before": max_history,
            "history_after": augmented_history,
            "margin": margin,
        }

    def _apply_epsilon_machine_acceptance(self, residuals: List[float]) -> None:
        """Filter `self.suggestions` through the ε-machine criterion.

        Three outcomes, not two. A candidate the criterion *rejected* is moved
        to `self.rejected`. A candidate it could not judge -- too few samples to
        reconstruct states from -- stays a suggestion but is recorded in
        `self.unverified` and says so in its evidence: "untested" is a different
        claim from "refuted", and collapsing the two would be the exact
        confusion this repo exists to avoid.
        """
        kept: List[HiddenNodeSuggestion] = []
        verdicts: Dict[str, Tuple[bool, Dict[str, Any]]] = {}

        for suggestion in self.suggestions:
            if suggestion.name not in verdicts:
                verdicts[suggestion.name] = self.accept_by_epsilon_machine(
                    residuals, suggestion.name)
            accepted, diagnostics = verdicts[suggestion.name]
            suggestion.diagnostics = dict(diagnostics)

            if diagnostics.get("acceptance") == "skipped":
                suggestion.evidence += (f"; eps-machine not applicable "
                                        f"({diagnostics.get('why', 'unknown')})")
                self.unverified.append(suggestion)
                kept.append(suggestion)
            elif accepted:
                d_h = diagnostics.get("delta_h_mu", 0.0)
                d_c = diagnostics.get("delta_c_mu", 0.0)
                suggestion.evidence += (f"; eps-machine: C_mu -{d_c:.2f} bits, "
                                        f"h_mu -{d_h:.2f} bits/symbol")
                kept.append(suggestion)
            else:
                self.rejected.append(suggestion)

        self.suggestions = kept

    def _detect_residual_gradient(self, residuals: List[float]):
        """Find environmental variables that correlate with residuals."""
        env_vars = self.environment.get("variables", {})
        time_series = self.environment.get("time_series", {})

        for var_name, var_data in time_series.items():
            if var_name in self.model.get("nodes", []):
                continue  # Already in model

            # Check correlation between residual and variable
            if len(var_data) == len(residuals):
                correlation = self._pearson_correlation(var_data, residuals)
                if abs(correlation) > 0.5:
                    self.suggestions.append(HiddenNodeSuggestion(
                        name=var_name,
                        confidence=min(1.0, abs(correlation)),
                        reason="Residual gradient detection",
                        evidence=f"Correlation with residuals: {correlation:.2f}",
                        category="causal"
                    ))

    def _detect_phantom_causality(self):
        """Find variables that are correlated but structurally disconnected."""
        nodes = self.model.get("nodes", [])
        dependencies = self.model.get("dependencies", {})

        # Build a set of all connected pairs
        connected_pairs = set()
        for source, targets in dependencies.items():
            for target in targets:
                connected_pairs.add((source, target))
                connected_pairs.add((target, source))

        # Check for correlations that are not structurally connected
        env_vars = self.environment.get("variables", {})
        time_series = self.environment.get("time_series", {})

        for var_a in nodes:
            for var_b in nodes:
                if (var_a, var_b) in connected_pairs:
                    continue  # Already connected

                if var_a not in time_series or var_b not in time_series:
                    continue

                corr = self._pearson_correlation(time_series[var_a], time_series[var_b])
                if abs(corr) > 0.7:
                    # Phantom causality detected - look for common mediator
                    mediator = self._find_common_cause(var_a, var_b, time_series)
                    if mediator:
                        self.suggestions.append(HiddenNodeSuggestion(
                            name=mediator,
                            confidence=0.8,
                            reason="Phantom causality detection",
                            evidence=f"Mediates correlation between {var_a} and {var_b} (r={corr:.2f})",
                            category="correlational"
                        ))

    def _detect_hidden_buffer(self):
        """Find variables that explain unexpected positive outcomes."""
        predicted = self.model.get("predicted_outputs", [])
        observed = self.environment.get("observed_outputs", [])

        if not predicted or not observed:
            return

        # If observed is consistently higher than predicted, there's a hidden buffer
        avg_improvement = sum(o - p for o, p in zip(observed, predicted)) / len(observed)

        if avg_improvement > 0.05:  # 5% unexpected improvement
            # Find variables trending up during the same period
            time_series = self.environment.get("time_series", {})
            for var_name, var_data in time_series.items():
                if var_name in self.model.get("nodes", []):
                    continue
                if len(var_data) >= 2 and var_data[-1] > var_data[0] * 1.1:
                    self.suggestions.append(HiddenNodeSuggestion(
                        name=var_name,
                        confidence=0.7,
                        reason="Hidden buffer detection",
                        evidence=f"Unexpected improvement of {avg_improvement:.2%} correlated with rising {var_name}",
                        category="buffer"
                    ))

    def _pearson_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation coefficient."""
        if len(x) != len(y) or len(x) < 2:
            return 0.0
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_x2 = sum(xi**2 for xi in x)
        sum_y2 = sum(yi**2 for yi in y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        numerator = n * sum_xy - sum_x * sum_y
        denominator = ((n * sum_x2 - sum_x**2) * (n * sum_y2 - sum_y**2)) ** 0.5
        if denominator == 0:
            return 0.0
        return numerator / denominator

    def _find_common_cause(self, var_a: str, var_b: str, time_series: Dict) -> Optional[str]:
        """Find a variable that correlates with both var_a and var_b."""
        for var_c, data_c in time_series.items():
            if var_c in [var_a, var_b]:
                continue
            if var_a not in time_series or var_b not in time_series:
                continue
            corr_a = self._pearson_correlation(time_series[var_a], data_c)
            corr_b = self._pearson_correlation(time_series[var_b], data_c)
            if abs(corr_a) > 0.6 and abs(corr_b) > 0.6:
                return var_c
        return None

    def generate_report(self) -> str:
        """Generate a human-readable report of hidden node detections."""
        if not self.suggestions and not self.rejected:
            return "No hidden nodes detected. Model is robust."

        if not self.suggestions:
            names = ", ".join(sorted({s.name for s in self.rejected}))
            return ("No hidden nodes accepted. Correlation flagged "
                    f"{names}, but the eps-machine criterion rejected "
                    "them (no joint drop in C_mu and h_mu).")

        lines = ["HIDDEN NODE DETECTION REPORT", "=" * 40, ""]
        for i, suggestion in enumerate(self.suggestions, 1):
            lines.append(f"{i}. {suggestion.name}")
            lines.append(f"   Confidence: {suggestion.confidence:.0%}")
            lines.append(f"   Category:   {suggestion.category}")
            lines.append(f"   Reason:     {suggestion.reason}")
            lines.append(f"   Evidence:   {suggestion.evidence}")
            lines.append("")
        if self.rejected:
            names = ", ".join(sorted({s.name for s in self.rejected}))
            lines.append(f"Rejected by the eps-machine criterion: {names}")
            lines.append("")
        if self.unverified:
            names = ", ".join(sorted({s.name for s in self.unverified}))
            lines.append(f"Untested by the eps-machine criterion (too little "
                         f"data, correlation evidence only): {names}")
            lines.append("")
        lines.append("RECOMMENDATIONS:")
        lines.append("- Add these nodes to the model")
        lines.append("- Re-run GAE to see if geometry changes")
        lines.append("- Re-run HND to validate residuals drop")
        return "\n".join(lines)
