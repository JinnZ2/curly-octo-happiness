"""Event-driven sensor encoding: send the change, not the sample.

An event camera does not produce frames. Each pixel holds the level it last
reported and emits an event only when the signal has moved from that level by
more than a threshold, after which it is refractory for a fixed interval. The
result is a sparse, asynchronous stream that spends bandwidth in proportion to
how much is happening rather than to how often you looked.

That is the same rule the repo's encoders want. A band-index encoder sampled
every step re-transmits the same codeword while nothing changes; the Δ-threshold
rule transmits only crossings. For the stewardship line — scavenged parts, a
radio budget, a battery — that difference is the difference between a telemetry
link that fits and one that does not.

Three properties, all of which fall out of the rule rather than being bolted on:

**Hysteresis.** The reference is the value at the *last event*, not the last
sample, so a signal dithering around a band edge fires once and then goes quiet.
Comparing against the previous sample would chatter.

**A bounded event rate.** The refractory interval caps events per unit time, so
a noisy sensor cannot flood the bus. This is a guarantee about the channel, not
a hope about the signal.

**Reconstructability, measured rather than claimed.** `reconstruct` replays an
event stream back into a dense band series by holding each level until the next
event, and `fidelity_claim` stakes the compression as a falsifiable claim: this
many events reproduce this fraction of the band series. If the threshold is too
coarse the claim fails, which is the point of staking it.

Events carry Gray-coded band indices, so an event is the same codeword the
plugin encoders already speak — the bus is the existing one, driven differently.

Stdlib only.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from grounding.core.claims import Claim
from grounding.core.graycode import gray_bits, gray_to_index

__all__ = ["Event", "EventEncoder", "fidelity_claim", "reconstruct"]


@dataclass
class Event:
    """One threshold crossing: when, which way, and to what band."""

    t: float
    polarity: int          # +1 rising, -1 falling
    band: int
    bits: str              # Gray-coded band index
    value: float

    def __str__(self) -> str:
        return (f"t={self.t:g} {'+' if self.polarity > 0 else '-'} "
                f"band {self.band} ({self.bits})")


class EventEncoder:
    """Δ-threshold + refractory encoder over the repo's band convention."""

    def __init__(self, bands: Sequence[float], threshold: float = 0.0,
                 refractory: float = 0.0, n_bits: int = 3):
        """
        Args:
            bands: ascending band thresholds, as everywhere else in the repo.
            threshold: hysteresis, in value units. An event needs *both* a
                change of band and a move of at least this much from the level
                last reported. 0 means report every band change, which is
                lossless by construction; larger values buy bandwidth by
                dropping marginal crossings, and `fidelity_claim` measures what
                that costs.
            refractory: minimum interval between events. 0 disables it.
            n_bits: width of the Gray-coded band index.

        The threshold is a *band* change with a value hysteresis, not a raw
        value distance. An event camera's threshold is its quantisation step, so
        the faithful analogue here is the band edge — and the repo's bands are
        equal-occupancy, hence unevenly spaced in value. A uniform value
        threshold silently misses crossings wherever the bands are narrow, which
        is exactly where the signal spends its time.
        """
        if not bands:
            raise ValueError("bands must not be empty")
        if threshold < 0:
            raise ValueError("threshold (hysteresis) must be >= 0")
        self.bands = list(bands)
        self.n_bits = n_bits
        self.refractory = refractory
        self.threshold = threshold

        self.reference: Optional[float] = None    # level at the last event
        self.last_band: Optional[int] = None      # band at the last event
        self.last_event_t: Optional[float] = None
        self.samples = 0
        self.events: List[Event] = []
        self.suppressed = 0                       # crossings lost to refractory

    def band_index(self, value: float) -> int:
        """Highest band whose threshold is <= value, via the Gray-code helpers."""
        return gray_to_index(gray_bits(value, self.bands, n_bits=self.n_bits))

    def observe(self, t: float, value: float) -> Optional[Event]:
        """Feed one sample. Returns an Event if this sample crossed, else None."""
        self.samples += 1

        if self.reference is None:                # first sample sets the level
            return self._emit(t, value, polarity=0)

        band = self.band_index(value)
        if band == self.last_band:
            return None                           # nothing new to say
        if abs(value - self.reference) < self.threshold:
            return None                           # hysteresis: too marginal

        if (self.refractory and self.last_event_t is not None
                and t - self.last_event_t < self.refractory):
            # The signal moved, but the channel is not allowed to say so yet.
            # Counted, not silently dropped: a high suppression count means the
            # refractory interval is throwing away real signal.
            self.suppressed += 1
            return None

        polarity = 1 if value > self.reference else -1
        return self._emit(t, value, polarity)

    def _emit(self, t: float, value: float, polarity: int) -> Event:
        band = self.band_index(value)
        event = Event(t=t, polarity=polarity, band=band,
                      bits=gray_bits(value, self.bands, n_bits=self.n_bits),
                      value=value)
        self.events.append(event)
        self.reference = value
        self.last_band = band
        self.last_event_t = t
        return event

    # -- channel statistics ---------------------------------------------

    @property
    def event_rate(self) -> float:
        """Events per sample. This is the bandwidth the stream actually costs."""
        return len(self.events) / self.samples if self.samples else 0.0

    @property
    def compression(self) -> float:
        """Samples saved, as a fraction: 0.9 means a tenth of the traffic."""
        return 1.0 - self.event_rate

    def retune(self, target_rate: float, gain: float = 0.5) -> Dict[str, float]:
        """Adjust the threshold toward a target event rate.

        The adaptive-band update, run as a control loop rather than a
        recalibration: firing too often means the hysteresis is too small for
        this signal, too rarely means it is too large. `gain` damps the
        correction, because a threshold that chases the rate oscillates.

        Raising the hysteresis is not free — it drops marginal crossings, and
        `fidelity_claim` is what says whether the bandwidth was worth the loss.
        Retuning without re-staking that claim is how a channel quietly stops
        carrying the signal.
        """
        if not 0.0 < target_rate <= 1.0:
            raise ValueError("target_rate must be in (0, 1]")
        if self.samples == 0:
            return {"threshold": self.threshold, "event_rate": 0.0, "note": "no data"}

        before = self.threshold
        rate = self.event_rate
        span = abs(self.bands[-1] - self.bands[0]) or 1.0
        if rate <= target_rate:
            # Under target: relax the hysteresis (toward reporting every change).
            self.threshold = max(0.0, self.threshold * (1.0 - gain))
        else:
            # Over target: widen it. Seed from the band span the first time, so
            # a threshold of exactly 0 can still grow.
            base = self.threshold or (span / max(1, len(self.bands) - 1)) * gain
            self.threshold = base * (1.0 + gain * (rate / target_rate - 1.0))
        return {"threshold_before": before, "threshold": self.threshold,
                "event_rate": rate, "target_rate": target_rate}

    def report(self) -> str:
        lines = [f"Event encoder: {len(self.events)} events from {self.samples} "
                 f"samples (rate {self.event_rate:.2f}, "
                 f"{self.compression:.0%} of traffic saved)",
                 f"  threshold {self.threshold:g}, refractory {self.refractory:g}"]
        if self.suppressed:
            lines.append(f"  ⚠ {self.suppressed} crossings suppressed by the "
                         "refractory interval — real signal is being dropped")
        return "\n".join(lines)


def reconstruct(events: Sequence[Event], n_samples: int,
                times: Optional[Sequence[float]] = None) -> List[int]:
    """Replay an event stream as a dense band series, holding each level.

    This is what a receiver can actually recover from the sparse stream, which
    is the only honest basis for claiming the compression was lossless enough.
    """
    if n_samples <= 0:
        return []
    schedule = list(times) if times is not None else list(range(n_samples))
    series: List[int] = []
    index, current = 0, (events[0].band if events else 0)
    for t in schedule:
        while index < len(events) and events[index].t <= t:
            current = events[index].band
            index += 1
        series.append(current)
    return series


def fidelity_claim(encoder: EventEncoder, values: Sequence[float],
                   times: Optional[Sequence[float]] = None,
                   tolerance: float = 0.05) -> Tuple[Claim, Dict[str, float]]:
    """Stake the compression as a falsifiable claim and test it.

    The claim is that the event stream reproduces the dense band series to
    within `tolerance` — measured by replaying the events and comparing, not
    assumed from the fact that a threshold was set. A threshold too coarse for
    the signal refutes it.
    """
    schedule = list(times) if times is not None else list(range(len(values)))
    dense = [encoder.band_index(v) for v in values]
    replayed = reconstruct(encoder.events, len(values), schedule)
    mismatches = sum(1 for a, b in zip(dense, replayed) if a != b)
    error = mismatches / len(values) if values else 0.0

    measurement = {
        "band_error": round(error, 4),
        "event_rate": round(encoder.event_rate, 4),
        "compression": round(encoder.compression, 4),
        "events": len(encoder.events),
        "samples": len(values),
        "threshold": encoder.threshold,
    }
    claim = Claim(
        text=(f"the event stream reproduces the band series to within "
              f"{tolerance:.0%} using {encoder.event_rate:.0%} of the samples"),
        falsification=(f"replaying the events disagrees with the dense band "
                       f"series on more than {tolerance:.0%} of samples"),
        logical_form={"op": "le", "args": ["band_error", tolerance]},
        scope={"threshold": encoder.threshold, "refractory": encoder.refractory,
               "n_bands": len(encoder.bands), "samples": len(values)},
        reference_class="event encodings of this sensor stream",
    )
    claim.evaluate({"band_error": error})
    return claim, measurement
