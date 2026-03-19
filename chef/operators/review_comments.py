import json
import re
import subprocess

from rich.console import Console

from ..context import Context

console = Console(stderr=True)


def _build_query(owner: str, repo: str, number: str, cursor: str | None) -> str:
    after = f', after: "{cursor}"' if cursor else ""
    return f"""
    query {{
      repository(owner: "{owner}", name: "{repo}") {{
        pullRequest(number: {number}) {{
          reviewThreads(first: 100{after}) {{
            pageInfo {{ hasNextPage endCursor }}
            nodes {{
              isResolved
              comments(first: 100) {{
                nodes {{
                  author {{ login }}
                  path
                  line
                  originalLine
                  body
                  url
                }}
              }}
            }}
          }}
        }}
      }}
    }}
    """


def _fetch_review_threads(owner: str, repo: str, number: str) -> list[dict]:
    threads = []
    cursor = None
    while True:
        result = subprocess.run(
            [
                "gh",
                "api",
                "graphql",
                "-f",
                f"query={_build_query(owner, repo, number, cursor)}",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(result.stdout)
        review_threads = data["data"]["repository"]["pullRequest"]["reviewThreads"]
        threads.extend(review_threads["nodes"])
        if not review_threads["pageInfo"]["hasNextPage"]:
            break
        cursor = review_threads["pageInfo"]["endCursor"]
    return threads


def review_comments_op(contexts: list[Context], url: str) -> list[Context]:
    assert not contexts, (
        "review_comments is a source operator and must be first in the pipeline"
    )
    assert url, "missing PR URL argument"
    m = re.search(r"github\.com/([^/]+)/([^/]+)/pull/(\d+)", url)
    assert m, f"cannot parse GitHub PR URL: {url!r}"
    owner, repo, number = m.group(1), m.group(2), m.group(3)

    console.print(f"[dim]fetching review comments for {owner}/{repo}#{number}[/dim]")
    comments = []
    for thread in _fetch_review_threads(owner, repo, number):
        if thread["isResolved"]:
            continue
        for node in thread["comments"]["nodes"]:
            body = node["body"].strip()
            if not body:
                continue
            line = node["line"] or node["originalLine"]
            value = (
                f"**Author:** {node['author']['login']}  \n"
                f"**File:** {node['path']} (line {line})  \n"
                f"**Link:** [view comment]({node['url']})\n\n"
                f"{body}"
            )
            comments.append(Context(value))
    console.print(f"[dim]found {len(comments)} unresolved comment(s)[/dim]")
    return comments
