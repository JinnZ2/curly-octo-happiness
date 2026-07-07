# hnd.py
"""
Hidden Node Detector (HND) v1.0

Analyzes residuals between predicted and observed outputs to
identify unmodeled variables, phantom causalities, and hidden buffers.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
import json

@dataclass
class HiddenNodeSuggestion:
    """A potential new node to add to the model."""
    name: str
    confidence: float  # 0.0 - 1.0
    reason: str
    evidence: str
    category: str  # "causal", "correlational", "buffer"

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

    def scan(self, residuals: List[float], threshold: float = 0.1) -> List[HiddenNodeSuggestion]:
        """
        Scan for hidden nodes.

        Args:
            residuals: List of (predicted - actual) values
            threshold: Minimum residual magnitude to trigger detection
        """
        self.suggestions = []
        avg_residual = sum(abs(r) for r in residuals) / len(residuals) if residuals else 0

        if avg_residual < threshold:
            return []  # Model is performing well

        # Method 1: Residual Gradient (unmodeled loss)
        self._detect_residual_gradient(residuals)

        # Method 2: Phantom Causality (ghost mediator)
        self._detect_phantom_causality()

        # Method 3: Negative Space (hidden buffer)
        self._detect_hidden_buffer()

        return self.suggestions

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
        if not self.suggestions:
            return "No hidden nodes detected. Model is robust."

        lines = ["HIDDEN NODE DETECTION REPORT", "=" * 40, ""]
        for i, suggestion in enumerate(self.suggestions, 1):
            lines.append(f"{i}. {suggestion.name}")
            lines.append(f"   Confidence: {suggestion.confidence:.0%}")
            lines.append(f"   Category:   {suggestion.category}")
            lines.append(f"   Reason:     {suggestion.reason}")
            lines.append(f"   Evidence:   {suggestion.evidence}")
            lines.append("")
        lines.append("RECOMMENDATIONS:")
        lines.append("- Add these nodes to the model")
        lines.append("- Re-run GAE to see if geometry changes")
        lines.append("- Re-run HND to validate residuals drop")
        return "\n".join(lines)
