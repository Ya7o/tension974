import logging
import requests
from ..models import FetchResult
from .base import FetchProvider

logger = logging.getLogger("tension974.firecrawl")

_CREDITS_URL = "https://api.firecrawl.dev/v1/team/credit-usage"


class FirecrawlProvider(FetchProvider):
    """Firecrawl-based fetch provider (v2 API via firecrawl-py SDK)."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from firecrawl import Firecrawl
                self._client = Firecrawl(api_key=self._api_key)
            except ImportError as exc:
                raise RuntimeError("firecrawl-py is not installed. Run: pip install firecrawl-py") from exc
        return self._client

    @property
    def name(self) -> str:
        return "firecrawl"

    def get_account_credits(self) -> dict:
        """Return remaining and plan credits from the Firecrawl account."""
        try:
            resp = requests.get(
                _CREDITS_URL,
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("success"):
                return data["data"]
            return {"error": data.get("message", "Unknown error")}
        except Exception as exc:
            logger.error("Credits fetch error: %s", exc)
            return {"error": str(exc)}

    def test_api_key(self) -> tuple[bool, str]:
        """Validate the API key by fetching account credits. Returns (ok, message)."""
        result = self.get_account_credits()
        if "error" in result:
            return False, f"Clé invalide ou erreur réseau : {result['error']}"
        remaining = result.get("remaining_credits")
        plan = result.get("plan_credits")
        return True, f"Clé valide — {remaining} crédits restants sur {plan}"

    def fetch(self, url: str) -> FetchResult:
        client = self._get_client()
        logger.info("Firecrawl fetch: %s", url)
        try:
            result = client.scrape(url, formats=["markdown", "html"])

            markdown = ""
            html = ""
            metadata = {}

            if isinstance(result, dict):
                markdown = result.get("markdown") or ""
                html = result.get("html") or ""
                metadata = result.get("metadata") or {}
            else:
                markdown = getattr(result, "markdown", "") or ""
                html = getattr(result, "html", "") or ""
                metadata = getattr(result, "metadata", {}) or {}

            # SDK returns a DocumentMetadata object, not a dict — use getattr
            if isinstance(metadata, dict):
                credits_used = metadata.get("credits_used") or metadata.get("creditsUsed")
                meta_dict = metadata
            else:
                credits_used = getattr(metadata, "credits_used", None)
                meta_dict = {}

            content = markdown if markdown else html
            logger.debug("Firecrawl response: %d chars, %s credit(s) used", len(content), credits_used)

            return FetchResult(
                success=True,
                content=content,
                content_type="markdown" if markdown else "html",
                provider=self.name,
                status_code=200,
                credits_used=int(credits_used) if credits_used is not None else None,
                raw_metadata=meta_dict,
            )

        except Exception as exc:
            logger.error("Firecrawl error: %s", exc)
            return FetchResult(
                success=False,
                content="",
                provider=self.name,
                error_message=str(exc),
            )
