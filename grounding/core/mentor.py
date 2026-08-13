"""Mentor interfaces.

Mentor          — returns formatted strings (unified_playground line).
MentorInterface — prints directly (shared.py / playground4-8 line).
TeachbackMentor — Pask's conversation theory: explanations are only learned
                  once the agent can reconstruct them and the mentor agrees.
All keep a (kind, text) log.
"""

import re

from grounding.core.claims import Claim

# A reconstruction that shares too few content words with the explanation
# missed the point; one that shares nearly all of them is parroting. Pask's
# criterion is reconstruction in the learner's *own* terms, so understanding
# lives in the band between.
OVERLAP_BAND = (0.2, 0.8)

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "because", "but", "by", "for",
    "from", "has", "have", "if", "in", "is", "it", "its", "of", "on", "or",
    "that", "the", "their", "then", "there", "this", "to", "was", "were",
    "when", "which", "with", "you", "your",
}


def _content_words(text):
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


def overlap_score(explanation, reconstruction):
    """Fraction of the explanation's content words the reconstruction reuses."""
    original = _content_words(explanation)
    if not original:
        return 0.0
    return len(original & _content_words(reconstruction)) / len(original)


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


class TeachbackMentor(Mentor):
    """A mentor whose explanations are not knowledge until they survive teachback.

    Pask's conversation theory: a concept is shared when the learner can
    reconstruct the teacher's explanation and the teacher agrees the
    reconstruction is the same concept. Here that becomes falsifiable rather
    than ceremonial — each reconstruction is a `Claim` staked against the
    explanation, resolved by the same Beta-posterior machinery as every other
    claim in the repo, and `learned()` is true only once the claim has
    *survived*. A concept the agent merely nodded at stays unlearned.

    The claim carries a machine-checkable `logical_form` on the overlap band,
    but the automatic check only *votes* where a word-overlap measure can
    actually support a verdict. High overlap is decisive: reciting the
    explanation back is demonstrably not reconstruction, whatever it means.
    Low overlap is not decisive, because "you missed it" and "you paraphrased it
    in synonyms" look identical to a lexical measure — so the automatic check
    abstains and waits for the mentor, the same way HND leaves an untestable
    candidate unverified rather than refuted.
    """

    def __init__(self, band=OVERLAP_BAND):
        super().__init__()
        self.band = band
        self.explanations = {}   # concept -> explanation text
        self.claims = {}         # concept -> Claim (the current reconstruction)

    def explain(self, concept, explanation):
        self.explanations[concept] = explanation
        self.log.append(("explain", f"{concept}: {explanation}"))
        return f"🧑‍🏫 Mentor explains {concept}: {explanation}"

    def teachback(self, concept, reconstruction):
        """Stake the agent's restatement as a claim and run the automatic check.

        Returns (message, claim). The claim is None when the concept was never
        explained — there is nothing to reconstruct.
        """
        explanation = self.explanations.get(concept)
        if explanation is None:
            return f"❓ Nothing explained about '{concept}' yet.", None

        low, high = self.band
        midpoint, halfwidth = (low + high) / 2, (high - low) / 2
        claim = self.claims.get(concept)
        if claim is None:
            claim = Claim(
                text=reconstruction,
                falsification=(f"the mentor rejects this as not the same concept as "
                               f"their explanation of '{concept}', or the wording "
                               f"falls outside the understanding band {self.band}"),
                logical_form={"op": "abs_diff_lt",
                              "args": ["overlap", midpoint, halfwidth]},
                scope={"concept": concept, "explained_as": explanation},
                reference_class=f"reconstructions of the mentor's '{concept}' explanation",
            )
            self.claims[concept] = claim
        elif claim.text != reconstruction:
            # A fresh wording is a fresh attempt at the same concept, not a
            # fresh claim: giving it a clean record would let the agent retry
            # until something sticks. The repo already has the right name for
            # that, so route it through the counted escape hatch.
            claim.reformulate(text=reconstruction)
            claim.scope = dict(claim.scope or {}, explained_as=explanation)

        score = overlap_score(explanation, reconstruction)
        self.log.append(("teachback", f"{concept}: {reconstruction} (overlap {score:.2f})"))

        if score >= low:
            # Decisive either way: inside the band is reconstruction, above it
            # is recitation. claim.evaluate runs the logical_form and records it.
            claim.evaluate({"overlap": score})
            verdict = (f"in your own words (overlap {score:.2f})" if score < high
                       else f"that is my wording repeated back (overlap {score:.2f}), not yours")
        else:
            # A lexical measure cannot separate "missed it" from "said it in
            # synonyms". Stake nothing; ask the mentor.
            verdict = (f"overlap {score:.2f} is too low for me to judge — "
                       "either you rephrased it entirely or you missed it; "
                       "confirm or correct me")
        message = f"🔁 Teachback on {concept}: {verdict}. Claim {claim.status}."
        if claim.escape_hatch_suspected:
            message += (f"\n   ⚠️ reworded {claim.reformulation_count}× without ever "
                        "surviving — this is talking around the concept, not learning it.")
        return message, claim

    def confirm(self, concept):
        """Mentor agrees the reconstruction is the same concept."""
        claim = self.claims.get(concept)
        if claim is None:
            return f"❓ No teachback on '{concept}' to confirm."
        claim.test(True)
        self.log.append(("confirm", concept))
        state = "learned" if self.learned(concept) else f"claim {claim.status}"
        return f"✅ Confirmed '{concept}' — {state}."

    def correct(self, concept, correction):
        """Mentor rejects the reconstruction and re-explains.

        The rejection is evidence against the claim, and the corrected
        explanation replaces the old one — so the next teachback is measured
        against what the mentor actually meant.
        """
        claim = self.claims.get(concept)
        if claim is None:
            return f"❓ No teachback on '{concept}' to correct."
        claim.test(False)
        self.explanations[concept] = correction
        self.log.append(("correct", f"{concept}: {correction}"))
        return (f"❌ Not quite — '{concept}' is: {correction}\n"
                f"   (claim {claim.status}, {claim.failed} failed; teach it back again)")

    def learned(self, concept):
        """True only once the reconstruction has survived testing.

        An escape-hatched concept is never learned however good the current
        wording looks: surviving on the fourth rewording is a fact about the
        rewording, not about the concept.
        """
        claim = self.claims.get(concept)
        return (claim is not None and claim.status == "survived"
                and not claim.escape_hatch_suspected)

    def status(self):
        if not self.explanations:
            return "No concepts under discussion."
        lines = ["Teachback status:"]
        for concept in sorted(self.explanations):
            claim = self.claims.get(concept)
            if claim is None:
                lines.append(f"  {concept}: explained, never taught back")
                continue
            mark = "learned" if self.learned(concept) else claim.status
            if claim.escape_hatch_suspected:
                mark += " [escape hatch]"
            lines.append(f"  {concept}: {mark} "
                         f"({claim.passed} passed / {claim.failed} failed, "
                         f"beta {claim.beta_confidence:.2f}, "
                         f"reworded {claim.reformulation_count}×)")
        return "\n".join(lines)


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
