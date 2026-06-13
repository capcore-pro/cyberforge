"""Comparaison A/B de prompts via benchmarks qualité."""

from __future__ import annotations

from typing import Any

from db.prompt_store import PromptStore, get_prompt_store


class ABTestingEngine:
    def __init__(self, store: PromptStore | None = None) -> None:
        self._store = store or get_prompt_store()

    async def compare(
        self,
        prompt_slug_a: str,
        prompt_slug_b: str,
        min_samples: int = 3,
    ) -> dict[str, Any]:
        prompt_a = await self._store.get_by_slug(prompt_slug_a)
        prompt_b = await self._store.get_by_slug(prompt_slug_b)

        if not prompt_a or not prompt_b:
            return {
                "winner": "error",
                "error": "Un ou deux prompts introuvables",
            }

        benchmarks_a = await self._store.list_benchmarks(
            prompt_id=str(prompt_a["id"]),
            limit=20,
        )
        benchmarks_b = await self._store.list_benchmarks(
            prompt_id=str(prompt_b["id"]),
            limit=20,
        )

        if len(benchmarks_a) < min_samples or len(benchmarks_b) < min_samples:
            return {
                "winner": "insufficient_data",
                "prompt_a": {
                    "slug": prompt_slug_a,
                    "samples": len(benchmarks_a),
                },
                "prompt_b": {
                    "slug": prompt_slug_b,
                    "samples": len(benchmarks_b),
                },
                "recommendation": (
                    f"Minimum {min_samples} benchmarks requis par prompt"
                ),
            }

        avg_a = sum(b["quality_score"] for b in benchmarks_a) / len(benchmarks_a)
        avg_b = sum(b["quality_score"] for b in benchmarks_b) / len(benchmarks_b)

        diff = abs(avg_a - avg_b)
        confidence = (
            "high"
            if diff > 10
            else "medium"
            if diff > 5
            else "low"
        )
        winner = (
            "a"
            if avg_a > avg_b + 2
            else "b"
            if avg_b > avg_a + 2
            else "tie"
        )

        return {
            "winner": winner,
            "prompt_a": {
                "slug": prompt_slug_a,
                "avg_score": round(avg_a, 1),
                "samples": len(benchmarks_a),
            },
            "prompt_b": {
                "slug": prompt_slug_b,
                "avg_score": round(avg_b, 1),
                "samples": len(benchmarks_b),
            },
            "confidence": confidence,
            "recommendation": (
                f"Utiliser {prompt_slug_a} (+{avg_a - avg_b:.1f} pts)"
                if winner == "a"
                else f"Utiliser {prompt_slug_b} (+{avg_b - avg_a:.1f} pts)"
                if winner == "b"
                else "Résultats équivalents"
            ),
        }


ab_testing_engine = ABTestingEngine()
