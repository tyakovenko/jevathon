"""Doc research via Browserbase headless browsers. Scraping only — ticket updates go through the GitHub API.

Real adapter not built: pick Browserbase Python SDK + Playwright, or Stagehand (Python), and implement
`search_and_fetch`. Internal-docs scraping needs the internal docs' URLs/auth — see docs §13.
"""

from typing import Protocol

from pydantic import BaseModel


class Page(BaseModel):
    url: str
    title: str
    text: str


class Browserbase(Protocol):
    async def search_and_fetch(self, query: str) -> list[Page]: ...


class RealBrowserbase:
    def __init__(self, api_key: str, project_id: str) -> None:
        raise NotImplementedError("Browserbase real adapter not built yet (docs §9, M6)")

    async def search_and_fetch(self, query: str) -> list[Page]:  # pragma: no cover
        raise NotImplementedError


class FakeBrowserbase:
    def __init__(self) -> None:
        self.queries: list[str] = []

    async def search_and_fetch(self, query: str) -> list[Page]:
        self.queries.append(query)
        return [Page(url=f"https://example.invalid/fake?q={len(self.queries)}", title=f"[fake] {query}", text=f"[fake page for] {query}")]
