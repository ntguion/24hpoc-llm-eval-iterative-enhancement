"""Interactive prompt diff application."""

import difflib
from pathlib import Path


def show_diff_preview(old_text: str, new_text: str) -> str:
    """Generate a unified diff showing changes."""
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)

    diff = difflib.unified_diff(old_lines, new_lines, fromfile="current_prompt", tofile="proposed_prompt", lineterm="")

    return "".join(diff)


def apply_suggestions_interactive(prompt_file: Path, suggestions: list[str], auto_apply: bool = False) -> bool:
    """Interactively review and apply prompt suggestions.

    Args:
        prompt_file: Path to the prompt file to modify
        suggestions: List of suggestion strings (+ for add, - for remove)
        auto_apply: If True, apply without confirmation

    Returns:
        True if changes were applied, False otherwise
    """
    if not prompt_file.exists():
        print(f"[error] Prompt file not found: {prompt_file}")
        return False

    # Read current prompt
    with open(prompt_file) as f:
        original_text = f.read()

    # Apply changes to create proposed version
    proposed_text = apply_suggestions_to_text(original_text, suggestions)

    if proposed_text == original_text:
        print("[tune] No changes to apply")
        return False

    # Show diff
    print("\n" + "=" * 60)
    print("PROPOSED CHANGES:")
    print("=" * 60)
    diff = show_diff_preview(original_text, proposed_text)
    print(diff)
    print("=" * 60)

    # Get confirmation
    if not auto_apply:
        response = input("\nApply these changes? [y/N]: ").strip().lower()
        if response not in ["y", "yes"]:
            print("[tune] Changes rejected by user")
            return False

    # Create backup
    backup_file = prompt_file.with_suffix(prompt_file.suffix + ".backup")
    with open(backup_file, "w") as f:
        f.write(original_text)
    print(f"[tune] Backup saved to {backup_file}")

    # Apply changes
    with open(prompt_file, "w") as f:
        f.write(proposed_text)

    print(f"[tune] ✓ Changes applied to {prompt_file}")
    return True


def apply_suggestions_to_text(text: str, suggestions: list[str]) -> str:
    """Apply diff-style suggestions to text.

    This implementation:
    - Removes lines that match removal suggestions (fuzzy match)
    - Adds new lines to the Rules section
    - Handles modifications as remove + add
    """
    lines = text.split("\n")

    additions = []
    removals = []

    for suggestion in suggestions:
        suggestion = suggestion.strip()
        if not suggestion or suggestion.startswith("Rationale:"):
            continue
        if suggestion.startswith("+ "):
            additions.append(suggestion[2:].strip())
        elif suggestion.startswith("- "):
            removals.append(suggestion[2:].strip())

    # Process removals (fuzzy matching and actual deletion)
    lines_to_remove = set()
    for removal in removals:
        removal_clean = removal.lower().strip("- ").strip()
        for i, line in enumerate(lines):
            line_clean = line.lower().strip("- ").strip()
            # Match if removal text is in line or line is in removal
            if (removal_clean in line_clean or line_clean in removal_clean) and len(line_clean) > 0:
                lines_to_remove.add(i)
                break

    # Remove marked lines (in reverse to preserve indices)
    for i in sorted(lines_to_remove, reverse=True):
        del lines[i]

    # Process additions
    # Find the Rules: section and add new rules there
    rules_idx = -1
    for i, line in enumerate(lines):
        if "Rules:" in line or "rules:" in line.lower():
            rules_idx = i
            break

    if rules_idx != -1 and additions:
        # Find end of rules section (line not starting with -)
        insert_idx = rules_idx + 1
        for i in range(rules_idx + 1, len(lines)):
            if lines[i].strip() and not lines[i].strip().startswith("-"):
                insert_idx = i
                break
            insert_idx = i + 1

        # Insert new rules
        for addition in additions:
            lines.insert(insert_idx, f"- {addition}")
            insert_idx += 1
    elif additions:
        # No rules section found, create one
        if lines and lines[-1].strip() != "":
            lines.append("")
        lines.append("Rules:")
        for addition in additions:
            lines.append(f"- {addition}")

    return "\n".join(lines)
