"""
planner_agent.py – High-level interface for the Startup Planner Agent.

This module wraps the low-level OrchestrateClient to provide a single
clean method: send a startup idea and receive the structured plan back.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from .config import Config
from .orchestrate_client import OrchestrateClient

logger = logging.getLogger(__name__)


@dataclass
class PlannerResult:
    """Return value from the Startup Planner Agent."""

    startup_idea: str
    """The original idea that was submitted."""

    plan: str
    """Free-text plan produced by the agent."""

    session_id: str
    """The Orchestrate session that was used."""

    raw_metadata: dict[str, Any] = field(default_factory=dict)
    """Any extra keys returned alongside the plan (for debugging)."""

    def __str__(self) -> str:
        separator = "─" * 60
        return (
            f"{separator}\n"
            f"STARTUP IDEA\n{separator}\n"
            f"{self.startup_idea}\n\n"
            f"{separator}\n"
            f"PLANNER AGENT OUTPUT\n{separator}\n"
            f"{self.plan}\n"
            f"{separator}\n"
        )


class StartupPlannerAgent:
    """
    Sends a startup idea to the Startup Planner Agent and returns
    a structured :class:`PlannerResult`.

    Parameters
    ----------
    config : Populated :class:`~startup_blueprint.config.Config` object.
    """

    def __init__(self, config: Config) -> None:
        self._config = config
        self._client = OrchestrateClient(
            base_url=config.wxo_base_url,
            api_key=config.wxo_api_key,
            instance_id=config.wxo_instance_id,
            app_id=config.app_id,
            timeout_seconds=config.timeout_seconds,
        )

    # ------------------------------------------------------------------ #
    # Public                                                               #
    # ------------------------------------------------------------------ #

    def run(
        self,
        startup_idea: str,
        *,
        additional_context: dict[str, Any] | None = None,
        poll_interval: float = 3.0,
    ) -> PlannerResult:
        """
        Submit a startup idea to the Planner Agent.

        Parameters
        ----------
        startup_idea       : A natural-language description of the startup idea.
        additional_context : Optional key/value pairs forwarded in the request
                             (e.g. {"industry": "FinTech", "stage": "idea"}).
        poll_interval      : Seconds between successive result polls.

        Returns
        -------
        PlannerResult
        """
        logger.info("Creating Orchestrate session …")
        session_id = self._client.create_session()

        logger.info(
            "Sending startup idea to Planner Agent (agent_id=%s) …",
            self._config.planner_agent_id,
        )
        task_id_or_answer = self._client.send_message(
            session_id=session_id,
            message=self._build_prompt(startup_idea),
            agent_id=self._config.planner_agent_id,
            additional_context=additional_context,
        )

        # send_message may return the final answer inline (synchronous path)
        if self._looks_like_answer(task_id_or_answer):
            plan_text = task_id_or_answer
        else:
            logger.info("Polling for agent response (task_id=%s) …", task_id_or_answer)
            plan_text = self._client.poll_result(
                session_id=session_id,
                task_id=task_id_or_answer,
                poll_interval=poll_interval,
                max_wait=float(self._config.timeout_seconds),
            )

        logger.info("Planner Agent responded successfully.")
        return PlannerResult(
            startup_idea=startup_idea,
            plan=plan_text,
            session_id=session_id,
        )

    # ------------------------------------------------------------------ #
    # Private                                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_prompt(startup_idea: str) -> str:
        return (
            "You are the Startup Planner Agent for the Startup Blueprint Generator.\n"
            "Analyse the following startup idea and produce a comprehensive startup plan.\n"
            "Include: problem statement, target audience, core value proposition, "
            "key milestones, resource requirements, and recommended next steps.\n\n"
            f"STARTUP IDEA:\n{startup_idea}"
        )

    @staticmethod
    def _looks_like_answer(value: str) -> bool:
        """
        Heuristic: if the returned string is more than 40 chars and contains
        a space it is almost certainly prose (an inline answer), not a UUID
        task-ID.
        """
        return len(value) > 40 and " " in value
