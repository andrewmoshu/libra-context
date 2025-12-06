"""
Agent Hive - Main orchestrator for the self-replicating, self-learning agent collective.

This module provides the AgentHive class that coordinates:
- Queen agent for strategic planning
- Drone agents for task execution
- ACE-based learning for continuous improvement
- Monetization tracking for profitability
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
import json

from agent_hive.config.settings import HiveConfig
from agent_hive.queen.agent import QueenAgent, HiveStatus
from agent_hive.queen.planner import Task, Priority
from agent_hive.drones.base import BaseDrone, DroneType, TaskResult, DroneStatus
from agent_hive.learning.hive_skillbook import HiveSkillbook
from agent_hive.learning.ace_wrapper import ACEWrapper, LearningResult

logger = logging.getLogger(__name__)


@dataclass
class HiveCycleResult:
    """Result from one hive operation cycle."""

    cycle_number: int
    tasks_assigned: int
    tasks_completed: int
    tasks_failed: int
    skills_learned: int
    revenue_generated: float
    cost_incurred: float
    new_drones_spawned: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle_number": self.cycle_number,
            "tasks_assigned": self.tasks_assigned,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "skills_learned": self.skills_learned,
            "revenue_generated": self.revenue_generated,
            "cost_incurred": self.cost_incurred,
            "new_drones_spawned": self.new_drones_spawned,
            "errors": self.errors,
            "timestamp": self.timestamp,
        }


class AgentHive:
    """
    Main orchestrator for the Agent Hive.

    The AgentHive coordinates all components:
    - Queen: Strategic planning, goal setting, resource allocation
    - Drones: Task execution (workers, builders, researchers, sellers)
    - Skillbook: Shared knowledge base for continuous learning
    - ACE: Reflector and SkillManager for self-improvement

    The hive is designed to be self-sufficient:
    - Self-replicating: Spawns new drones based on demand
    - Self-learning: Uses ACE to learn from every task
    - Self-monetizing: Tracks revenue and optimizes for profit
    """

    def __init__(self, config: Optional[HiveConfig] = None):
        """
        Initialize the Agent Hive.

        Args:
            config: Configuration for the hive. Uses defaults if not provided.
        """
        self.config = config or HiveConfig()
        self.hive_id = self.config.hive_id
        self.created_at = datetime.now(timezone.utc)

        # Core components
        self.queen = QueenAgent(self.config)
        self.skillbook = HiveSkillbook(self.config.learning.skillbook_path)
        self.ace = ACEWrapper(
            skillbook=self.skillbook,
            ace_model=self.config.llm.ace_model,
            async_learning=self.config.learning.async_learning,
            on_learning_complete=self._on_learning_complete,
        )

        # State tracking
        self._initialized = False
        self._running = False
        self._cycle_count = 0
        self._cycle_history: List[HiveCycleResult] = []

        # Callbacks
        self._on_task_complete: Optional[Callable[[TaskResult], None]] = None
        self._on_skill_learned: Optional[Callable[[LearningResult], None]] = None
        self._on_cycle_complete: Optional[Callable[[HiveCycleResult], None]] = None

        logger.info(f"AgentHive created: {self.hive_id} ({self.config.hive_name})")

    def initialize(self) -> None:
        """
        Initialize the hive with initial drones and goals.

        This must be called before running the hive.
        """
        if self._initialized:
            logger.warning("Hive already initialized")
            return

        # Initialize queen (spawns initial drones, sets initial goals)
        self.queen.initialize()

        # Set up drone callbacks for learning
        for drone in self.queen.replicator.drones.values():
            self._setup_drone_callbacks(drone)

        # Load any existing skillbook
        if self.skillbook.stats()["skills"] > 0:
            logger.info(
                f"Loaded existing skillbook with {self.skillbook.stats()['skills']} skills"
            )

        self._initialized = True
        logger.info(f"Hive {self.hive_id} initialized with {len(self.queen.replicator.drones)} drones")

    def _setup_drone_callbacks(self, drone: BaseDrone) -> None:
        """Set up callbacks on a drone for learning integration."""
        original_callback = drone._on_task_complete

        def wrapped_callback(result: TaskResult):
            # Call original callback if exists
            if original_callback:
                original_callback(result)

            # Trigger learning
            asyncio.create_task(self._learn_from_result(drone, result))

        drone.set_callbacks(on_task_complete=wrapped_callback)

    async def _learn_from_result(self, drone: BaseDrone, result: TaskResult) -> None:
        """Learn from a completed task result."""
        try:
            # Get task description from planner
            task_description = "Unknown task"
            for task in self.queen.planner.completed_tasks:
                if task.task_id == result.task_id:
                    task_description = task.description
                    break

            # Run ACE learning
            learning_result = await self.ace.learn_from_task(
                task_description=task_description,
                task_result=result,
                drone_id=drone.drone_id,
                context={"drone_type": drone.drone_type.value},
            )

            logger.debug(
                f"Learning complete for task {result.task_id}: "
                f"{len(learning_result.skills_added)} skills added"
            )

        except Exception as e:
            logger.error(f"Learning failed for task {result.task_id}: {e}")

    def _on_learning_complete(self, result: LearningResult) -> None:
        """Callback when ACE learning completes."""
        if self._on_skill_learned:
            self._on_skill_learned(result)

    @property
    def status(self) -> HiveStatus:
        """Get current hive status."""
        return self.queen.get_status()

    @property
    def drones(self) -> Dict[str, BaseDrone]:
        """Get all drones in the hive."""
        return self.queen.replicator.drones

    def add_task(
        self,
        title: str,
        description: str,
        drone_type: str = "worker",
        priority: Priority = Priority.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
    ) -> Task:
        """
        Add a new task to the hive.

        Args:
            title: Task title
            description: Task description
            drone_type: Type of drone to handle this task
            priority: Task priority
            context: Additional context for the task

        Returns:
            The created Task
        """
        return self.queen.create_task(
            title=title,
            description=description,
            drone_type=drone_type,
            priority=priority,
            context=context,
        )

    async def run_cycle(self) -> HiveCycleResult:
        """
        Run one complete hive operation cycle.

        A cycle includes:
        1. Assigning pending tasks to idle drones
        2. Executing assigned tasks
        3. Learning from results
        4. Checking for replication needs
        5. Updating metrics

        Returns:
            HiveCycleResult with cycle summary
        """
        if not self._initialized:
            raise RuntimeError("Hive not initialized. Call initialize() first.")

        self._cycle_count += 1
        cycle_result = HiveCycleResult(
            cycle_number=self._cycle_count,
            tasks_assigned=0,
            tasks_completed=0,
            tasks_failed=0,
            skills_learned=0,
            revenue_generated=0.0,
            cost_incurred=0.0,
        )

        try:
            # Run queen's cycle (assigns and executes tasks)
            queen_result = await self.queen.run_cycle()

            cycle_result.tasks_assigned = queen_result["tasks_assigned"]
            cycle_result.tasks_completed = queen_result["tasks_completed"]
            cycle_result.tasks_failed = queen_result["tasks_failed"]

            # Track new drone if spawned
            if queen_result.get("new_drone"):
                cycle_result.new_drones_spawned.append(queen_result["new_drone"])
                # Set up callbacks for new drone
                new_drone = self.queen.replicator.get_drone(queen_result["new_drone"])
                if new_drone:
                    self._setup_drone_callbacks(new_drone)

            # Get learning stats
            learning_stats = self.ace.get_learning_stats()
            cycle_result.skills_learned = learning_stats["total_skills_added"]

            # Get cost tracking
            cycle_result.cost_incurred = self.queen.total_cost
            cycle_result.revenue_generated = self.queen.total_revenue

        except Exception as e:
            logger.error(f"Cycle {self._cycle_count} error: {e}")
            cycle_result.errors.append(str(e))

        # Store in history
        self._cycle_history.append(cycle_result)

        # Callback
        if self._on_cycle_complete:
            self._on_cycle_complete(cycle_result)

        return cycle_result

    async def run(
        self,
        cycles: int = 10,
        interval: float = 1.0,
        stop_on_empty: bool = True,
    ) -> List[HiveCycleResult]:
        """
        Run the hive for multiple cycles.

        Args:
            cycles: Maximum number of cycles to run
            interval: Seconds between cycles
            stop_on_empty: Stop if no tasks are pending

        Returns:
            List of HiveCycleResult for each cycle
        """
        if not self._initialized:
            self.initialize()

        self._running = True
        results = []

        try:
            for i in range(cycles):
                if not self._running:
                    logger.info("Hive stopped by external signal")
                    break

                result = await self.run_cycle()
                results.append(result)

                # Check if we should stop
                if stop_on_empty:
                    status = self.status
                    if status.pending_tasks == 0 and status.active_tasks == 0:
                        logger.info("No more tasks, stopping hive")
                        break

                # Wait between cycles
                if i < cycles - 1:
                    await asyncio.sleep(interval)

        finally:
            self._running = False

        return results

    def stop(self) -> None:
        """Stop the hive gracefully."""
        self._running = False
        logger.info(f"Hive {self.hive_id} stop requested")

    def add_revenue(self, amount: float, source: str) -> None:
        """Record revenue from a product or service."""
        self.queen.add_revenue(amount, source)

    def get_skillbook_prompt(self) -> str:
        """Get the skillbook formatted for LLM prompt injection."""
        return self.skillbook.as_prompt()

    def get_top_skills(self, n: int = 10) -> List[Dict[str, Any]]:
        """Get top performing skills."""
        return self.skillbook.get_top_skills(n)

    def get_learning_insights(self, n: int = 10) -> List[str]:
        """Get recent learning insights."""
        return self.ace.get_recent_insights(n)

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive hive statistics."""
        status = self.status
        learning = self.ace.get_learning_stats()
        skillbook = self.skillbook.stats()

        return {
            "hive_id": self.hive_id,
            "name": self.config.hive_name,
            "uptime_seconds": (datetime.now(timezone.utc) - self.created_at).total_seconds(),
            "cycles_completed": self._cycle_count,
            "status": {
                "total_drones": status.total_drones,
                "active_tasks": status.active_tasks,
                "pending_tasks": status.pending_tasks,
                "completed_tasks": status.completed_tasks,
                "goals_active": status.goals_active,
                "goals_completed": status.goals_completed,
            },
            "financials": {
                "total_revenue": status.total_revenue,
                "total_cost": status.total_cost,
                "profit": status.total_revenue - status.total_cost,
            },
            "learning": learning,
            "skillbook": skillbook,
        }

    def save_state(self, path: Optional[str] = None) -> str:
        """
        Save hive state to file.

        Args:
            path: Path to save state. Uses default if not provided.

        Returns:
            Path where state was saved
        """
        path = path or f"{self.config.data_dir}/hive_state_{self.hive_id}.json"

        state = {
            "hive_id": self.hive_id,
            "config": self.config.to_dict(),
            "created_at": self.created_at.isoformat(),
            "cycle_count": self._cycle_count,
            "queen": self.queen.to_dict(),
            "cycle_history": [c.to_dict() for c in self._cycle_history[-100:]],
        }

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(state, f, indent=2)

        logger.info(f"Hive state saved to {path}")
        return path

    def set_callbacks(
        self,
        on_task_complete: Optional[Callable[[TaskResult], None]] = None,
        on_skill_learned: Optional[Callable[[LearningResult], None]] = None,
        on_cycle_complete: Optional[Callable[[HiveCycleResult], None]] = None,
    ) -> None:
        """Set callback functions for hive events."""
        self._on_task_complete = on_task_complete
        self._on_skill_learned = on_skill_learned
        self._on_cycle_complete = on_cycle_complete

    def __repr__(self) -> str:
        status = "initialized" if self._initialized else "not initialized"
        running = "running" if self._running else "stopped"
        return f"AgentHive(id={self.hive_id}, name={self.config.hive_name}, {status}, {running})"
