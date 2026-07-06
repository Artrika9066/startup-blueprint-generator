"""
blueprint_agents.py – All 6 specialised agents for the Startup Blueprint Generator.

Each agent sends its prompt directly to the IBM watsonx Orchestrate endpoint:
    POST /v1/agents/{agent_id}/chat

Agents
------
1. StartupPlannerAgent      – core plan, milestones, value proposition
2. MarketIntelligenceAgent  – market size, competitors, trends
3. BusinessStrategyAgent    – business model, competitive moat, partnerships
4. FinanceFundingAgent      – financial projections, funding strategy
5. GoToMarketAgent          – launch strategy, channels, user acquisition
6. PitchDeckAgent           – investor-ready pitch narrative
"""

from __future__ import annotations

import logging
from typing import Any

from .config import Config
from .orchestrate_client import OrchestrateClient

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Shared base
# ─────────────────────────────────────────────────────────────────────────────

class _BaseAgent:
    """Internal base that wires up a shared OrchestrateClient."""

    #: Override in each subclass with the Config attribute name for the agent UUID.
    _agent_id_attr: str = ""

    def __init__(self, config: Config, client: OrchestrateClient) -> None:
        self._config = config
        self._client = client

    @property
    def _agent_id(self) -> str:
        return getattr(self._config, self._agent_id_attr)

    def _run(
        self,
        prompt: str,
        additional_context: dict[str, Any] | None = None,
    ) -> str:
        """Send *prompt* to this agent and return the response text."""
        return self._client.chat(
            agent_id=self._agent_id,
            message=prompt,
            additional_context=additional_context,
        )


# ─────────────────────────────────────────────────────────────────────────────
# 1. Startup Planner Agent
# ─────────────────────────────────────────────────────────────────────────────

class StartupPlannerAgent(_BaseAgent):
    _agent_id_attr = "planner_agent_id"

    def run(
        self,
        startup_idea: str,
        additional_context: dict[str, Any] | None = None,
    ) -> str:
        logger.info("Startup Planner Agent – processing …")
        prompt = (
            "You are the Startup Planner Agent for the Startup Blueprint Generator.\n"
            "Analyse the following startup idea and produce a comprehensive startup plan.\n"
            "Include: problem statement, target audience, core value proposition, "
            "key milestones, resource requirements, and recommended next steps.\n\n"
            f"STARTUP IDEA:\n{startup_idea}"
        )
        return self._run(prompt, additional_context)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Market Intelligence Agent
# ─────────────────────────────────────────────────────────────────────────────

class MarketIntelligenceAgent(_BaseAgent):
    _agent_id_attr = "market_agent_id"

    def run(
        self,
        startup_idea: str,
        additional_context: dict[str, Any] | None = None,
    ) -> str:
        logger.info("Market Intelligence Agent – processing …")
        prompt = (
            "You are the Market Intelligence Agent for the Startup Blueprint Generator.\n"
            "Conduct a thorough market analysis for the following startup idea.\n"
            "Include: total addressable market (TAM/SAM/SOM), key competitors, "
            "market trends, customer segments, pain points, and market entry barriers.\n\n"
            f"STARTUP IDEA:\n{startup_idea}"
        )
        return self._run(prompt, additional_context)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Business Strategy Agent
# ─────────────────────────────────────────────────────────────────────────────

class BusinessStrategyAgent(_BaseAgent):
    _agent_id_attr = "strategy_agent_id"

    def run(
        self,
        startup_idea: str,
        additional_context: dict[str, Any] | None = None,
    ) -> str:
        logger.info("Business Strategy Agent – processing …")
        prompt = (
            "You are the Business Strategy Agent for the Startup Blueprint Generator.\n"
            "Develop a robust business strategy for the following startup idea.\n"
            "Include: business model (revenue streams, pricing), competitive moat, "
            "strategic partnerships, SWOT analysis, and 3-year strategic roadmap.\n\n"
            f"STARTUP IDEA:\n{startup_idea}"
        )
        return self._run(prompt, additional_context)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Finance and Funding Agent
# ─────────────────────────────────────────────────────────────────────────────

class FinanceFundingAgent(_BaseAgent):
    _agent_id_attr = "finance_agent_id"

    def run(
        self,
        startup_idea: str,
        additional_context: dict[str, Any] | None = None,
    ) -> str:
        logger.info("Finance & Funding Agent – processing …")
        prompt = (
            "You are the Finance and Funding Agent for the Startup Blueprint Generator.\n"
            "Create a detailed financial and funding plan for the following startup idea.\n"
            "Include: startup cost estimates, revenue projections (Y1–Y3), burn rate, "
            "funding requirements, recommended funding rounds (pre-seed/seed/Series A), "
            "investor types to target, and key financial KPIs.\n\n"
            f"STARTUP IDEA:\n{startup_idea}"
        )
        return self._run(prompt, additional_context)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Go-To-Market Agent
# ─────────────────────────────────────────────────────────────────────────────

class GoToMarketAgent(_BaseAgent):
    _agent_id_attr = "gtm_agent_id"

    def run(
        self,
        startup_idea: str,
        additional_context: dict[str, Any] | None = None,
    ) -> str:
        logger.info("Go-To-Market Agent – processing …")
        prompt = (
            "You are the Go-To-Market Agent for the Startup Blueprint Generator.\n"
            "Design a detailed go-to-market strategy for the following startup idea.\n"
            "Include: launch strategy, marketing channels, user acquisition tactics, "
            "growth hacking ideas, partnerships, community building, and 90-day launch plan.\n\n"
            f"STARTUP IDEA:\n{startup_idea}"
        )
        return self._run(prompt, additional_context)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Pitch Deck Agent
# ─────────────────────────────────────────────────────────────────────────────

class PitchDeckAgent(_BaseAgent):
    _agent_id_attr = "pitch_agent_id"

    def run(
        self,
        startup_idea: str,
        additional_context: dict[str, Any] | None = None,
    ) -> str:
        logger.info("Pitch Deck Agent – processing …")
        prompt = (
            "You are the Pitch Deck Agent for the Startup Blueprint Generator.\n"
            "Create a compelling investor pitch narrative for the following startup idea.\n"
            "Structure it as a 10-slide pitch deck outline covering: "
            "Problem, Solution, Market Opportunity, Product, Business Model, "
            "Traction, Team Requirements, Financials, Ask (funding amount & use of funds), "
            "and Vision. Write the talking points for each slide.\n\n"
            f"STARTUP IDEA:\n{startup_idea}"
        )
        return self._run(prompt, additional_context)


# ─────────────────────────────────────────────────────────────────────────────
# Orchestrator – runs all 6 agents and collects results
# ─────────────────────────────────────────────────────────────────────────────

class BlueprintOrchestrator:
    """
    Runs all 6 agents against a single startup idea and returns a
    structured blueprint dict.  Each agent targets its own
    POST /v1/agents/{agent_id}/chat endpoint independently.
    """

    def __init__(self, config: Config) -> None:
        self._config = config
        self._client = OrchestrateClient(
            base_url=config.wxo_base_url,
            api_key=config.wxo_api_key,
            instance_id=config.wxo_instance_id,
            timeout_seconds=config.timeout_seconds,
        )
        self._agents: list[tuple[str, _BaseAgent]] = [
            ("startup_plan",        StartupPlannerAgent(config, self._client)),
            ("market_intelligence", MarketIntelligenceAgent(config, self._client)),
            ("business_strategy",   BusinessStrategyAgent(config, self._client)),
            ("finance_funding",     FinanceFundingAgent(config, self._client)),
            ("go_to_market",        GoToMarketAgent(config, self._client)),
            ("pitch_deck",          PitchDeckAgent(config, self._client)),
        ]

    def generate(
        self,
        startup_idea: str,
        additional_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Run all agents and return a dict keyed by section name.

        Returns
        -------
        {
            "startup_idea": str,
            "sections": {
                "startup_plan":        str,
                "market_intelligence": str,
                "business_strategy":   str,
                "finance_funding":     str,
                "go_to_market":        str,
                "pitch_deck":          str,
            }
        }
        """
        sections: dict[str, str] = {}
        for key, agent in self._agents:
            try:
                sections[key] = agent.run(
                    startup_idea=startup_idea,
                    additional_context=additional_context,
                )
            except Exception as exc:  # noqa: BLE001
                logger.error("Agent %s failed: %s", key, exc)
                sections[key] = f"[Agent unavailable: {exc}]"

        return {
            "startup_idea": startup_idea,
            "sections": sections,
        }
