# Startup Blueprint Generator
### Powered by IBM watsonx Orchestrate

A Python client that connects to your **IBM watsonx Orchestrate** multi-agent
application, submits a startup idea to the **Startup Planner Agent**, and
retrieves the structured blueprint plan.

---

## Project Structure

```
.
├── main.py                            # Entry-point — run this
├── requirements.txt
├── .env.example                       # Copy → .env and fill in values
└── startup_blueprint/
    ├── __init__.py
    ├── config.py                      # Env-var loader & Config dataclass
    ├── auth.py                        # IBM IAM token manager (auto-refresh)
    ├── orchestrate_client.py          # Low-level Orchestrate REST client
    └── planner_agent.py               # High-level Planner Agent interface
```

---

## The 6-Agent Architecture

| # | Agent | Role |
|---|-------|------|
| 1 | **Startup Planner Agent** | Validates the idea, defines milestones & resources |
| 2 | **Market Intelligence Agent** | TAM/SAM/SOM, competitor landscape |
| 3 | **Business Strategy Agent** | Business model, moats, partnerships |
| 4 | **Finance & Funding Agent** | Unit economics, runway, fundraising path |
| 5 | **Go-To-Market Agent** | Launch strategy, channels, ICP |
| 6 | **Pitch Deck Agent** | Narrative structure, slide content |

> This script integrates with **Agent 1 (Startup Planner)**. The same
> `OrchestrateClient` can reach any other agent by swapping `agent_id`.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python ≥ 3.10 | `python --version` |
| IBM Cloud account | <https://cloud.ibm.com> |
| watsonx Orchestrate instance | Region: `us-south`, `eu-de`, etc. |
| IBM Cloud API key | IAM → API keys |
| Deployed multi-agent application | Note the **App ID** and each **Agent ID** |

---

## Quick Start

### 1. Clone / download this project

```bash
git clone <your-repo>
cd startup-blueprint-generator
```

### 2. Create a virtual environment

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure credentials

```bash
cp .env.example .env
```

Open `.env` and fill in:

| Variable | Where to find it |
|---|---|
| `WXO_BASE_URL` | Orchestrate instance URL (e.g. `https://us-south.orchestrate.ibm.com`) |
| `WXO_API_KEY` | IBM Cloud → IAM → API keys |
| `WXO_INSTANCE_ID` | Orchestrate service instance / space ID |
| `WXO_APP_ID` | Orchestrate UI → Applications → your app ID |
| `PLANNER_AGENT_ID` | Orchestrate UI → Applications → Agents → Startup Planner Agent |

### 5. Run

```bash
# Use the built-in default startup idea
python main.py

# Pass your own idea
python main.py --idea "A B2B SaaS platform that automates ESG reporting for SMEs"

# Add optional context
python main.py \
  --idea "AI-powered legal contract review for startups" \
  --industry "LegalTech" \
  --stage "mvp" \
  --verbose
```

The plan is printed to the console **and** saved to `planner_output.txt`.

---

## CLI Reference

| Flag | Type | Default | Description |
|---|---|---|---|
| `--idea` | str | built-in default | Startup idea text |
| `--industry` | str | — | Optional industry tag forwarded as context |
| `--stage` | str | — | `idea` \| `mvp` \| `growth` \| `scale` |
| `--poll-interval` | float | `3.0` | Seconds between result-polling calls |
| `--verbose` / `-v` | flag | off | Enable DEBUG-level logging |

---

## Extending to Other Agents

To call a different agent (e.g. **Market Intelligence**), add its ID to `.env`
and create a new agent class following the same pattern as
`startup_blueprint/planner_agent.py`:

```python
from startup_blueprint.orchestrate_client import OrchestrateClient

client = OrchestrateClient(...)
session_id = client.create_session()
task_or_answer = client.send_message(
    session_id, message="<your prompt>", agent_id="market-intelligence-agent"
)
result = client.poll_result(session_id, task_or_answer)
print(result)
```

---

## Authentication Flow

```
Your Script
   │
   ▼
IAMTokenManager ──POST──► https://iam.cloud.ibm.com/identity/token
                           (grant_type=apikey)
                           Returns: access_token (1 h TTL, auto-refreshed)
   │
   ▼
OrchestrateClient ──Bearer token──► watsonx Orchestrate REST API
```

---

## Security Notes

- `.env` is **never** committed (add it to `.gitignore`).
- The API key only ever leaves your machine as a POST body to the IBM IAM
  endpoint over TLS.
- Tokens are refreshed automatically 60 s before expiry.

---

## License

MIT
