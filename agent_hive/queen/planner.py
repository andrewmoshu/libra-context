"""Strategic planning for Agent Hive."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import json
import logging

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
    """

    def __init__(self):
        self.goals: Dict[str, StrategicGoal] = {}
        self.task_queue: List[Task] = []
        self.completed_tasks: List[Task] = []

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

    def generate_tasks_for_goal(self, goal: StrategicGoal) -> List[Task]:
        """
        Generate tasks to achieve a goal.

        This is a template - actual implementation will use LLM.
        """
        import uuid

        tasks = []

        # Default task generation based on strategy type
        if goal.strategy_type == StrategyType.EXPAND:
            tasks.append(
                Task(
                    task_id=str(uuid.uuid4())[:8],
                    title=f"Research: {goal.title}",
                    description=f"Research opportunities for: {goal.description}",
                    required_drone_type="researcher",
                    priority=goal.priority,
                    estimated_time=30,
                    goal_id=goal.goal_id,
                )
            )
            tasks.append(
                Task(
                    task_id=str(uuid.uuid4())[:8],
                    title=f"Build: {goal.title}",
                    description=f"Create deliverables for: {goal.description}",
                    required_drone_type="builder",
                    priority=goal.priority,
                    estimated_time=60,
                    goal_id=goal.goal_id,
                    dependencies=[tasks[0].task_id],
                )
            )

        elif goal.strategy_type == StrategyType.OPTIMIZE:
            tasks.append(
                Task(
                    task_id=str(uuid.uuid4())[:8],
                    title=f"Analyze: {goal.title}",
                    description=f"Analyze current state for: {goal.description}",
                    required_drone_type="worker",
                    priority=goal.priority,
                    estimated_time=20,
                    goal_id=goal.goal_id,
                )
            )

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
