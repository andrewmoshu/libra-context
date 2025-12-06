#!/usr/bin/env python3
"""
Example runner script for Agent Hive.

This demonstrates how to:
1. Initialize and configure the hive
2. Add tasks and goals
3. Run the hive operation cycle
4. Monitor progress and learning
5. Track monetization
6. Manage business opportunities
7. Use the full drone ecosystem (including Analyst)
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_hive import AgentHive, HiveConfig
from agent_hive.config.settings import LLMConfig, ReplicationConfig, LearningConfig
from agent_hive.queen.planner import Priority, StrategicGoal, StrategyType
from agent_hive.monetization.treasury import Treasury
from agent_hive.monetization.products import ProductRegistry, ProductType, ProductStatus
from agent_hive.monetization.strategies import PricingEngine
from agent_hive.monetization.opportunities import (
    OpportunityManager,
    OpportunityCategory,
    OpportunityStatus,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_sample_products(registry: ProductRegistry) -> None:
    """Create some sample products for the hive to sell."""
    # Digital product: Code template
    template = registry.create_product_template(
        name="AI Agent Template Pack",
        description="Collection of production-ready AI agent templates for common tasks",
        product_type=ProductType.DIGITAL_PRODUCT,
        base_price=49.0,
        cost_estimate=5.0,
    )
    template.category = "automation"
    template.tags = ["ai", "template", "automation"]
    template.status = ProductStatus.ACTIVE
    registry.add_product(template)

    # Service: Consulting
    consulting = registry.create_service_template(
        name="AI Strategy Consulting",
        description="1-hour consultation on AI agent strategy and implementation",
        hourly_rate=150.0,
        skills_required=["ai", "strategy", "architecture"],
    )
    consulting.status = ProductStatus.ACTIVE
    registry.add_service(consulting)

    # Another product: Research report
    report = registry.create_product_template(
        name="Market Research Report",
        description="Custom market research report on any topic",
        product_type=ProductType.DIGITAL_PRODUCT,
        base_price=99.0,
        cost_estimate=20.0,
    )
    report.category = "content"
    report.status = ProductStatus.ACTIVE
    registry.add_product(report)


def demonstrate_opportunity_pipeline(opp_manager: OpportunityManager) -> None:
    """Demonstrate the opportunity management pipeline."""
    logger.info("\n" + "=" * 50)
    logger.info("OPPORTUNITY PIPELINE DEMONSTRATION")
    logger.info("=" * 50)

    # Add sample opportunities (simulating researcher discoveries)
    opportunities = [
        {
            "name": "Automated SEO Audit Tool",
            "description": "SaaS tool for automated SEO analysis and recommendations",
            "category": OpportunityCategory.SAAS_PRODUCT,
            "revenue_low": 5000.0,
            "revenue_high": 15000.0,
            "cost": 2000.0,
            "market_size": 50_000_000,
            "competitors": ["Ahrefs", "SEMrush"],
            "time_to_revenue": 30,
        },
        {
            "name": "AI Content Generation API",
            "description": "REST API for generating marketing content at scale",
            "category": OpportunityCategory.API_SERVICE,
            "revenue_low": 3000.0,
            "revenue_high": 20000.0,
            "cost": 1500.0,
            "market_size": 100_000_000,
            "competitors": ["OpenAI", "Jasper"],
            "time_to_revenue": 14,
        },
        {
            "name": "Competitor Monitoring Bot",
            "description": "Automated competitor tracking and alerting service",
            "category": OpportunityCategory.AUTOMATION,
            "revenue_low": 1000.0,
            "revenue_high": 5000.0,
            "cost": 500.0,
            "market_size": 20_000_000,
            "competitors": ["Crayon", "Klue"],
            "time_to_revenue": 21,
        },
        {
            "name": "LinkedIn Growth Templates",
            "description": "Digital product with LinkedIn engagement templates",
            "category": OpportunityCategory.DIGITAL_PRODUCT,
            "revenue_low": 500.0,
            "revenue_high": 2000.0,
            "cost": 100.0,
            "market_size": 10_000_000,
            "competitors": [],
            "time_to_revenue": 7,
        },
    ]

    logger.info("\n[A] Adding discovered opportunities...")
    for opp_data in opportunities:
        opp = opp_manager.add_opportunity(
            name=opp_data["name"],
            description=opp_data["description"],
            category=opp_data["category"],
        )
        # Update with financial data
        opp_manager.update_opportunity(
            opp.opportunity_id,
            revenue_low=opp_data["revenue_low"],
            revenue_high=opp_data["revenue_high"],
            cost=opp_data["cost"],
        )
        # Set market data
        opp.market_size = opp_data["market_size"]
        opp.competitors = opp_data["competitors"]
        opp.time_to_revenue_days = opp_data["time_to_revenue"]
        logger.info(f"  + {opp_data['name']} ({opp_data['category'].value})")

    logger.info("\n[B] Scoring opportunities...")
    for opp_id in opp_manager.opportunities:
        score = opp_manager.score_opportunity(opp_id)
        opp = opp_manager.opportunities[opp_id]
        logger.info(f"  {opp.name}: Score {score}/100 (ROI: {opp.roi_estimate:.0f}%)")

    logger.info("\n[C] Top opportunities (actionable):")
    top_opps = opp_manager.get_top_opportunities(n=3)
    for i, opp in enumerate(top_opps, 1):
        template = opp_manager.match_template(opp)
        template_name = template.name if template else "Custom implementation"
        logger.info(
            f"  #{i} {opp.name}\n"
            f"      Score: {opp.score}/100\n"
            f"      Revenue: ${opp.revenue_estimate_low:,.0f} - ${opp.revenue_estimate_high:,.0f}\n"
            f"      Template: {template_name}"
        )

    logger.info("\n[D] Pipeline summary:")
    summary = opp_manager.get_pipeline_summary()
    logger.info(f"  Total opportunities: {summary['total_opportunities']}")
    logger.info(f"  Average score: {summary['avg_score']:.1f}")
    logger.info(f"  Total potential revenue: ${summary['total_potential_revenue']:,.0f}")
    logger.info(f"  Actionable (score >= 60): {summary['actionable_count']}")

    # Show available service templates
    logger.info("\n[E] Available service templates:")
    for template in opp_manager.templates.values():
        logger.info(
            f"  - {template.name}\n"
            f"    Category: {template.category.value}\n"
            f"    Build time: {template.estimated_build_hours}h\n"
            f"    Price range: ${template.price_range[0]:.0f} - ${template.price_range[1]:.0f}"
        )


async def run_demo_hive():
    """Run a demonstration of the Agent Hive."""
    logger.info("=" * 60)
    logger.info("AGENT HIVE DEMONSTRATION")
    logger.info("=" * 60)

    # Create configuration with all drone types (Gemini-only)
    config = HiveConfig(
        hive_name="DemoHive",
        llm=LLMConfig(
            primary_model="gemini-2.5-flash",
            fast_model="gemini-2.5-flash",
            ace_model="gemini/gemini-2.0-flash",
        ),
        replication=ReplicationConfig(
            initial_workers=1,
            initial_builders=1,
            initial_researchers=1,
            initial_sellers=0,
            initial_analysts=1,  # Include analyst drone
            min_queue_depth=3,
        ),
        learning=LearningConfig(
            skillbook_path="data/demo_skillbook.json",
            async_learning=True,
        ),
        debug=True,
        verbose=True,
    )

    # Initialize hive
    logger.info("\n[1] Initializing Agent Hive...")
    hive = AgentHive(config)
    hive.initialize()

    # Display initial status
    status = hive.status
    logger.info(f"Hive ID: {hive.hive_id}")
    logger.info(f"Initial drones: {status.total_drones}")
    logger.info(f"Active goals: {status.goals_active}")

    # Set up monetization
    logger.info("\n[2] Setting up monetization...")
    treasury = Treasury("data/demo_treasury.db")
    registry = ProductRegistry("data/demo_products.json")
    pricing = PricingEngine()

    # Create sample products
    create_sample_products(registry)
    catalog = registry.get_catalog_summary()
    logger.info(f"Products in catalog: {catalog['total_products']}")
    logger.info(f"Services in catalog: {catalog['total_services']}")

    # Add some tasks using all drone types
    logger.info("\n[3] Adding tasks to the hive...")

    tasks = [
        ("Research AI market trends", "researcher", Priority.HIGH),
        ("Build landing page template", "builder", Priority.MEDIUM),
        ("Analyze competitor pricing", "researcher", Priority.MEDIUM),
        ("Calculate ROI for new opportunity", "analyst", Priority.HIGH),
        ("Create product documentation", "worker", Priority.LOW),
        ("Assess risk for AI API service", "analyst", Priority.MEDIUM),
    ]

    for title, drone_type, priority in tasks:
        task = hive.add_task(
            title=title,
            description=f"Task: {title}",
            drone_type=drone_type,
            priority=priority,
        )
        logger.info(f"  Added: {title} (drone={drone_type}, priority={priority.name})")

    # Display queue status
    status = hive.status
    logger.info(f"\nTask queue: {status.pending_tasks} pending, {status.active_tasks} active")

    # Run hive cycles
    logger.info("\n[4] Running hive operation cycles...")

    try:
        # Run 3 cycles (in demo mode, tasks won't actually execute without real LLM)
        results = await hive.run(cycles=3, interval=0.5, stop_on_empty=True)

        for result in results:
            logger.info(
                f"  Cycle {result.cycle_number}: "
                f"assigned={result.tasks_assigned}, "
                f"completed={result.tasks_completed}, "
                f"failed={result.tasks_failed}"
            )

    except Exception as e:
        logger.warning(f"Hive execution error (expected in demo without LLM): {e}")

    # Simulate some revenue
    logger.info("\n[5] Recording sample transactions...")
    treasury.add_revenue(49.0, "AI Agent Template Pack", "Template sale")
    treasury.add_revenue(150.0, "AI Strategy Consulting", "1hr consultation")
    treasury.add_cost(5.0, "LLM API", "OpenAI API usage")
    treasury.add_cost(2.0, "Infrastructure", "Cloud compute")

    financials = treasury.get_financial_summary()
    logger.info(f"Total revenue: ${financials['total_revenue']:.2f}")
    logger.info(f"Total costs: ${financials['total_costs']:.2f}")
    logger.info(f"Profit: ${financials['profit']:.2f}")
    logger.info(f"Margin: {financials['profit_margin']*100:.1f}%")

    # Display learning status
    logger.info("\n[6] Learning status...")
    skillbook_stats = hive.skillbook.stats()
    logger.info(f"Skills in skillbook: {skillbook_stats['skills']}")
    logger.info(f"Sections: {skillbook_stats['sections']}")

    # Get pricing recommendations
    logger.info("\n[7] Pricing recommendations...")
    for product in registry.get_active_products():
        rec = pricing.get_optimal_price(product)
        logger.info(
            f"  {product.name}: ${rec.recommended_price:.2f} "
            f"(confidence: {rec.confidence:.0%})"
        )

    # Demonstrate opportunity pipeline
    logger.info("\n[8] Opportunity Pipeline...")
    opp_manager = OpportunityManager("data/demo_opportunities.json")
    demonstrate_opportunity_pipeline(opp_manager)

    # Show task generation from opportunities
    logger.info("\n[9] Task generation for opportunities...")
    top_opp = opp_manager.get_top_opportunities(n=1)
    if top_opp:
        opp = top_opp[0]
        from agent_hive.queen.planner import StrategicPlanner
        planner = StrategicPlanner()
        tasks = planner.create_opportunity_tasks(
            opportunity_name=opp.name,
            opportunity_score=opp.score,
            revenue_estimate=opp.revenue_estimate_high,
        )
        logger.info(f"  Generated {len(tasks)} tasks for '{opp.name}':")
        for task in tasks:
            logger.info(f"    - {task.title} ({task.required_drone_type})")

    # Final status
    logger.info("\n[10] Final hive statistics...")
    stats = hive.get_stats()
    logger.info(f"Uptime: {stats['uptime_seconds']:.1f}s")
    logger.info(f"Cycles completed: {stats['cycles_completed']}")
    logger.info(f"Total drones: {stats['status']['total_drones']}")
    logger.info(f"Tasks completed: {stats['status']['completed_tasks']}")

    # Show drone breakdown
    logger.info("\nDrone breakdown by type:")
    for drone_id, drone in hive.drones.items():
        logger.info(f"  - {drone.name} ({drone.drone_type.value})")

    # Save state
    state_path = hive.save_state()
    logger.info(f"\nHive state saved to: {state_path}")

    logger.info("\n" + "=" * 60)
    logger.info("DEMONSTRATION COMPLETE")
    logger.info("=" * 60)


def main():
    """Main entry point."""
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                     AGENT HIVE                            ║
    ║           Self-Replicating, Self-Learning                 ║
    ║              Autonomous Agent Collective                  ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    asyncio.run(run_demo_hive())


if __name__ == "__main__":
    main()
