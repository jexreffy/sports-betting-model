#!/usr/bin/env python3
"""Deny protected-branch git, GitHub approve/merge, and secret-path staging."""

from __future__ import annotations

import json
import re
import subprocess
import sys

PROTECTED = ("main", "master", "staging", "development")
SECRET_RE = re.compile(
    r"(?:^|/)("
    r"\.env(?:\..+)?(?<!\.example)"
    r"|credentials\.json"
    r"|\.venv(?:/|$)"
    r"|data/(?:raw|simulation|live)(?:/|$)"
    r")",
    re.IGNORECASE,
)


def out(permission: str, *, user: str = "", agent: str = "") -> None:
    payload: dict[str, str] = {"permission": permission}
    if user:
        payload["user_message"] = user
    if agent:
        payload["agent_message"] = agent
    sys.stdout.write(json.dumps(payload) + "\n")


def deny(msg: str) -> None:
    out("deny", user=msg, agent=msg)
    raise SystemExit(0)


def load() -> dict:
    raw = sys.stdin.buffer.read().decode("utf-8-sig", errors="replace").strip()
    if not raw:
        return {}
    data = json.loads(raw)
    return data if isinstance(data, dict) else {}


def cwd_of(data: dict) -> str:
    cwd = str(data.get("cwd") or "").strip()
    if cwd:
        return cwd
    roots = data.get("workspace_roots") or []
    if isinstance(roots, list) and roots:
        return str(roots[0])
    return ""


def git(cwd: str, *args: str) -> str | None:
    if not cwd:
        return None
    try:
        proc = subprocess.run(
            ["git", "-C", cwd, *args],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def branch_name(ref: str) -> str:
    ref = ref.strip().strip("'\"")
    if ":" in ref:
        ref = ref.split(":", 1)[1]
    ref = re.sub(r"^refs/heads/", "", ref)
    return ref.split("/")[-1] if "/" in ref and ref.split("/")[0] in {"refs", "heads"} else ref


def is_protected_ref(ref: str) -> bool:
    name = branch_name(ref)
    return name in PROTECTED


def tokens(command: str) -> list[str]:
    return command.replace("\n", " ").split()


def has_git_commit(command: str) -> bool:
    return bool(re.search(r"\bgit\b(?:\s+[^\n]+)?\s+commit\b", command))


def has_git_push(command: str) -> bool:
    return bool(re.search(r"\bgit\b(?:\s+[^\n]+)?\s+push\b", command))


def has_git_add(command: str) -> bool:
    return bool(re.search(r"\bgit\b(?:\s+[^\n]+)?\s+add\b", command))


def push_targets_protected(command: str) -> bool:
    if re.search(
        r"(?:HEAD|heads)/(?:refs/heads/)?(?:main|master|staging|development)\b"
        r"|:(?:refs/heads/)?(?:main|master|staging|development)\b",
        command,
    ):
        return True
    parts = tokens(command)
    push_at = None
    for n, p in enumerate(parts):
        if p == "push" and n > 0 and (parts[n - 1] == "git" or parts[n - 1].endswith("/git")):
            push_at = n
            break
    if push_at is None:
        return False
    args = [p for p in parts[push_at + 1 :] if not p.startswith("-")]
    refs = args[1:] if args else []
    return any(is_protected_ref(r) for r in refs)


def gh_forbidden(command: str) -> str | None:
    if re.search(r"\bgh\s+pr\s+merge\b", command):
        return "gh pr merge is blocked. jexreffy approves and merges."
    if re.search(r"\bgh\s+merge\b", command):
        return "gh merge is blocked. jexreffy approves and merges."
    if re.search(r"\bgh\s+pr\s+review\b", command) and re.search(r"--approve\b", command):
        return "gh pr review --approve is blocked. jexreffy approves."
    if re.search(r"--auto(?:-merge)?\b", command) and re.search(r"\bgh\s+pr\b", command):
        return "GitHub auto-merge is blocked. jexreffy merges."
    return None


def merge_or_rebase_on_protected(command: str, cwd: str) -> str | None:
    head = git(cwd, "rev-parse", "--abbrev-ref", "HEAD")
    if head not in PROTECTED:
        return None
    if re.search(r"\bgit\b(?:\s+[^\n]+)?\s+merge\b", command):
        return f"git merge while on {head} is blocked. Use a feature branch and a PR."
    if re.search(r"\bgit\b(?:\s+[^\n]+)?\s+rebase\b", command):
        return f"git rebase while on {head} is blocked."
    if has_git_commit(command):
        return f"git commit on {head} is blocked. Branch first."
    if has_git_push(command) and implicit_push_of_current(command):
        return f"git push from {head} is blocked."
    return None


def implicit_push_of_current(command: str) -> bool:
    """True when the command would push the current branch (no other refspec)."""
    parts = tokens(command)
    push_at = None
    for n, p in enumerate(parts):
        if p == "push" and n > 0 and (parts[n - 1] == "git" or parts[n - 1].endswith("/git")):
            push_at = n
            break
    if push_at is None:
        return False
    args = [p for p in parts[push_at + 1 :] if not p.startswith("-")]
    if len(args) <= 1:
        return True
    refs = args[1:]
    return any(r == "HEAD" or r.startswith("HEAD:") for r in refs)


def secret_in_add(command: str) -> str | None:
    if not has_git_add(command):
        return None
    for tok in tokens(command):
        if tok.startswith("-"):
            continue
        if SECRET_RE.search(tok.replace("\\", "/")):
            if tok.endswith(".example") or tok.endswith(".env.example"):
                continue
            if re.fullmatch(r"\.env\.example", tok.split("/")[-1] or ""):
                continue
            return f"Refusing to git add secret or machine-local path: {tok}"
    return None


def secret_staged(cwd: str) -> str | None:
    names = git(cwd, "diff", "--cached", "--name-only")
    if not names:
        return None
    for line in names.splitlines():
        path = line.replace("\\", "/")
        if path.endswith(".env.example"):
            continue
        if SECRET_RE.search(path) or path == ".env" or path.startswith(".env."):
            if path.endswith(".example"):
                continue
            return f"Refusing commit; staged secret or local data: {path}"
    return None


def main() -> None:
    try:
        data = load()
    except json.JSONDecodeError:
        deny("Git/GitHub policy hook could not parse its input.")
        return

    command = str(data.get("command") or "")
    cwd = cwd_of(data)

    reason = gh_forbidden(command)
    if reason:
        deny(reason)

    if push_targets_protected(command):
        deny("Push to main/staging/development is blocked. Use a feature branch and a PR.")

    reason = merge_or_rebase_on_protected(command, cwd)
    if reason:
        deny(reason)

    reason = secret_in_add(command)
    if reason:
        deny(reason)

    if has_git_commit(command):
        reason = secret_staged(cwd)
        if reason:
            deny(reason)

    out("allow")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        deny(f"Git/GitHub policy hook error: {exc}")
