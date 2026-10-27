# Contributing to FamilyVault

## Branches
- `main` — always deployable. Only updated by Runeet at the end of each sprint.
- `develop` — integration branch. All feature work merges here.
- Never push directly to `main` or `develop`. Always work on your own branch.

## Branch naming
feature/<firstname>-<short-description>
fix/<firstname>-<short-description>

Examples:
feature/riya-cypher-shortestpath
feature/ayushman-r2-upload
fix/anushka-tree-zoom-bug

## Commits
Use conventional prefixes:
feat:  new feature
fix:   bug fix
chore: setup/config/tooling
test:  test-only changes
docs:  documentation only

Example: feat: add shortestPath kinship query

## Pull requests
1. Push your branch, open a PR into `develop` (never into `main`).
2. Write a one-line description: what changed + which contract/endpoint it touches, if any.
3. Tag your reviewer (see pairing below). If your change touches auth, RLS, or
   biometric matching, tag Ayush regardless of the normal pairing.
4. Reviewer responds same working day.
5. Squash-merge once approved. Delete the branch after merging.

## Reviewer pairing
- Runeet <-> Riya        (schema / ID-sync overlap)
- Raghuvendra <-> Anushka (both in /frontend)
- Ayushman -> reviewed by Ayush (security/biometric-sensitive)
- Ayush's own test PRs -> reviewed by the owner of the module being tested

## Folder ownership
/frontend       - Raghuvendra, Anushka
/backend        - Runeet
/graph-service  - Riya
/biometrics     - Ayushman
/contracts      - shared — see below
/tests          - Ayush
/docs           - shared

## Contracts (breaking the dependency chain)
If your work is a dependency for someone else (e.g. Riya's graph API for
Anushka's tree UI, Ayushman's match payload for Raghuvendra's inbox UI),
publish a mock JSON of your response shape in /contracts/ as early as
possible — even before the real implementation is done — and ping the
consumer in Slack the moment it's pushed. Update the file and re-ping
the same day if the shape changes. Silent breaking changes here are the
#1 cause of late-sprint integration issues.

## Environment variables
Never commit credentials. Each service has its own .env / .env.local,
all listed in .gitignore from the first commit. Actual values live in
the shared credentials doc (link pinned in #familyvault-dev).

## main updates
Only Runeet merges develop -> main, at the end of each sprint, after
Ayush confirms that sprint's test items are passing. Each merge is
tagged (sprint-1, sprint-2, ...).