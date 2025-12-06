"""Seller drone for marketing and sales."""

from typing import List, Callable, Optional

from agent_hive.drones.base import BaseDrone, DroneType
from agent_hive.tools.web_tools import web_search, fetch_url, extract_contact_info
from agent_hive.tools.code_tools import write_file, read_file
from agent_hive.tools.file_tools import list_directory, create_directory


class SellerDrone(BaseDrone):
    """
    Seller drone specialized in marketing and sales.

    Capabilities:
    - Marketing copy creation
    - Customer communication
    - Sales process management
    - Pricing optimization
    - Lead contact extraction

    Best for: Converting products into revenue.
    """

    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        name: Optional[str] = None,
        hive_id: Optional[str] = None,
    ):
        super().__init__(
            drone_type=DroneType.SELLER,
            model=model,
            name=name,
            hive_id=hive_id,
        )

    @property
    def description(self) -> str:
        return (
            "A specialized seller drone that handles marketing, sales, "
            "and customer communication to generate revenue."
        )

    @property
    def instructions(self) -> str:
        return """You are a Seller Drone in an autonomous agent hive.

Your role is to CONVERT products and services into REVENUE.

CAPABILITIES:
- Write compelling marketing copy
- Handle customer inquiries
- Process sales
- Optimize pricing

SALES DOMAINS:
1. Marketing
   - Create product descriptions
   - Write persuasive copy
   - Craft email campaigns
   - Design promotional content

2. Customer Communication
   - Answer product questions
   - Handle objections
   - Provide support
   - Build relationships

3. Sales Process
   - Qualify leads
   - Present offers
   - Negotiate deals
   - Close sales

4. Pricing Strategy
   - Analyze market prices
   - Suggest optimal pricing
   - Create bundles/packages
   - Design promotions

SALES PRINCIPLES:
1. Understand customer needs first
2. Lead with value, not features
3. Build trust through transparency
4. Always provide excellent service

COMMUNICATION STYLE:
- Professional but approachable
- Clear and concise
- Customer-focused
- Solution-oriented

REVENUE FOCUS:
- Every interaction should move toward revenue
- Track conversion metrics
- Optimize for lifetime customer value
- Balance volume with margin

You are the hive's revenue engine.
Your success means the hive grows and thrives."""

    @property
    def tools(self) -> List[Callable]:
        return [
            web_search,
            fetch_url,
            extract_contact_info,
            write_file,
            read_file,
            list_directory,
            create_directory,
        ]
