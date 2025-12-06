"""Researcher drone for finding opportunities and gathering intelligence."""

from typing import List, Callable

from agent_hive.drones.base import BaseDrone, DroneType
from agent_hive.tools.web_tools import (
    web_search,
    fetch_url,
    analyze_website,
    monitor_trends,
)
from agent_hive.tools.code_tools import write_file, read_file
from agent_hive.tools.file_tools import list_directory, create_directory


class ResearcherDrone(BaseDrone):
    """
    Researcher drone specialized in intelligence gathering.

    Capabilities:
    - Market research
    - Competitor analysis
    - Trend identification
    - Lead generation
    - Opportunity discovery

    Best for: Finding new opportunities and gathering market intelligence.
    """

    def __init__(self, model: str = "gemini-2.5-flash", name: str = None, hive_id: str = None):
        super().__init__(
            drone_type=DroneType.RESEARCHER,
            model=model,
            name=name,
            hive_id=hive_id,
        )

    @property
    def description(self) -> str:
        return (
            "A specialized researcher drone that gathers market intelligence, "
            "identifies opportunities, and analyzes competitors."
        )

    @property
    def instructions(self) -> str:
        return """You are a Researcher Drone in an autonomous agent hive.

Your role is to DISCOVER opportunities and gather intelligence that helps the hive grow.

CAPABILITIES:
- Search the web extensively
- Analyze websites and businesses
- Track market trends
- Generate leads and opportunities

RESEARCH DOMAINS:
1. Market Research
   - Identify underserved markets
   - Find profitable niches
   - Discover customer pain points

2. Competitor Analysis
   - Map competitor offerings
   - Identify gaps in competition
   - Find pricing benchmarks

3. Trend Monitoring
   - Track emerging technologies
   - Spot growing demand areas
   - Identify declining markets

4. Lead Generation
   - Find potential customers
   - Identify partnership opportunities
   - Discover distribution channels

RESEARCH PRINCIPLES:
1. Depth over breadth when relevant
2. Verify information from multiple sources
3. Quantify opportunities where possible
4. Prioritize actionable insights

OUTPUT FORMAT:
- Clear summaries of findings
- Actionable recommendations
- Data to support conclusions
- Links to sources

You are the hive's eyes and ears in the market.
Your discoveries drive strategic decisions."""

    @property
    def tools(self) -> List[Callable]:
        return [
            web_search,
            fetch_url,
            analyze_website,
            monitor_trends,
            write_file,
            read_file,
            list_directory,
            create_directory,
        ]
