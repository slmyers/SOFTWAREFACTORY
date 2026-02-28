"""
Supervisor agent: central decision maker for routing in test graphs.

This is a hybrid implementation: fast rules for clear cases, DeepSeek-R1 for ambiguous cases (quality_score < 0.85).
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from openai import OpenAI

__all__ = ["Supervisor"]


class Supervisor:
    """Hybrid supervisor: rules for clear cases, DeepSeek-R1 for ambiguous.

    Methods
    -------
    decide_next_node(current_node, quality_score, invariants_ok, test_results, human_pause, strategy)
        Returns a dict with keys: next_node, reason, strategy
    """

    def __init__(self, strategy: str = "Hybrid-Rule+DeepSeek-R1") -> None:
        self.strategy = strategy
        self.client = OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
        )
        self.prompt_path = (
            Path(__file__).parent.parent / "prompts" / "supervisor_decision.md"
        )

    def _call_deepseek(
        self,
        quality_score: float,
        invariants_ok: bool,
        test_results: Any,
        human_pause: bool,
        current_node: str,
    ) -> Dict[str, Any]:
        """Call DeepSeek-R1 for ambiguous decisions."""
        # Compute q for fallback — quality_score is on a 0..100 scale
        if quality_score is None:
            q = 0.0
        else:
            try:
                q = float(quality_score)
            except Exception:
                q = 0.0

        try:
            with open(self.prompt_path, "r") as f:
                prompt_template = f.read()

            prompt = prompt_template.format(
                quality_score=quality_score,
                invariants_ok=invariants_ok,
                test_results=test_results,
                human_pause=human_pause,
                current_node=current_node,
            )

            response = self.client.chat.completions.create(
                model="deepseek/deepseek-r1",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.1,
            )

            content = response.choices[0].message.content.strip()
            result = json.loads(content)
            return result
        except Exception:
            # Fallback to rule-based for ambiguous cases
            if q < 50.0:
                return {
                    "next_node": "improvement_agent",
                    "reason": "low_quality_fallback",
                }
            else:
                return {
                    "next_node": "refinement_agent",
                    "reason": "medium_quality_fallback",
                }

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
        - quality_score: float in [0, 100] where higher is better
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

        # Use quality_score to decide
        if quality_score is None:
            q = 0.0
        else:
            try:
                q = float(quality_score)
            except Exception:
                q = 0.0

        # quality_score is on a 0..100 scale; threshold is 85.0
        if q >= 85.0:
            return {
                "next_node": "next_node",
                "reason": "high_quality",
                "strategy": strat,
            }
        else:
            # Ambiguous case: call DeepSeek-R1
            result = self._call_deepseek(
                q, invariants_ok, test_results, human_pause, current_node
            )
            return {**result, "strategy": strat}


# convenience function
def decide_next_node(*args, **kwargs):
    return Supervisor().decide_next_node(*args, **kwargs)
