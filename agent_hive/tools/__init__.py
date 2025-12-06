"""Tools for Agent Hive drones."""

from agent_hive.tools.web_tools import (
    web_search,
    fetch_url,
    analyze_website,
    monitor_trends,
)
from agent_hive.tools.code_tools import (
    execute_python,
    write_file,
    read_file,
    generate_code,
    review_code,
)
from agent_hive.tools.file_tools import (
    list_directory,
    create_directory,
    delete_path,
    copy_path,
    move_path,
)

__all__ = [
    # Web tools
    "web_search",
    "fetch_url",
    "analyze_website",
    "monitor_trends",
    # Code tools
    "execute_python",
    "write_file",
    "read_file",
    "generate_code",
    "review_code",
    # File tools
    "list_directory",
    "create_directory",
    "delete_path",
    "copy_path",
    "move_path",
]
