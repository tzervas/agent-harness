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


#: What each stage is for, and what it must not do.
STAGE_MISSION: dict[str, str] = {
    "plan": (
        "## Your stage: PLAN\n\n"
        "Produce a plan. **Do not modify, create, or delete any code.** Read enough\n"
        "of the repo to be concrete, then write the plan into the handoff file:\n\n"
        "- the exact files you would change, and what changes\n"
        "- the order of operations, and what each step is verified by\n"
        "- the risks, and what would falsify your approach\n"
        "- anything you discovered that makes the stated task wrong or incomplete\n\n"
        "A plan that says 'investigate further' is not a plan. If the task cannot be\n"
        "planned as stated, say exactly why and stop — that is a useful result."
    ),
    "implement": (
        "## Your stage: IMPLEMENT\n\n"
        "**Read the handoff file first — it contains the plan.** Execute it. Deviate\n"
        "from the plan only where it is actually wrong, and record any deviation and\n"
        "its reason in the handoff.\n\n"
        "Make the change, run the gate, and only then claim success."
    ),
    "verify": (
        "## Your stage: VERIFY\n\n"
        "Independently check the work of the previous stage. **Do not fix what you\n"
        "find** — report it. Run the gate yourself rather than trusting the handoff.\n\n"
        "Confirm the change does what the task asked, that the gate genuinely passes,\n"
        "and that nothing outside the leased component was touched. A verification\n"
        "that rubber-stamps a broken change is worse than no verification at all."
    ),
}


def build_autoprompt(
    unit: WorkUnit,
    *,
    handoff_dir: str | Path,
    agent_name: str,
    coop_home: str = "",
    attempt: int = 1,
    prior_error: str = "",
    stage: str = "implement",
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

    if stage == "plan":
        done_block = (
            "The plan is written to the handoff file and is concrete enough that the\n"
            "next session can execute it without rediscovering the problem. Do not run\n"
            "the validation gate — you changed nothing."
        )
    else:
        done_block = (
            "Run the validation gate and let it pass before you claim success:\n\n"
            f"    {unit.validate}"
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

{STAGE_MISSION.get(stage, STAGE_MISSION["implement"])}
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

{done_block}

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
