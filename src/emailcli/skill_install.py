from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Literal

SKILL_NAME = "send-email"

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


def load_skill_content() -> str:
    """Read the bundled SKILL.md shipped as package data."""
    return (
        files("emailcli")
        .joinpath(f"skills/{SKILL_NAME}/SKILL.md")
        .read_text(encoding="utf-8")
    )


def skill_dest(home: Path, target: str) -> Path:
    """Destination SKILL.md path for a target under the given home dir."""
    return home / TARGET_HOME_DIRS[target] / "skills" / SKILL_NAME / "SKILL.md"


@dataclass
class InstallResult:
    target: str
    path: Path
    status: Literal["created", "updated", "failed"]
    error: str | None = None


def install_skill(home: Path, targets: list[str]) -> list[InstallResult]:
    """Write the bundled skill into each target's user-level skills dir.

    Each target is handled independently; a write failure on one target is
    recorded and does not stop the others.
    """
    unknown = [t for t in targets if t not in TARGET_HOME_DIRS]
    if unknown:
        raise ValueError(f"Unknown target(s): {', '.join(unknown)}")
    content = load_skill_content()
    results: list[InstallResult] = []
    for target in targets:
        dest = skill_dest(home, target)
        try:
            existed = dest.exists()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
            results.append(
                InstallResult(target, dest, "updated" if existed else "created")
            )
        except OSError as exc:
            results.append(InstallResult(target, dest, "failed", str(exc)))
    return results
