# chef

Compose agentic workflows as recipes — pipelines of operators that pass contexts through Claude.

## Install

```bash
uv tool install .
```

Requires: [`claude`](https://github.com/anthropics/claude-code) CLI and [`gh`](https://cli.github.com/) CLI (for GitHub operators).

## Usage

```bash
chef '<recipe>'
chef --from <checkpoint-uuid> '<recipe>'
```

After each step, a checkpoint is automatically saved to `~/.cache/chef/checkpoints/`. The UUIDs are printed at the end of every run so you can resume any step with `--from`.

A recipe is a sequence of operators separated by `|`. Each operator receives a list of contexts and produces a new list.

## Operators

### Sources (must be first)

| Operator | Description |
|---|---|
| `text "a" "b"` | Create contexts from literal strings |
| `review_comments "URL"` | Fetch unresolved PR review comments from GitHub |
| `stdin` | Read one context per line from stdin |
| _(use `--from <uuid>`)_ | Resume from an auto-saved checkpoint |

### Transforms

| Operator | Description |
|---|---|
| `map "prompt"` | Run Claude on each context in parallel (uses worktree pool) |
| `reduce "prompt"` | Merge all contexts into one with Claude |
| `commit` | Generate a commit message from the diff and commit |
| `commit "hint"` | Same, with a hint to guide the message |
| `fork N` | Duplicate each context N times |
| `fork "a" "b"` | Fork into variants, appending each string |
| `apply` | Apply all context diffs to the local working tree; opens configured `git difftool` if available |
| `confirm` | Interactively review and keep/discard contexts |

## Examples

```bash
# Address PR review comments
chef 'review_comments "https://github.com/owner/repo/pull/42" | confirm | map "Address this review comment"'

# Explore multiple approaches in parallel
chef 'text "refactor the auth module" | fork "use JWT" "use sessions" | map "implement this approach"'

# Resume an interrupted run (UUIDs printed at end of each run)
chef --from abc12345 'reduce "pick the best approach"'

# Pipe from another command
gh pr list --json url -q '.[].url' | chef 'stdin | map "summarize this PR"'
```

## Worktree pool

`map` runs each context in an isolated git worktree. Worktrees are pooled at `~/.cache/chef/worktrees/` and reused across runs (reset to `HEAD` on each acquire).
