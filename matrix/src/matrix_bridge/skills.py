from __future__ import annotations

import os
from dataclasses import dataclass


class SkillError(Exception):
    pass


@dataclass
class Skill:
    skill_id: str
    content: str
    description: str = ""


def load_skill(skills_dir: str, skill_id: str) -> Skill:
    skill_path = os.path.join(skills_dir, skill_id, "skill.md")
    if not os.path.exists(skill_path):
        raise SkillError(
            f"Skill {skill_id!r} not found.\nExpected: {skill_path}"
        )
    with open(skill_path) as fh:
        content = fh.read()

    description = ""
    for line in content.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            description = line[:120]
            break

    return Skill(skill_id=skill_id, content=content, description=description)


def load_skills(skills_dir: str, skill_ids: list[str]) -> tuple[list[Skill], list[str]]:
    """Returns (loaded, failed_ids)."""
    loaded, failed = [], []
    for sid in skill_ids:
        try:
            loaded.append(load_skill(skills_dir, sid))
        except SkillError:
            failed.append(sid)
    return loaded, failed
