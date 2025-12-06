"""Tests for the Agent Hive core functionality."""

import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

from agent_hive.config.settings import HiveConfig, LLMConfig, ReplicationConfig, LearningConfig
from agent_hive.drones.base import DroneType, DroneStatus, TaskResult
from agent_hive.drones.worker import WorkerDrone
from agent_hive.drones.builder import BuilderDrone
from agent_hive.drones.researcher import ResearcherDrone
from agent_hive.drones.seller import SellerDrone
from agent_hive.learning.hive_skillbook import HiveSkillbook
from agent_hive.queen.planner import Priority


class TestHiveConfig(unittest.TestCase):
    """Tests for HiveConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = HiveConfig()

        self.assertIsNotNone(config.hive_id)
        self.assertEqual(config.hive_name, "AgentHive")
        self.assertFalse(config.debug)

    def test_custom_config(self):
        """Test custom configuration."""
        config = HiveConfig(
            hive_name="TestHive",
            debug=True,
            llm=LLMConfig(primary_model="gpt-4"),
        )

        self.assertEqual(config.hive_name, "TestHive")
        self.assertTrue(config.debug)
        self.assertEqual(config.llm.primary_model, "gpt-4")


class TestDrones(unittest.TestCase):
    """Tests for drone classes."""

    def test_worker_drone_creation(self):
        """Test WorkerDrone initialization."""
        drone = WorkerDrone(model="test-model", name="test-worker")

        self.assertEqual(drone.drone_type, DroneType.WORKER)
        self.assertEqual(drone.model, "test-model")
        self.assertEqual(drone.name, "test-worker")
        self.assertEqual(drone.status, DroneStatus.IDLE)
        self.assertIsNotNone(drone.description)
        self.assertIsNotNone(drone.instructions)
        self.assertTrue(len(drone.tools) > 0)

    def test_builder_drone_creation(self):
        """Test BuilderDrone initialization."""
        drone = BuilderDrone()

        self.assertEqual(drone.drone_type, DroneType.BUILDER)
        self.assertIn("generate_code", [t.__name__ for t in drone.tools])

    def test_researcher_drone_creation(self):
        """Test ResearcherDrone initialization."""
        drone = ResearcherDrone()

        self.assertEqual(drone.drone_type, DroneType.RESEARCHER)
        self.assertIn("analyze_website", [t.__name__ for t in drone.tools])
        self.assertIn("extract_contact_info", [t.__name__ for t in drone.tools])

    def test_seller_drone_creation(self):
        """Test SellerDrone initialization."""
        drone = SellerDrone()

        self.assertEqual(drone.drone_type, DroneType.SELLER)
        self.assertIn("extract_contact_info", [t.__name__ for t in drone.tools])

    def test_drone_metrics_update(self):
        """Test that drone metrics are updated after task execution."""
        drone = WorkerDrone()

        result = TaskResult(
            task_id="test-1",
            success=True,
            output="test output",
            execution_time=1.5,
            tokens_used=100,
            cost_estimate=0.01,
        )

        drone.metrics.update(result)

        self.assertEqual(drone.metrics.tasks_completed, 1)
        self.assertEqual(drone.metrics.tasks_failed, 0)
        self.assertEqual(drone.metrics.success_rate, 1.0)
        self.assertEqual(drone.metrics.total_tokens, 100)


class TestHiveSkillbook(unittest.TestCase):
    """Tests for HiveSkillbook."""

    def setUp(self):
        """Set up test fixtures."""
        # Use a temp path that won't exist
        self.skillbook = HiveSkillbook("test_data/test_skillbook.json")

    def test_add_skill(self):
        """Test adding a skill."""
        skill_id = self.skillbook.add_skill(
            section="Test Section",
            content="Test skill content",
            source_drone="test-drone",
        )

        self.assertIsNotNone(skill_id)

        skill = self.skillbook.get_skill(skill_id)
        self.assertIsNotNone(skill)
        self.assertEqual(skill["section"], "Test Section")
        self.assertEqual(skill["content"], "Test skill content")

    def test_tag_skill(self):
        """Test tagging a skill as helpful/harmful."""
        skill_id = self.skillbook.add_skill(
            section="Test",
            content="Test content",
        )

        # Tag as helpful
        result = self.skillbook.tag_skill(skill_id, "helpful", 1)
        self.assertTrue(result)

        skill = self.skillbook.get_skill(skill_id)
        self.assertEqual(skill["helpful"], 1)

        # Tag as harmful
        self.skillbook.tag_skill(skill_id, "harmful", 1)
        skill = self.skillbook.get_skill(skill_id)
        self.assertEqual(skill["harmful"], 1)

    def test_get_top_skills(self):
        """Test getting top skills by helpful count."""
        # Add skills with different helpful counts
        self.skillbook.add_skill("Test", "Skill 1")
        skill2_id = self.skillbook.add_skill("Test", "Skill 2")
        self.skillbook.tag_skill(skill2_id, "helpful", 5)

        top_skills = self.skillbook.get_top_skills(2)

        self.assertEqual(len(top_skills), 2)
        self.assertEqual(top_skills[0]["helpful"], 5)  # Skill 2 should be first

    def test_stats(self):
        """Test skillbook statistics."""
        self.skillbook.add_skill("Section1", "Content1")
        self.skillbook.add_skill("Section2", "Content2")

        stats = self.skillbook.stats()

        self.assertIn("skills", stats)
        self.assertIn("sections", stats)
        self.assertEqual(stats["skills"], 2)


class TestTaskResult(unittest.TestCase):
    """Tests for TaskResult dataclass."""

    def test_task_result_creation(self):
        """Test TaskResult creation."""
        result = TaskResult(
            task_id="test-123",
            success=True,
            output="Task completed",
            execution_time=2.5,
        )

        self.assertEqual(result.task_id, "test-123")
        self.assertTrue(result.success)
        self.assertEqual(result.output, "Task completed")
        self.assertIsNone(result.error)

    def test_task_result_to_dict(self):
        """Test TaskResult serialization."""
        result = TaskResult(
            task_id="test-456",
            success=False,
            output=None,
            error="Task failed",
        )

        result_dict = result.to_dict()

        self.assertIsInstance(result_dict, dict)
        self.assertEqual(result_dict["task_id"], "test-456")
        self.assertFalse(result_dict["success"])
        self.assertEqual(result_dict["error"], "Task failed")


if __name__ == "__main__":
    unittest.main()
