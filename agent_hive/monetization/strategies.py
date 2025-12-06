"""Pricing strategies for Agent Hive monetization."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import logging

from agent_hive.monetization.products import Product, ServiceOffering

logger = logging.getLogger(__name__)


@dataclass
class PricingRecommendation:
    """A pricing recommendation from a strategy."""

    strategy_name: str
    recommended_price: float
    confidence: float
    reasoning: str
    min_price: float
    max_price: float
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class PricingStrategy(ABC):
    """Base class for pricing strategies."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the strategy."""
        pass

    @abstractmethod
    def calculate_price(
        self,
        product: Product,
        context: Optional[Dict[str, Any]] = None,
    ) -> PricingRecommendation:
        """
        Calculate recommended price for a product.

        Args:
            product: Product to price
            context: Additional context (market data, competitors, etc.)

        Returns:
            PricingRecommendation with suggested price
        """
        pass

    @abstractmethod
    def calculate_service_rate(
        self,
        service: ServiceOffering,
        context: Optional[Dict[str, Any]] = None,
    ) -> PricingRecommendation:
        """
        Calculate recommended rate for a service.

        Args:
            service: Service to price
            context: Additional context

        Returns:
            PricingRecommendation with suggested rate
        """
        pass


class CostPlusPricing(PricingStrategy):
    """
    Cost-plus pricing strategy.

    Sets price as cost + markup percentage.
    Simple and ensures profitability.
    """

    def __init__(self, markup_percentage: float = 0.5):
        """
        Initialize cost-plus pricing.

        Args:
            markup_percentage: Markup as decimal (0.5 = 50% markup)
        """
        self.markup_percentage = markup_percentage

    @property
    def name(self) -> str:
        return "cost_plus"

    def calculate_price(
        self,
        product: Product,
        context: Optional[Dict[str, Any]] = None,
    ) -> PricingRecommendation:
        cost = product.cost_to_produce
        recommended = cost * (1 + self.markup_percentage)

        return PricingRecommendation(
            strategy_name=self.name,
            recommended_price=recommended,
            confidence=0.8,
            reasoning=f"Cost (${cost:.2f}) + {self.markup_percentage*100:.0f}% markup",
            min_price=cost * 1.1,  # At least 10% margin
            max_price=cost * 3.0,  # Cap at 3x cost
            metadata={"markup": self.markup_percentage, "cost": cost},
        )

    def calculate_service_rate(
        self,
        service: ServiceOffering,
        context: Optional[Dict[str, Any]] = None,
    ) -> PricingRecommendation:
        cost = service.estimated_cost_per_hour
        recommended = cost * (1 + self.markup_percentage) if cost > 0 else 50.0

        return PricingRecommendation(
            strategy_name=self.name,
            recommended_price=recommended,
            confidence=0.7,
            reasoning=f"Hourly cost (${cost:.2f}) + {self.markup_percentage*100:.0f}% markup",
            min_price=max(cost * 1.1, 25.0),
            max_price=max(cost * 3.0, 200.0),
            metadata={"markup": self.markup_percentage, "cost_per_hour": cost},
        )


class ValueBasedPricing(PricingStrategy):
    """
    Value-based pricing strategy.

    Sets price based on perceived value to customer.
    Higher prices for high-value offerings.
    """

    def __init__(self, value_multipliers: Optional[Dict[str, float]] = None):
        """
        Initialize value-based pricing.

        Args:
            value_multipliers: Multipliers by category/type
        """
        self.value_multipliers = value_multipliers or {
            "automation": 5.0,
            "consulting": 3.0,
            "content": 2.0,
            "template": 1.5,
            "default": 2.0,
        }

    @property
    def name(self) -> str:
        return "value_based"

    def calculate_price(
        self,
        product: Product,
        context: Optional[Dict[str, Any]] = None,
    ) -> PricingRecommendation:
        cost = product.cost_to_produce

        # Get multiplier based on category or tags
        multiplier = self.value_multipliers.get(product.category.lower())
        if not multiplier:
            for tag in product.tags:
                multiplier = self.value_multipliers.get(tag.lower())
                if multiplier:
                    break
        if not multiplier:
            multiplier = self.value_multipliers["default"]

        recommended = cost * multiplier

        # Ensure minimum profitability
        min_price = cost * 1.3

        return PricingRecommendation(
            strategy_name=self.name,
            recommended_price=max(recommended, min_price),
            confidence=0.7,
            reasoning=f"Value multiplier {multiplier}x for {product.category}",
            min_price=min_price,
            max_price=cost * multiplier * 2,
            metadata={"multiplier": multiplier, "category": product.category},
        )

    def calculate_service_rate(
        self,
        service: ServiceOffering,
        context: Optional[Dict[str, Any]] = None,
    ) -> PricingRecommendation:
        base_cost = service.estimated_cost_per_hour or 20.0

        # Higher rates for specialized skills
        skill_premium = 1.0
        high_value_skills = ["ai", "ml", "automation", "architecture", "strategy"]
        for skill in service.skills_required:
            if skill.lower() in high_value_skills:
                skill_premium += 0.3

        multiplier = self.value_multipliers.get("consulting", 3.0) * skill_premium
        recommended = base_cost * multiplier

        return PricingRecommendation(
            strategy_name=self.name,
            recommended_price=recommended,
            confidence=0.65,
            reasoning=f"Value rate with {skill_premium:.1f}x skill premium",
            min_price=50.0,
            max_price=500.0,
            metadata={"skill_premium": skill_premium, "base_multiplier": multiplier},
        )


class CompetitivePricing(PricingStrategy):
    """
    Competitive pricing strategy.

    Sets price based on competitor analysis.
    Requires market data in context.
    """

    def __init__(self, position: str = "match"):
        """
        Initialize competitive pricing.

        Args:
            position: "undercut" (10% below), "match", or "premium" (10% above)
        """
        self.position = position
        self.position_factor = {
            "undercut": 0.9,
            "match": 1.0,
            "premium": 1.1,
        }.get(position, 1.0)

    @property
    def name(self) -> str:
        return "competitive"

    def calculate_price(
        self,
        product: Product,
        context: Optional[Dict[str, Any]] = None,
    ) -> PricingRecommendation:
        context = context or {}

        # Get competitor prices from context
        competitor_prices = context.get("competitor_prices", [])
        market_average = context.get("market_average_price")

        if competitor_prices:
            avg_price = sum(competitor_prices) / len(competitor_prices)
            min_competitor = min(competitor_prices)
            max_competitor = max(competitor_prices)
        elif market_average:
            avg_price = market_average
            min_competitor = market_average * 0.7
            max_competitor = market_average * 1.3
        else:
            # Fall back to cost-plus if no market data
            return CostPlusPricing().calculate_price(product, context)

        recommended = avg_price * self.position_factor

        # Ensure profitability
        min_profitable = product.cost_to_produce * 1.2
        recommended = max(recommended, min_profitable)

        return PricingRecommendation(
            strategy_name=self.name,
            recommended_price=recommended,
            confidence=0.75 if competitor_prices else 0.5,
            reasoning=f"Market avg ${avg_price:.2f}, position: {self.position}",
            min_price=min(min_competitor * 0.9, min_profitable),
            max_price=max_competitor * 1.2,
            metadata={
                "market_average": avg_price,
                "competitor_count": len(competitor_prices),
                "position": self.position,
            },
        )

    def calculate_service_rate(
        self,
        service: ServiceOffering,
        context: Optional[Dict[str, Any]] = None,
    ) -> PricingRecommendation:
        context = context or {}

        market_rate = context.get("market_hourly_rate")
        competitor_rates = context.get("competitor_rates", [])

        if competitor_rates:
            avg_rate = sum(competitor_rates) / len(competitor_rates)
        elif market_rate:
            avg_rate = market_rate
        else:
            avg_rate = 100.0  # Default market rate

        recommended = avg_rate * self.position_factor

        # Minimum rate
        min_rate = max(service.estimated_cost_per_hour * 1.5, 50.0)
        recommended = max(recommended, min_rate)

        return PricingRecommendation(
            strategy_name=self.name,
            recommended_price=recommended,
            confidence=0.7 if competitor_rates else 0.5,
            reasoning=f"Market rate ${avg_rate:.2f}/hr, position: {self.position}",
            min_price=min_rate,
            max_price=avg_rate * 2,
            metadata={"market_rate": avg_rate, "position": self.position},
        )


class PricingEngine:
    """
    Engine that combines multiple pricing strategies.

    Aggregates recommendations from different strategies
    to provide optimal pricing suggestions.
    """

    def __init__(self, strategies: Optional[List[PricingStrategy]] = None):
        """
        Initialize pricing engine.

        Args:
            strategies: List of pricing strategies to use
        """
        self.strategies = strategies or [
            CostPlusPricing(),
            ValueBasedPricing(),
            CompetitivePricing(),
        ]

    def get_price_recommendations(
        self,
        product: Product,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[PricingRecommendation]:
        """Get recommendations from all strategies."""
        recommendations = []
        for strategy in self.strategies:
            try:
                rec = strategy.calculate_price(product, context)
                recommendations.append(rec)
            except Exception as e:
                logger.warning(f"Strategy {strategy.name} failed: {e}")
        return recommendations

    def get_optimal_price(
        self,
        product: Product,
        context: Optional[Dict[str, Any]] = None,
    ) -> PricingRecommendation:
        """
        Get optimal price by weighing all strategies.

        Uses confidence-weighted average of recommendations.
        """
        recommendations = self.get_price_recommendations(product, context)

        if not recommendations:
            # Fallback
            return PricingRecommendation(
                strategy_name="fallback",
                recommended_price=product.cost_to_produce * 2,
                confidence=0.3,
                reasoning="Fallback: 2x cost",
                min_price=product.cost_to_produce * 1.2,
                max_price=product.cost_to_produce * 5,
            )

        # Confidence-weighted average
        total_weight = sum(r.confidence for r in recommendations)
        weighted_price = sum(
            r.recommended_price * r.confidence for r in recommendations
        ) / total_weight

        avg_confidence = total_weight / len(recommendations)

        return PricingRecommendation(
            strategy_name="optimal_blend",
            recommended_price=weighted_price,
            confidence=avg_confidence,
            reasoning=f"Weighted average of {len(recommendations)} strategies",
            min_price=min(r.min_price for r in recommendations),
            max_price=max(r.max_price for r in recommendations),
            metadata={
                "strategies_used": [r.strategy_name for r in recommendations],
                "individual_prices": {r.strategy_name: r.recommended_price for r in recommendations},
            },
        )

    def get_service_rate_recommendations(
        self,
        service: ServiceOffering,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[PricingRecommendation]:
        """Get rate recommendations from all strategies."""
        recommendations = []
        for strategy in self.strategies:
            try:
                rec = strategy.calculate_service_rate(service, context)
                recommendations.append(rec)
            except Exception as e:
                logger.warning(f"Strategy {strategy.name} failed: {e}")
        return recommendations

    def get_optimal_service_rate(
        self,
        service: ServiceOffering,
        context: Optional[Dict[str, Any]] = None,
    ) -> PricingRecommendation:
        """Get optimal service rate by weighing all strategies."""
        recommendations = self.get_service_rate_recommendations(service, context)

        if not recommendations:
            return PricingRecommendation(
                strategy_name="fallback",
                recommended_price=100.0,
                confidence=0.3,
                reasoning="Fallback: $100/hr",
                min_price=50.0,
                max_price=200.0,
            )

        total_weight = sum(r.confidence for r in recommendations)
        weighted_rate = sum(
            r.recommended_price * r.confidence for r in recommendations
        ) / total_weight

        avg_confidence = total_weight / len(recommendations)

        return PricingRecommendation(
            strategy_name="optimal_blend",
            recommended_price=weighted_rate,
            confidence=avg_confidence,
            reasoning=f"Weighted average of {len(recommendations)} strategies",
            min_price=min(r.min_price for r in recommendations),
            max_price=max(r.max_price for r in recommendations),
            metadata={
                "strategies_used": [r.strategy_name for r in recommendations],
                "individual_rates": {r.strategy_name: r.recommended_price for r in recommendations},
            },
        )
