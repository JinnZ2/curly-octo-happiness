from grounding.core.claims import Claim, DependencyTree
from grounding.core.memory import EpisodicMemory


def test_claim_status_transitions():
    c = Claim("water boils at 100C", "thermometer reads other value at boil")
    assert c.status == "active"
    for _ in range(3):
        c.test(True)
    assert c.status == "survived"
    d = Claim("x", "y")
    for _ in range(3):
        d.test(False)
    assert d.status == "falsified"


def test_claim_confidence_bounds():
    c = Claim("x", "y")
    for _ in range(50):
        c.test(True)
    assert c.confidence == 1.0
    for _ in range(50):
        c.test(False)
    assert c.confidence == 0.0


def test_tree_aliases_and_propagation():
    t = DependencyTree()
    t.add_dependency("a", "b")
    assert t.get_or_create("a") is t.get("a")
    assert t.add_node("c") is t.get("c")

    good = Claim("g", "f")
    for _ in range(5):
        good.test(True)
    t.add_claim("b", good)
    t.propagate_confidence()
    b_conf = t.nodes["b"].confidence
    assert b_conf > 0.5                      # claim confidence lifted the node
    # confidence travels one hop per pass: after the second pass, "a"
    # (claimless, depending on "b") rises above its 0.5 prior
    t.recalibrate()                          # alias of propagate_confidence
    assert t.nodes["a"].confidence > 0.5
    assert abs(t.nodes["a"].confidence - (0.5 + b_conf) / 2) < 1e-9

    assert "Dependency Tree:" in t.summary()
    assert t.summary() == t.summary_text()


def test_node_dependencies_alias():
    t = DependencyTree()
    t.add_dependency("a", "b")
    assert t.nodes["a"].dependencies == t.nodes["a"].deps == {"b"}


def test_episodic_memory_retrieval():
    m = EpisodicMemory()
    m.add("user", "the red fox jumped")
    m.add("user", "completely unrelated text")
    m.add("agent", "I saw the fox too")
    hits = m.retrieve("where is the fox", k=2)
    assert all("fox" in h["content"] for h in hits)
    assert len(m.recent(2)) == 2
