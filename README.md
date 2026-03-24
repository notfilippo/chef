# chef

Compose agentic workflows as recipes — pipelines of operators that pass contexts through Claude.

## Install

```bash
uv tool install --from git+https://github.com/notfilippo/chef chef
```

Requires: [`claude`](https://github.com/anthropics/claude-code) CLI and [`gh`](https://cli.github.com/) CLI (for GitHub operators).

## Usage

```bash
chef '<recipe>'
chef --from <checkpoint-uuid> '<recipe>'
```

A recipe is a sequence of operators separated by `|`. Each operator receives a list of contexts and produces a new list.

## Operators

### Sources (must be first)

| Operator | Description |
|---|---|
| `text "a" "b"` | Create contexts from literal strings |
| `gh_pr_comments "URL"` | Fetch unresolved PR review comments from GitHub |
| `stdin` | Read one context per line from stdin |
| `stdin "sep"` | Read from stdin, splitting on a custom separator instead of newlines |
| _(use `--from <uuid>`)_ | Resume from an auto-saved checkpoint |

### Transforms

| Operator | Description |
|---|---|
| `map "prompt"` | Run Claude on each context in parallel (uses worktree pool) |
| `reduce "prompt"` | Merge all contexts into one with Claude |
| `fork N` | Duplicate each context N times |
| `fork "a" "b"` | Fork into variants, appending each string |
| `apply` | Apply all context diffs to the local working tree; opens configured `git difftool` if available |
| `review` | Interactively review contexts one by one with keyboard controls |

`review` displays each context (and its diff, if any) then waits for a keypress:

| Key | Action |
|---|---|
| `e` | Open `$EDITOR` to edit the context value |
| `d` | Open `git difftool` to edit the diff in a temporary worktree (shown only when a diff is present) |
| `y` / Enter | Keep and advance to the next context |
| `n` | Discard this context |

## Examples

### Address PR review comments

Fetch unresolved comments, let Claude fix each one in parallel, review the diffs, then apply:

```bash
chef 'gh_pr_comments "https://github.com/owner/repo/pull/42" | map "Address this review comment" | review | apply'
```

### Explore multiple implementations

Fork a task into variants, implement each in an isolated worktree, pick one, apply:

```bash
chef 'text "refactor the auth module" | fork "use JWT" "use sessions" | map "implement this approach" | review | apply'
```

### Bulk edits from stdin

Pipe file paths in, edit each one, apply all at once:

```bash
fd '\.go$' | chef 'stdin | map "add missing error handling" | apply'
```

## Worktree pool

`map` runs each context in an isolated git worktree so that parallel Claude sessions can edit files without interfering with each other or with your working tree.

Worktrees are pooled at `~/.cache/chef/worktrees/` and reused across runs. When `map` needs a worktree it scans the pool for a free one tied to the same repository, resets it to `HEAD` (`git reset --hard` + `git clean -fd`), and locks it for the duration of the task. If none is free a new worktree is created with `git worktree add --detach`. On completion the lock is released and the worktree goes back into the pool — it is never deleted.

This means the first run for a given repo may be slower (worktree creation), while subsequent runs reuse existing ones.

## Checkpoints

After every operator step chef saves the current list of contexts to `~/.cache/chef/checkpoints/<uuid>.json`. At the end of a run the UUIDs are printed alongside the step that produced them:

```
─────────────────── checkpoints ───────────────────
 a1b2c3d4   map "Address this review comment"
 e5f6a7b8   review
```

Pass any UUID to `--from` to resume a pipeline from that point:

```bash
# Skip re-running map; jump straight to apply
chef --from e5f6a7b8 'apply'

# Continue with a different follow-up step
chef --from a1b2c3d4 'reduce "summarise all changes"'
```

Checkpoints are never cleaned up automatically — remove `~/.cache/chef/checkpoints/` manually if disk space is a concern.
