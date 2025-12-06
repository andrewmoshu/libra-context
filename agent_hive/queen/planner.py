"""Strategic planning for Agent Hive."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import json
import logging
import uuid

if TYPE_CHECKING:
    from google.adk.agents import Agent

logger = logging.getLogger(__name__)


class StrategyType(Enum):
    """Types of strategic actions."""

    EXPAND = "expand"  # Grow into new markets/products
    OPTIMIZE = "optimize"  # Improve existing operations
    CONSOLIDATE = "consolidate"  # Focus on core strengths
    PIVOT = "pivot"  # Change direction based on learnings


class Priority(Enum):
    """Task priority levels."""

    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class StrategicGoal:
    """A strategic goal for the hive."""

    goal_id: str
    title: str
    description: str
    strategy_type: StrategyType
    priority: Priority
    target_metric: str
    target_value: float
    current_value: float = 0.0
    deadline: Optional[str] = None
    status: str = "active"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def progress(self) -> float:
        """Calculate progress toward goal (0-1)."""
        if self.target_value == 0:
            return 0.0
        return min(self.current_value / self.target_value, 1.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "title": self.title,
            "description": self.description,
            "strategy_type": self.strategy_type.value,
            "priority": self.priority.value,
            "target_metric": self.target_metric,
            "target_value": self.target_value,
            "current_value": self.current_value,
            "progress": self.progress(),
            "deadline": self.deadline,
            "status": self.status,
            "created_at": self.created_at,
        }


@dataclass
class Task:
    """A task to be assigned to drones."""

    task_id: str
    title: str
    description: str
    required_drone_type: str
    priority: Priority
    estimated_time: int  # minutes
    goal_id: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    assigned_drone: Optional[str] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "required_drone_type": self.required_drone_type,
            "priority": self.priority.value,
            "estimated_time": self.estimated_time,
            "goal_id": self.goal_id,
            "dependencies": self.dependencies,
            "context": self.context,
            "status": self.status,
            "assigned_drone": self.assigned_drone,
            "created_at": self.created_at,
        }


class StrategicPlanner:
    """
    Strategic planning component for the Queen Agent.

    Responsibilities:
    - Define and track strategic goals
    - Break down goals into tasks
    - Prioritize task queue
    - Allocate resources to tasks
    - LLM-powered intelligent task generation
    """

    # Task templates for each strategy type and drone type combination
    TASK_TEMPLATES = {
        StrategyType.EXPAND: {
            "researcher": [
                "Research market opportunities for {goal}",
                "Identify target customer segments for {goal}",
                "Analyze competitor landscape for {goal}",
            ],
            "analyst": [
                "Calculate ROI potential for {goal}",
                "Assess risks and mitigation strategies for {goal}",
            ],
            "builder": [
                "Create prototype/MVP for {goal}",
                "Build landing page or documentation for {goal}",
            ],
            "seller": [
                "Create marketing strategy for {goal}",
                "Identify potential sales channels for {goal}",
            ],
        },
        StrategyType.OPTIMIZE: {
            "analyst": [
                "Analyze current performance metrics for {goal}",
                "Identify optimization opportunities for {goal}",
            ],
            "worker": [
                "Implement optimization improvements for {goal}",
            ],
        },
        StrategyType.CONSOLIDATE: {
            "analyst": [
                "Evaluate current resource allocation for {goal}",
            ],
            "worker": [
                "Consolidate and streamline processes for {goal}",
            ],
        },
        StrategyType.PIVOT: {
            "researcher": [
                "Research alternative directions for {goal}",
            ],
            "analyst": [
                "Compare pivot options and outcomes for {goal}",
            ],
        },
    }

    def __init__(self, model: Optional[str] = None):
        """
        Initialize the strategic planner.

        Args:
            model: Optional LLM model for intelligent task generation
        """
        self.goals: Dict[str, StrategicGoal] = {}
        self.task_queue: List[Task] = []
        self.completed_tasks: List[Task] = []
        self.model = model
        self._task_generator: Optional["Agent"] = None

    def add_goal(self, goal: StrategicGoal) -> None:
        """Add a strategic goal."""
        self.goals[goal.goal_id] = goal
        logger.info(f"Added goal: {goal.title} (priority={goal.priority.name})")

    def remove_goal(self, goal_id: str) -> bool:
        """Remove a goal."""
        if goal_id in self.goals:
            del self.goals[goal_id]
            return True
        return False

    def update_goal_progress(self, goal_id: str, new_value: float) -> None:
        """Update progress toward a goal."""
        if goal_id in self.goals:
            self.goals[goal_id].current_value = new_value
            if self.goals[goal_id].progress() >= 1.0:
                self.goals[goal_id].status = "completed"
                logger.info(f"Goal completed: {self.goals[goal_id].title}")

    def add_task(self, task: Task) -> None:
        """Add a task to the queue."""
        self.task_queue.append(task)
        self._sort_queue()
        logger.debug(f"Added task: {task.title}")

    def _sort_queue(self) -> None:
        """Sort task queue by priority."""
        self.task_queue.sort(key=lambda t: t.priority.value)

    def get_next_task(self, drone_type: str = None) -> Optional[Task]:
        """Get the next task to execute, optionally filtering by drone type."""
        for task in self.task_queue:
            if task.status != "pending":
                continue
            if drone_type and task.required_drone_type != drone_type:
                continue
            # Check dependencies
            deps_met = all(
                dep in [t.task_id for t in self.completed_tasks]
                for dep in task.dependencies
            )
            if deps_met:
                return task
        return None

    def assign_task(self, task_id: str, drone_id: str) -> bool:
        """Assign a task to a drone."""
        for task in self.task_queue:
            if task.task_id == task_id:
                task.assigned_drone = drone_id
                task.status = "assigned"
                return True
        return False

    def complete_task(self, task_id: str, success: bool = True) -> Optional[Task]:
        """Mark a task as completed."""
        for i, task in enumerate(self.task_queue):
            if task.task_id == task_id:
                task.status = "completed" if success else "failed"
                completed = self.task_queue.pop(i)
                self.completed_tasks.append(completed)
                return completed
        return None

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get statistics about the task queue."""
        by_type = {}
        by_priority = {}
        by_status = {}

        for task in self.task_queue:
            # By drone type
            by_type[task.required_drone_type] = by_type.get(task.required_drone_type, 0) + 1
            # By priority
            by_priority[task.priority.name] = by_priority.get(task.priority.name, 0) + 1
            # By status
            by_status[task.status] = by_status.get(task.status, 0) + 1

        return {
            "total_pending": len([t for t in self.task_queue if t.status == "pending"]),
            "total_assigned": len([t for t in self.task_queue if t.status == "assigned"]),
            "total_completed": len(self.completed_tasks),
            "by_drone_type": by_type,
            "by_priority": by_priority,
            "by_status": by_status,
        }

    def generate_tasks_for_goal(
        self,
        goal: StrategicGoal,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Task]:
        """
        Generate tasks to achieve a goal using templates and optional LLM enhancement.

        Args:
            goal: The strategic goal to generate tasks for
            context: Optional context for task generation (skillbook insights, etc.)

        Returns:
            List of tasks to achieve the goal
        """
        tasks = []
        templates = self.TASK_TEMPLATES.get(goal.strategy_type, {})

        # Generate tasks from templates
        previous_task_id = None
        for drone_type, task_templates in templates.items():
            for i, template in enumerate(task_templates):
                task_id = str(uuid.uuid4())[:8]
                description = template.format(goal=goal.description)

                # Add context if provided
                if context:
                    description += f"\n\nContext: {json.dumps(context, indent=2)}"

                task = Task(
                    task_id=task_id,
                    title=f"{drone_type.title()}: {goal.title}",
                    description=description,
                    required_drone_type=drone_type,
                    priority=goal.priority,
                    estimated_time=self._estimate_time(drone_type),
                    goal_id=goal.goal_id,
                    dependencies=[previous_task_id] if previous_task_id and i > 0 else [],
                )
                tasks.append(task)

                # Chain dependencies within same drone type
                if i == len(task_templates) - 1:
                    previous_task_id = task_id

        return tasks

    def _estimate_time(self, drone_type: str) -> int:
        """Estimate task time based on drone type."""
        time_estimates = {
            "researcher": 30,
            "analyst": 25,
            "builder": 60,
            "seller": 45,
            "worker": 20,
        }
        return time_estimates.get(drone_type, 30)

    def create_opportunity_tasks(
        self,
        opportunity_name: str,
        opportunity_score: int,
        revenue_estimate: float,
    ) -> List[Task]:
        """
        Create a sequence of tasks to pursue a business opportunity.

        Args:
            opportunity_name: Name of the opportunity
            opportunity_score: Score from analyst (0-100)
            revenue_estimate: Estimated revenue potential

        Returns:
            List of tasks in execution order
        """
        tasks = []

        # Only pursue opportunities with score >= 60
        if opportunity_score < 60:
            logger.info(
                f"Skipping opportunity '{opportunity_name}' (score {opportunity_score} < 60)"
            )
            return tasks

        priority = Priority.HIGH if opportunity_score >= 80 else Priority.MEDIUM

        # Phase 1: Deep research
        research_task = Task(
            task_id=str(uuid.uuid4())[:8],
            title=f"Deep dive: {opportunity_name}",
            description=(
                f"Conduct in-depth research on '{opportunity_name}'.\n"
                f"Opportunity Score: {opportunity_score}/100\n"
                f"Revenue Estimate: ${revenue_estimate:,.2f}\n\n"
                "Research requirements:\n"
                "1. Validate market size and demand\n"
                "2. Identify top 3 competitors\n"
                "3. Document customer pain points\n"
                "4. Outline technical requirements"
            ),
            required_drone_type="researcher",
            priority=priority,
            estimated_time=45,
            context={"opportunity_score": opportunity_score, "revenue_estimate": revenue_estimate},
        )
        tasks.append(research_task)

        # Phase 2: Financial analysis
        analysis_task = Task(
            task_id=str(uuid.uuid4())[:8],
            title=f"Financial analysis: {opportunity_name}",
            description=(
                f"Create detailed financial projections for '{opportunity_name}'.\n"
                "Analysis requirements:\n"
                "1. Cost breakdown (development, marketing, operations)\n"
                "2. Revenue projections (6mo, 12mo, 24mo)\n"
                "3. Break-even analysis\n"
                "4. Risk-adjusted ROI calculation"
            ),
            required_drone_type="analyst",
            priority=priority,
            estimated_time=30,
            dependencies=[research_task.task_id],
            context={"opportunity_score": opportunity_score, "revenue_estimate": revenue_estimate},
        )
        tasks.append(analysis_task)

        # Phase 3: Build MVP (only for high-scoring opportunities)
        if opportunity_score >= 75:
            build_task = Task(
                task_id=str(uuid.uuid4())[:8],
                title=f"Build MVP: {opportunity_name}",
                description=(
                    f"Create minimum viable product for '{opportunity_name}'.\n"
                    "Build requirements:\n"
                    "1. Core functionality implementation\n"
                    "2. Basic documentation\n"
                    "3. Simple landing page or demo\n"
                    "4. Initial pricing structure"
                ),
                required_drone_type="builder",
                priority=priority,
                estimated_time=120,
                dependencies=[analysis_task.task_id],
                context={"opportunity_score": opportunity_score, "revenue_estimate": revenue_estimate},
            )
            tasks.append(build_task)

            # Phase 4: Go-to-market
            market_task = Task(
                task_id=str(uuid.uuid4())[:8],
                title=f"Launch: {opportunity_name}",
                description=(
                    f"Execute go-to-market strategy for '{opportunity_name}'.\n"
                    "Launch requirements:\n"
                    "1. Create marketing materials\n"
                    "2. Identify initial target customers\n"
                    "3. Set up sales funnel\n"
                    "4. Track initial metrics"
                ),
                required_drone_type="seller",
                priority=priority,
                estimated_time=60,
                dependencies=[build_task.task_id],
                context={"opportunity_score": opportunity_score, "revenue_estimate": revenue_estimate},
            )
            tasks.append(market_task)

        return tasks

    def to_dict(self) -> Dict[str, Any]:
        """Serialize planner state."""
        return {
            "goals": {gid: g.to_dict() for gid, g in self.goals.items()},
            "task_queue": [t.to_dict() for t in self.task_queue],
            "completed_tasks": [t.to_dict() for t in self.completed_tasks],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StrategicPlanner":
        """Deserialize planner state."""
        planner = cls()

        for gid, gdata in data.get("goals", {}).items():
            goal = StrategicGoal(
                goal_id=gdata["goal_id"],
                title=gdata["title"],
                description=gdata["description"],
                strategy_type=StrategyType(gdata["strategy_type"]),
                priority=Priority(gdata["priority"]),
                target_metric=gdata["target_metric"],
                target_value=gdata["target_value"],
                current_value=gdata.get("current_value", 0.0),
                deadline=gdata.get("deadline"),
                status=gdata.get("status", "active"),
                created_at=gdata.get("created_at", datetime.now(timezone.utc).isoformat()),
            )
            planner.goals[gid] = goal

        for tdata in data.get("task_queue", []):
            task = Task(
                task_id=tdata["task_id"],
                title=tdata["title"],
                description=tdata["description"],
                required_drone_type=tdata["required_drone_type"],
                priority=Priority(tdata["priority"]),
                estimated_time=tdata["estimated_time"],
                goal_id=tdata.get("goal_id"),
                dependencies=tdata.get("dependencies", []),
                context=tdata.get("context", {}),
                status=tdata.get("status", "pending"),
                assigned_drone=tdata.get("assigned_drone"),
                created_at=tdata.get("created_at", datetime.now(timezone.utc).isoformat()),
            )
            planner.task_queue.append(task)

        return planner
