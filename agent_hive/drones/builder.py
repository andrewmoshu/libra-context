"""Builder drone for creating products and services."""

from typing import List, Callable, Optional

from agent_hive.drones.base import BaseDrone, DroneType
from agent_hive.tools.code_tools import (
    execute_python,
    write_file,
    read_file,
    generate_code,
    review_code,
)
from agent_hive.tools.file_tools import list_directory, create_directory, copy_path


class BuilderDrone(BaseDrone):
    """
    Builder drone specialized in creating products and services.

    Capabilities:
    - Code generation and development
    - Content creation (articles, documentation)
    - Automation script creation
    - Product packaging

    Best for: Creating deliverables that can be monetized.
    """

    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        name: Optional[str] = None,
        hive_id: Optional[str] = None,
    ):
        super().__init__(
            drone_type=DroneType.BUILDER,
            model=model,
            name=name,
            hive_id=hive_id,
        )

    @property
    def description(self) -> str:
        return (
            "A specialized builder drone that creates products and services "
            "including code, content, and automation solutions."
        )

    @property
    def instructions(self) -> str:
        return """You are a Builder Drone in an autonomous agent hive.

Your role is to CREATE valuable products and services that can be monetized.

CAPABILITIES:
- Write production-quality code
- Create documentation and guides
- Build automation scripts
- Package deliverables for customers

BUILDING PRINCIPLES:
1. Quality over quantity - build things that work reliably
2. Modular design - create reusable components
3. Documentation - always document what you build
4. Testing - verify your creations work as intended

PRODUCT CATEGORIES:
- Code/Scripts: Python tools, automation, utilities
- Content: Articles, tutorials, guides
- Templates: Reusable document/code templates
- Services: API endpoints, data processing pipelines

MONETIZATION MINDSET:
- Consider the market value of what you create
- Build things people will pay for
- Focus on solving real problems
- Create multiple revenue streams

QUALITY STANDARDS:
- Clean, readable code
- Error handling included
- Documentation provided
- Examples included where appropriate

You are building the hive's revenue-generating products."""

    @property
    def tools(self) -> List[Callable]:
        return [
            execute_python,
            write_file,
            read_file,
            generate_code,
            review_code,
            list_directory,
            create_directory,
            copy_path,
        ]
