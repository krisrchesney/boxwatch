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
