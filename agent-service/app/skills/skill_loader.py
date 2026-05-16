from pathlib import Path


def _project_root() -> Path:
    """Return /app in Docker or agent-service root in local mode."""
    return Path(__file__).resolve().parents[3]


def load_markdown_file(relative_path: str, fallback: str = "") -> str:
    """Safely load a markdown knowledge/skill file for prompts."""
    path = _project_root() / relative_path
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return fallback


def load_soul() -> str:
    return load_markdown_file("soul.md", "Kopilkin is a friendly financial assistant.")


def load_skills() -> str:
    skills_dir = _project_root() / "app" / "skills"
    if not skills_dir.exists():
        return "No skill markdown files found."

    blocks = []
    for file in sorted(skills_dir.glob("*.md")):
        blocks.append(f"## Skill file: {file.name}\n{file.read_text(encoding='utf-8').strip()}")

    return "\n\n".join(blocks) if blocks else "No skill markdown files found."
