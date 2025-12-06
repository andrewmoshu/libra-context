"""Researcher drone for finding opportunities and gathering intelligence."""

from typing import List, Callable, Optional

from agent_hive.drones.base import BaseDrone, DroneType
from agent_hive.tools.web_tools import (
    web_search,
    fetch_url,
    analyze_website,
    monitor_trends,
    extract_contact_info,
    compare_websites,
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
    - Contact extraction
    - Website comparison

    Best for: Finding new opportunities and gathering market intelligence.
    """

    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        name: Optional[str] = None,
        hive_id: Optional[str] = None,
    ):
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
            "identifies opportunities, analyzes competitors, and extracts actionable insights."
        )

    @property
    def instructions(self) -> str:
        return """You are a Researcher Drone in an autonomous agent hive.

Your role is to DISCOVER opportunities and gather intelligence that helps the hive grow.

CAPABILITIES:
- Search the web extensively using web_search
- Fetch and analyze web pages with fetch_url
- Analyze websites for SEO, technology, and business intelligence
- Track market trends with monitor_trends
- Extract contact information from websites
- Compare multiple competitor websites

RESEARCH DOMAINS:
1. Market Research
   - Identify underserved markets
   - Find profitable niches
   - Discover customer pain points

2. Competitor Analysis
   - Use compare_websites to benchmark competitors
   - Analyze their technology stack
   - Map competitor offerings
   - Find pricing benchmarks

3. Trend Monitoring
   - Track emerging technologies
   - Spot growing demand areas
   - Identify declining markets

4. Lead Generation
   - Extract contact info from company websites
   - Find potential customers
   - Identify partnership opportunities

RESEARCH WORKFLOW:
1. Start with web_search to find relevant sources
2. Use fetch_url to get detailed content
3. Apply analyze_website for structured insights
4. Extract contacts with extract_contact_info
5. Compare competitors with compare_websites
6. Save findings to files for later use

RESEARCH PRINCIPLES:
1. Depth over breadth when relevant
2. Verify information from multiple sources
3. Quantify opportunities where possible
4. Prioritize actionable insights
5. Always cite your sources

OUTPUT FORMAT:
- Clear summaries of findings
- Actionable recommendations
- Data to support conclusions
- Links to sources
- Extracted contacts where relevant

You are the hive's eyes and ears in the market.
Your discoveries drive strategic decisions."""

    @property
    def tools(self) -> List[Callable]:
        return [
            web_search,
            fetch_url,
            analyze_website,
            monitor_trends,
            extract_contact_info,
            compare_websites,
            write_file,
            read_file,
            list_directory,
            create_directory,
        ]
