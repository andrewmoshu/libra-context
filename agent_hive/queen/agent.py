"""Queen agent - orchestrates the Agent Hive."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import logging
import uuid

from google.adk import Agent
from google.adk.agents import SequentialAgent

from agent_hive.queen.planner import StrategicPlanner, Task, StrategicGoal, Priority, StrategyType
from agent_hive.queen.replicator import ReplicationManager, ReplicationMetrics
from agent_hive.drones.base import BaseDrone, DroneType, TaskResult
from agent_hive.config.settings import HiveConfig

logger = logging.getLogger(__name__)


@dataclass
class HiveStatus:
    """Current status of the hive."""

    total_drones: int = 0
    active_tasks: int = 0
    pending_tasks: int = 0
    completed_tasks: int = 0
    total_revenue: float = 0.0
    total_cost: float = 0.0
    uptime_seconds: float = 0.0
    goals_active: int = 0
    goals_completed: int = 0


class QueenAgent:
    """
    The Queen Agent orchestrates the entire Agent Hive.

    Responsibilities:
    - Strategic planning and goal setting
    - Resource allocation and task assignment
    - Drone replication decisions
    - Performance monitoring
    - Revenue and cost tracking
    """

    def __init__(self, config: HiveConfig):
        """
        Initialize the Queen Agent.

        Args:
            config: Configuration for the hive
        """
        self.config = config
        self.hive_id = config.hive_id
        self.created_at = datetime.now(timezone.utc)

        # Core components
        self.planner = StrategicPlanner()
        self.replicator = ReplicationManager(config.replication, self.hive_id)

        # ADK agent for complex decisions
        self._decision_agent: Optional[Agent] = None

        # Metrics
        self.total_revenue = 0.0
        self.total_cost = 0.0
        self.task_history: List[Dict[str, Any]] = []

        logger.info(f"Queen Agent initialized for hive {self.hive_id}")

    def _initialize_decision_agent(self) -> None:
        """Initialize the ADK agent for complex decisions."""
        if self._decision_agent is not None:
            return

        self._decision_agent = Agent(
            model=self.config.llm.primary_model,
            name="queen_decision_agent",
            description="Strategic decision-making agent for the hive",
            instruction=self._get_decision_instructions(),
        )

    def _get_decision_instructions(self) -> str:
        """Get instructions for the decision agent."""
        return """You are the Queen Agent's decision-making module for an autonomous agent hive.

Your role is to make strategic decisions that maximize the hive's success.

DECISION DOMAINS:
1. Goal Setting
   - Identify high-value opportunities
   - Set measurable targets
   - Prioritize based on ROI potential

2. Resource Allocation
   - Assign tasks to appropriate drones
   - Balance workload across the hive
   - Optimize for efficiency

3. Replication Decisions
   - Determine when to spawn new drones
   - Select optimal drone types
   - Manage hive capacity

4. Performance Optimization
   - Identify underperforming areas
   - Suggest improvements
   - Learn from successes and failures

DECISION PRINCIPLES:
1. Data-driven: Base decisions on metrics
2. ROI-focused: Prioritize profitable activities
3. Long-term thinking: Build sustainable growth
4. Adaptive: Adjust strategy based on results

OUTPUT FORMAT:
Always provide:
- Clear recommendation
- Supporting reasoning
- Expected outcomes
- Risk assessment"""

    def initialize(self) -> None:
        """Initialize the hive with initial drones and goals."""
        # Spawn initial drones
        self.replicator.spawn_initial_drones(model=self.config.llm.fast_model)

        # Set up initial strategic goals
        self._set_initial_goals()

        logger.info(f"Hive {self.hive_id} initialized with {len(self.replicator.drones)} drones")

    def _set_initial_goals(self) -> None:
        """Set initial strategic goals for the hive."""
        # Goal 1: Establish revenue stream
        revenue_goal = StrategicGoal(
            goal_id=str(uuid.uuid4())[:8],
            title="First Revenue",
            description="Generate the first $100 in revenue through products or services",
            strategy_type=StrategyType.EXPAND,
            priority=Priority.HIGH,
            target_metric="revenue",
            target_value=100.0,
        )
        self.planner.add_goal(revenue_goal)

        # Generate initial tasks for this goal
        tasks = self.planner.generate_tasks_for_goal(revenue_goal)
        for task in tasks:
            self.planner.add_task(task)

        # Goal 2: Build knowledge base
        learning_goal = StrategicGoal(
            goal_id=str(uuid.uuid4())[:8],
            title="Knowledge Foundation",
            description="Accumulate 50 validated skills in the skillbook",
            strategy_type=StrategyType.OPTIMIZE,
            priority=Priority.MEDIUM,
            target_metric="skill_count",
            target_value=50.0,
        )
        self.planner.add_goal(learning_goal)

    def get_status(self) -> HiveStatus:
        """Get current hive status."""
        uptime = (datetime.now(timezone.utc) - self.created_at).total_seconds()

        return HiveStatus(
            total_drones=len(self.replicator.drones),
            active_tasks=len([t for t in self.planner.task_queue if t.status == "assigned"]),
            pending_tasks=len([t for t in self.planner.task_queue if t.status == "pending"]),
            completed_tasks=len(self.planner.completed_tasks),
            total_revenue=self.total_revenue,
            total_cost=self.total_cost,
            uptime_seconds=uptime,
            goals_active=len([g for g in self.planner.goals.values() if g.status == "active"]),
            goals_completed=len([g for g in self.planner.goals.values() if g.status == "completed"]),
        )

    def assign_tasks(self) -> List[tuple[str, str]]:
        """
        Assign pending tasks to idle drones.

        Returns:
            List of (task_id, drone_id) assignments
        """
        assignments = []
        idle_drones = self.replicator.get_idle_drones()

        for drone in idle_drones:
            task = self.planner.get_next_task(drone.drone_type.value)
            if task:
                self.planner.assign_task(task.task_id, drone.drone_id)
                assignments.append((task.task_id, drone.drone_id))
                logger.debug(f"Assigned task {task.task_id} to drone {drone.drone_id}")

        return assignments

    async def execute_assigned_tasks(self) -> List[TaskResult]:
        """Execute all assigned tasks."""
        results = []

        for task in self.planner.task_queue:
            if task.status != "assigned" or not task.assigned_drone:
                continue

            drone = self.replicator.get_drone(task.assigned_drone)
            if not drone:
                continue

            # Execute task
            result = await drone.execute(task.description, task.context)

            # Update task status
            self.planner.complete_task(task.task_id, result.success)

            # Track costs
            self.total_cost += result.cost_estimate

            # Record in history
            self.task_history.append({
                "task_id": task.task_id,
                "drone_id": drone.drone_id,
                "success": result.success,
                "cost": result.cost_estimate,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            results.append(result)

        return results

    def check_replication(self) -> Optional[BaseDrone]:
        """
        Check if we should spawn a new drone.

        Returns:
            Newly spawned drone, or None
        """
        metrics = ReplicationMetrics(
            task_queue_depth=len([t for t in self.planner.task_queue if t.status == "pending"]),
            drones_by_type=self.replicator.get_drone_counts(),
            revenue_potential=self.total_revenue * 1.5,  # Simple estimate
            estimated_cost=0.01,  # Cost per drone operation
        )

        # Calculate success rates
        for drone in self.replicator.drones.values():
            total = drone.metrics.tasks_completed + drone.metrics.tasks_failed
            if total > 0:
                metrics.success_rate_by_type[drone.drone_type.value] = (
                    drone.metrics.success_rate
                )

        decision = self.replicator.should_replicate(metrics)

        if decision.should_replicate and decision.drone_type:
            return self.replicator.spawn_drone(
                decision.drone_type,
                model=self.config.llm.fast_model,
            )

        return None

    def add_revenue(self, amount: float, source: str) -> None:
        """Record revenue."""
        self.total_revenue += amount

        # Update goal progress
        for goal in self.planner.goals.values():
            if goal.target_metric == "revenue":
                self.planner.update_goal_progress(goal.goal_id, self.total_revenue)

        logger.info(f"Revenue added: ${amount:.2f} from {source}")

    def create_task(
        self,
        title: str,
        description: str,
        drone_type: str,
        priority: Priority = Priority.MEDIUM,
        estimated_time: int = 30,
        context: Optional[Dict[str, Any]] = None,
    ) -> Task:
        """Create and add a new task."""
        task = Task(
            task_id=str(uuid.uuid4())[:8],
            title=title,
            description=description,
            required_drone_type=drone_type,
            priority=priority,
            estimated_time=estimated_time,
            context=context or {},
        )
        self.planner.add_task(task)
        return task

    def to_dict(self) -> Dict[str, Any]:
        """Serialize Queen state."""
        return {
            "hive_id": self.hive_id,
            "created_at": self.created_at.isoformat(),
            "total_revenue": self.total_revenue,
            "total_cost": self.total_cost,
            "planner": self.planner.to_dict(),
            "replicator_status": self.replicator.get_status(),
            "task_history": self.task_history[-100:],  # Keep last 100
        }

    async def run_cycle(self) -> Dict[str, Any]:
        """
        Run one cycle of hive operations.

        Returns:
            Summary of cycle results
        """
        cycle_start = datetime.now(timezone.utc)

        # 1. Assign pending tasks
        assignments = self.assign_tasks()

        # 2. Execute assigned tasks
        results = await self.execute_assigned_tasks()

        # 3. Check if we should spawn new drones
        new_drone = self.check_replication()

        # 4. Compile cycle summary
        cycle_duration = (datetime.now(timezone.utc) - cycle_start).total_seconds()

        return {
            "cycle_duration": cycle_duration,
            "tasks_assigned": len(assignments),
            "tasks_completed": len([r for r in results if r.success]),
            "tasks_failed": len([r for r in results if not r.success]),
            "new_drone": new_drone.drone_id if new_drone else None,
            "status": self.get_status().__dict__,
        }
