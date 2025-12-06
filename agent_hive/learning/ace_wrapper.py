"""ACE (Agentic Context Engineering) wrapper for Agent Hive learning."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
import logging
import json

from agent_hive.learning.hive_skillbook import HiveSkillbook
from agent_hive.drones.base import TaskResult

logger = logging.getLogger(__name__)

# Try to import ACE components
try:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
    from ace.roles import Reflector, SkillManager, ReflectorOutput, AgentOutput
    from ace.llm_providers.litellm_client import LiteLLMClient
    from ace.adaptation import Sample, TaskEnvironment, EnvironmentResult
    ACE_AVAILABLE = True
except ImportError:
    ACE_AVAILABLE = False
    logger.warning("ACE framework not available, using simplified learning")


@dataclass
class LearningResult:
    """Result from the learning process."""

    task_id: str
    success: bool
    skills_added: List[str] = field(default_factory=list)
    skills_updated: List[str] = field(default_factory=list)
    skills_tagged: List[str] = field(default_factory=list)
    key_insight: str = ""
    error: Optional[str] = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "success": self.success,
            "skills_added": self.skills_added,
            "skills_updated": self.skills_updated,
            "skills_tagged": self.skills_tagged,
            "key_insight": self.key_insight,
            "error": self.error,
            "timestamp": self.timestamp,
        }


class HiveEnvironment:
    """Task environment for hive operations."""

    def evaluate(
        self,
        task_description: str,
        task_result: TaskResult,
        expected_outcome: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate task execution results.

        Args:
            task_description: What the task was supposed to do
            task_result: The actual result from execution
            expected_outcome: Optional expected outcome for comparison

        Returns:
            Evaluation results with feedback
        """
        feedback_parts = []
        metrics = {}

        # Check success
        if task_result.success:
            feedback_parts.append("Task completed successfully.")
            metrics["success"] = 1.0
        else:
            feedback_parts.append(f"Task failed: {task_result.error}")
            metrics["success"] = 0.0

        # Check execution time
        if task_result.execution_time < 30:
            feedback_parts.append("Execution was fast.")
            metrics["efficiency"] = 1.0
        elif task_result.execution_time < 120:
            feedback_parts.append("Execution time was reasonable.")
            metrics["efficiency"] = 0.7
        else:
            feedback_parts.append("Execution was slow.")
            metrics["efficiency"] = 0.3

        # Compare with expected outcome if provided
        if expected_outcome and task_result.output:
            output_str = str(task_result.output).lower()
            expected_str = expected_outcome.lower()
            if expected_str in output_str:
                feedback_parts.append("Output matches expected outcome.")
                metrics["accuracy"] = 1.0
            else:
                feedback_parts.append("Output differs from expected outcome.")
                metrics["accuracy"] = 0.5

        return {
            "feedback": " ".join(feedback_parts),
            "metrics": metrics,
            "ground_truth": expected_outcome,
        }


class ACEWrapper:
    """
    Wrapper for ACE (Agentic Context Engineering) integration.

    This provides the learning loop for the Agent Hive:
    1. Task executed by drone
    2. Result evaluated by environment
    3. Reflector analyzes outcome
    4. SkillManager updates skillbook

    All learning is shared across the hive through the shared skillbook.
    """

    def __init__(
        self,
        skillbook: HiveSkillbook,
        ace_model: str = "gemini/gemini-2.0-flash",
        async_learning: bool = True,
        on_learning_complete: Optional[Callable[[LearningResult], None]] = None,
    ):
        """
        Initialize ACE wrapper.

        Args:
            skillbook: Shared hive skillbook
            ace_model: Model to use for reflection and skill management
            async_learning: Enable async learning (faster but eventual consistency)
            on_learning_complete: Callback when learning is done
        """
        self.skillbook = skillbook
        self.ace_model = ace_model
        self.async_learning = async_learning
        self.on_learning_complete = on_learning_complete
        self.environment = HiveEnvironment()

        # Initialize ACE components if available
        if ACE_AVAILABLE:
            try:
                self._llm = LiteLLMClient(model=ace_model)
                self._reflector = Reflector(self._llm)
                self._skill_manager = SkillManager(self._llm)
                self._ace_enabled = True
                logger.info(f"ACE learning enabled with model {ace_model}")
            except Exception as e:
                logger.warning(f"Failed to initialize ACE: {e}")
                self._ace_enabled = False
        else:
            self._ace_enabled = False

        # Learning history
        self.learning_history: List[LearningResult] = []

    @property
    def is_ace_enabled(self) -> bool:
        """Check if full ACE learning is enabled."""
        return self._ace_enabled

    async def learn_from_task(
        self,
        task_description: str,
        task_result: TaskResult,
        drone_id: str,
        expected_outcome: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> LearningResult:
        """
        Learn from a completed task.

        Args:
            task_description: Description of the task
            task_result: Result from task execution
            drone_id: ID of the drone that executed the task
            expected_outcome: Optional expected outcome
            context: Additional context

        Returns:
            LearningResult with details of what was learned
        """
        result = LearningResult(task_id=task_result.task_id, success=False)

        try:
            # Evaluate the task
            evaluation = self.environment.evaluate(
                task_description, task_result, expected_outcome
            )

            if self._ace_enabled:
                # Full ACE learning loop
                result = await self._ace_learn(
                    task_description=task_description,
                    task_result=task_result,
                    drone_id=drone_id,
                    evaluation=evaluation,
                    context=context or {},
                )
            else:
                # Simplified learning
                result = await self._simple_learn(
                    task_description=task_description,
                    task_result=task_result,
                    drone_id=drone_id,
                    evaluation=evaluation,
                )

        except Exception as e:
            logger.error(f"Learning failed: {e}")
            result.error = str(e)

        # Record in history
        self.learning_history.append(result)

        # Callback
        if self.on_learning_complete:
            self.on_learning_complete(result)

        return result

    async def _ace_learn(
        self,
        task_description: str,
        task_result: TaskResult,
        drone_id: str,
        evaluation: Dict[str, Any],
        context: Dict[str, Any],
    ) -> LearningResult:
        """Full ACE learning loop."""
        result = LearningResult(task_id=task_result.task_id, success=False)

        # Create agent output representation
        agent_output = AgentOutput(
            reasoning=f"Executed task: {task_description}",
            final_answer=str(task_result.output) if task_result.output else "",
            skill_ids=[],
            raw={"task_result": task_result.to_dict()},
        )

        # Get ACE skillbook for reflection
        if self.skillbook.is_ace_enabled:
            ace_skillbook = self.skillbook._skillbook
        else:
            # Create a temporary ACE skillbook for reflection
            from ace.skillbook import Skillbook
            ace_skillbook = Skillbook()
            for skill in self.skillbook.get_all_skills():
                ace_skillbook.add_skill(
                    section=skill["section"],
                    content=skill["content"],
                    skill_id=skill["id"],
                )

        # Reflect on the outcome
        reflection = self._reflector.reflect(
            question=task_description,
            agent_output=agent_output,
            skillbook=ace_skillbook,
            ground_truth=evaluation.get("ground_truth"),
            feedback=evaluation["feedback"],
        )

        result.key_insight = reflection.key_insight

        # Process skill tags
        for tag in reflection.skill_tags:
            tagged = self.skillbook.tag_skill(tag.id, tag.tag)
            if tagged:
                result.skills_tagged.append(tag.id)

        # Update skillbook via SkillManager
        progress = f"Task {task_result.task_id} completed"
        question_context = json.dumps({
            "task": task_description,
            "feedback": evaluation["feedback"],
            "metrics": evaluation["metrics"],
        })

        skill_update = self._skill_manager.update_skills(
            reflection=reflection,
            skillbook=ace_skillbook,
            question_context=question_context,
            progress=progress,
        )

        # Apply updates to our skillbook
        for op in skill_update.update.operations:
            op_type = op.type.upper()
            if op_type == "ADD":
                skill_id = self.skillbook.add_skill(
                    section=op.section,
                    content=op.content or "",
                    source_drone=drone_id,
                    source_task=task_result.task_id,
                )
                result.skills_added.append(skill_id)
            elif op_type == "UPDATE" and op.skill_id:
                self.skillbook.update_skill(
                    op.skill_id,
                    content=op.content,
                    metadata=op.metadata,
                )
                result.skills_updated.append(op.skill_id)
            elif op_type == "TAG" and op.skill_id:
                for tag, increment in op.metadata.items():
                    self.skillbook.tag_skill(op.skill_id, tag, increment)
                    result.skills_tagged.append(op.skill_id)

        result.success = True
        return result

    async def _simple_learn(
        self,
        task_description: str,
        task_result: TaskResult,
        drone_id: str,
        evaluation: Dict[str, Any],
    ) -> LearningResult:
        """Simplified learning when ACE is not available."""
        result = LearningResult(task_id=task_result.task_id, success=False)

        # Extract simple insights based on success/failure
        metrics = evaluation.get("metrics", {})

        if task_result.success:
            # Learn from success
            section = "Successful Strategies"
            content = f"For tasks like '{task_description[:100]}': {evaluation['feedback']}"

            skill_id = self.skillbook.add_skill(
                section=section,
                content=content,
                source_drone=drone_id,
                source_task=task_result.task_id,
            )
            result.skills_added.append(skill_id)
            result.key_insight = "Task succeeded - strategy recorded"

        else:
            # Learn from failure
            section = "Failure Patterns"
            content = f"Failed approach for '{task_description[:100]}': {task_result.error}"

            skill_id = self.skillbook.add_skill(
                section=section,
                content=content,
                source_drone=drone_id,
                source_task=task_result.task_id,
                metadata={"harmful": 1},
            )
            result.skills_added.append(skill_id)
            result.key_insight = f"Task failed - pattern recorded: {task_result.error}"

        result.success = True
        return result

    def get_learning_stats(self) -> Dict[str, Any]:
        """Get statistics about learning."""
        total = len(self.learning_history)
        successful = len([r for r in self.learning_history if r.success])
        total_skills_added = sum(len(r.skills_added) for r in self.learning_history)
        total_skills_tagged = sum(len(r.skills_tagged) for r in self.learning_history)

        return {
            "ace_enabled": self._ace_enabled,
            "total_learning_events": total,
            "successful_learning": successful,
            "failed_learning": total - successful,
            "total_skills_added": total_skills_added,
            "total_skills_tagged": total_skills_tagged,
            "skillbook_stats": self.skillbook.stats(),
        }

    def get_recent_insights(self, n: int = 10) -> List[str]:
        """Get recent key insights from learning."""
        recent = self.learning_history[-n:]
        return [r.key_insight for r in recent if r.key_insight]
