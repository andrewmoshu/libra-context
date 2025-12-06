# Agent Hive Implementation Plan

## Project Status: ✅ Core Implementation Complete + Google ADK Integration Fixed

The Agent Hive is now a fully functional self-replicating, self-learning agent collective built on Google ADK and ACE Framework.

### Recent Updates (2025-12-06)
- Fixed ADK imports to use correct `google-adk` API (`llm_agent.LlmAgent`, `runners.InMemoryRunner`)
- Updated drone execute method to use proper async runner pattern with `types.Content`
- Changed all models to Gemini-only (ace_model: `gemini/gemini-2.0-flash`)
- All 25 tests passing

## Completed Components

### 1. ✅ Main Hive Orchestrator (`hive.py`)
- `AgentHive` class coordinates all components
- Queen agent for strategic planning
- Drone management with callbacks
- ACE learning integration
- Monetization tracking
- State persistence (save/load)

### 2. ✅ Queen Module (`queen/`)
- `QueenAgent`: Strategic orchestration
- `StrategicPlanner`: Goal and task management
- `ReplicationManager`: Dynamic drone spawning

### 3. ✅ Drone Types (`drones/`)
- `WorkerDrone`: General-purpose task execution
- `BuilderDrone`: Product/code creation
- `ResearcherDrone`: Market intelligence with real web tools
- `SellerDrone`: Marketing and sales with contact extraction

### 4. ✅ ACE Learning Integration (`learning/`)
- `ACEWrapper`: Full ACE loop with Reflector + SkillManager
- `HiveSkillbook`: Thread-safe, persistent skill storage
- `HiveEnvironment`: Task evaluation
- Fallback to simplified learning when ACE unavailable

### 5. ✅ Monetization Module (`monetization/`)
- `Treasury`: Financial tracking (SQLite-based)
- `ProductRegistry`: Product/service catalog
- `PricingEngine`: Multiple pricing strategies
  - Cost-plus pricing
  - Value-based pricing
  - Competitive pricing

### 6. ✅ Web Tools (`tools/web_tools.py`)
- `fetch_url`: Real web fetching with httpx + BeautifulSoup
- `analyze_website`: SEO, technology, business analysis
- `extract_contact_info`: Email/phone extraction
- `compare_websites`: Multi-site comparison
- `monitor_trends`: Placeholder for trend API integration

### 7. ✅ Runner Script (`run_hive.py`)
- Demo initialization and configuration
- Task creation and execution
- Monetization setup with sample products
- Status and metrics reporting

### 8. ✅ Tests (`tests/`)
- `test_web_tools.py`: Web tool unit tests
- `test_hive.py`: Core component tests

## Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                        AGENT HIVE                              │
├───────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                    QUEEN AGENT                           │ │
│  │  ┌──────────────┐  ┌─────────────┐  ┌────────────────┐  │ │
│  │  │   Planner    │  │ Replicator  │  │    Decision    │  │ │
│  │  │  (Goals &    │  │  (Drone     │  │     Agent      │  │ │
│  │  │   Tasks)     │  │  Spawning)  │  │  (ADK-based)   │  │ │
│  │  └──────────────┘  └─────────────┘  └────────────────┘  │ │
│  └──────────────────────────────────────────────────────────┘ │
│                              │                                 │
│                              ▼                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                      DRONES                              │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │ │
│  │  │ Worker   │ │ Builder  │ │Researcher│ │  Seller  │   │ │
│  │  │ (General │ │ (Code/   │ │ (Market  │ │ (Sales/  │   │ │
│  │  │  Tasks)  │ │ Products)│ │  Intel)  │ │Marketing)│   │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │ │
│  └──────────────────────────────────────────────────────────┘ │
│                              │                                 │
│                              ▼                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                    ACE LEARNING                          │ │
│  │  Task Result → Reflector → SkillManager → Skillbook      │ │
│  │                    (Shared across all drones)            │ │
│  └──────────────────────────────────────────────────────────┘ │
│                              │                                 │
│                              ▼                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                   MONETIZATION                           │ │
│  │  ┌──────────┐  ┌───────────────┐  ┌────────────────┐    │ │
│  │  │ Treasury │  │ Product       │  │ Pricing        │    │ │
│  │  │ (Finances)│ │ Registry      │  │ Engine         │    │ │
│  │  └──────────┘  └───────────────┘  └────────────────┘    │ │
│  └──────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
```

## Key Features

1. **Self-Replicating**: Automatically spawns new drones based on task queue depth
2. **Self-Learning**: Uses ACE framework to learn from every task execution
3. **Monetization-First**: Built-in financial tracking and pricing optimization
4. **Real Web Capabilities**: Actual HTTP fetching and content analysis
5. **Persistence**: Skillbook and state saved to disk

## Usage

```python
from agent_hive import AgentHive, HiveConfig
from agent_hive.config.settings import LLMConfig

# Configure the hive
config = HiveConfig(
    hive_name="ProductionHive",
    llm=LLMConfig(
        primary_model="gemini-2.5-flash",
        ace_model="gpt-4o-mini",
    ),
)

# Create and initialize
hive = AgentHive(config)
hive.initialize()

# Add tasks
hive.add_task(
    title="Research AI market",
    description="Find profitable niches in AI automation",
    drone_type="researcher",
)

# Run the hive
import asyncio
results = asyncio.run(hive.run(cycles=5))
```

## Future Enhancements

1. **Trend API Integration**: Connect to Google Trends or similar
2. **Payment Processing**: Stripe/PayPal integration for actual revenue
3. **Multi-Hive Coordination**: Hives that spawn child hives
4. **Advanced Learning**: Cross-hive skillbook sharing
5. **Deployment**: Docker/Kubernetes deployment templates

## Dependencies

- google-adk >= 1.0.0 (installed via `uv pip install google-adk`)
- google-genai (for types.Content message handling)
- pydantic >= 2.0.0
- litellm >= 1.0.0
- httpx >= 0.25.0
- beautifulsoup4 >= 4.12.0
- ace-framework (optional, for full learning)

## ADK API Reference

### Correct Imports
```python
from google.adk.agents import llm_agent
from google.adk import runners
from google.genai import types

Agent = llm_agent.LlmAgent
InMemoryRunner = runners.InMemoryRunner
```

### Running Agent
```python
runner = InMemoryRunner(agent=agent, app_name="my_app")
session = await runner.session_service.create_session(
    app_name=app_name,
    user_id=user_id,
)

message = types.Content(
    role="user",
    parts=[types.Part.from_text(text=prompt)]
)

async for event in runner.run_async(
    user_id=user_id,
    session_id=session.id,
    new_message=message,
):
    if event.is_final_response() and event.content and event.content.parts:
        response = event.content.parts[0].text
        break
```
