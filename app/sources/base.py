"""
Source Adapter Base Architecture (Section 9)
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import httpx
from app.normalization.hash import compute_content_hash
from app.normalization.taxonomy import normalize_category


@dataclass
class NormalizedSection:
    category: str  # Canonical category from CANONICAL_CATEGORIES
    content: str
    subcategory: Optional[str] = None
    content_type: str = "STRUCTURED_EXTRACTION"
    audience: str = "patient"
    disagreement_status: str = "CONSISTENT"
    quote_snippet: Optional[str] = None
    source_url: Optional[str] = None
    source_locator: Optional[str] = None


@dataclass
class NormalizedDocument:
    source_id: str
    original_url: str
    canonical_url: str
    title: str
    cancer_slug: str
    source_cancer_name: str
    language: str
    country_code: str
    jurisdiction_scope: str
    content_hash: str
    sections: List[NormalizedSection] = field(default_factory=list)
    published_at: Optional[datetime] = None
    source_updated_at: Optional[datetime] = None
    http_etag: Optional[str] = None
    http_last_modified: Optional[str] = None


class BaseSourceAdapter(ABC):
    """
    Standard interface for all external source adapters (Section 9).
    """
    source_id: str
    organization_name: str
    source_name: str
    base_url: str
    country_code: str
    region: str
    trust_tier: str
    authority_type: str
    license_type: str
    license_status: str
    attribution_text: str

    def __init__(self, timeout: float = 20.0):
        self.timeout = timeout
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "User-Agent": "CancerInfoAPI/1.0 (+https://cancerinfo.org/bot; developer-data-indexing)",
                "Accept": "text/html,application/xhtml+xml,application/json",
            },
            follow_redirects=True,
        )

    async def close(self):
        await self.client.aclose()

    @abstractmethod
    async def discover_urls(self) -> List[Dict[str, str]]:
        """
        Discovers document targets to ingest.
        Returns list of dicts with keys: url, cancer_slug, source_cancer_name.
        """
        pass

    @abstractmethod
    def parse_document(
        self,
        html_content: str,
        url: str,
        cancer_slug: str,
        source_cancer_name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> NormalizedDocument:
        """
        Parses raw HTML/JSON into a standard NormalizedDocument structure.
        """
        pass

    async def fetch_url(self, url: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Fetches URL returning (content, etag, last_modified)
        """
        try:
            resp = await self.client.get(url)
            if resp.status_code == 200:
                etag = resp.headers.get("ETag")
                last_mod = resp.headers.get("Last-Modified")
                return resp.text, etag, last_mod
            return None, None, None
        except Exception:
            return None, None, None
