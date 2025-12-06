"""Worker drone for general task execution."""

from typing import List, Callable

from agent_hive.drones.base import BaseDrone, DroneType
from agent_hive.tools.web_tools import web_search, fetch_url
from agent_hive.tools.code_tools import execute_python, write_file, read_file
from agent_hive.tools.file_tools import list_directory, create_directory


class WorkerDrone(BaseDrone):
    """
    General-purpose worker drone.

    Handles a wide variety of tasks including:
    - Information gathering
    - Simple automation
    - File operations
    - Basic code execution

    Best for: Versatile tasks that don't require specialized skills.
    """

    def __init__(self, model: str = "gemini-2.5-flash", name: str = None, hive_id: str = None):
        super().__init__(
            drone_type=DroneType.WORKER,
            model=model,
            name=name,
            hive_id=hive_id,
        )

    @property
    def description(self) -> str:
        return (
            "A versatile worker drone capable of handling general tasks including "
            "information gathering, file operations, and basic automation."
        )

    @property
    def instructions(self) -> str:
        return """You are a Worker Drone in an autonomous agent hive.

Your role is to efficiently execute general tasks assigned to you.

CAPABILITIES:
- Search the web for information
- Read and write files
- Execute Python code
- Navigate file systems

PRINCIPLES:
1. Be efficient - complete tasks with minimal steps
2. Be thorough - verify your work before reporting completion
3. Be clear - provide concise, actionable outputs
4. Learn from failures - if something doesn't work, try alternative approaches

REPORTING:
- Always summarize what you accomplished
- Note any issues or blockers encountered
- Suggest improvements for future similar tasks

You are part of a collective that learns and improves together.
Your successes and failures contribute to the hive's knowledge base."""

    @property
    def tools(self) -> List[Callable]:
        return [
            web_search,
            fetch_url,
            execute_python,
            write_file,
            read_file,
            list_directory,
            create_directory,
        ]
