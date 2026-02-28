from agents.supervisor import Supervisor, decide_next_node


def test_human_pause_has_priority():
    sup = Supervisor()
    r = sup.decide_next_node("nodeA", human_pause=True)
    assert r["next_node"] == "human_pause"
    assert r["reason"] == "human_paused"


def test_invariants_route_to_invariant_agent():
    sup = Supervisor()
    r = sup.decide_next_node("nodeA", invariants_ok=False)
    assert r["next_node"] == "invariant_agent"


def test_failed_tests_route_to_test_fix_agent():
    sup = Supervisor()
    r = sup.decide_next_node("nodeA", test_results={"passed": False})
    assert r["next_node"] == "test_fix_agent"


def test_quality_routing_levels():
    sup = Supervisor()
    # unknown quality -> improvement (since q=0.0 < 50)
    r = sup.decide_next_node("nodeA", quality_score=None)
    assert r["next_node"] == "improvement_agent"

    # low quality (0..100 scale)
    r = sup.decide_next_node("nodeA", quality_score=30)
    assert r["next_node"] == "improvement_agent"

    # medium quality
    r = sup.decide_next_node("nodeA", quality_score=60)
    assert r["next_node"] == "refinement_agent"

    # high quality
    r = sup.decide_next_node("nodeA", quality_score=95)
    assert r["next_node"] == "next_node"


def test_convenience_function_matches_class():
    # ensure decide_next_node convenience function behaves the same
    rc = decide_next_node("nodeA", quality_score=95)
    s = Supervisor().decide_next_node("nodeA", quality_score=95)
    assert rc == s


# Synthetic state tests for hybrid logic
def test_synthetic_state_1_high_quality_clear():
    """High quality, all checks pass -> next_node"""
    sup = Supervisor()
    r = sup.decide_next_node(
        "coder",
        quality_score=90,
        invariants_ok=True,
        test_results={"passed": True},
        human_pause=False,
    )
    assert r["next_node"] == "next_node"
    assert r["reason"] == "high_quality"


def test_synthetic_state_2_tests_failed_clear():
    """Tests failed -> test_fix_agent"""
    sup = Supervisor()
    r = sup.decide_next_node(
        "reviewer",
        quality_score=80,
        invariants_ok=True,
        test_results={"passed": False},
        human_pause=False,
    )
    assert r["next_node"] == "test_fix_agent"
    assert r["reason"] == "tests_failed"


def test_synthetic_state_3_invariants_failed_clear():
    """Invariants failed -> invariant_agent"""
    sup = Supervisor()
    r = sup.decide_next_node(
        "executor",
        quality_score=70,
        invariants_ok=False,
        test_results={"passed": True},
        human_pause=False,
    )
    assert r["next_node"] == "invariant_agent"
    assert r["reason"] == "invariants_failed"


def test_synthetic_state_4_ambiguous_medium_quality():
    """Ambiguous quality 70 -> refinement_agent (fallback)"""
    sup = Supervisor()
    r = sup.decide_next_node(
        "coder",
        quality_score=70,
        invariants_ok=True,
        test_results={"passed": True},
        human_pause=False,
    )
    assert r["next_node"] == "refinement_agent"
    assert r["reason"] == "medium_quality_fallback"


def test_synthetic_state_5_ambiguous_low_quality():
    """Ambiguous quality 40 -> improvement_agent (fallback)"""
    sup = Supervisor()
    r = sup.decide_next_node(
        "reviewer",
        quality_score=40,
        invariants_ok=True,
        test_results={"passed": True},
        human_pause=False,
    )
    assert r["next_node"] == "improvement_agent"
    assert r["reason"] == "low_quality_fallback"
