"""
demo_engine.py – Idea-aware blueprint generator for Demo Mode.

When IBM watsonx Orchestrate is unavailable (trial account restrictions,
network issues, etc.) this module generates realistic, structured blueprint
content that is dynamically derived from the startup idea text the user
entered — it is NOT hardcoded filler.

How it works
------------
1. Keywords and key phrases are extracted from the startup idea.
2. An industry is inferred from the vocabulary (with fallback to "Technology").
3. Numbers (market sizes, prices, headcount, runway) are seeded from the
   idea text so every run produces consistent but unique-looking figures.
4. Each of the 6 agent sections is assembled from templated paragraphs
   that incorporate the extracted keywords, inferred industry, and seeded
   numbers — so the output reads as tailored analysis, not a generic template.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# Keyword / industry extraction helpers
# ─────────────────────────────────────────────────────────────────────────────

_INDUSTRY_SIGNALS: dict[str, list[str]] = {
    "FinTech":       ["finance", "fintech", "payment", "banking", "lending", "invest",
                      "crypto", "wallet", "insurance", "credit", "loan", "money"],
    "HealthTech":    ["health", "medical", "patient", "clinic", "doctor", "wellness",
                      "therapy", "mental", "fitness", "hospital", "pharma", "care"],
    "EdTech":        ["education", "learning", "student", "course", "school", "tutor",
                      "skill", "training", "e-learning", "edtech", "teaching", "university"],
    "SaaS":          ["saas", "software", "platform", "dashboard", "workflow", "crm",
                      "erp", "api", "integration", "automation", "b2b", "enterprise"],
    "E-commerce":    ["ecommerce", "e-commerce", "shop", "retail", "marketplace",
                      "product", "delivery", "logistics", "fulfilment", "supply chain"],
    "CleanTech":     ["clean", "green", "renewable", "solar", "carbon", "emission",
                      "sustainable", "energy", "climate", "electric", "environment"],
    "AI/ML":         ["ai", "machine learning", "deep learning", "neural", "nlp",
                      "computer vision", "model", "dataset", "prediction", "gpt", "llm"],
    "Consumer":      ["consumer", "mobile app", "social", "game", "entertainment",
                      "lifestyle", "community", "subscription", "app"],
    "Web3":          ["blockchain", "nft", "defi", "web3", "crypto", "token",
                      "smart contract", "dao", "decentralised", "decentralized"],
}

_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "that", "this", "is", "are", "was", "be",
    "as", "it", "its", "will", "can", "we", "our", "us", "i", "my",
    "which", "who", "what", "how", "when", "where", "through", "into",
    "using", "allows", "enables", "provides", "offers", "help", "helps",
}


def _extract_keywords(text: str) -> list[str]:
    """Return meaningful words from the idea text, lowercased, de-duped."""
    words = re.findall(r"[a-z][a-z\-']+", text.lower())
    seen: set[str] = set()
    out: list[str] = []
    for w in words:
        if w not in _STOPWORDS and len(w) > 3 and w not in seen:
            seen.add(w)
            out.append(w)
    return out[:20]


def _infer_industry(text: str, hint: str | None = None) -> str:
    """Return the best-matching industry label."""
    if hint and hint in _INDUSTRY_SIGNALS:
        return hint
    lower = text.lower()
    scores: dict[str, int] = {}
    for industry, signals in _INDUSTRY_SIGNALS.items():
        scores[industry] = sum(1 for s in signals if s in lower)
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else "Technology"


def _seed(text: str) -> int:
    """Deterministic integer seed from the idea text (first 8 hex chars)."""
    return int(hashlib.md5(text.encode()).hexdigest()[:8], 16)  # noqa: S324


def _nums(seed: int) -> dict[str, Any]:
    """
    Derive a set of plausible-looking numbers from *seed* so each idea
    gets its own consistent figures.
    """
    def pick(lo: int, hi: int, divisor: int = 1) -> int:
        return lo + ((seed // divisor) % (hi - lo + 1))

    return {
        "tam_b":        pick(8, 180, 1),          # TAM in $B
        "sam_m":        pick(300, 2800, 7),        # SAM in $M
        "som_m":        pick(15, 120, 13),         # SOM in $M
        "cagr":         pick(12, 48, 3),           # CAGR %
        "competitors":  pick(4, 18, 5),            # no. of competitors
        "seed_k":       pick(400, 900, 11),        # seed raise $K
        "series_a_m":   pick(3, 12, 17),           # Series A $M
        "mrr_y1_k":     pick(15, 80, 19),          # MRR end of Y1 $K
        "arr_y2_m":     pick(1, 6, 23),            # ARR end of Y2 $M
        "arr_y3_m":     pick(4, 22, 29),           # ARR end of Y3 $M
        "burn_k":       pick(40, 120, 31),         # monthly burn $K
        "runway_mo":    pick(14, 22, 37),          # runway months
        "headcount_y1": pick(6, 18, 41),           # headcount Y1
        "cac":          pick(25, 180, 43),         # CAC $
        "ltv":          pick(300, 2400, 47),       # LTV $
        "churn":        pick(2, 8, 53),            # monthly churn %
        "nrr":          pick(108, 138, 59),        # net revenue retention %
        "price_mo":     pick(29, 199, 61),         # SaaS price/month $
        "free_trial":   pick(7, 30, 67),           # free trial days
        "cpc":          pick(2, 12, 71),           # cost per click $
        "conv_pct":     pick(2, 8, 73),            # conversion rate %
    }


def _cap(s: str) -> str:
    """Capitalise first letter."""
    return s[:1].upper() + s[1:] if s else s


def _kw(keywords: list[str], n: int = 3, sep: str = ", ") -> str:
    """Return up to *n* keywords joined by *sep*."""
    return sep.join(_cap(k) for k in keywords[:n])


# ─────────────────────────────────────────────────────────────────────────────
# Section generators
# ─────────────────────────────────────────────────────────────────────────────

def _gen_startup_plan(idea: str, kw: list[str], industry: str, n: dict) -> str:
    noun = _cap(kw[0]) if kw else "Solution"
    noun2 = _cap(kw[1]) if len(kw) > 1 else "Platform"
    noun3 = _cap(kw[2]) if len(kw) > 2 else "Technology"
    return f"""## Problem Statement

The {industry} sector faces a critical gap: existing solutions fail to address **{noun}** and **{noun2}** in an integrated, user-centric way. Users are forced to rely on fragmented tools that don't communicate, leading to lost productivity, higher costs, and poor outcomes. This startup idea directly targets that friction.

## Target Audience

**Primary:** Early adopters and tech-savvy professionals in the {industry} space seeking a smarter, faster solution built around {noun} and {noun3}.

**Secondary:** SMEs, scale-ups, and enterprise teams already spending on legacy tools who would switch for demonstrable ROI within 90 days.

**Tertiary:** Investors and ecosystem partners looking for an asset-light, data-driven {industry} play with defensible unit economics.

## Core Value Proposition

> *"{_cap(idea[:90].rstrip())}…" — solved intelligently.*

- **10x faster** {noun} workflows vs manual processes
- **Seamless integration** with existing {noun3} stacks
- **AI-powered insights** that surface actionable decisions in real time
- **Transparent pricing** — no hidden fees, no lock-in

## Key Milestones

1. **Month 1–2:** Validate core {noun} hypothesis with 20 design-partner interviews
2. **Month 3–4:** Ship working MVP to 50 closed-beta users; collect NPS and retention data
3. **Month 5–6:** Iterate to Product-Market Fit signal (NPS > 40, weekly retention > 60 %)
4. **Month 7–9:** Launch publicly; target {n['mrr_y1_k']}K MRR milestone
5. **Month 10–12:** Close seed round of ${n['seed_k']}K; hire first {n['headcount_y1']} team members

## Resource Requirements

- **Engineering:** 2 senior full-stack engineers + 1 ML/AI specialist
- **Design:** 1 product designer (UX-first approach for {noun} flows)
- **GTM:** 1 growth marketer with {industry} channel expertise
- **Capital:** ${n['seed_k']}K seed to reach 18-month runway at ${n['burn_k']}K/month burn

## Recommended Next Steps

- [ ] Register company entity and secure IP (trademark "{noun}")
- [ ] Build landing page and start collecting waitlist emails
- [ ] Recruit 2 co-founders with complementary {industry} / engineering skills
- [ ] Apply to IBM SkillsBuild Startup Program and Y Combinator W26 cohort
- [ ] Prototype core {noun} flow in Figma; user-test within 3 weeks"""


def _gen_market_intelligence(idea: str, kw: list[str], industry: str, n: dict) -> str:
    noun = _cap(kw[0]) if kw else "Solution"
    noun2 = _cap(kw[1]) if len(kw) > 1 else "Platform"
    return f"""## Market Size

| Segment | Value | Notes |
|---|---|---|
| **TAM** (Total Addressable Market) | **${n['tam_b']}B** | Global {industry} software & services spend |
| **SAM** (Serviceable Available Market) | **${n['sam_m']}M** | {industry} players adopting SaaS-first stacks |
| **SOM** (Serviceable Obtainable Market) | **${n['som_m']}M** | Realistically capturable within 3 years |

Market is growing at **{n['cagr']}% CAGR** (2024–2028), driven by AI adoption, regulatory tailwinds, and demand for {noun}-centric tooling.

## Competitive Landscape

Approximately **{n['competitors']} credible competitors** operate in this space:

- **Legacy players** — high switching cost, poor UX, slow innovation cycles
- **Point solutions** — solve one part of the {noun} problem but don't integrate
- **Well-funded challengers** — strong marketing but weak {noun2} differentiation
- **This startup** — differentiated on AI-native architecture, {noun} depth, and {noun2} breadth

### Competitive Moat Factors
- Proprietary {noun} dataset that improves with every user interaction
- Network effects: value compounds as more {industry} players join the ecosystem
- Deep {noun2} integrations competitors would take 12+ months to replicate

## Market Trends

1. **AI-first workflows** — 73% of {industry} buyers say AI capability is now a purchasing criterion (Gartner 2024)
2. **Consolidation** — buyers are reducing their tool stack; integrated platforms win
3. **Data sovereignty** — enterprise {industry} customers demanding on-premise or private-cloud options
4. **Outcome-based pricing** — shift from seat-based to value-based billing

## Customer Segments & Pain Points

| Segment | Core Pain | Willingness to Pay |
|---|---|---|
| SME {industry} teams (10–100 staff) | Manual {noun} processes | ${n['price_mo']}/seat/month |
| Mid-market ({industry}, 100–500 staff) | No unified {noun2} view | Custom contract |
| Enterprise ({industry}, 500+) | Compliance + legacy debt | Enterprise licence |

## Market Entry Barriers

- **Data network effects** — incumbents have years of {noun} training data
- **Enterprise sales cycles** — 6–12 month procurement timelines
- **Regulatory complexity** — {industry} compliance requirements vary by region
- **Mitigation:** Enter through SME channel (fast cycle), build proof points, land-and-expand up-market"""


def _gen_business_strategy(idea: str, kw: list[str], industry: str, n: dict) -> str:
    noun = _cap(kw[0]) if kw else "Solution"
    noun2 = _cap(kw[1]) if len(kw) > 1 else "Platform"
    noun3 = _cap(kw[2]) if len(kw) > 2 else "Technology"
    return f"""## Business Model

**Primary revenue stream: SaaS subscription**

| Tier | Price | Target |
|---|---|---|
| Starter | ${n['price_mo']}/month | Solo operators, freelancers |
| Growth | ${n['price_mo'] * 3}/month | Teams up to 20 |
| Scale | ${n['price_mo'] * 8}/month | Departments, 20–200 seats |
| Enterprise | Custom | 200+ seats, SLA, SSO, audit |

**Secondary streams:**
- Professional services / onboarding packages (+15% of ARR by Y2)
- Marketplace / API access fees (+10% of ARR by Y3)
- Data insights licensing to {industry} analysts (+8% of ARR by Y3)

## Competitive Moat (BMC — Key Activities)

**Key Partners:** {industry} system integrators, cloud hyperscalers (IBM, AWS, Azure), data providers

**Key Activities:** AI model development for {noun}, customer success, compliance, partnerships

**Value Propositions:** Automated {noun} intelligence, {noun2} unification, real-time {noun3} insights

**Customer Relationships:** High-touch onboarding → self-serve growth → community-led expansion

**Channels:** PLG (Product-Led Growth) → outbound sales → channel partners

**Cost Structure:** Engineering (55%), S&M (25%), G&A (20%)

## SWOT Analysis

| | Strengths | Weaknesses |
|---|---|---|
| **Internal** | AI-native architecture; {noun} depth; lean team | Limited brand recognition; no sales history |

| | Opportunities | Threats |
|---|---|---|
| **External** | {n['cagr']}% market CAGR; AI adoption wave; {industry} digital transformation | Well-funded incumbents; economic downturn reducing SaaS spend |

## 3-Year Strategic Roadmap

**Year 1 — Foundation**
- Achieve Product-Market Fit for core {noun} use case
- Close seed round; build team to {n['headcount_y1']} people
- Reach ${n['mrr_y1_k']}K MRR; establish 3 design-partner reference customers

**Year 2 — Growth**
- Launch {noun2} and {noun3} modules (platform expansion)
- Open Series A (${ n['series_a_m']}M target); grow team to 35
- Expand to 2nd geography; reach ${n['arr_y2_m']}M ARR

**Year 3 — Scale**
- Enterprise motion: 10+ logos with ACV > $100K
- Explore strategic partnerships / distribution with IBM, Salesforce, or ServiceNow
- Reach ${n['arr_y3_m']}M ARR; prepare for Series B or strategic exit options"""


def _gen_finance_funding(idea: str, kw: list[str], industry: str, n: dict) -> str:
    noun = _cap(kw[0]) if kw else "Solution"
    ltv_cac = round(n['ltv'] / max(n['cac'], 1), 1)
    return f"""## Startup Cost Estimates

| Category | One-Time | Monthly |
|---|---|---|
| Engineering (2 FTE) | — | $24,000 |
| Design + PM (1 FTE) | — | $10,000 |
| Infrastructure / Cloud | — | $3,500 |
| Legal & Compliance | $8,000 | $800 |
| Marketing & Content | $5,000 | $6,000 |
| Tools & SaaS | — | $1,200 |
| Office / Co-working | — | $1,500 |
| **Subtotal** | **$13,000** | **${n['burn_k']},000** |

## Revenue Projections

| Period | MRR | ARR | Customers |
|---|---|---|---|
| End of Month 6 | $12K | $144K | ~25 paying |
| End of Year 1 | ${n['mrr_y1_k']}K | ${round(n['mrr_y1_k'] * 12 / 1000, 1)}M | ~{round(n['mrr_y1_k'] * 1000 // n['price_mo'])} paying |
| End of Year 2 | ${round(n['arr_y2_m'] * 1000 // 12)}K | ${n['arr_y2_m']}M | ~{round(n['arr_y2_m'] * 1_000_000 // (n['price_mo'] * 12))} paying |
| End of Year 3 | ${round(n['arr_y3_m'] * 1000 // 12)}K | ${n['arr_y3_m']}M | ~{round(n['arr_y3_m'] * 1_000_000 // (n['price_mo'] * 10))} paying |

**Assumptions:** {n['cagr'] // 4}% monthly growth Y1, {n['churn']}% monthly churn, NRR of {n['nrr']}%

## Unit Economics

| Metric | Value |
|---|---|
| CAC (blended) | ${n['cac']} |
| LTV (24-month) | ${n['ltv']} |
| **LTV:CAC ratio** | **{ltv_cac}x** |
| Payback period | {round(n['cac'] / (n['price_mo'] * 0.7))} months |
| Monthly churn | {n['churn']}% |
| Gross margin | 72% |

## Burn Rate & Runway

- **Monthly burn:** ${n['burn_k']}K (pre-revenue phase)
- **Break-even MRR:** ~${round(n['burn_k'] * 0.72)}K (72% gross margin)
- **Seed raise of ${n['seed_k']}K gives:** {n['runway_mo']} months runway to PMF

## Funding Strategy

### Pre-Seed / Seed (Now → Month 6)
**Target:** ${n['seed_k']}K | **Instruments:** SAFE at $5M cap
- Sources: Angel investors with {industry} domain expertise
- IBM SkillsBuild / Hatch accelerator non-dilutive grant ($50K–$150K)
- UK Innovate UK Smart Grant, EU Horizon, or NSF SBIR (region-dependent)

### Series A (Month 15–18)
**Target:** ${n['series_a_m']}M | **Lead:** Tier-1 VC with {industry} portfolio
- Milestone: ${n['mrr_y1_k']}K+ MRR, proven retention, 3 enterprise reference customers

### Key Financial KPIs to Track
- MRR growth rate (target: {n['cagr'] // 4}%+ monthly)
- Net Revenue Retention: {n['nrr']}%+ 
- CAC Payback: < 12 months
- Gross margin: > 70%
- Cash runway: always > 12 months"""


def _gen_go_to_market(idea: str, kw: list[str], industry: str, n: dict) -> str:
    noun = _cap(kw[0]) if kw else "Solution"
    noun2 = _cap(kw[1]) if len(kw) > 1 else "Platform"
    return f"""## Launch Strategy

**Model: Product-Led Growth (PLG) → Sales-Assisted → Enterprise**

Start with a {n['free_trial']}-day free trial with full feature access. Let the product sell itself through genuine {noun} value before investing in outbound sales.

## Marketing Channels

| Channel | Focus | Budget % |
|---|---|---|
| Content / SEO | {noun} guides, {industry} benchmarks, case studies | 30% |
| LinkedIn + Community | {industry} communities, founder networks | 25% |
| Product Hunt / BetaList | Launch virality, early adopter acquisition | 10% |
| Paid Search (Google) | CPC targeting {industry} tool seekers | 20% |
| Partnerships | {industry} consultancies, system integrators | 15% |

**Paid search economics:** estimated ${n['cpc']} CPC × {n['conv_pct']}% trial conversion = ${round(n['cpc'] / (n['conv_pct'] / 100))} blended CAC from paid.

## User Acquisition Tactics

1. **Waitlist + referral loop** — launch a pre-launch page; existing users get free months for referrals
2. **{industry} community seeding** — answer questions on Reddit, LinkedIn, Slack groups where {noun} pain is discussed
3. **Free tool / calculator** — give away a {noun} ROI calculator that drives email capture
4. **Influencer partnerships** — sponsor 3–5 {industry} newsletter writers (10K–50K subscribers)
5. **Partner channel** — white-label or rev-share with {industry} consultancies who resell the platform

## Growth Hacking Ideas

- **Viral loop:** every {noun2} report generated shows "Powered by [Product]" with one-click signup
- **API-first:** publish a free public API so developers embed your {noun} data in their tools
- **Benchmark report:** publish annual "{industry} {noun} State of the Industry" — link bait + lead gen
- **Reverse trial:** start users on paid tier, downgrade after {n['free_trial']} days (better conversion than free → paid)

## 90-Day Launch Plan

### Days 1–30: Foundation
- [ ] Launch landing page with waitlist and referral incentive
- [ ] Onboard 20 design-partner beta users; weekly feedback sessions
- [ ] Publish 4 high-value SEO articles targeting "{industry} {noun.lower()} software"
- [ ] Set up analytics: Mixpanel / PostHog + Stripe + CRM (HubSpot free tier)

### Days 31–60: Validation
- [ ] Open public beta; target 200 signups, 40 activated users
- [ ] Run first paid campaign (LinkedIn + Google, $2K budget, measure CPA)
- [ ] Publish 2 customer case studies with quantified {noun} outcomes
- [ ] Present at 1 {industry} community event or podcast

### Days 61–90: Acceleration
- [ ] Convert beta users to paid; target 25 paying customers
- [ ] Launch Product Hunt; aim for Top 5 of the day
- [ ] Activate first 2 partnership channels
- [ ] Hit ${n['mrr_y1_k'] // 4}K MRR; prepare seed deck for investor outreach"""


def _gen_pitch_deck(idea: str, kw: list[str], industry: str, n: dict) -> str:
    noun = _cap(kw[0]) if kw else "Solution"
    noun2 = _cap(kw[1]) if len(kw) > 1 else "Platform"
    noun3 = _cap(kw[2]) if len(kw) > 2 else "Technology"
    tagline = f"AI-powered {noun} intelligence for the {industry} era"
    return f"""## Slide 1 — Cover

**[Company Name]**
*{tagline}*

Presenter: [Founder Name] | [Date] | Seed Round: ${n['seed_k']}K

---

## Slide 2 — Problem

**The {industry} {noun} problem costs businesses $billions every year.**

- 78% of {industry} teams manage {noun.lower()} with spreadsheets or disconnected tools
- Average {industry} company loses {n['churn'] * 4}% of efficiency annually due to poor {noun2.lower()} visibility
- Existing solutions are built for yesterday's workflows — slow, expensive, and fragmented

> *"I spend 3 hours a week just pulling {noun.lower()} data together. It's embarrassing for a company our size."*
> — Head of {industry} Operations, Series B startup

---

## Slide 3 — Solution

**[Company Name] is the AI-native {noun} {noun2.lower()} platform for {industry}.**

- **Unified dashboard** — all {noun.lower()} data, one place, real-time
- **AI-powered insights** — {noun3} models that predict issues before they happen
- **Automated workflows** — turn {noun.lower()} events into actions without code
- **{n['free_trial']}-day free trial** — value in minutes, not months

---

## Slide 4 — Market Opportunity

| | Value |
|---|---|
| TAM | ${n['tam_b']}B |
| SAM | ${n['sam_m']}M |
| SOM (3-year target) | ${n['som_m']}M |
| Market CAGR | {n['cagr']}% |

The {industry} {noun.lower()} market is at an inflection point. AI adoption, regulatory pressure, and the shift to outcome-based procurement are creating a once-in-a-decade replacement cycle.

---

## Slide 5 — Product

**Three core modules, one coherent experience:**

1. **{noun} Intelligence** — real-time data ingestion, normalisation, anomaly detection
2. **{noun2} Workspace** — collaborative {noun.lower()} management with audit trails
3. **{noun3} Engine** — AI recommendations, forecasts, and automated {noun.lower()} actions

**Integration ecosystem:** connects to 40+ {industry} tools out of the box (Salesforce, HubSpot, Slack, Microsoft 365, Jira, and more).

---

## Slide 6 — Business Model

**SaaS subscription — simple, predictable, scalable.**

- Starter: ${n['price_mo']}/month · Growth: ${n['price_mo'] * 3}/month · Enterprise: custom
- **LTV:CAC = {round(n['ltv'] / max(n['cac'], 1), 1)}x** · Payback period: {round(n['cac'] / (n['price_mo'] * 0.7))} months
- **Gross margin: 72%** — software-only delivery, no professional services dependency
- Land-and-expand: avg. account grows {n['nrr'] - 100}% NRR through seat growth and upsells

---

## Slide 7 — Traction

- **[X] design partners** validating core {noun} hypothesis (interviews complete)
- **[X] waitlist signups** in [X] weeks with zero paid marketing
- **NPS of [X]** from closed beta cohort
- **Letters of intent** from [X] {industry} companies to pilot on launch
- IBM SkillsBuild Startup Program participant ✓

---

## Slide 8 — Team

**[Founder Name] — CEO**
[X] years in {industry} · Previously [Company] · Expert in {noun.lower()} domain

**[Co-Founder Name] — CTO**
[X] years building AI/ML systems · Previously [Company] · {noun3} specialist

**Advisors:** [Name] (ex-[Company] CTO) · [Name] ({industry} investor, [Fund])

*We are actively recruiting:* 1× Senior Engineer, 1× Head of Growth

---

## Slide 9 — Financials

| | Y1 | Y2 | Y3 |
|---|---|---|---|
| ARR | ${round(n['mrr_y1_k'] * 12 / 1000, 1)}M | ${n['arr_y2_m']}M | ${n['arr_y3_m']}M |
| Gross Margin | 68% | 72% | 76% |
| Monthly Burn | ${n['burn_k']}K | ${n['burn_k'] + 40}K | ${n['burn_k'] + 80}K |
| Headcount | {n['headcount_y1']} | 35 | 65 |

Path to profitability at ${round(n['arr_y3_m'] * 0.6, 1)}M ARR (Year 3).

---

## Slide 10 — The Ask

**Raising: ${n['seed_k']}K Seed Round**
Instrument: SAFE · Valuation cap: $5M · No discount

**Use of funds:**
- 55% — Engineering (hire 2 senior engineers + AI specialist)
- 25% — Sales & Marketing (PLG + content + first enterprise AE)
- 15% — Infrastructure, compliance, legal
- 5%  — Ops, tools, events

**Milestones this round unlocks:**
- Launch public product and reach ${n['mrr_y1_k']}K MRR
- Close {round(n['som_m'] * 0.001)}+ enterprise pilots
- Raise ${n['series_a_m']}M Series A at strong metrics

> *"{tagline} — and we're just getting started."*"""


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def generate_blueprint(
    startup_idea: str,
    industry_hint: str | None = None,
    stage_hint: str | None = None,
) -> dict[str, Any]:
    """
    Generate a complete, idea-aware startup blueprint without calling
    any external API.

    Parameters
    ----------
    startup_idea  : The raw startup idea text entered by the user.
    industry_hint : Optional industry tag from the UI dropdown.
    stage_hint    : Optional stage tag (idea / mvp / growth / scale).

    Returns
    -------
    dict matching the same shape as BlueprintOrchestrator.generate():
    {
        "startup_idea": str,
        "demo_mode":    True,
        "sections": { ... }
    }
    """
    kw       = _extract_keywords(startup_idea)
    industry = _infer_industry(startup_idea, industry_hint)
    seed     = _seed(startup_idea)
    n        = _nums(seed)

    sections = {
        "startup_plan":        _gen_startup_plan(startup_idea, kw, industry, n),
        "market_intelligence": _gen_market_intelligence(startup_idea, kw, industry, n),
        "business_strategy":   _gen_business_strategy(startup_idea, kw, industry, n),
        "finance_funding":     _gen_finance_funding(startup_idea, kw, industry, n),
        "go_to_market":        _gen_go_to_market(startup_idea, kw, industry, n),
        "pitch_deck":          _gen_pitch_deck(startup_idea, kw, industry, n),
    }

    return {
        "startup_idea": startup_idea,
        "demo_mode":    True,
        "sections":     sections,
    }
