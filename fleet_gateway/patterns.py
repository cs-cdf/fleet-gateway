"""
fleet_gateway.patterns — High-level multi-model reasoning patterns.

Patterns call multiple models in parallel or sequence, then aggregate
or synthesize results. Useful for tasks where a single model answer
isn't sufficient.

Available patterns:
  consensus   — Ask N models the same question; optionally synthesize
  loop        — Iterative refinement (feed each response as context)
  review      — Multi-model review with structured synthesis
  challenge   — Devil's advocate: stress-test an idea/decision
  brainstorm  — Multi-model idea generation, deduplicated
  swot        — SWOT analysis (Strengths, Weaknesses, Opportunities, Threats)
  perspectives — Get multiple expert viewpoints on a topic
  adversarial  — Red-team an idea for flaws and attack vectors

Usage:
    from fleet_gateway import Fleet
    fleet = Fleet()

    # Consensus across 3 models
    result = fleet.patterns.consensus("Is Rust better than Go for CLIs?")
    print(result["synthesis"])    # synthesized answer
    print(result["responses"])    # individual model responses

    # Iterative refinement
    final = fleet.patterns.loop("Write a Python sorting function", iterations=3)

    # Devil's advocate
    critique = fleet.patterns.challenge("We should rewrite everything in microservices")
"""

from __future__ import annotations

import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED
from typing import Any, Dict, List, Optional, Union

from .router import Router


class Patterns:
    """High-level multi-model reasoning patterns.

    Accessed via fleet.patterns (automatically created by Fleet).
    """

    def __init__(self, router: Router):
        self._router = router

    # ── Helpers ─────────────────────────────────────────────────

    def _call(self, model: str, messages: list, **kw) -> Optional[str]:
        return self._router.call(model, messages=messages, **kw)

    def _parallel_call(
        self,
        models: List[str],
        messages: list,
        timeout: float = 120.0,
        **kw,
    ) -> Dict[str, Optional[str]]:
        """Call multiple models in parallel. Returns {model: response}."""
        results: Dict[str, Optional[str]] = {}
        with ThreadPoolExecutor(max_workers=min(len(models), 8)) as pool:
            futures = {pool.submit(self._call, m, messages, timeout=timeout, **kw): m for m in models}
            for fut in as_completed(futures, timeout=timeout + 5):
                model_name = futures[fut]
                try:
                    results[model_name] = fut.result()
                except Exception as e:
                    _log(f"Model {model_name!r} failed: {e}")
                    results[model_name] = None
        return results

    def _default_models(self, n: int = 3) -> List[str]:
        """Pick the top N available models from the routing table."""
        available = [m for m in self._router.available_models() if m["available"]]
        # Prefer models with broader capabilities
        preferred = [m for m in available if "general" in m.get("capabilities", [])]
        pool = preferred or available
        seen_backends: set = set()
        chosen = []
        for m in pool:
            backend = m["backend"]
            if backend not in seen_backends:
                seen_backends.add(backend)
                chosen.append(m["id"])
            if len(chosen) >= n:
                break
        # Fill up if needed
        if len(chosen) < n:
            for m in pool:
                if m["id"] not in chosen:
                    chosen.append(m["id"])
                if len(chosen) >= n:
                    break
        return chosen[:n]

    # ── Patterns ─────────────────────────────────────────────────

    def consensus(
        self,
        question: Union[str, list],
        models: Optional[List[str]] = None,
        n: int = 3,
        synthesize: bool = True,
        synthesis_model: Optional[str] = None,
        system: Optional[str] = None,
        max_tokens: int = 2048,
        timeout: float = 120.0,
    ) -> Dict[str, Any]:
        """Ask N models the same question; optionally synthesize into one answer.

        Args:
            question: Prompt string or message list.
            models: Explicit list of "backend/model_id" to use. If None, auto-selects.
            n: Number of models to use (when models=None).
            synthesize: If True, add a synthesis pass combining all responses.
            synthesis_model: Model used for synthesis. Defaults to "reasoning".
            system: Optional system prompt injected into all calls.
            max_tokens: Max tokens per model response.
            timeout: Timeout per model in seconds.

        Returns:
            {
                "responses": {"model_id": "text", ...},
                "synthesis": "synthesized answer" (if synthesize=True),
                "models_used": [...],
                "models_failed": [...],
            }
        """
        if models is None:
            models = self._default_models(n)

        msgs = _norm(question, system)
        _log(f"consensus: asking {len(models)} models: {models}")
        raw = self._parallel_call(models, msgs, max_tokens=max_tokens, timeout=timeout)

        responses = {k: v for k, v in raw.items() if v is not None}
        failed = [k for k, v in raw.items() if v is None]

        result: Dict[str, Any] = {
            "responses": responses,
            "models_used": list(responses.keys()),
            "models_failed": failed,
            "synthesis": None,
        }

        if synthesize and responses:
            synthesis_prompt = _build_synthesis_prompt(question, responses)
            synth = self._call(
                synthesis_model or "reasoning",
                messages=[{"role": "user", "content": synthesis_prompt}],
                max_tokens=max_tokens,
                timeout=timeout,
            )
            result["synthesis"] = synth

        return result

    def loop(
        self,
        prompt: str,
        iterations: int = 3,
        model: str = "general",
        critique_model: Optional[str] = None,
        max_tokens: int = 2048,
        timeout: float = 120.0,
    ) -> Dict[str, Any]:
        """Iterative refinement: generate → critique → improve, N times.

        Each iteration feeds the previous response as context and asks
        the model to improve it.

        Args:
            prompt: Initial task or question.
            iterations: Number of refinement cycles (2-5 recommended).
            model: Model for generation steps.
            critique_model: Model for critique steps. Defaults to same as model.
            max_tokens: Max tokens per step.
            timeout: Timeout per call.

        Returns:
            {
                "final": "final improved response",
                "history": [{"step": n, "role": "generate|critique", "content": ...}],
                "iterations": N,
            }
        """
        history: List[Dict[str, Any]] = []
        messages = [{"role": "user", "content": prompt}]
        current = None

        for i in range(iterations):
            is_last = (i == iterations - 1)

            if current is None:
                # First generation
                current = self._call(model, messages=messages, max_tokens=max_tokens, timeout=timeout)
                if current is None:
                    break
                history.append({"step": i + 1, "role": "generate", "content": current})
                _log(f"loop step {i+1}: generated ({len(current)} chars)")
            else:
                if not is_last:
                    # Critique step
                    critique_msgs = messages + [
                        {"role": "assistant", "content": current},
                        {"role": "user", "content": (
                            "Review the response above critically. "
                            "Identify specific weaknesses, errors, or areas to improve. "
                            "Be concrete and direct."
                        )},
                    ]
                    critique = self._call(
                        critique_model or model,
                        messages=critique_msgs,
                        max_tokens=max_tokens // 2,
                        timeout=timeout,
                    )
                    if critique:
                        history.append({"step": i + 1, "role": "critique", "content": critique})
                        _log(f"loop step {i+1}: critique ({len(critique)} chars)")

                    # Improve step
                    improve_msgs = messages + [
                        {"role": "assistant", "content": current},
                        {"role": "user", "content": (
                            f"Here is a critique of your response:\n\n{critique}\n\n"
                            "Now rewrite your response, addressing all the issues raised. "
                            "Make it significantly better."
                        )},
                    ]
                    improved = self._call(model, messages=improve_msgs, max_tokens=max_tokens, timeout=timeout)
                    if improved:
                        current = improved
                        history.append({"step": i + 1, "role": "generate", "content": current})
                        _log(f"loop step {i+1}: improved ({len(current)} chars)")

        return {
            "final": current,
            "history": history,
            "iterations": len([h for h in history if h["role"] == "generate"]),
        }

    def review(
        self,
        content: str,
        content_type: str = "code",
        models: Optional[List[str]] = None,
        n: int = 3,
        synthesis_model: Optional[str] = None,
        max_tokens: int = 2048,
        timeout: float = 120.0,
    ) -> Dict[str, Any]:
        """Multi-model review with structured synthesis.

        Args:
            content: Code, text, or document to review.
            content_type: "code", "text", "document", "plan", "essay"
            models: Explicit list of models. If None, auto-selects coding/general models.
            n: Number of models to use.
            synthesis_model: Model for final synthesis.
            max_tokens: Max tokens per reviewer.
            timeout: Timeout per call.

        Returns:
            {
                "reviews": {"model_id": "review text", ...},
                "synthesis": "consolidated review with key findings",
                "models_used": [...],
            }
        """
        type_instructions = {
            "code": (
                "You are a senior software engineer doing a code review. "
                "Identify: bugs, security issues, performance problems, readability issues, "
                "and concrete improvements. Be specific and actionable."
            ),
            "text": (
                "You are an expert editor. Review the text for: clarity, structure, "
                "logical flow, tone, and specific improvements. Be direct and concrete."
            ),
            "document": (
                "You are an expert technical writer. Review for: completeness, accuracy, "
                "structure, clarity, and missing information."
            ),
            "plan": (
                "You are a critical strategic advisor. Review the plan for: feasibility, "
                "risks, missing steps, dependencies, and potential failure modes."
            ),
            "essay": (
                "You are a critical academic reviewer. Evaluate: argument strength, "
                "evidence quality, logical consistency, and clarity of thesis."
            ),
        }
        system = type_instructions.get(content_type, type_instructions["text"])
        prompt = f"Review the following {content_type}:\n\n```\n{content}\n```"

        result = self.consensus(
            prompt,
            models=models,
            n=n,
            synthesize=False,
            system=system,
            max_tokens=max_tokens,
            timeout=timeout,
        )

        # Synthesis tailored for reviews
        if result["responses"]:
            synth_prompt = (
                f"Multiple reviewers have analyzed this {content_type}. "
                f"Synthesize their feedback into a structured review:\n\n"
            )
            for model_name, review in result["responses"].items():
                synth_prompt += f"**Reviewer {model_name}:**\n{review}\n\n"
            synth_prompt += (
                "Produce a consolidated review with:\n"
                "1. Key issues (ranked by severity)\n"
                "2. Strengths\n"
                "3. Specific actionable improvements\n"
            )
            synthesis = self._call(
                synthesis_model or "reasoning",
                messages=[{"role": "user", "content": synth_prompt}],
                max_tokens=max_tokens,
                timeout=timeout,
            )
            result["synthesis"] = synthesis

        result["reviews"] = result.pop("responses")
        return result

    def challenge(
        self,
        idea_or_decision: str,
        depth: str = "thorough",
        model: str = "reasoning",
        max_tokens: int = 2048,
        timeout: float = 120.0,
    ) -> Dict[str, Any]:
        """Devil's advocate: stress-test an idea, assumption, or decision.

        Generates structured critique: counterarguments, risks, hidden assumptions,
        better alternatives, and failure scenarios.

        Args:
            idea_or_decision: The claim, plan, or decision to challenge.
            depth: "quick" (3 weaknesses), "thorough" (full analysis), "deep" (red team)
            model: Model to use for challenging.
            max_tokens: Max tokens.
            timeout: Timeout.

        Returns:
            {
                "challenge": "full devil's advocate response",
                "structure": {
                    "counterarguments": [...],
                    "hidden_assumptions": [...],
                    "risks": [...],
                    "better_alternatives": [...],
                    "failure_scenarios": [...],
                } (best-effort parsing)
            }
        """
        depth_instructions = {
            "quick": "List 3 key weaknesses and 1 better alternative. Be brief.",
            "thorough": (
                "Provide a thorough devil's advocate analysis with:\n"
                "1. Strongest counterarguments (at least 3)\n"
                "2. Hidden assumptions being made\n"
                "3. Key risks and failure modes\n"
                "4. Better alternatives to consider\n"
                "5. The strongest version of the opposing view"
            ),
            "deep": (
                "Act as an adversarial red team. Your goal is to find every flaw, "
                "attack vector, and failure mode. Be rigorous:\n"
                "1. Logical flaws and fallacies\n"
                "2. Hidden assumptions (list all of them)\n"
                "3. Technical/practical risks\n"
                "4. Economic/incentive misalignments\n"
                "5. Failure scenarios (best case, worst case, most likely)\n"
                "6. What would need to be true for this to be a good idea?\n"
                "7. What are 3 better alternatives?\n"
                "8. Steelman the opposition"
            ),
        }

        system = (
            "You are a rigorous critical thinker and devil's advocate. "
            "Your job is NOT to be constructive or helpful — "
            "your job is to find every weakness, flaw, and problem. "
            "Be honest, direct, and don't sugarcoat."
        )
        prompt = (
            f"Play devil's advocate for the following idea/decision:\n\n"
            f"**{idea_or_decision}**\n\n"
            f"{depth_instructions.get(depth, depth_instructions['thorough'])}"
        )

        response = self._call(
            model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            timeout=timeout,
        )

        return {
            "challenge": response,
            "depth": depth,
            "model": model,
        }

    def brainstorm(
        self,
        topic: str,
        models: Optional[List[str]] = None,
        n: int = 3,
        deduplicate: bool = True,
        synthesis_model: Optional[str] = None,
        max_tokens: int = 2048,
        timeout: float = 120.0,
    ) -> Dict[str, Any]:
        """Multi-model brainstorm: generate diverse ideas from multiple perspectives.

        Args:
            topic: What to brainstorm about.
            models: Models to use. If None, auto-selects.
            n: Number of models.
            deduplicate: Ask synthesis model to remove duplicates and rank ideas.
            synthesis_model: Model for deduplication/ranking.
            max_tokens: Max tokens per model.
            timeout: Timeout per call.

        Returns:
            {
                "raw_ideas": {"model_id": "ideas text", ...},
                "synthesis": "deduplicated ranked ideas" (if deduplicate=True),
                "models_used": [...],
            }
        """
        system = (
            "You are a creative brainstorming assistant. "
            "Generate diverse, creative, and unconventional ideas. "
            "Don't filter yourself — quantity and variety matter more than perfection. "
            "Each idea should be distinct and non-obvious."
        )
        prompt = (
            f"Brainstorm ideas for: {topic}\n\n"
            "Generate at least 8 distinct ideas. "
            "Format as a numbered list. "
            "Include both conventional and unconventional ideas."
        )

        result = self.consensus(
            prompt,
            models=models,
            n=n,
            synthesize=False,
            system=system,
            max_tokens=max_tokens,
            timeout=timeout,
        )

        if deduplicate and result["responses"]:
            all_ideas = "\n\n".join(
                f"[{model}]:\n{ideas}"
                for model, ideas in result["responses"].items()
            )
            synth_prompt = (
                f"Multiple models brainstormed ideas for: {topic}\n\n"
                f"{all_ideas}\n\n"
                "Synthesize these into a ranked list of the best and most diverse ideas:\n"
                "1. Remove obvious duplicates\n"
                "2. Keep the most interesting and actionable ideas\n"
                "3. Rank from most to least promising\n"
                "4. Add a brief note on why each top idea is valuable\n"
            )
            synthesis = self._call(
                synthesis_model or "general",
                messages=[{"role": "user", "content": synth_prompt}],
                max_tokens=max_tokens,
                timeout=timeout,
            )
        else:
            synthesis = None

        return {
            "raw_ideas": result["responses"],
            "synthesis": synthesis,
            "models_used": result["models_used"],
            "models_failed": result["models_failed"],
        }

    def swot(
        self,
        subject: str,
        context: str = "",
        model: str = "reasoning",
        max_tokens: int = 2048,
        timeout: float = 120.0,
    ) -> Dict[str, Any]:
        """SWOT analysis: Strengths, Weaknesses, Opportunities, Threats.

        Args:
            subject: What to analyze (product, business, strategy, technology, etc.)
            context: Optional additional context.
            model: Model to use.
            max_tokens: Max tokens.
            timeout: Timeout.

        Returns:
            {
                "analysis": "full SWOT analysis text",
                "parsed": {
                    "strengths": [...],
                    "weaknesses": [...],
                    "opportunities": [...],
                    "threats": [...],
                } (best-effort parsing)
            }
        """
        context_str = f"\nContext: {context}" if context else ""
        prompt = (
            f"Perform a comprehensive SWOT analysis for:\n\n**{subject}**{context_str}\n\n"
            "Structure your response as:\n\n"
            "## Strengths\n(internal advantages)\n\n"
            "## Weaknesses\n(internal disadvantages)\n\n"
            "## Opportunities\n(external possibilities)\n\n"
            "## Threats\n(external risks)\n\n"
            "For each section, list 3-5 specific, concrete points. "
            "Be realistic and avoid generic statements."
        )

        response = self._call(
            model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            timeout=timeout,
        )

        return {
            "analysis": response,
            "subject": subject,
            "parsed": _parse_swot(response) if response else {},
        }

    def perspectives(
        self,
        topic: str,
        viewpoints: Optional[List[str]] = None,
        models: Optional[List[str]] = None,
        synthesis_model: Optional[str] = None,
        max_tokens: int = 2048,
        timeout: float = 120.0,
    ) -> Dict[str, Any]:
        """Get multiple expert viewpoints on a topic.

        Each model is assigned a different expert persona.

        Args:
            topic: Topic or question to explore.
            viewpoints: List of expert roles. Defaults to a balanced set.
            models: Models to use. If None, auto-selects one per viewpoint.
            synthesis_model: Model for final synthesis.
            max_tokens: Max tokens per perspective.
            timeout: Timeout per call.

        Returns:
            {
                "perspectives": {"role": "response", ...},
                "synthesis": "integrated multi-perspective view",
            }
        """
        default_viewpoints = [
            "skeptical critic",
            "optimistic advocate",
            "pragmatic engineer",
            "end user",
            "domain expert",
        ]
        viewpoints = viewpoints or default_viewpoints[:3]

        if models is None:
            models = self._default_models(len(viewpoints))
        # Pair each viewpoint with a model (cycle if fewer models than viewpoints)
        pairs = [(viewpoints[i], models[i % len(models)]) for i in range(len(viewpoints))]

        def _ask_perspective(role: str, model: str) -> tuple[str, Optional[str]]:
            msgs = [
                {"role": "system", "content": f"You are a {role}. Respond from that perspective only."},
                {"role": "user", "content": topic},
            ]
            return role, self._call(model, messages=msgs, max_tokens=max_tokens, timeout=timeout)

        persp_results: Dict[str, Optional[str]] = {}
        with ThreadPoolExecutor(max_workers=len(pairs)) as pool:
            futures = {pool.submit(_ask_perspective, r, m): (r, m) for r, m in pairs}
            for fut in as_completed(futures, timeout=timeout + 5):
                try:
                    role, resp = fut.result()
                    persp_results[role] = resp
                except Exception:
                    pass

        valid = {k: v for k, v in persp_results.items() if v}

        synthesis = None
        if valid and synthesis_model is not False:
            synth_parts = "\n\n".join(f"**{role}**: {resp}" for role, resp in valid.items())
            synth_prompt = (
                f"Topic: {topic}\n\nMultiple experts have shared their perspectives:\n\n"
                f"{synth_parts}\n\n"
                "Synthesize these viewpoints into a balanced, nuanced analysis that:\n"
                "1. Identifies points of agreement\n"
                "2. Highlights key tensions and trade-offs\n"
                "3. Draws actionable conclusions\n"
            )
            synthesis = self._call(
                synthesis_model or "reasoning",
                messages=[{"role": "user", "content": synth_prompt}],
                max_tokens=max_tokens,
                timeout=timeout,
            )

        return {
            "perspectives": valid,
            "synthesis": synthesis,
            "viewpoints": viewpoints,
        }

    def adversarial(
        self,
        claim_or_plan: str,
        rounds: int = 2,
        attacker_model: str = "reasoning",
        defender_model: str = "general",
        max_tokens: int = 1024,
        timeout: float = 120.0,
    ) -> Dict[str, Any]:
        """Structured adversarial debate: attacker vs defender.

        Args:
            claim_or_plan: The claim or plan being evaluated.
            rounds: Number of attack/defend rounds.
            attacker_model: Model playing the attacker role.
            defender_model: Model playing the defender role.
            max_tokens: Max tokens per turn.
            timeout: Timeout per call.

        Returns:
            {
                "debate": [{"role": "attacker|defender", "content": ...}],
                "verdict": "final assessment of whether claim survived scrutiny",
            }
        """
        debate: List[Dict[str, str]] = []
        context = claim_or_plan

        for i in range(rounds):
            # Attack
            attack_msgs = [
                {"role": "system", "content": "You are a rigorous critic. Find the fatal flaw."},
                {"role": "user", "content": (
                    f"Round {i+1} attack. Find the most damaging weakness in:\n\n{context}\n\n"
                    "Be specific and devastating. Cite evidence where possible."
                )},
            ]
            attack = self._call(attacker_model, messages=attack_msgs, max_tokens=max_tokens, timeout=timeout)
            if attack:
                debate.append({"role": "attacker", "round": i + 1, "content": attack})
                _log(f"adversarial round {i+1}: attack ({len(attack)} chars)")

            # Defend
            defense_msgs = [
                {"role": "system", "content": "You are a rigorous defender. Address each attack directly."},
                {"role": "user", "content": (
                    f"The following attack has been made against:\n\n{context}\n\n"
                    f"**Attack:** {attack}\n\n"
                    "Defend point by point. Acknowledge valid concerns but refute invalid ones."
                )},
            ]
            defense = self._call(defender_model, messages=defense_msgs, max_tokens=max_tokens, timeout=timeout)
            if defense:
                debate.append({"role": "defender", "round": i + 1, "content": defense})
                context = f"{claim_or_plan}\n\nDefense: {defense}"

        # Verdict
        verdict_msgs = [
            {"role": "user", "content": (
                f"After this adversarial debate about:\n\n{claim_or_plan}\n\n"
                f"**Debate:**\n" + "\n\n".join(f"[{d['role'].upper()} R{d['round']}]: {d['content']}" for d in debate) +
                "\n\nGive a final objective verdict:\n"
                "1. Did the claim/plan survive scrutiny?\n"
                "2. What are the 1-2 most valid criticisms?\n"
                "3. What modifications would strengthen it?\n"
                "4. Overall recommendation (proceed / modify / abandon)"
            )},
        ]
        verdict = self._call("reasoning", messages=verdict_msgs, max_tokens=max_tokens * 2, timeout=timeout)

        return {
            "debate": debate,
            "verdict": verdict,
            "rounds": rounds,
        }


# ── Helpers ────────────────────────────────────────────────────────────────────

def _norm(prompt: Union[str, list], system: Optional[str] = None) -> list:
    if isinstance(prompt, str):
        msgs = [{"role": "user", "content": prompt}]
    else:
        msgs = list(prompt)
    if system:
        msgs = [{"role": "system", "content": system}] + msgs
    return msgs


def _build_synthesis_prompt(question: Union[str, list], responses: Dict[str, str]) -> str:
    q = question if isinstance(question, str) else (question[-1].get("content", "") if question else "")
    parts = [f"**{model}:**\n{resp}" for model, resp in responses.items()]
    return (
        f"Multiple AI models have answered the following question:\n\n**{q}**\n\n"
        + "\n\n".join(parts)
        + "\n\nSynthesize these responses into a single, comprehensive answer that:\n"
        "1. Captures the key points of agreement\n"
        "2. Addresses important differences or nuances\n"
        "3. Provides the most complete and accurate answer possible\n"
        "Be direct and avoid just listing what each model said."
    )


def _parse_swot(text: str) -> Dict[str, List[str]]:
    """Best-effort parser for SWOT sections."""
    import re
    result: Dict[str, List[str]] = {"strengths": [], "weaknesses": [], "opportunities": [], "threats": []}
    current = None
    for line in text.splitlines():
        line_lower = line.lower().strip()
        if "strength" in line_lower:
            current = "strengths"
        elif "weakness" in line_lower:
            current = "weaknesses"
        elif "opportunit" in line_lower:
            current = "opportunities"
        elif "threat" in line_lower:
            current = "threats"
        elif current and re.match(r"^[-*\d\.]", line.strip()):
            item = re.sub(r"^[-*\d\.\s]+", "", line).strip()
            if item:
                result[current].append(item)
    return result


def _log(msg: str):
    print(f"[fleet_gateway.patterns] {msg}", file=sys.stderr, flush=True)
