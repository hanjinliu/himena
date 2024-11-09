from app_model.types import CommandRule


def formatter_general(cmd: CommandRule) -> str:
    """Format a general command for the command palette."""
    if ":" in cmd.id:
        mod, *_ = cmd.id.split(":")
        return f"{mod}: {cmd.title}"
    else:
        return cmd.title


def formatter_recent(cmd: CommandRule) -> str:
    """Format a "open recent" command for the command palette."""
    return str(cmd.title)
