"""Self-replication management for Agent Hive."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Type
import logging
import uuid

from agent_hive.drones.base import BaseDrone, DroneType, DroneMetrics
from agent_hive.drones.worker import WorkerDrone
from agent_hive.drones.builder import BuilderDrone
from agent_hive.drones.researcher import ResearcherDrone
from agent_hive.drones.seller import SellerDrone
from agent_hive.drones.analyst import AnalystDrone
from agent_hive.config.settings import ReplicationConfig

logger = logging.getLogger(__name__)


@dataclass
class ReplicationMetrics:
    """Metrics for replication decisions."""

    task_queue_depth: int = 0
    avg_task_wait_time: float = 0.0  # seconds
    drones_by_type: Dict[str, int] = field(default_factory=dict)
    revenue_potential: float = 0.0
    estimated_cost: float = 0.0
    success_rate_by_type: Dict[str, float] = field(default_factory=dict)


@dataclass
class ReplicationDecision:
    """Decision about whether to replicate and how."""

    should_replicate: bool
    drone_type: Optional[DroneType]
    reason: str
    estimated_roi: float = 0.0
    confidence: float = 0.0
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ReplicationManager:
    """
    Manages self-replication of drone agents.

    Responsibilities:
    - Monitor hive metrics to identify need for new drones
    - Decide when and what type of drone to spawn
    - Handle drone lifecycle (creation, termination)
    - Manage resource allocation for new drones
    """

    # Map drone types to their classes
    DRONE_CLASSES: Dict[DroneType, Type[BaseDrone]] = {
        DroneType.WORKER: WorkerDrone,
        DroneType.BUILDER: BuilderDrone,
        DroneType.RESEARCHER: ResearcherDrone,
        DroneType.SELLER: SellerDrone,
        DroneType.ANALYST: AnalystDrone,
    }

    def __init__(self, config: ReplicationConfig, hive_id: str):
        self.config = config
        self.hive_id = hive_id
        self.drones: Dict[str, BaseDrone] = {}
        self.last_replication: Optional[datetime] = None
        self.replication_history: List[Dict[str, Any]] = []

    def get_drone_counts(self) -> Dict[str, int]:
        """Get count of drones by type."""
        counts = {dt.value: 0 for dt in DroneType}
        for drone in self.drones.values():
            counts[drone.drone_type.value] += 1
        return counts

    def spawn_drone(
        self,
        drone_type: DroneType,
        model: str = "gemini-2.5-flash",
        name: Optional[str] = None,
    ) -> Optional[BaseDrone]:
        """
        Spawn a new drone of the specified type.

        Args:
            drone_type: Type of drone to create
            model: LLM model to use
            name: Optional name for the drone

        Returns:
            The newly created drone, or None if at capacity
        """
        counts = self.get_drone_counts()

        # Check capacity
        if counts[drone_type.value] >= self.config.max_drones_per_type:
            logger.warning(
                f"Cannot spawn {drone_type.value}: at max capacity "
                f"({self.config.max_drones_per_type})"
            )
            return None

        # Create the drone
        drone_class = self.DRONE_CLASSES[drone_type]
        drone = drone_class(model=model, name=name, hive_id=self.hive_id)

        self.drones[drone.drone_id] = drone
        self.last_replication = datetime.now(timezone.utc)

        # Record in history
        self.replication_history.append({
            "action": "spawn",
            "drone_id": drone.drone_id,
            "drone_type": drone_type.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        logger.info(f"Spawned new drone: {drone.name} (type={drone_type.value})")
        return drone

    def terminate_drone(self, drone_id: str) -> bool:
        """
        Terminate a drone.

        Args:
            drone_id: ID of drone to terminate

        Returns:
            True if drone was terminated
        """
        if drone_id not in self.drones:
            return False

        drone = self.drones[drone_id]
        drone.terminate()
        del self.drones[drone_id]

        # Record in history
        self.replication_history.append({
            "action": "terminate",
            "drone_id": drone_id,
            "drone_type": drone.drone_type.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        logger.info(f"Terminated drone: {drone_id}")
        return True

    def should_replicate(self, metrics: ReplicationMetrics) -> ReplicationDecision:
        """
        Determine if the hive should spawn a new drone.

        Decision factors:
        1. Task queue depth exceeds threshold
        2. Expected revenue > cost * multiplier
        3. Not in cooldown period
        4. Not at capacity for the needed type

        Args:
            metrics: Current hive metrics

        Returns:
            ReplicationDecision with recommendation
        """
        # Check cooldown
        if self.last_replication:
            cooldown_elapsed = (
                datetime.now(timezone.utc) - self.last_replication
            ).total_seconds()
            if cooldown_elapsed < self.config.replication_cooldown:
                return ReplicationDecision(
                    should_replicate=False,
                    drone_type=None,
                    reason=f"In cooldown period ({cooldown_elapsed:.0f}s < {self.config.replication_cooldown}s)",
                )

        # Check queue depth
        if metrics.task_queue_depth < self.config.min_queue_depth:
            return ReplicationDecision(
                should_replicate=False,
                drone_type=None,
                reason=f"Queue depth too low ({metrics.task_queue_depth} < {self.config.min_queue_depth})",
            )

        # Determine which type is needed most
        needed_type = self._identify_needed_type(metrics)

        # Check capacity
        counts = self.get_drone_counts()
        if counts[needed_type.value] >= self.config.max_drones_per_type:
            return ReplicationDecision(
                should_replicate=False,
                drone_type=needed_type,
                reason=f"At max capacity for {needed_type.value}",
            )

        # Check ROI
        estimated_roi = self._estimate_roi(needed_type, metrics)
        if metrics.revenue_potential > metrics.estimated_cost * self.config.cost_revenue_multiplier:
            return ReplicationDecision(
                should_replicate=True,
                drone_type=needed_type,
                reason=f"High demand for {needed_type.value} tasks",
                estimated_roi=estimated_roi,
                confidence=0.8,
            )

        return ReplicationDecision(
            should_replicate=False,
            drone_type=needed_type,
            reason="ROI threshold not met",
            estimated_roi=estimated_roi,
        )

    def _identify_needed_type(self, metrics: ReplicationMetrics) -> DroneType:
        """Identify which drone type is most needed."""
        counts = self.get_drone_counts()

        # Simple heuristic: spawn the type with fewest drones relative to tasks
        # This could be enhanced with actual task type analysis
        min_count = float("inf")
        needed_type = DroneType.WORKER

        for drone_type in DroneType:
            count = counts[drone_type.value]
            if count < min_count:
                min_count = count
                needed_type = drone_type

        return needed_type

    def _estimate_roi(self, drone_type: DroneType, metrics: ReplicationMetrics) -> float:
        """Estimate ROI for spawning a new drone of given type."""
        # Simple estimation based on success rate and queue depth
        success_rate = metrics.success_rate_by_type.get(drone_type.value, 0.5)
        potential_tasks = metrics.task_queue_depth / max(1, len(self.drones))
        avg_task_value = metrics.revenue_potential / max(1, metrics.task_queue_depth)

        expected_revenue = potential_tasks * success_rate * avg_task_value
        return expected_revenue / max(0.01, metrics.estimated_cost)

    def spawn_initial_drones(self, model: str = "gemini-2.5-flash") -> List[BaseDrone]:
        """Spawn the initial set of drones as configured."""
        spawned = []

        for _ in range(self.config.initial_workers):
            drone = self.spawn_drone(DroneType.WORKER, model)
            if drone:
                spawned.append(drone)

        for _ in range(self.config.initial_builders):
            drone = self.spawn_drone(DroneType.BUILDER, model)
            if drone:
                spawned.append(drone)

        for _ in range(self.config.initial_sellers):
            drone = self.spawn_drone(DroneType.SELLER, model)
            if drone:
                spawned.append(drone)

        for _ in range(self.config.initial_researchers):
            drone = self.spawn_drone(DroneType.RESEARCHER, model)
            if drone:
                spawned.append(drone)

        for _ in range(self.config.initial_analysts):
            drone = self.spawn_drone(DroneType.ANALYST, model)
            if drone:
                spawned.append(drone)

        logger.info(f"Spawned {len(spawned)} initial drones")
        return spawned

    def get_drone(self, drone_id: str) -> Optional[BaseDrone]:
        """Get a drone by ID."""
        return self.drones.get(drone_id)

    def get_drones_by_type(self, drone_type: DroneType) -> List[BaseDrone]:
        """Get all drones of a specific type."""
        return [d for d in self.drones.values() if d.drone_type == drone_type]

    def get_idle_drones(self) -> List[BaseDrone]:
        """Get all idle drones."""
        from agent_hive.drones.base import DroneStatus
        return [d for d in self.drones.values() if d.status == DroneStatus.IDLE]

    def get_status(self) -> Dict[str, Any]:
        """Get replication manager status."""
        return {
            "total_drones": len(self.drones),
            "drones_by_type": self.get_drone_counts(),
            "last_replication": (
                self.last_replication.isoformat() if self.last_replication else None
            ),
            "replication_history_count": len(self.replication_history),
            "config": {
                "max_per_type": self.config.max_drones_per_type,
                "min_queue_depth": self.config.min_queue_depth,
                "cooldown": self.config.replication_cooldown,
            },
        }
