"""Normalization layer — guarantees every Document conforms to the contract.

Runs after each executor returns. Fills missing fields, stamps domain, ensures
telemetry dict exists. Consumers (parsers, memory, analytics) can assume a
normalized Document.
"""
from urllib.parse import urlparse
from fetcher.base import Document


def normalize(doc: Document) -> Document:
    if not doc.domain and doc.url:
        doc.domain = urlparse(doc.url).netloc
    if doc.telemetry is None:
        doc.telemetry = {}
    if doc.headers is None:
        doc.headers = {}
    # Ensure content/markdown presence is explicit (None is valid)
    return doc


def normalize_list(docs: list) -> list:
    return [normalize(d) for d in docs]
