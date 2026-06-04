from __future__ import annotations

import httpx


class TavilyClient:
    async def search(self, *, api_key: str, query: str, max_results: int = 5) -> dict:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": api_key,
                    "query": query,
                    "max_results": max_results,
                    "include_answer": True,
                    "search_depth": "advanced",
                },
            )
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("invalid tavily response")
        return payload

