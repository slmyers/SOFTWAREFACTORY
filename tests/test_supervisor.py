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
    # unknown quality -> refinement
    r = sup.decide_next_node("nodeA", quality_score=None)
    assert r["next_node"] == "refinement_agent"

    # low quality
    r = sup.decide_next_node("nodeA", quality_score=0.3)
    assert r["next_node"] == "improvement_agent"

    # medium quality
    r = sup.decide_next_node("nodeA", quality_score=0.6)
    assert r["next_node"] == "refinement_agent"

    # high quality
    r = sup.decide_next_node("nodeA", quality_score=0.95)
    assert r["next_node"] == "next_node"


def test_convenience_function_matches_class():
    # ensure decide_next_node convenience function behaves the same
    rc = decide_next_node("nodeA", quality_score=0.95)
    s = Supervisor().decide_next_node("nodeA", quality_score=0.95)
    assert rc == s
