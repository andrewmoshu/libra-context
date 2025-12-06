"""
Agent Hive - A self-replicating, self-learning agent collective.

This package implements an autonomous agent hive that:
1. Creates products and services
2. Monetizes them successfully
3. Learns from every interaction using ACE (Agentic Context Engineering)
4. Replicates agents to scale operations

Built on:
- Google ADK (Agent Development Kit) for agent orchestration
- ACE Framework for self-improvement through learning
"""

from agent_hive.hive import AgentHive
from agent_hive.config.settings import HiveConfig

__version__ = "0.1.0"
__all__ = ["AgentHive", "HiveConfig"]
