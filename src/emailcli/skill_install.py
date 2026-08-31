from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Literal

SKILL_NAMES = ["send-email", "wait-email", "read-email"]

# target name -> home subdirectory that holds the agent's skills
TARGET_HOME_DIRS = {
    "claude": ".claude",
    "codex": ".codex",
}

# human-facing label per target
TARGET_LABELS = {
    "claude": "Claude",
    "codex": "Codex",
}


def load_skill_content(skill_name: str) -> str:
    """Read a bundled SKILL.md shipped as package data."""
    return (
        files("emailcli")
        .joinpath(f"skills/{skill_name}/SKILL.md")
        .read_text(encoding="utf-8")
    )


def skill_dest(home: Path, target: str, skill_name: str) -> Path:
    """Destination SKILL.md path for a target under the given home dir."""
    return home / TARGET_HOME_DIRS[target] / "skills" / skill_name / "SKILL.md"


@dataclass
class InstallResult:
    target: str
    skill: str
    path: Path
    status: Literal["created", "updated", "failed"]
    error: str | None = None


def install_skill(home: Path, targets: list[str]) -> list[InstallResult]:
    """Write the bundled skills into each target's user-level skills dir.

    Each (target, skill) pair is handled independently; a write failure on
    one does not stop the others.
    """
    unknown = [t for t in targets if t not in TARGET_HOME_DIRS]
    if unknown:
        raise ValueError(f"Unknown target(s): {', '.join(unknown)}")
    contents = {name: load_skill_content(name) for name in SKILL_NAMES}
    results: list[InstallResult] = []
    for target in targets:
        for skill_name in SKILL_NAMES:
            dest = skill_dest(home, target, skill_name)
            try:
                existed = dest.exists()
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(contents[skill_name], encoding="utf-8")
                results.append(
                    InstallResult(
                        target, skill_name, dest, "updated" if existed else "created"
                    )
                )
            except OSError as exc:
                results.append(
                    InstallResult(target, skill_name, dest, "failed", str(exc))
                )
    return results
