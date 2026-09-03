"""Fragrantica adapter — perfume data extraction.

Preferred executor: flaresolverr (Cloudflare Managed). Falls back to curl_cffi
if CF not yet solved (will return UNVERIFIED, router escalates).
"""
import re
from fetcher.adapters.base import Adapter
from fetcher.base import Document


class FragranticaAdapter(Adapter):
    domain = "fragrantica.com"
    preferred_executor = "flaresolverr"
    cache_ttl = 3600

    def extract(self, doc: Document) -> dict:
        if not doc.content:
            return {}
        data = {}
        m = re.search(r'<h1[^>]*class="[^"]*"[^>]*>([^<]+)</h1>', doc.content)
        if not m:
            m = re.search(r"<h1[^>]*>([^<]+)</h1>", doc.content)
        if m:
            data["name"] = m.group(1).strip()
        # Note blocks (perfume notes)
        notes = re.findall(r'class="[^"]*notes[^"]*"[^>]*>([^<]+)<', doc.content)
        if notes:
            data["notes"] = [n.strip() for n in notes]
        # Brand
        brand = re.search(r'class="[^"]*brand[^"]*"[^>]*>([^<]+)<', doc.content)
        if brand:
            data["brand"] = brand.group(1).strip()
        return data

    def validate(self, data: dict) -> bool:
        return bool(data.get("name"))
