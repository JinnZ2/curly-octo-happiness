"""Memory stores.

EpisodicMemory — speaker-tagged events with keyword-overlap retrieval
(the unified_playground / weave_with_memory line).
MemoryStream   — content-only stream with tag sampling (weave.py line).
SharedMemory   — free-form event dicts (shared.py / playground4-8 line).
"""

import re
import time
from collections import deque
from datetime import datetime
from typing import Any, Dict


class EpisodicMemory:
    def __init__(self, max_events=500):
        self.events = deque(maxlen=max_events)

    def add(self, speaker, content, tags=None):
        self.events.append({
            "timestamp": datetime.now(),
            "speaker": speaker,
            "content": content,
            "tags": tags or []
        })

    def retrieve(self, query, k=3):
        """Keyword-overlap retrieval with a small recency boost."""
        query_words = set(re.findall(r'\w+', query.lower()))
        scored = []
        for i, ev in enumerate(self.events):
            ev_words = set(re.findall(r'\w+', ev["content"].lower()))
            overlap = len(query_words & ev_words)
            recency = 1.0 / (1 + len(self.events) - i)
            scored.append((overlap + 0.1 * recency, ev))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [ev for score, ev in scored[:k]]

    def recent(self, n=5):
        return list(self.events)[-n:]


class MemoryStream:
    def __init__(self, capacity=50):
        self.events = deque(maxlen=capacity)

    def add(self, content, tags=None):
        self.events.append({
            "timestamp": datetime.now().isoformat(),
            "content": content,
            "tags": tags or []
        })

    def recent(self, n=5):
        return list(self.events)[-n:]

    def sample_by_tag(self, tag):
        return [e for e in self.events if tag in e["tags"]]

    def all(self):
        return list(self.events)


class SharedMemory:
    def __init__(self, capacity=1000):
        self.stream = deque(maxlen=capacity)

    def add(self, event: Dict[str, Any]):
        event['timestamp'] = time.time()
        self.stream.append(event)

    def recent(self, n=10):
        return list(self.stream)[-n:]
