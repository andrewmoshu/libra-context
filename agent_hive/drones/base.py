"""Base drone class for Agent Hive."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
import uuid
import logging

from google.adk.agents import llm_agent
from google.adk import runners
from google.genai import types

Agent = llm_agent.LlmAgent
InMemoryRunner = runners.InMemoryRunner

logger = logging.getLogger(__name__)


class DroneType(Enum):
    """Types of drone agents in the hive."""

    WORKER = "worker"
    BUILDER = "builder"
    RESEARCHER = "researcher"
    SELLER = "seller"
    ANALYST = "analyst"


class DroneStatus(Enum):
    """Status of a drone agent."""

    IDLE = "idle"
    WORKING = "working"
    LEARNING = "learning"
    ERROR = "error"
    TERMINATED = "terminated"


@dataclass
class TaskResult:
    """Result from executing a task."""

    task_id: str
    success: bool
    output: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    tokens_used: int = 0
    cost_estimate: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "execution_time": self.execution_time,
            "tokens_used": self.tokens_used,
            "cost_estimate": self.cost_estimate,
            "metadata": self.metadata,
        }


@dataclass
class DroneMetrics:
    """Metrics tracked for each drone."""

    tasks_completed: int = 0
    tasks_failed: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    total_revenue: float = 0.0
    avg_execution_time: float = 0.0
    success_rate: float = 0.0
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    last_active: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def update(self, result: TaskResult) -> None:
        """Update metrics based on task result."""
        if result.success:
            self.tasks_completed += 1
        else:
            self.tasks_failed += 1

        self.total_tokens += result.tokens_used
        self.total_cost += result.cost_estimate

        # Update average execution time
        total_tasks = self.tasks_completed + self.tasks_failed
        self.avg_execution_time = (
            (self.avg_execution_time * (total_tasks - 1) + result.execution_time)
            / total_tasks
            if total_tasks > 0
            else result.execution_time
        )

        # Update success rate
        self.success_rate = (
            self.tasks_completed / total_tasks if total_tasks > 0 else 0.0
        )

        self.last_active = datetime.now(timezone.utc).isoformat()


class BaseDrone(ABC):
    """
    Base class for all drone agents in the hive.

    Drones are specialized agents that perform specific tasks.
    Each drone type has its own set of tools and capabilities.
    """

    def __init__(
        self,
        drone_type: DroneType,
        model: str = "gemini-2.5-flash",
        name: Optional[str] = None,
        hive_id: Optional[str] = None,
    ):
        """
        Initialize a drone agent.

        Args:
            drone_type: Type of drone (worker, builder, etc.)
            model: LLM model to use
            name: Optional name for the drone
            hive_id: ID of the hive this drone belongs to
        """
        self.drone_id = str(uuid.uuid4())[:8]
        self.drone_type = drone_type
        self.model = model
        self.name = name or f"{drone_type.value}_{self.drone_id}"
        self.hive_id = hive_id

        self.status = DroneStatus.IDLE
        self.metrics = DroneMetrics()
        self.current_task_id: Optional[str] = None

        # ADK components - initialized lazily
        self._agent: Optional[Agent] = None
        self._runner: Optional[InMemoryRunner] = None

        # Callbacks
        self._on_task_complete: Optional[Callable[[TaskResult], None]] = None
        self._on_error: Optional[Callable[[Exception], None]] = None

        logger.info(f"Initialized {self.name} (type={drone_type.value})")

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what this drone does."""
        pass

    @property
    @abstractmethod
    def instructions(self) -> str:
        """System instructions for the drone."""
        pass

    @property
    @abstractmethod
    def tools(self) -> List[Callable]:
        """List of tools available to this drone."""
        pass

    def _initialize_agent(self) -> None:
        """Initialize the ADK agent components."""
        if self._agent is not None:
            return

        self._agent = Agent(
            model=self.model,
            name=self.name,
            description=self.description,
            instruction=self.instructions,
            tools=self.tools,
        )

        self._runner = InMemoryRunner(
            agent=self._agent,
            app_name=f"hive_{self.hive_id or 'default'}",
        )

    async def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> TaskResult:
        """
        Execute a task.

        Args:
            task: Task description to execute
            context: Optional context for the task

        Returns:
            TaskResult with execution details
        """
        import time

        task_id = str(uuid.uuid4())[:8]
        self.current_task_id = task_id
        self.status = DroneStatus.WORKING

        start_time = time.time()
        result = TaskResult(
            task_id=task_id,
            success=False,
            output=None,
        )

        try:
            self._initialize_agent()

            # Build the full prompt with context
            full_prompt = task
            if context:
                context_str = "\n".join(f"{k}: {v}" for k, v in context.items())
                full_prompt = f"Context:\n{context_str}\n\nTask: {task}"

            # Create a session for this task
            user_id = f"drone_{self.drone_id}"
            app_name = f"hive_{self.hive_id or 'default'}"
            session = await self._runner.session_service.create_session(
                app_name=app_name,
                user_id=user_id,
            )

            # Create message content
            message = types.Content(
                role="user",
                parts=[types.Part.from_text(text=full_prompt)]
            )

            # Execute via runner and collect response
            response_text = ""
            async for event in self._runner.run_async(
                user_id=user_id,
                session_id=session.id,
                new_message=message,
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    response_text = event.content.parts[0].text or ""
                    break

            # Extract response
            result.success = True
            result.output = response_text

        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
            result.error = str(e)
            self.status = DroneStatus.ERROR

            if self._on_error:
                self._on_error(e)

        finally:
            result.execution_time = time.time() - start_time
            self.metrics.update(result)
            self.current_task_id = None

            if result.success:
                self.status = DroneStatus.IDLE

            if self._on_task_complete:
                self._on_task_complete(result)

        return result

    def execute_sync(self, task: str, context: Optional[Dict[str, Any]] = None) -> TaskResult:
        """
        Synchronous wrapper for execute.

        Args:
            task: Task description to execute
            context: Optional context for the task

        Returns:
            TaskResult with execution details
        """
        import asyncio
        return asyncio.run(self.execute(task, context))

    def set_callbacks(
        self,
        on_task_complete: Optional[Callable[[TaskResult], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ) -> None:
        """Set callback functions for task events."""
        self._on_task_complete = on_task_complete
        self._on_error = on_error

    def get_status(self) -> Dict[str, Any]:
        """Get current status and metrics."""
        return {
            "drone_id": self.drone_id,
            "name": self.name,
            "type": self.drone_type.value,
            "status": self.status.value,
            "current_task": self.current_task_id,
            "metrics": {
                "tasks_completed": self.metrics.tasks_completed,
                "tasks_failed": self.metrics.tasks_failed,
                "success_rate": self.metrics.success_rate,
                "total_tokens": self.metrics.total_tokens,
                "total_cost": self.metrics.total_cost,
                "avg_execution_time": self.metrics.avg_execution_time,
                "last_active": self.metrics.last_active,
            },
        }

    def terminate(self) -> None:
        """Terminate the drone."""
        self.status = DroneStatus.TERMINATED
        logger.info(f"Terminated drone {self.name}")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, status={self.status.value})"
