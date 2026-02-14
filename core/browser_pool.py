"""
Browser Pool - Manages Playwright browser lifecycle for WebMCP.
Lazy initialization: browser only starts when first needed.
Singleton pattern: one browser instance shared across all calls.
"""

import asyncio
import threading


class BrowserPool:
    """Manages a shared Playwright browser instance and page pool."""

    def __init__(self, headless: bool = True, timeout: int = 30):
        self.headless = headless
        self.timeout = timeout * 1000  # Playwright uses milliseconds
        self._playwright = None
        self._browser = None
        self._pages = {}  # url -> page
        self._lock = threading.Lock()
        self._loop = None
        self._thread = None
        self._initialized = False

    def _ensure_event_loop(self):
        """Create a dedicated event loop in a background thread for async Playwright."""
        if self._loop is not None and self._loop.is_running():
            return

        def _run_loop(loop):
            asyncio.set_event_loop(loop)
            loop.run_forever()

        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=_run_loop, args=(self._loop,), daemon=True)
        self._thread.start()

    def _run_async(self, coro):
        """Run an async coroutine on the dedicated event loop and return the result."""
        self._ensure_event_loop()
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=self.timeout / 1000 + 10)

    async def _async_init(self):
        """Initialize Playwright and launch browser (async)."""
        if self._initialized:
            return

        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.headless)
        self._initialized = True

    def _ensure_browser(self):
        """Ensure the browser is initialized (thread-safe, lazy)."""
        with self._lock:
            if not self._initialized:
                self._run_async(self._async_init())

    async def _async_get_page(self, url: str, force_new: bool = False):
        """Get or create a page for the given URL."""
        if not force_new and url in self._pages:
            page = self._pages[url]
            # Check if page is still open
            try:
                if not page.is_closed():
                    return page
            except Exception:
                pass

        # Create new page
        context = await self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/146.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()
        page.set_default_timeout(self.timeout)

        await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
        # Give JS a moment to register WebMCP tools
        await page.wait_for_timeout(2000)

        self._pages[url] = page
        return page

    def get_page(self, url: str, force_new: bool = False):
        """Get or create a page for the given URL (sync wrapper)."""
        self._ensure_browser()
        return self._run_async(self._async_get_page(url, force_new))

    async def _async_close_page(self, url: str):
        """Close a specific page."""
        if url in self._pages:
            page = self._pages.pop(url)
            try:
                if not page.is_closed():
                    await page.context.close()
            except Exception:
                pass

    def close_page(self, url: str):
        """Close a specific page (sync wrapper)."""
        if url in self._pages:
            self._run_async(self._async_close_page(url))

    async def _async_evaluate(self, page, script: str):
        """Evaluate JS on a page."""
        return await page.evaluate(script)

    def evaluate(self, page, script: str):
        """Evaluate JS on a page (sync wrapper)."""
        return self._run_async(self._async_evaluate(page, script))

    async def _async_close(self):
        """Close all pages and the browser."""
        for url in list(self._pages.keys()):
            await self._async_close_page(url)
        
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
        
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
        
        self._initialized = False
        self._browser = None
        self._playwright = None

    def close(self):
        """Close the browser pool and clean up all resources."""
        if self._initialized and self._loop:
            try:
                self._run_async(self._async_close())
            except Exception:
                pass

        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)

        if self._thread:
            self._thread.join(timeout=5)
