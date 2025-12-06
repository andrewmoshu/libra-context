"""Opportunity detection and service creation for Agent Hive monetization."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import json
import logging
import uuid

logger = logging.getLogger(__name__)


class OpportunityStatus(Enum):
    """Status of a business opportunity."""

    IDENTIFIED = "identified"
    RESEARCHING = "researching"
    ANALYZING = "analyzing"
    BUILDING = "building"
    LAUNCHED = "launched"
    GENERATING_REVENUE = "generating_revenue"
    DECLINED = "declined"
    PAUSED = "paused"


class OpportunityCategory(Enum):
    """Categories of monetizable opportunities."""

    API_SERVICE = "api_service"
    SAAS_PRODUCT = "saas_product"
    DIGITAL_PRODUCT = "digital_product"
    CONSULTING = "consulting"
    CONTENT = "content"
    AUTOMATION = "automation"
    DATA_SERVICE = "data_service"


@dataclass
class Opportunity:
    """A business opportunity identified by the hive."""

    opportunity_id: str
    name: str
    description: str
    category: OpportunityCategory
    status: OpportunityStatus = OpportunityStatus.IDENTIFIED

    # Scoring and analysis
    score: int = 0  # 0-100
    confidence: float = 0.0  # 0.0-1.0

    # Financial projections
    revenue_estimate_low: float = 0.0
    revenue_estimate_high: float = 0.0
    cost_estimate: float = 0.0
    time_to_revenue_days: int = 90

    # Risk assessment
    risk_level: str = "medium"  # low, medium, high
    risks: List[str] = field(default_factory=list)
    mitigations: List[str] = field(default_factory=list)

    # Market data
    market_size: Optional[float] = None
    competitors: List[str] = field(default_factory=list)
    target_customers: List[str] = field(default_factory=list)

    # Tracking
    source_task_id: Optional[str] = None
    source_drone_id: Optional[str] = None
    research_data: Dict[str, Any] = field(default_factory=dict)

    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def roi_estimate(self) -> float:
        """Calculate estimated ROI."""
        avg_revenue = (self.revenue_estimate_low + self.revenue_estimate_high) / 2
        if self.cost_estimate == 0:
            return float("inf") if avg_revenue > 0 else 0.0
        return (avg_revenue - self.cost_estimate) / self.cost_estimate * 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "status": self.status.value,
            "score": self.score,
            "confidence": self.confidence,
            "revenue_estimate_low": self.revenue_estimate_low,
            "revenue_estimate_high": self.revenue_estimate_high,
            "cost_estimate": self.cost_estimate,
            "time_to_revenue_days": self.time_to_revenue_days,
            "risk_level": self.risk_level,
            "risks": self.risks,
            "mitigations": self.mitigations,
            "market_size": self.market_size,
            "competitors": self.competitors,
            "target_customers": self.target_customers,
            "source_task_id": self.source_task_id,
            "source_drone_id": self.source_drone_id,
            "research_data": self.research_data,
            "roi_estimate": self.roi_estimate,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Opportunity":
        return cls(
            opportunity_id=data["opportunity_id"],
            name=data["name"],
            description=data["description"],
            category=OpportunityCategory(data["category"]),
            status=OpportunityStatus(data.get("status", "identified")),
            score=data.get("score", 0),
            confidence=data.get("confidence", 0.0),
            revenue_estimate_low=data.get("revenue_estimate_low", 0.0),
            revenue_estimate_high=data.get("revenue_estimate_high", 0.0),
            cost_estimate=data.get("cost_estimate", 0.0),
            time_to_revenue_days=data.get("time_to_revenue_days", 90),
            risk_level=data.get("risk_level", "medium"),
            risks=data.get("risks", []),
            mitigations=data.get("mitigations", []),
            market_size=data.get("market_size"),
            competitors=data.get("competitors", []),
            target_customers=data.get("target_customers", []),
            source_task_id=data.get("source_task_id"),
            source_drone_id=data.get("source_drone_id"),
            research_data=data.get("research_data", {}),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
        )


@dataclass
class ServiceTemplate:
    """Template for a monetizable service the hive can offer."""

    template_id: str
    name: str
    description: str
    category: OpportunityCategory

    # Implementation details
    implementation_steps: List[str] = field(default_factory=list)
    required_drone_types: List[str] = field(default_factory=list)
    tech_stack: List[str] = field(default_factory=list)

    # Pricing
    pricing_model: str = "subscription"  # subscription, per_use, one_time, custom
    base_price: float = 0.0
    price_range: tuple = (0.0, 0.0)

    # Time estimates
    estimated_build_hours: int = 40
    estimated_launch_days: int = 14

    # Success metrics
    success_rate: float = 0.0
    avg_revenue: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "implementation_steps": self.implementation_steps,
            "required_drone_types": self.required_drone_types,
            "tech_stack": self.tech_stack,
            "pricing_model": self.pricing_model,
            "base_price": self.base_price,
            "price_range": list(self.price_range),
            "estimated_build_hours": self.estimated_build_hours,
            "estimated_launch_days": self.estimated_launch_days,
            "success_rate": self.success_rate,
            "avg_revenue": self.avg_revenue,
        }


class OpportunityManager:
    """
    Manages opportunity detection, scoring, and conversion to services.

    The OpportunityManager coordinates:
    1. Opportunity discovery from research tasks
    2. Scoring and prioritization
    3. Service template matching
    4. Task generation for implementation
    """

    # Pre-defined service templates
    SERVICE_TEMPLATES = [
        ServiceTemplate(
            template_id="api-data-analysis",
            name="Data Analysis API",
            description="API service that processes and analyzes data for clients",
            category=OpportunityCategory.API_SERVICE,
            implementation_steps=[
                "Design API endpoints and data models",
                "Implement core analysis logic",
                "Add authentication and rate limiting",
                "Create documentation and examples",
                "Deploy to cloud infrastructure",
            ],
            required_drone_types=["builder", "researcher"],
            tech_stack=["python", "fastapi", "postgres"],
            pricing_model="per_use",
            base_price=0.01,
            price_range=(0.001, 0.10),
            estimated_build_hours=60,
            estimated_launch_days=14,
        ),
        ServiceTemplate(
            template_id="content-generator",
            name="AI Content Generator",
            description="Automated content creation service for marketing, blogs, social media",
            category=OpportunityCategory.CONTENT,
            implementation_steps=[
                "Define content templates and formats",
                "Implement content generation pipeline",
                "Add customization options",
                "Create review and approval workflow",
                "Set up delivery automation",
            ],
            required_drone_types=["builder", "seller"],
            tech_stack=["python", "llm-api"],
            pricing_model="subscription",
            base_price=29.0,
            price_range=(9.0, 99.0),
            estimated_build_hours=40,
            estimated_launch_days=7,
        ),
        ServiceTemplate(
            template_id="automation-bot",
            name="Custom Automation Bot",
            description="Automated task execution bot for repetitive business processes",
            category=OpportunityCategory.AUTOMATION,
            implementation_steps=[
                "Analyze target workflow",
                "Design automation pipeline",
                "Implement bot logic",
                "Add error handling and logging",
                "Create monitoring dashboard",
            ],
            required_drone_types=["builder", "worker"],
            tech_stack=["python", "selenium", "celery"],
            pricing_model="custom",
            base_price=500.0,
            price_range=(200.0, 5000.0),
            estimated_build_hours=80,
            estimated_launch_days=21,
        ),
        ServiceTemplate(
            template_id="market-research",
            name="Market Research Report",
            description="Comprehensive market research and competitor analysis reports",
            category=OpportunityCategory.CONSULTING,
            implementation_steps=[
                "Define research scope and questions",
                "Gather data from multiple sources",
                "Analyze trends and patterns",
                "Identify opportunities and risks",
                "Compile and format report",
            ],
            required_drone_types=["researcher", "analyst"],
            tech_stack=["python", "data-analysis"],
            pricing_model="one_time",
            base_price=250.0,
            price_range=(100.0, 1000.0),
            estimated_build_hours=20,
            estimated_launch_days=5,
        ),
        ServiceTemplate(
            template_id="digital-product",
            name="Digital Product (Templates/Tools)",
            description="Digital products like templates, tools, or datasets",
            category=OpportunityCategory.DIGITAL_PRODUCT,
            implementation_steps=[
                "Identify product niche and value",
                "Create product content/functionality",
                "Package and format for delivery",
                "Set up sales page and checkout",
                "Create marketing materials",
            ],
            required_drone_types=["builder", "seller", "researcher"],
            tech_stack=["varies"],
            pricing_model="one_time",
            base_price=19.0,
            price_range=(5.0, 199.0),
            estimated_build_hours=30,
            estimated_launch_days=10,
        ),
    ]

    def __init__(self, storage_path: str = "data/opportunities.json"):
        """
        Initialize the opportunity manager.

        Args:
            storage_path: Path to store opportunities data
        """
        self.storage_path = storage_path
        self.opportunities: Dict[str, Opportunity] = {}
        self.templates = {t.template_id: t for t in self.SERVICE_TEMPLATES}

        # Load existing opportunities
        self._load()

    def add_opportunity(
        self,
        name: str,
        description: str,
        category: OpportunityCategory,
        source_task_id: Optional[str] = None,
        source_drone_id: Optional[str] = None,
        initial_data: Optional[Dict[str, Any]] = None,
    ) -> Opportunity:
        """
        Add a new opportunity to track.

        Args:
            name: Opportunity name
            description: Description of the opportunity
            category: Category type
            source_task_id: ID of task that discovered this
            source_drone_id: ID of drone that discovered this
            initial_data: Any initial research data

        Returns:
            The created Opportunity
        """
        opportunity = Opportunity(
            opportunity_id=str(uuid.uuid4())[:8],
            name=name,
            description=description,
            category=category,
            source_task_id=source_task_id,
            source_drone_id=source_drone_id,
            research_data=initial_data or {},
        )

        self.opportunities[opportunity.opportunity_id] = opportunity
        self._save()

        logger.info(f"Added opportunity: {name} ({category.value})")
        return opportunity

    def update_opportunity(
        self,
        opportunity_id: str,
        score: Optional[int] = None,
        status: Optional[OpportunityStatus] = None,
        revenue_low: Optional[float] = None,
        revenue_high: Optional[float] = None,
        cost: Optional[float] = None,
        risks: Optional[List[str]] = None,
        research_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[Opportunity]:
        """Update an existing opportunity."""
        if opportunity_id not in self.opportunities:
            return None

        opp = self.opportunities[opportunity_id]

        if score is not None:
            opp.score = score
        if status is not None:
            opp.status = status
        if revenue_low is not None:
            opp.revenue_estimate_low = revenue_low
        if revenue_high is not None:
            opp.revenue_estimate_high = revenue_high
        if cost is not None:
            opp.cost_estimate = cost
        if risks is not None:
            opp.risks = risks
        if research_data is not None:
            opp.research_data.update(research_data)

        opp.updated_at = datetime.now(timezone.utc).isoformat()
        self._save()

        return opp

    def score_opportunity(self, opportunity_id: str) -> int:
        """
        Calculate opportunity score based on multiple factors.

        Scoring criteria (0-100):
        - Market size potential (0-25)
        - ROI estimate (0-25)
        - Implementation feasibility (0-20)
        - Competition level (0-15)
        - Time to revenue (0-15)
        """
        if opportunity_id not in self.opportunities:
            return 0

        opp = self.opportunities[opportunity_id]
        score = 0

        # Market size (0-25)
        if opp.market_size:
            if opp.market_size >= 1_000_000_000:  # $1B+
                score += 25
            elif opp.market_size >= 100_000_000:  # $100M+
                score += 20
            elif opp.market_size >= 10_000_000:  # $10M+
                score += 15
            elif opp.market_size >= 1_000_000:  # $1M+
                score += 10
            else:
                score += 5

        # ROI estimate (0-25)
        roi = opp.roi_estimate
        if roi >= 500:
            score += 25
        elif roi >= 200:
            score += 20
        elif roi >= 100:
            score += 15
        elif roi >= 50:
            score += 10
        elif roi > 0:
            score += 5

        # Implementation feasibility (0-20)
        # Based on template match and complexity
        template = self.match_template(opp)
        if template:
            if template.estimated_build_hours <= 40:
                score += 20
            elif template.estimated_build_hours <= 80:
                score += 15
            else:
                score += 10
        else:
            score += 5  # No template, harder to implement

        # Competition (0-15)
        num_competitors = len(opp.competitors)
        if num_competitors == 0:
            score += 15
        elif num_competitors <= 3:
            score += 12
        elif num_competitors <= 5:
            score += 8
        else:
            score += 3

        # Time to revenue (0-15)
        if opp.time_to_revenue_days <= 14:
            score += 15
        elif opp.time_to_revenue_days <= 30:
            score += 12
        elif opp.time_to_revenue_days <= 60:
            score += 8
        elif opp.time_to_revenue_days <= 90:
            score += 5
        else:
            score += 2

        opp.score = score
        self._save()

        return score

    def match_template(self, opportunity: Opportunity) -> Optional[ServiceTemplate]:
        """Find the best matching service template for an opportunity."""
        # Match by category first
        matching = [
            t for t in self.templates.values() if t.category == opportunity.category
        ]

        if not matching:
            return None

        # Could add more sophisticated matching based on keywords, requirements, etc.
        return matching[0]

    def get_top_opportunities(self, n: int = 5) -> List[Opportunity]:
        """Get top N opportunities by score."""
        sorted_opps = sorted(
            self.opportunities.values(), key=lambda o: o.score, reverse=True
        )
        return sorted_opps[:n]

    def get_opportunities_by_status(
        self, status: OpportunityStatus
    ) -> List[Opportunity]:
        """Get all opportunities with a specific status."""
        return [o for o in self.opportunities.values() if o.status == status]

    def get_actionable_opportunities(
        self, min_score: int = 60
    ) -> List[Opportunity]:
        """Get opportunities ready for action (scored and above threshold)."""
        return [
            o
            for o in self.opportunities.values()
            if o.score >= min_score
            and o.status in [OpportunityStatus.IDENTIFIED, OpportunityStatus.RESEARCHING]
        ]

    def get_pipeline_summary(self) -> Dict[str, Any]:
        """Get summary of opportunity pipeline."""
        by_status = {}
        by_category = {}
        total_potential_revenue = 0.0

        for opp in self.opportunities.values():
            by_status[opp.status.value] = by_status.get(opp.status.value, 0) + 1
            by_category[opp.category.value] = by_category.get(opp.category.value, 0) + 1

            avg_revenue = (opp.revenue_estimate_low + opp.revenue_estimate_high) / 2
            total_potential_revenue += avg_revenue

        return {
            "total_opportunities": len(self.opportunities),
            "by_status": by_status,
            "by_category": by_category,
            "total_potential_revenue": total_potential_revenue,
            "avg_score": (
                sum(o.score for o in self.opportunities.values())
                / len(self.opportunities)
                if self.opportunities
                else 0
            ),
            "actionable_count": len(self.get_actionable_opportunities()),
        }

    def _save(self) -> None:
        """Save opportunities to file."""
        from pathlib import Path

        Path(self.storage_path).parent.mkdir(parents=True, exist_ok=True)

        data = {
            oid: opp.to_dict() for oid, opp in self.opportunities.items()
        }

        with open(self.storage_path, "w") as f:
            json.dump(data, f, indent=2)

    def _load(self) -> None:
        """Load opportunities from file."""
        from pathlib import Path

        if not Path(self.storage_path).exists():
            return

        try:
            with open(self.storage_path, "r") as f:
                data = json.load(f)

            for oid, odata in data.items():
                self.opportunities[oid] = Opportunity.from_dict(odata)

            logger.info(f"Loaded {len(self.opportunities)} opportunities")
        except Exception as e:
            logger.error(f"Failed to load opportunities: {e}")
