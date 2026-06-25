import logging
from typing import Protocol

from deerflow.skills.types import Skill

logger = logging.getLogger(__name__)


class NamedTool(Protocol):
    name: str


def allowed_tool_names_for_skills(skills: list[Skill]) -> set[str] | None:
    """Return the union of explicit skill allowed-tools declarations.

    None means legacy allow-all behavior. It is returned only when no loaded
    skill declares allowed-tools. Once any skill declares the field, legacy
    skills without the field contribute no tools instead of disabling the
    explicit restrictions from other skills.
    """
    if not skills:
        return None

    allowed: set[str] = set()
    has_explicit_declaration = False
    for skill in skills:
        if skill.allowed_tools is None:
            continue
        has_explicit_declaration = True
        if not skill.allowed_tools:
            logger.info("Skill %s declared empty allowed-tools", skill.name)
        allowed.update(skill.allowed_tools)

    if not has_explicit_declaration:
        return None
    return allowed


def filter_tools_by_explicit_skill_allowed_tools[ToolT: NamedTool](tools: list[ToolT], skills: list[Skill]) -> list[ToolT]:
    """Apply allowed-tools for an explicit skill selection.

    The default "all enabled skills" catalogue is prompt context, not an
    execution policy. Explicit skill whitelists are different: the user or
    agent author intentionally selected a bounded workflow, so its
    ``allowed-tools`` declarations should constrain the runtime tools.
    """
    allowed = allowed_tool_names_for_skills(skills)
    if allowed is None:
        return tools

    filtered = [tool for tool in tools if tool.name in allowed]
    if tools and allowed and not filtered:
        available = sorted({tool.name for tool in tools})
        raise ValueError(
            "Explicit skill allowed-tools did not match any available DeerFlow tool. "
            f"allowed={sorted(allowed)!r}; available={available!r}"
        )
    return filtered
