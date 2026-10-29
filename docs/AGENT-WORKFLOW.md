# How the agent workflow works

This repo is set up so several Claude sessions can work on it at once without
stepping on each other or shipping broken code. None of it is magic. Every piece
is a plain file you can read and change.

## The loop

```
 you: "I want X"
   │
   ▼
 planner agent ──writes──► TASKS.md (tickets with "Owns" + "Done when")
   │
   ▼
 builder sessions, one per ticket, each in its own worktree/branch
   │   (optional: test-writer agent writes the tests first)
   │   Stop hook runs scripts/check.py; a builder can't say "done" while it fails
   ▼
 reviewer agent (read-only, fresh context) ──► APPROVE / CHANGES NEEDED
   │                                             │
   │                                             └─► back to that ticket's builder
   ▼
 you merge the branch to main
```

You stay the prioritizer and the person who merges. The agents do the work in between.

## The pieces, and why each one exists

| File | What it is | Why |
|---|---|---|
| `CLAUDE.md` | Loaded into **every** session and agent automatically. | Puts the rules (no secrets, BGG terms, stdlib only) in one place so you don't repeat them in every prompt. |
| `TASKS.md` | The shared backlog. | Agents don't message each other; they coordinate through this file and git, like a team uses a ticket board. "Owns" stops two builders from editing the same function. |
| `.claude/agents/planner.md` | Subagent: idea → tickets. Opus. Can't touch app code. | Splitting work so it really can run in parallel is the hardest part, so it gets the strongest model. |
| `.claude/agents/test-writer.md` | Subagent: writes tests from "Done when". Sonnet. Edits only `tests/`. | Tests written from the spec, not from the code, catch the builder's misreadings. A cheaper model is fine here. |
| `.claude/agents/reviewer.md` | Subagent: read-only review of one branch. Opus. | The author of code is the worst reviewer of it. A clean context with no edit tools can only judge. |
| `scripts/check.py` | One command: compile all Python + run `tests/`. | Gives every agent and you the same definition of "healthy". |
| `.claude/settings.json` + `.claude/hooks/check_on_stop.py` | A **Stop hook**: when Claude tries to end its turn, the harness runs the check. If it fails, exit code 2 sends the failure back and Claude keeps working. | Turns "I think it works" into "the tests passed". The harness enforces this, so the model can't skip it. It lets Claude stop on the second try so a check it can't fix never loops forever. |
| `tests/` | Parser tests and repo-hygiene tests (demo only uses catalog games, BGG credit present, secrets not tracked). | The hygiene tests make the CLAUDE.md "Never" list machine-checked. |

**Subagent vs. session.** A *subagent* (the `.md` files) runs inside a session,
does one job in its own context and hands back a summary. A *session* is a full
conversation you can watch and steer. Builders are sessions because you'll want to
look in on them. Planner and reviewer are subagents because they do one job and report back.

**Worktree.** A second checkout of the same repo in another folder, on its own
branch. Two builders in two worktrees can both edit `index.html` without
overwriting each other. Git sorts it out at merge time, and "Owns" keeps those
merges clean.

## Running it (desktop app)

1. **Plan.** In a session in this repo:
   > Use the planner agent to turn this into tickets: <your idea>
2. **Build in parallel.** For each Ready ticket, start a new session with a worktree and say:
   > Take T-2 from TASKS.md.
   Two or three at once is plenty.
3. **Review.** When a builder says it's in Review:
   > Use the reviewer agent on T-2, branch ticket/T-2-ci.
   If it says CHANGES NEEDED, paste the findings back into that builder's session.
4. **Merge.** You merge the approved branch (or ask a session to, and watch it).
   Move the ticket to Done.

Optional: start a ticket with "use the test-writer agent on T-3 first", then build until those tests pass.

## Running it from the CLI or on a schedule

The same files work in the terminal `claude` CLI. Run it from this folder.
Headless one-shots are how you'd automate pieces later:

```
claude -p "Use the reviewer agent on branch ticket/T-2-ci and print its verdict"
```

T-2 (the CI ticket) brings the same check to GitHub so it runs on every push.

## Guardrails borrowed from the literature

These come from the Databricks *Guide to Agentic Systems* and Roitman's
*Hitchhiker's Guide to Agentic AI* (arXiv 2606.24937, ch. 19 and 26).

- **The model that does the work never judges it.** Deterministic checks (the
  hook) come first, and the separate reviewer covers what tests can't.
- **Gaming the checks.** The easiest way for an agent to turn a failing check green is
  to delete or loosen the test. CLAUDE.md forbids it, and the reviewer rejects
  any weakened test or edited check/hook unless the ticket asks for it.
- **Comprehension debt.** Agents can change code faster than you understand it.
  Read each diff before merging, not just the reviewer's verdict. Run 2-3 builders, not 10.
- **Cost caps.** Check a session's usage when it finishes. Any unattended
  `claude -p` job gets `--max-turns` (and a budget flag if your CLI version has
  one; check `claude --help`), so a stuck loop can't run all night.
- **Learning between runs.** Each approved ticket adds one line to "Lessons" in
  CLAUDE.md, which every later session reads. That's the cheap version of agent memory.

## Known gaps

- The front end's logic (shelf layout etc.) is JavaScript inside index.html, and
  there's no Node here, so nothing tests it yet. That's the next good ticket once
  Node is installed, or the layout code could be pulled into its own .js file.
- `check.py` is only as strong as `tests/`. A reviewer that approves against
  weak tests is still guessing.
