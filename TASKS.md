# Boxwatch backlog

The shared board for every session. Statuses: Ready -> In progress -> Review -> Done.
A ticket owns the files/functions it lists; two tickets in progress must never own the same thing.

Template:

    ### T-<n>: <title>
    Status: Ready | In progress (branch) | Review (branch) | Done
    Owns: <files, and for index.html the function or section names>
    Blocked by: <ticket or "none">
    Why: <one or two lines>
    Done when:
    - [ ] <something a reviewer can check without asking anyone>

## Ready

### T-4: Harden build_demo.py edge cases
Status: Ready
Owns: scripts/build_demo.py (a comment and one guard); tests/test_build_demo.py
Blocked by: none
Why: T-3's reviewer found a hand-picked game with no box size would crash the build, a comment says ~80% full where the setting is 72%, and the checked-out game and per-game placement overrides have no tests.
Done when:
- [ ] A hand-picked game with no dimensions gives a clear error naming the game, not a crash, with a test
- [ ] The fill comment matches the real setting
- [ ] Tests cover the checked-out game and one placement override
- [ ] The rebuilt demo-data.json is unchanged

## In progress

## Review

## Done

### T-1: Pick a better category than the first alphabetical tag
Status: Done (merged ticket/T-1-category, b407950)
Owns: server.py `parse_thing_item`; scripts/build_catalog.py category field; tests/test_parsers.py
Blocked by: none
Why: Category is the first tag BGG lists (alphabetical), so games often get a period
or theme ("Ancient") instead of a genre ("Card Game").
Done when:
- [ ] A documented preference list of genre-like categories is used before falling back to the first tag
- [ ] 7 Wonders Duel ("Ancient", "Card Game") gets "Card Game" in a unit test
- [ ] Existing saved games are unaffected until they're refreshed

### T-2: Run the checks on every push and pull request
Status: Done (merged ticket/T-2-ci, 8401f4d)
Owns: .github/workflows/check.yml (new file only; don't touch pages.yml)
Blocked by: none
Why: The Stop hook only guards local sessions. CI makes the same check visible on GitHub.
Done when:
- [ ] Workflow runs `python scripts/check.py` on push and pull_request, Python 3.12, no installs
- [ ] README has a one-line status badge for it

### T-3: Test the data builders offline
Status: Done (merged ticket/T-3-demo-tests, f0e42e8)
Owns: tests/test_build_demo.py (new); scripts/build_demo.py only if a function must be split out to be testable
Blocked by: none
Why: build_demo.py writes what the public sees. It has no tests.
Done when:
- [ ] Tests build a demo from a tiny fake catalog with no network
- [ ] They check every demo game comes from the catalog and `demoVersion` changes when the games change
