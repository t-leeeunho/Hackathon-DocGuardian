---
name: commit-and-push
description: >-
  Smartly stage, commit, and push the current changes in the workspace. USE WHEN
  the user asks to "commit", "commit and push", "save my changes to git", "push
  my work", or similar. The skill inspects the working tree, generates a clear
  Conventional Commits message from the actual diff, stages the changes, commits,
  and pushes to the current branch's upstream. DO NOT USE for destructive history
  operations (force-push, rebase, reset --hard, amending pushed commits).
---

# Commit and Push

Smartly stage, commit, and push the current workspace changes with a generated,
meaningful commit message.

## When to use

- The user says "commit", "commit and push", "push my changes", "save to git".
- After completing a unit of work the user wants persisted to the remote.

## When NOT to use

- History rewriting: `git push --force`, `rebase`, `reset --hard`, amending
  already-pushed commits. These are destructive — confirm with the user first.
- The user explicitly wants to write the commit message themselves.

## Procedure

Run these steps in order. Use the terminal tool for git commands. Do NOT run git
commands in parallel — run one and read its output before the next.

### 1. Inspect the working tree

```powershell
git status --porcelain=v1 --branch
git diff --stat HEAD
```

- If there are no changes (`git status` is empty), tell the user there is nothing
  to commit and stop.
- Note whether the branch has an upstream (look for `origin/<branch>` in the
  status branch line). If there is no upstream, you will need `-u` on push.

### 2. Understand what changed

```powershell
git diff HEAD
```

- Read the actual diff so the commit message reflects real changes, not guesses.
- For new untracked files, also check them:

```powershell
git status --short
```

### 3. Stage the changes

```powershell
git add -A
```

- Use `git add -A` to stage modifications, additions, and deletions.
- If the user named specific files, stage only those instead.

### 4. Generate a Conventional Commits message

Build the message from the diff. Format:

```
<type>(<optional scope>): <concise summary in imperative mood>

<optional body: what changed and why, wrapped at ~72 chars>
```

Allowed `type` values:

- `feat` — new feature or capability
- `fix` — bug fix
- `docs` — documentation only (e.g. README edits)
- `chore` — tooling, config, scaffolding
- `refactor` — code change that neither fixes a bug nor adds a feature
- `test` — adding or updating tests
- `style` — formatting only

Rules:

- Summary line <= 72 characters, imperative mood ("add", not "added").
- Choose the type from the dominant change in the diff.
- Add a short body only when the change is non-trivial.
- Never invent changes that are not in the diff.

### 5. Commit

```powershell
git commit -m "<summary>" -m "<optional body>"
```

If the commit fails due to a pre-commit hook, report the hook output to the user
and fix the underlying issue rather than bypassing with `--no-verify`.

### 6. Push

```powershell
# If the branch already has an upstream:
git push

# If there is NO upstream (new branch):
git push -u origin HEAD
```

### 7. Confirm

Report back briefly:

- The commit message used.
- The branch and remote pushed to.
- The short commit SHA (`git rev-parse --short HEAD`).

## Safety

- Never force-push or rewrite published history without explicit user confirmation.
- Never bypass hooks with `--no-verify` unless the user explicitly asks.
- If pushing fails because the remote is ahead, do NOT force. Tell the user and
  suggest `git pull --rebase` (with their confirmation) before retrying.
