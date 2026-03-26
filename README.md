# chef

Compose agentic workflows as shell pipelines — each `ch` invocation runs one operator, passing contexts as JSON between stages.

## Install

```bash
uv tool install --from git+https://github.com/notfilippo/chef chef
```

Requires: [`claude`](https://github.com/anthropics/claude-code) CLI and [`gh`](https://cli.github.com/) CLI (for GitHub operators).

## Usage

```bash
ch <operator> [args...]
```

Operators are chained with shell pipes. Each stage reads contexts from stdin and writes contexts to stdout. If stdin is raw text (not a checkpoint), one context is created per line. If stdout is a terminal the final result is rendered as markdown.

## Shell completions

```bash
# bash — add to ~/.bashrc
source <(ch completions bash)

# zsh — add to ~/.zshrc
source <(ch completions zsh)

# fish — add to ~/.config/fish/config.fish
ch completions fish | source
# or as a file:
ch completions fish > ~/.config/fish/completions/ch.fish
```

## Operators

### Sources

| Operator | Description |
|---|---|
| `checkpoint <uuid>` | Load contexts from a checkpoint |
| `gh_pr_comments "URL"` | Fetch unresolved PR review comments from GitHub |
| `stdin "sep"` | Read from stdin splitting on a custom separator (default: newlines) |

For plain line-delimited input, just pipe text directly — one context per line is created automatically. Use standard shell tools like `echo`, `printf`, or `fd` as sources.

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
ch gh_pr_comments "https://github.com/owner/repo/pull/42" \
  | ch map "Address this review comment" \
  | ch review \
  | ch apply
```

### Explore multiple implementations

Fork a task into variants, implement each in an isolated worktree, pick one, apply:

```bash
echo "refactor the auth module" \
  | ch fork "use JWT" "use sessions" \
  | ch map "implement this approach" \
  | ch review \
  | ch apply
```

### Bulk edits from stdin

Pipe file paths in, edit each one, apply all at once:

```bash
fd '\.go$' | ch map "add missing error handling" | ch apply
```

### Custom separator

```bash
cat notes.txt | ch stdin "---" | ch map "summarize"
```

## Worktree pool

`map` runs each context in an isolated git worktree so that parallel Claude sessions can edit files without interfering with each other or with your working tree.

Worktrees are pooled at `~/.cache/chef/worktrees/` and reused across runs. When `map` needs a worktree it scans the pool for a free one tied to the same repository, resets it to `HEAD` (`git reset --hard` + `git clean -fd`), and locks it for the duration of the task. If none is free a new worktree is created with `git worktree add --detach`. On completion the lock is released and the worktree goes back into the pool — it is never deleted.

This means the first run for a given repo may be slower (worktree creation), while subsequent runs reuse existing ones.

## Checkpoints

After every operator step `ch` saves the current list of contexts to `~/.cache/chef/checkpoints/<uuid>.json` and prints the UUID to stderr. Pipe a checkpoint file into any stage to resume from that point:

```bash
# Skip re-running map; jump straight to apply
ch checkpoint e5f6a7b8 | ch apply

# Continue with a different follow-up step
ch checkpoint a1b2c3d4 | ch reduce "summarise all changes"
```

Checkpoints are never cleaned up automatically — remove `~/.cache/chef/checkpoints/` manually if disk space is a concern.
