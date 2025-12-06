"""Shared skillbook management for Agent Hive."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import logging
import threading

logger = logging.getLogger(__name__)

# Try to import ACE Skillbook, fall back to local implementation
try:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
    from ace.skillbook import Skillbook, Skill
    ACE_AVAILABLE = True
except ImportError:
    ACE_AVAILABLE = False
    logger.warning("ACE framework not available, using local skillbook implementation")


@dataclass
class LocalSkill:
    """Local skill implementation when ACE is not available."""

    id: str
    section: str
    content: str
    helpful: int = 0
    harmful: int = 0
    neutral: int = 0
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    source_drone: Optional[str] = None
    source_task: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "section": self.section,
            "content": self.content,
            "helpful": self.helpful,
            "harmful": self.harmful,
            "neutral": self.neutral,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "source_drone": self.source_drone,
            "source_task": self.source_task,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LocalSkill":
        return cls(
            id=data["id"],
            section=data["section"],
            content=data["content"],
            helpful=data.get("helpful", 0),
            harmful=data.get("harmful", 0),
            neutral=data.get("neutral", 0),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
            source_drone=data.get("source_drone"),
            source_task=data.get("source_task"),
        )


class HiveSkillbook:
    """
    Shared skillbook for the Agent Hive.

    This wraps the ACE Skillbook (if available) and provides:
    - Thread-safe access for multiple drones
    - Hive-specific metadata tracking
    - Automatic persistence
    - Skill attribution (which drone learned what)

    All drones share this skillbook, enabling collective learning.
    """

    def __init__(self, skillbook_path: str = "data/hive_skillbook.json"):
        self.skillbook_path = Path(skillbook_path)
        self._lock = threading.RLock()

        # Use ACE Skillbook if available
        if ACE_AVAILABLE:
            if self.skillbook_path.exists():
                self._skillbook = Skillbook.load_from_file(str(self.skillbook_path))
                logger.info(f"Loaded ACE skillbook from {self.skillbook_path}")
            else:
                self._skillbook = Skillbook()
                logger.info("Created new ACE skillbook")
            self._local_skills: Dict[str, LocalSkill] = {}
            self._using_ace = True
        else:
            self._skillbook = None
            self._local_skills: Dict[str, LocalSkill] = {}
            self._sections: Dict[str, List[str]] = {}
            self._next_id = 0
            self._using_ace = False

            # Load from file if exists
            if self.skillbook_path.exists():
                self._load_local()

        # Track skill attribution
        self._skill_attribution: Dict[str, Dict[str, Any]] = {}

    @property
    def is_ace_enabled(self) -> bool:
        """Check if using ACE Skillbook."""
        return self._using_ace

    def add_skill(
        self,
        section: str,
        content: str,
        skill_id: Optional[str] = None,
        source_drone: Optional[str] = None,
        source_task: Optional[str] = None,
        metadata: Optional[Dict[str, int]] = None,
    ) -> str:
        """
        Add a new skill to the skillbook.

        Args:
            section: Category/section for the skill
            content: The skill content/strategy
            skill_id: Optional custom ID
            source_drone: ID of drone that learned this
            source_task: ID of task that produced this learning
            metadata: Optional helpful/harmful/neutral counts

        Returns:
            The skill ID
        """
        with self._lock:
            if self._using_ace:
                skill = self._skillbook.add_skill(
                    section=section,
                    content=content,
                    skill_id=skill_id,
                    metadata=metadata,
                )
                actual_id = skill.id
            else:
                actual_id = skill_id or self._generate_id(section)
                skill = LocalSkill(
                    id=actual_id,
                    section=section,
                    content=content,
                    source_drone=source_drone,
                    source_task=source_task,
                )
                if metadata:
                    skill.helpful = metadata.get("helpful", 0)
                    skill.harmful = metadata.get("harmful", 0)
                    skill.neutral = metadata.get("neutral", 0)

                self._local_skills[actual_id] = skill
                self._sections.setdefault(section, []).append(actual_id)

            # Track attribution
            self._skill_attribution[actual_id] = {
                "source_drone": source_drone,
                "source_task": source_task,
                "added_at": datetime.now(timezone.utc).isoformat(),
            }

            # Auto-save
            self.save()

            logger.debug(f"Added skill {actual_id} to section {section}")
            return actual_id

    def update_skill(
        self,
        skill_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, int]] = None,
    ) -> bool:
        """Update an existing skill."""
        with self._lock:
            if self._using_ace:
                result = self._skillbook.update_skill(
                    skill_id, content=content, metadata=metadata
                )
                if result:
                    self.save()
                return result is not None
            else:
                if skill_id not in self._local_skills:
                    return False
                skill = self._local_skills[skill_id]
                if content:
                    skill.content = content
                if metadata:
                    skill.helpful = metadata.get("helpful", skill.helpful)
                    skill.harmful = metadata.get("harmful", skill.harmful)
                    skill.neutral = metadata.get("neutral", skill.neutral)
                skill.updated_at = datetime.now(timezone.utc).isoformat()
                self.save()
                return True

    def tag_skill(self, skill_id: str, tag: str, increment: int = 1) -> bool:
        """Tag a skill as helpful, harmful, or neutral."""
        with self._lock:
            if self._using_ace:
                result = self._skillbook.tag_skill(skill_id, tag, increment)
                if result:
                    self.save()
                return result is not None
            else:
                if skill_id not in self._local_skills:
                    return False
                skill = self._local_skills[skill_id]
                if tag == "helpful":
                    skill.helpful += increment
                elif tag == "harmful":
                    skill.harmful += increment
                elif tag == "neutral":
                    skill.neutral += increment
                else:
                    return False
                skill.updated_at = datetime.now(timezone.utc).isoformat()
                self.save()
                return True

    def remove_skill(self, skill_id: str) -> bool:
        """Remove a skill from the skillbook."""
        with self._lock:
            if self._using_ace:
                self._skillbook.remove_skill(skill_id)
                self.save()
                return True
            else:
                if skill_id not in self._local_skills:
                    return False
                skill = self._local_skills.pop(skill_id)
                if skill.section in self._sections:
                    self._sections[skill.section] = [
                        sid for sid in self._sections[skill.section] if sid != skill_id
                    ]
                self.save()
                return True

    def get_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Get a skill by ID."""
        with self._lock:
            if self._using_ace:
                skill = self._skillbook.get_skill(skill_id)
                if skill:
                    return {
                        "id": skill.id,
                        "section": skill.section,
                        "content": skill.content,
                        "helpful": skill.helpful,
                        "harmful": skill.harmful,
                        "neutral": skill.neutral,
                    }
                return None
            else:
                skill = self._local_skills.get(skill_id)
                return skill.to_dict() if skill else None

    def get_all_skills(self) -> List[Dict[str, Any]]:
        """Get all skills in the skillbook."""
        with self._lock:
            if self._using_ace:
                return [
                    {
                        "id": s.id,
                        "section": s.section,
                        "content": s.content,
                        "helpful": s.helpful,
                        "harmful": s.harmful,
                        "neutral": s.neutral,
                    }
                    for s in self._skillbook.skills()
                ]
            else:
                return [s.to_dict() for s in self._local_skills.values()]

    def get_skills_by_section(self, section: str) -> List[Dict[str, Any]]:
        """Get all skills in a section."""
        with self._lock:
            if self._using_ace:
                return [
                    {
                        "id": s.id,
                        "section": s.section,
                        "content": s.content,
                        "helpful": s.helpful,
                        "harmful": s.harmful,
                        "neutral": s.neutral,
                    }
                    for s in self._skillbook.skills()
                    if s.section == section
                ]
            else:
                skill_ids = self._sections.get(section, [])
                return [
                    self._local_skills[sid].to_dict()
                    for sid in skill_ids
                    if sid in self._local_skills
                ]

    def get_top_skills(self, n: int = 10) -> List[Dict[str, Any]]:
        """Get top N skills by helpful count."""
        all_skills = self.get_all_skills()
        sorted_skills = sorted(all_skills, key=lambda s: s["helpful"], reverse=True)
        return sorted_skills[:n]

    def as_prompt(self) -> str:
        """Get skillbook formatted for LLM prompt."""
        with self._lock:
            if self._using_ace:
                return self._skillbook.as_prompt()
            else:
                # Simple markdown format
                if not self._local_skills:
                    return "(empty skillbook)"

                parts = []
                for section in sorted(self._sections.keys()):
                    parts.append(f"## {section}")
                    for skill_id in self._sections[section]:
                        skill = self._local_skills.get(skill_id)
                        if skill:
                            parts.append(
                                f"- [{skill.id}] {skill.content} "
                                f"(helpful={skill.helpful}, harmful={skill.harmful})"
                            )
                return "\n".join(parts)

    def stats(self) -> Dict[str, Any]:
        """Get skillbook statistics."""
        with self._lock:
            if self._using_ace:
                return self._skillbook.stats()
            else:
                total_helpful = sum(s.helpful for s in self._local_skills.values())
                total_harmful = sum(s.harmful for s in self._local_skills.values())
                total_neutral = sum(s.neutral for s in self._local_skills.values())
                return {
                    "sections": len(self._sections),
                    "skills": len(self._local_skills),
                    "tags": {
                        "helpful": total_helpful,
                        "harmful": total_harmful,
                        "neutral": total_neutral,
                    },
                }

    def save(self) -> None:
        """Save skillbook to file."""
        with self._lock:
            self.skillbook_path.parent.mkdir(parents=True, exist_ok=True)

            if self._using_ace:
                self._skillbook.save_to_file(str(self.skillbook_path))
            else:
                data = {
                    "skills": {sid: s.to_dict() for sid, s in self._local_skills.items()},
                    "sections": self._sections,
                    "next_id": self._next_id,
                    "attribution": self._skill_attribution,
                }
                with open(self.skillbook_path, "w") as f:
                    json.dump(data, f, indent=2)

    def _load_local(self) -> None:
        """Load local skillbook from file."""
        try:
            with open(self.skillbook_path, "r") as f:
                data = json.load(f)

            for sid, sdata in data.get("skills", {}).items():
                self._local_skills[sid] = LocalSkill.from_dict(sdata)

            self._sections = data.get("sections", {})
            self._next_id = data.get("next_id", 0)
            self._skill_attribution = data.get("attribution", {})

            logger.info(f"Loaded local skillbook from {self.skillbook_path}")
        except Exception as e:
            logger.error(f"Failed to load skillbook: {e}")

    def _generate_id(self, section: str) -> str:
        """Generate a new skill ID."""
        self._next_id += 1
        section_prefix = section.split()[0].lower()
        return f"{section_prefix}-{self._next_id:05d}"

    def get_attribution(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Get attribution info for a skill."""
        return self._skill_attribution.get(skill_id)
