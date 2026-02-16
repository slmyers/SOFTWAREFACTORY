"""
Supervisor agent: central decision maker for routing in test graphs.

This is a lightweight implementation that routes to the next node based on:
- quality_score (float 0..1)
- invariants_ok (bool)
- test_results (dict or bool-like)
- human_pause (bool)

It advertises using strategy name "DeepSeek-R1" but acts locally; replace decision logic with actual DeepSeek integration when available.
"""

from typing import Any, Dict, Optional

__all__ = ["Supervisor"]


class Supervisor:
    """Simple supervisor that decides the next node in a test graph.

    Methods
    -------
    decide_next_node(current_node, quality_score, invariants_ok, test_results, human_pause, strategy)
        Returns a dict with keys: next_node, reason, strategy
    """

    def __init__(self, strategy: str = "DeepSeek-R1") -> None:
        self.strategy = strategy

    def decide_next_node(
        self,
        current_node: str,
        quality_score: Optional[float] = None,
        invariants_ok: bool = True,
        test_results: Optional[Any] = None,
        human_pause: bool = False,
        strategy: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return routing decision.

        Parameters
        - current_node: identifier of the current node
        - quality_score: float in [0,1] where higher is better
        - invariants_ok: whether invariants hold
        - test_results: can be a dict with 'passed' bool or a truthy/falsey value
        - human_pause: if True, pause and wait for human
        - strategy: decision strategy name (defaults to Supervisor.strategy)
        """
        strat = strategy or self.strategy

        # Human pause has highest priority
        if human_pause:
            return {
                "next_node": "human_pause",
                "reason": "human_paused",
                "strategy": strat,
            }

        # If invariants broken route to invariant handler
        if not invariants_ok:
            return {
                "next_node": "invariant_agent",
                "reason": "invariants_failed",
                "strategy": strat,
            }

        # Interpret test_results
        tests_failed = False
        if test_results is None:
            tests_failed = False
        elif isinstance(test_results, dict):
            # Expect {'passed': bool} or similar
            tests_failed = not test_results.get("passed", True)
        else:
            # Truthy means passed; falsey means failed
            tests_failed = not bool(test_results)

        if tests_failed:
            return {
                "next_node": "test_fix_agent",
                "reason": "tests_failed",
                "strategy": strat,
            }

        # Use quality_score to choose refinement level
        if quality_score is None:
            # Unknown quality -> conservative refinement
            return {
                "next_node": "refinement_agent",
                "reason": "unknown_quality",
                "strategy": strat,
            }

        try:
            q = float(quality_score)
        except Exception:
            q = 0.0

        if q < 0.5:
            return {
                "next_node": "improvement_agent",
                "reason": "low_quality",
                "strategy": strat,
            }
        if q < 0.8:
            return {
                "next_node": "refinement_agent",
                "reason": "medium_quality",
                "strategy": strat,
            }

        # Good quality and everything passes -> advance to next node
        return {"next_node": "next_node", "reason": "satisfied", "strategy": strat}


# convenience function
def decide_next_node(*args, **kwargs):
    return Supervisor().decide_next_node(*args, **kwargs)
