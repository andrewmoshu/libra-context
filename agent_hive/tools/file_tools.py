"""File system tools for Agent Hive drones."""

from typing import Optional, Dict, Any, List
from pathlib import Path
import shutil
import json


def list_directory(
    path: str = ".",
    pattern: str = "*",
    recursive: bool = False,
    include_hidden: bool = False,
) -> Dict[str, Any]:
    """
    List files and directories.

    Args:
        path: Directory path to list
        pattern: Glob pattern to filter files
        recursive: Include subdirectories recursively
        include_hidden: Include hidden files (starting with .)

    Returns:
        Dict containing list of files and directories
    """
    result = {
        "status": "success",
        "path": path,
        "files": [],
        "directories": [],
        "total_count": 0,
    }

    try:
        dir_path = Path(path)

        if not dir_path.exists():
            result["status"] = "error"
            result["message"] = f"Directory not found: {path}"
            return result

        if not dir_path.is_dir():
            result["status"] = "error"
            result["message"] = f"Not a directory: {path}"
            return result

        glob_func = dir_path.rglob if recursive else dir_path.glob

        for item in glob_func(pattern):
            if not include_hidden and item.name.startswith("."):
                continue

            item_info = {
                "name": item.name,
                "path": str(item),
                "size": item.stat().st_size if item.is_file() else 0,
                "modified": item.stat().st_mtime,
            }

            if item.is_file():
                result["files"].append(item_info)
            elif item.is_dir():
                result["directories"].append(item_info)

        result["total_count"] = len(result["files"]) + len(result["directories"])

    except Exception as e:
        result["status"] = "error"
        result["message"] = str(e)

    return result


def create_directory(
    path: str,
    parents: bool = True,
    exist_ok: bool = True,
) -> Dict[str, Any]:
    """
    Create a directory.

    Args:
        path: Directory path to create
        parents: Create parent directories if needed
        exist_ok: Don't raise error if directory exists

    Returns:
        Dict containing operation status
    """
    result = {
        "status": "success",
        "path": path,
        "created": False,
        "message": "",
    }

    try:
        dir_path = Path(path)

        if dir_path.exists():
            if exist_ok:
                result["message"] = f"Directory already exists: {path}"
            else:
                result["status"] = "error"
                result["message"] = f"Directory already exists: {path}"
            return result

        dir_path.mkdir(parents=parents, exist_ok=exist_ok)
        result["created"] = True
        result["message"] = f"Created directory: {path}"

    except Exception as e:
        result["status"] = "error"
        result["message"] = str(e)

    return result


def delete_path(
    path: str,
    recursive: bool = False,
    force: bool = False,
) -> Dict[str, Any]:
    """
    Delete a file or directory.

    Args:
        path: Path to delete
        recursive: Delete directories recursively
        force: Force deletion without confirmation

    Returns:
        Dict containing operation status
    """
    result = {
        "status": "success",
        "path": path,
        "deleted": False,
        "message": "",
    }

    try:
        target = Path(path)

        if not target.exists():
            result["status"] = "error"
            result["message"] = f"Path not found: {path}"
            return result

        if target.is_file():
            target.unlink()
            result["deleted"] = True
            result["message"] = f"Deleted file: {path}"
        elif target.is_dir():
            if recursive:
                shutil.rmtree(target)
                result["deleted"] = True
                result["message"] = f"Deleted directory: {path}"
            else:
                # Only delete empty directories
                try:
                    target.rmdir()
                    result["deleted"] = True
                    result["message"] = f"Deleted empty directory: {path}"
                except OSError:
                    result["status"] = "error"
                    result["message"] = (
                        f"Directory not empty: {path}. Set recursive=True to delete."
                    )

    except Exception as e:
        result["status"] = "error"
        result["message"] = str(e)

    return result


def copy_path(
    source: str,
    destination: str,
    overwrite: bool = False,
) -> Dict[str, Any]:
    """
    Copy a file or directory.

    Args:
        source: Source path
        destination: Destination path
        overwrite: Overwrite if destination exists

    Returns:
        Dict containing operation status
    """
    result = {
        "status": "success",
        "source": source,
        "destination": destination,
        "copied": False,
        "message": "",
    }

    try:
        src = Path(source)
        dst = Path(destination)

        if not src.exists():
            result["status"] = "error"
            result["message"] = f"Source not found: {source}"
            return result

        if dst.exists() and not overwrite:
            result["status"] = "error"
            result["message"] = (
                f"Destination exists: {destination}. Set overwrite=True to replace."
            )
            return result

        if src.is_file():
            shutil.copy2(src, dst)
        else:
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)

        result["copied"] = True
        result["message"] = f"Copied {source} to {destination}"

    except Exception as e:
        result["status"] = "error"
        result["message"] = str(e)

    return result


def move_path(
    source: str,
    destination: str,
    overwrite: bool = False,
) -> Dict[str, Any]:
    """
    Move a file or directory.

    Args:
        source: Source path
        destination: Destination path
        overwrite: Overwrite if destination exists

    Returns:
        Dict containing operation status
    """
    result = {
        "status": "success",
        "source": source,
        "destination": destination,
        "moved": False,
        "message": "",
    }

    try:
        src = Path(source)
        dst = Path(destination)

        if not src.exists():
            result["status"] = "error"
            result["message"] = f"Source not found: {source}"
            return result

        if dst.exists() and not overwrite:
            result["status"] = "error"
            result["message"] = (
                f"Destination exists: {destination}. Set overwrite=True to replace."
            )
            return result

        if dst.exists():
            if dst.is_file():
                dst.unlink()
            else:
                shutil.rmtree(dst)

        shutil.move(str(src), str(dst))
        result["moved"] = True
        result["message"] = f"Moved {source} to {destination}"

    except Exception as e:
        result["status"] = "error"
        result["message"] = str(e)

    return result
