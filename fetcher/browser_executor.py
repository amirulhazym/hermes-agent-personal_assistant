"""Browser Executor abstraction.

The Router depends on THIS interface, never on Crawl4AI directly.
Crawl4AI is the CURRENT implementation (executors/crawl4ai_executor.py).
To swap browser engines (new Playwright feature, different engine, regression),
implement BrowserExecutor with a new class and change the factory in router.py.
Router code stays unchanged.
"""
from abc import ABC
from fetcher.base import Executor, Document


class BrowserExecutor(Executor, ABC):
    """Marker + contract for browser-capable executors.

    Router checks `isinstance(exec, BrowserExecutor)` to know an executor can
    render JS, take screenshots, and run browser interactions.
    """

    is_browser: bool = True

    # Browser executors inherit all 8 Executor methods. The abstract methods
    # remain abstract here; the concrete implementation (Crawl4AIExecutor)
    # provides them. No browser-specific method is forced at this layer so the
    # contract stays identical to non-browser executors.
