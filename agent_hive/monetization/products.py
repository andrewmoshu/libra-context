"""Product and service registry for Agent Hive monetization."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import logging

logger = logging.getLogger(__name__)


class ProductType(Enum):
    """Types of products/services the hive can offer."""

    DIGITAL_PRODUCT = "digital_product"
    SERVICE = "service"
    SUBSCRIPTION = "subscription"
    CONSULTING = "consulting"
    API_ACCESS = "api_access"


class ProductStatus(Enum):
    """Status of a product/service."""

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    DISCONTINUED = "discontinued"


@dataclass
class Product:
    """A product that the hive can sell."""

    product_id: str
    name: str
    description: str
    product_type: ProductType
    base_price: float
    cost_to_produce: float
    status: ProductStatus = ProductStatus.DRAFT
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    sales_count: int = 0
    total_revenue: float = 0.0

    @property
    def profit_margin(self) -> float:
        """Calculate profit margin."""
        if self.base_price == 0:
            return 0.0
        return (self.base_price - self.cost_to_produce) / self.base_price

    @property
    def profit_per_unit(self) -> float:
        """Calculate profit per unit sold."""
        return self.base_price - self.cost_to_produce

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_id": self.product_id,
            "name": self.name,
            "description": self.description,
            "product_type": self.product_type.value,
            "base_price": self.base_price,
            "cost_to_produce": self.cost_to_produce,
            "status": self.status.value,
            "category": self.category,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "sales_count": self.sales_count,
            "total_revenue": self.total_revenue,
            "profit_margin": self.profit_margin,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Product":
        return cls(
            product_id=data["product_id"],
            name=data["name"],
            description=data["description"],
            product_type=ProductType(data["product_type"]),
            base_price=data["base_price"],
            cost_to_produce=data["cost_to_produce"],
            status=ProductStatus(data.get("status", "draft")),
            category=data.get("category", "general"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
            sales_count=data.get("sales_count", 0),
            total_revenue=data.get("total_revenue", 0.0),
        )


@dataclass
class ServiceOffering:
    """A service that the hive can provide."""

    service_id: str
    name: str
    description: str
    hourly_rate: float
    minimum_hours: float = 1.0
    estimated_cost_per_hour: float = 0.0
    status: ProductStatus = ProductStatus.DRAFT
    skills_required: List[str] = field(default_factory=list)
    deliverables: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    bookings_count: int = 0
    total_hours: float = 0.0
    total_revenue: float = 0.0

    @property
    def profit_margin(self) -> float:
        """Calculate profit margin."""
        if self.hourly_rate == 0:
            return 0.0
        return (self.hourly_rate - self.estimated_cost_per_hour) / self.hourly_rate

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_id": self.service_id,
            "name": self.name,
            "description": self.description,
            "hourly_rate": self.hourly_rate,
            "minimum_hours": self.minimum_hours,
            "estimated_cost_per_hour": self.estimated_cost_per_hour,
            "status": self.status.value,
            "skills_required": self.skills_required,
            "deliverables": self.deliverables,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "bookings_count": self.bookings_count,
            "total_hours": self.total_hours,
            "total_revenue": self.total_revenue,
            "profit_margin": self.profit_margin,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ServiceOffering":
        return cls(
            service_id=data["service_id"],
            name=data["name"],
            description=data["description"],
            hourly_rate=data["hourly_rate"],
            minimum_hours=data.get("minimum_hours", 1.0),
            estimated_cost_per_hour=data.get("estimated_cost_per_hour", 0.0),
            status=ProductStatus(data.get("status", "draft")),
            skills_required=data.get("skills_required", []),
            deliverables=data.get("deliverables", []),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            bookings_count=data.get("bookings_count", 0),
            total_hours=data.get("total_hours", 0.0),
            total_revenue=data.get("total_revenue", 0.0),
        )


class ProductRegistry:
    """
    Registry for all products and services offered by the hive.

    Manages the catalog of what the hive can sell:
    - Digital products (templates, code, content)
    - Services (consulting, development, research)
    - Subscriptions (ongoing access to capabilities)
    """

    def __init__(self, data_path: str = "data/products.json"):
        """
        Initialize the product registry.

        Args:
            data_path: Path to JSON file for persistence
        """
        self.data_path = Path(data_path)
        self.products: Dict[str, Product] = {}
        self.services: Dict[str, ServiceOffering] = {}

        self._load()
        logger.info(f"ProductRegistry initialized with {len(self.products)} products, {len(self.services)} services")

    def _load(self) -> None:
        """Load registry from file."""
        if not self.data_path.exists():
            return

        try:
            with open(self.data_path, "r") as f:
                data = json.load(f)

            for pid, pdata in data.get("products", {}).items():
                self.products[pid] = Product.from_dict(pdata)

            for sid, sdata in data.get("services", {}).items():
                self.services[sid] = ServiceOffering.from_dict(sdata)

        except Exception as e:
            logger.error(f"Failed to load product registry: {e}")

    def _save(self) -> None:
        """Save registry to file."""
        self.data_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "products": {pid: p.to_dict() for pid, p in self.products.items()},
            "services": {sid: s.to_dict() for sid, s in self.services.items()},
        }

        with open(self.data_path, "w") as f:
            json.dump(data, f, indent=2)

    def add_product(self, product: Product) -> str:
        """Add a product to the registry."""
        self.products[product.product_id] = product
        self._save()
        logger.info(f"Added product: {product.name} (${product.base_price})")
        return product.product_id

    def add_service(self, service: ServiceOffering) -> str:
        """Add a service to the registry."""
        self.services[service.service_id] = service
        self._save()
        logger.info(f"Added service: {service.name} (${service.hourly_rate}/hr)")
        return service.service_id

    def get_product(self, product_id: str) -> Optional[Product]:
        """Get a product by ID."""
        return self.products.get(product_id)

    def get_service(self, service_id: str) -> Optional[ServiceOffering]:
        """Get a service by ID."""
        return self.services.get(service_id)

    def get_active_products(self) -> List[Product]:
        """Get all active products."""
        return [p for p in self.products.values() if p.status == ProductStatus.ACTIVE]

    def get_active_services(self) -> List[ServiceOffering]:
        """Get all active services."""
        return [s for s in self.services.values() if s.status == ProductStatus.ACTIVE]

    def record_sale(self, product_id: str, price: float) -> bool:
        """Record a product sale."""
        if product_id not in self.products:
            return False

        product = self.products[product_id]
        product.sales_count += 1
        product.total_revenue += price
        product.updated_at = datetime.now(timezone.utc).isoformat()
        self._save()

        logger.info(f"Recorded sale for {product.name}: ${price}")
        return True

    def record_service_booking(
        self, service_id: str, hours: float, revenue: float
    ) -> bool:
        """Record a service booking."""
        if service_id not in self.services:
            return False

        service = self.services[service_id]
        service.bookings_count += 1
        service.total_hours += hours
        service.total_revenue += revenue
        self._save()

        logger.info(f"Recorded booking for {service.name}: {hours}hr, ${revenue}")
        return True

    def update_product_status(
        self, product_id: str, status: ProductStatus
    ) -> bool:
        """Update product status."""
        if product_id not in self.products:
            return False

        self.products[product_id].status = status
        self.products[product_id].updated_at = datetime.now(timezone.utc).isoformat()
        self._save()
        return True

    def get_top_products(self, n: int = 5, by: str = "revenue") -> List[Product]:
        """Get top products by metric."""
        products = list(self.products.values())

        if by == "revenue":
            products.sort(key=lambda p: p.total_revenue, reverse=True)
        elif by == "sales":
            products.sort(key=lambda p: p.sales_count, reverse=True)
        elif by == "margin":
            products.sort(key=lambda p: p.profit_margin, reverse=True)

        return products[:n]

    def get_catalog_summary(self) -> Dict[str, Any]:
        """Get summary of the product catalog."""
        active_products = self.get_active_products()
        active_services = self.get_active_services()

        total_product_revenue = sum(p.total_revenue for p in self.products.values())
        total_service_revenue = sum(s.total_revenue for s in self.services.values())

        return {
            "total_products": len(self.products),
            "active_products": len(active_products),
            "total_services": len(self.services),
            "active_services": len(active_services),
            "total_product_sales": sum(p.sales_count for p in self.products.values()),
            "total_service_bookings": sum(
                s.bookings_count for s in self.services.values()
            ),
            "total_product_revenue": total_product_revenue,
            "total_service_revenue": total_service_revenue,
            "total_revenue": total_product_revenue + total_service_revenue,
        }

    def create_product_template(
        self,
        name: str,
        description: str,
        product_type: ProductType,
        base_price: float,
        cost_estimate: float = 0.0,
    ) -> Product:
        """Create a new product from template."""
        import uuid

        return Product(
            product_id=str(uuid.uuid4())[:8],
            name=name,
            description=description,
            product_type=product_type,
            base_price=base_price,
            cost_to_produce=cost_estimate,
        )

    def create_service_template(
        self,
        name: str,
        description: str,
        hourly_rate: float,
        skills_required: Optional[List[str]] = None,
    ) -> ServiceOffering:
        """Create a new service from template."""
        import uuid

        return ServiceOffering(
            service_id=str(uuid.uuid4())[:8],
            name=name,
            description=description,
            hourly_rate=hourly_rate,
            skills_required=skills_required or [],
        )
