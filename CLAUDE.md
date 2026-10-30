# Boxwatch: rules for every Claude session and agent

Boxwatch plans board game shelving from BoardGameGeek data. `server.py` is a
Python-stdlib server (BGG proxy + local save). `index.html` is the whole front end
in one file, plain JS, no build step. The public demo is GitHub Pages.

## Workflow
- Work comes from TASKS.md. Take one ticket, move it to "In progress" with your
  branch name, and only touch the files/functions that ticket owns.
- Builders work in their own git worktree and branch (`ticket/T-<n>-<slug>`), never on main.
- `python scripts/check.py` must pass before you say a ticket is done. A Stop hook
  runs it automatically.
- When done: commit on your branch, set the ticket to "Review", and say so. Don't
  merge to main or push. The user merges after the `reviewer` agent approves.
- Never delete, skip or loosen a test, or edit scripts/check.py or .claude/hooks/,
  to make the check pass, unless the ticket says to. Fix the code instead.
- When a ticket is approved, report in one line what went wrong or what the
  reviewer caught, so it can be added to "Lessons" below.
- Models: Sonnet 5.5 is the default for every session and agent. Use Opus only
  after asking the user and getting a yes, and say why (e.g. a reviewer's ESCALATE
  line, or a task Sonnet has failed twice). Never switch to Opus on your own.
- Runs on the user's Claude subscription. Report usage (tokens, turns, time), not dollars.
- See docs/AGENT-WORKFLOW.md for how the pieces fit together.

## Conventions
- Python: standard library only. No pip installs, no new dependencies.
- index.html stays a single file. Match the existing style of the function you're in.
- Saved data lives in the visitor's localStorage. A change to the saved shape must
  still load an older save (or bump `demoVersion` via scripts/build_demo.py).
- UI words: "complexity" (never "weight") for BGG's 1-5 rules rating.
- Shelf titles stay a fixed 13px.

## Never
- Commit `bgg_token.txt`, `boxwatch-data.json`, or anything from the user's own collection.
- Copy BGG cover images into the repo. Covers are hotlinked from BGG's CDN only.
- Remove the BGG credit footer or `powered-by-bgg.png` from public pages, or alter BGG data values.
- Use BGG data for AI training, or add anything commercial.

## Command Center asks (read at the start of every turn)
This project is tracked on the user's Command Center Projects tab as `devprojects/boxwatch` in
the private Command Center artifact (its link is in D:/Users/Kao/Claude/CommandCenter/CLAUDE.md) (load ArtifactData with ToolSearch "select:ArtifactData").
- At the start of each turn, read that doc and every `devdecisions` doc whose `project` is "boxwatch".
  Those are the user's clicks on its asks: approved, declined, done, snoozed, or an `answer`.
- Treat an approved or answered ask as the user's own answer for routine local work and act on it.
  For anything public or that uses a secret (pushing, creating a repo, publishing, tokens), confirm
  once in chat first and say the page approval was seen.
- When done, update the ask in `devprojects/boxwatch` pinned with `if_version`: copy the status and
  answer, set `handledAt` and `handledBy`, and note the result in `lastActivity`. Add an ask there when
  you need something only the user can give, and append a `usage` entry when a run finishes.
- Full rules: D:\Users\Kao\Claude\CommandCenter\CLAUDE.md, rule `cc-projects-status`. Never put
  secrets or tokens in the database.

## Lessons
One line per finished ticket: what went wrong or what review caught. Added on
main by the session that merges (not by builders, so branches don't conflict).
Read these before starting a ticket.
- T-1: the reviewer found nothing, but the risk was cached catalog entries losing their genre when the category list is cut to three, so a test now covers it. When a ticket can't edit index.html, reordering the data so the first item is the right one avoids touching it.
- T-2: CI is only proven once pushed. Pin real action versions (checked: checkout v7, setup-python v7).
- T-3: a "version changes" test passed only because the game order changed (auto-fill re-added the swapped game). Check the inputs really differ before comparing outputs.
- Start builder sessions inside the repo folder. Sessions started elsewhere don't load the project's agents or the Stop hook, so the builder had to run the reviewer and checks by hand.
- T-4: the reviewer approved with nothing to fix, but the test-writer's tests failed first (KeyError/IndexError on a game with no dims), which proved the guard was needed; a guard placed before the first use of the data is the minimal fix. A comment that quotes a setting (72%) goes stale, so name the constant instead.
- Auto-arrange all once stranded games although earlier cubes had room: it only ever moved forward from the last cube it used ("next-fit"), so a game too thick for the remaining cubes was reported as not fitting. It now goes back over earlier cubes before giving up. index.html has no JS tests, so check layout changes in a browser: set "Lying flat" on the demo and confirm no "didn't fit anywhere" alert.
