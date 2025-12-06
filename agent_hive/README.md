# Agent Hive

A self-replicating, self-learning agent collective built on Google ADK and ACE Framework.

## Overview

Agent Hive is an autonomous multi-agent system designed to:
- **Self-Replicate**: Spawn new agents based on workload demand
- **Self-Learn**: Use ACE (Agentic Context Engineering) to improve from every task
- **Self-Monetize**: Track revenue, costs, and optimize for profitability

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         AGENT HIVE                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                     QUEEN AGENT                         │   │
│  │  - Strategic Planning        - Goal Management          │   │
│  │  - Resource Allocation       - Replication Decisions    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│              ┌───────────────┼───────────────┐                 │
│              ▼               ▼               ▼                 │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐  │
│  │  WORKER DRONES  │ │ BUILDER DRONES  │ │RESEARCHER DRONES│  │
│  │  General tasks  │ │ Create products │ │ Market research │  │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘  │
│              │               │               │                 │
│              └───────────────┼───────────────┘                 │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  SHARED SKILLBOOK                       │   │
│  │  ACE-based learning from all task executions            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    MONETIZATION                         │   │
│  │  Treasury │ Product Registry │ Pricing Engine           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### Queen Agent
- **Strategic Planner**: Sets goals and breaks them into tasks
- **Replicator**: Decides when and what type of drones to spawn
- **Decision Agent**: Uses LLM for complex strategic decisions

### Drone Types
- **Worker**: General-purpose task execution
- **Builder**: Creates products, code, and content
- **Researcher**: Market research and opportunity discovery
- **Seller**: Marketing and sales execution

### Learning System
- **Hive Skillbook**: Shared knowledge base across all drones
- **ACE Wrapper**: Reflector and SkillManager for continuous learning
- **Async Learning**: Non-blocking learning pipeline

### Monetization
- **Treasury**: Track revenue, costs, and profit
- **Product Registry**: Catalog of products and services
- **Pricing Engine**: Multiple pricing strategies (cost-plus, value-based, competitive)

## Quick Start

```python
from agent_hive import AgentHive, HiveConfig

# Create and configure the hive
config = HiveConfig(hive_name="MyHive")
hive = AgentHive(config)

# Initialize (spawns initial drones)
hive.initialize()

# Add tasks
hive.add_task(
    title="Research AI trends",
    description="Find emerging AI market opportunities",
    drone_type="researcher",
)

# Run the hive
import asyncio
results = asyncio.run(hive.run(cycles=10))

# Check status
print(hive.get_stats())
```

## Configuration

```python
from agent_hive import HiveConfig
from agent_hive.config import LLMConfig, ReplicationConfig

config = HiveConfig(
    hive_name="ProductionHive",
    llm=LLMConfig(
        primary_model="gemini-2.5-flash",
        fast_model="gemini-2.5-flash",
        ace_model="gemini/gemini-2.0-flash",
    ),
    replication=ReplicationConfig(
        initial_workers=2,
        initial_builders=2,
        initial_researchers=1,
        max_drones_per_type=5,
    ),
)
```

## Directory Structure

```
agent_hive/
├── __init__.py          # Package exports
├── hive.py              # Main AgentHive orchestrator
├── run_hive.py          # Example runner script
├── config/
│   ├── __init__.py
│   └── settings.py      # Configuration classes
├── queen/
│   ├── __init__.py
│   ├── agent.py         # Queen agent
│   ├── planner.py       # Strategic planning
│   └── replicator.py    # Self-replication management
├── drones/
│   ├── __init__.py
│   ├── base.py          # Base drone class
│   ├── worker.py        # Worker drone
│   ├── builder.py       # Builder drone
│   ├── researcher.py    # Researcher drone
│   └── seller.py        # Seller drone
├── tools/
│   ├── __init__.py
│   ├── web_tools.py     # Web search, fetch
│   ├── code_tools.py    # Code execution, file ops
│   └── file_tools.py    # File system operations
├── learning/
│   ├── __init__.py
│   ├── hive_skillbook.py  # Shared skillbook
│   └── ace_wrapper.py     # ACE integration
└── monetization/
    ├── __init__.py
    ├── treasury.py      # Financial tracking
    ├── products.py      # Product/service registry
    └── strategies.py    # Pricing strategies
```

## Requirements

- Python 3.11+
- Google ADK
- ACE Framework (optional, for full learning capabilities)
- LiteLLM (for multi-provider LLM support)

## License

MIT License
