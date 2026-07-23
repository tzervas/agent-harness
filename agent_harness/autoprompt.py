"""Build the prompt handed to an ephemeral session.

This is the *autoprompt* half of the harness. A spawned session gets no
conversational history, so everything it needs to behave correctly has to be in
this one string: the task, the coordination discipline, the exit contract, and the
handoff obligation.

The prompt deliberately tells the session it is **short-lived**. Issue #24 inverts
the old model: instead of fighting context exhaustion, a session takes one unit,
finishes it, writes a handoff, and dies.
"""

from __future__ import annotations

from pathlib import Path

from agent_harness.units import WorkUnit

#: Kept well inside provider CLI argv limits.
MAX_PROMPT_CHARS = 8000


def handoff_path_for(unit: WorkUnit, handoff_dir: str | Path) -> Path:
    """Where this unit's successor will look for context."""
    return Path(handoff_dir) / f"{unit.uid}.md"


def build_autoprompt(
    unit: WorkUnit,
    *,
    handoff_dir: str | Path,
    agent_name: str,
    coop_home: str = "",
    attempt: int = 1,
    prior_error: str = "",
) -> str:
    """Render the full instruction set for one ephemeral session."""
    handoff = handoff_path_for(unit, handoff_dir)
    issue_line = f"  issue:     #{unit.issue}\n" if unit.issue else ""
    cwd_line = f"  cwd:       {unit.cwd}\n" if unit.cwd else ""

    retry_block = ""
    if attempt > 1:
        retry_block = (
            f"\n## This is attempt {attempt}\n\n"
            f"A previous session failed on this exact unit. Its error was:\n\n"
            f"    {prior_error or '(no error recorded)'}\n\n"
            "Read the handoff file before doing anything else, and do not blindly\n"
            "repeat the previous approach. If the unit is genuinely blocked, say so\n"
            "and stop — an honest block beats a third identical failure.\n"
        )

    env_block = ""
    if coop_home:
        env_block = (
            "\n```bash\n"
            'export PATH="$HOME/.local/bin:$PATH"\n'
            f"export AGENT_COOP_HOME={coop_home}\n"
            f"export AGENT_COOP_AGENT={agent_name}\n"
            "export AGENT_COOP_ENV=/dev/null\n"
            "```\n"
        )

    prompt = f"""You are an ephemeral worker session spawned by agent-harness.

You exist to complete exactly ONE unit of work, record the result, and exit. You
will not be asked a follow-up question. Nothing will wake you again.

## Your unit

  uid:       {unit.uid}
  repo:      {unit.repo}
  component: {unit.component}
{issue_line}{cwd_line}  lane:      {unit.lane}

## Task

{unit.task.strip()}
{retry_block}
## Coordination discipline (non-negotiable)

The lease on `{unit.key}` has already been claimed for you by the supervisor. It
has a TTL. Within that scope you may write freely. Outside it you may not.

- Before writing any file outside `{unit.component}`, claim its lease first.
- `coop lease claim` exiting **3** means another agent holds it. That is a
  back-off signal, not a race to win. Do not retry, do not steal, do not wait in a
  loop. Re-scope your work or stop.
- Peek the bus before acting; drain only messages you actually handled.
- Never release a lease you did not claim.
{env_block}
## Definition of done

Run the validation gate and let it pass before you claim success:

    {unit.validate}

Report honestly. A failing gate reported as failing is a useful result. A failing
gate reported as passing poisons every downstream decision.

## Before you exit — write the handoff

Your context is a work boundary, not an outage. Write what your successor needs to
`{handoff}` as markdown:

- what you actually changed (paths, not prose)
- what you verified, and the command output that proves it
- what is left, and the single next action you would take
- anything you learned that is not obvious from the diff

Keep the payload in that file. The bus message is a pointer to it, never the
payload itself.

## Exit contract

Exit 0 only if the unit is genuinely complete and the gate passed. Exit non-zero
otherwise. Your exit code is the signal the supervisor acts on, so do not dress up
a failure as a success.
"""
    return _clamp(prompt)


def _clamp(text: str, limit: int = MAX_PROMPT_CHARS) -> str:
    """Bound the prompt so an oversized task cannot blow the argv limit."""
    if len(text) <= limit:
        return text
    head = text[: limit - 80].rstrip()
    return head + "\n\n[prompt truncated by agent-harness to fit the argv limit]\n"


def build_handoff_stub(unit: WorkUnit, *, provider: str, attempt: int) -> str:
    """Seed content written when a session dies without leaving a handoff."""
    return (
        f"# handoff: {unit.uid}\n\n"
        f"- repo: {unit.repo}\n"
        f"- component: {unit.component}\n"
        f"- provider: {provider}\n"
        f"- attempt: {attempt}\n\n"
        "## Status\n\n"
        "The session exited without writing a handoff. Treat everything below the\n"
        "task statement as unverified.\n\n"
        "## Task\n\n"
        f"{unit.task.strip()}\n"
    )
