# src/jarvis/tools/browser.py
# ============================================
# Browser Tool — controls Chrome via Playwright
#
# Playwright is a browser automation library.
# It lets JARVIS open URLs, click elements,
# fill forms, scrape text, and take screenshots
# — all programmatically.
#
# headless=False → you SEE the browser open
# headless=True  → browser runs invisibly (faster)
# ============================================

from loguru import logger


class BrowserTool:
    name = "browser"

    # We keep one persistent browser instance
    # so we don't open/close Chrome on every command
    _browser = None
    _playwright = None

    def get_schemas(self) -> dict:
        return {
            "open_url": {
                "type": "function",
                "function": {
                    "name": "open_url",
                    "description": (
                        "Open a URL in Chrome browser. Use this when the user wants to "
                        "visit a website, open a link, or navigate to a page."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "Full URL including https://, e.g. https://google.com",
                            }
                        },
                        "required": ["url"],
                    },
                },
            },
            "scrape_text": {
                "type": "function",
                "function": {
                    "name": "scrape_text",
                    "description": (
                        "Fetch and return the visible text content of a webpage. "
                        "Use this to read articles, get information from a site, "
                        "or summarise a webpage."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "Full URL to scrape",
                            }
                        },
                        "required": ["url"],
                    },
                },
            },
            "take_screenshot": {
                "type": "function",
                "function": {
                    "name": "take_screenshot",
                    "description": (
                        "Take a screenshot of a webpage and save it as a PNG file. "
                        "Returns the file path of the saved screenshot."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "Full URL to screenshot",
                            },
                            "save_path": {
                                "type": "string",
                                "description": "Where to save the PNG file, e.g. C:\\jarvis\\screenshot.png",
                            },
                        },
                        "required": ["url"],
                    },
                },
            },
            "click_element": {
                "type": "function",
                "function": {
                    "name": "click_element",
                    "description": (
                        "On the currently open browser page, click an element "
                        "identified by a CSS selector or visible text."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "selector": {
                                "type": "string",
                                "description": (
                                    "CSS selector (e.g. '#submit-btn', '.nav-link') "
                                    "or visible text of the element (e.g. 'Sign In')"
                                ),
                            }
                        },
                        "required": ["selector"],
                    },
                },
            },
            "fill_form": {
                "type": "function",
                "function": {
                    "name": "fill_form",
                    "description": (
                        "Fill in a text input or textarea on the current page "
                        "with the given value."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "selector": {
                                "type": "string",
                                "description": "CSS selector for the input field",
                            },
                            "value": {
                                "type": "string",
                                "description": "Text to type into the field",
                            },
                        },
                        "required": ["selector", "value"],
                    },
                },
            },
            "get_page_title": {
                "type": "function",
                "function": {
                    "name": "get_page_title",
                    "description": "Get the title of the currently open browser page.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            },
        }

    # ------------------------------------------------------------------
    # INTERNAL: browser lifecycle
    # ------------------------------------------------------------------

    def _get_page(self, headless: bool = False):
        """
        Get or create a Playwright browser page.
        Reuses the existing browser if already open.
        """
        from playwright.sync_api import sync_playwright

        if self._playwright is None:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=headless,
                args=["--start-maximized"],
            )
            logger.info("Chromium browser launched")

        # Always open a new page (tab)
        page = self._browser.new_page()
        return page

    def _close(self):
        """Close the browser cleanly."""
        try:
            if self._browser:
                self._browser.close()
                self._browser = None
            if self._playwright:
                self._playwright.stop()
                self._playwright = None
        except Exception as e:
            logger.warning(f"Browser close error: {e}")

    # ------------------------------------------------------------------
    # TOOL IMPLEMENTATIONS
    # ------------------------------------------------------------------

    def open_url(self, url: str) -> str:
        """Open a URL in a visible Chrome browser window."""
        logger.info(f"open_url: {url}")

        # Add https:// if missing
        if not url.startswith("http"):
            url = "https://" + url

        try:
            page = self._get_page(headless=False)
            page.goto(url, timeout=15000, wait_until="domcontentloaded")
            title = page.title()
            return f"Opened: {title} ({url})"
        except Exception as e:
            logger.error(f"open_url failed: {e}")
            return f"Error opening {url}: {e}"

    def scrape_text(self, url: str) -> str:
        """Fetch and return the visible text of a webpage."""
        logger.info(f"scrape_text: {url}")

        if not url.startswith("http"):
            url = "https://" + url

        try:
            page = self._get_page(headless=True)
            page.goto(url, timeout=15000, wait_until="networkidle")

            # Remove script and style tags for cleaner text
            page.evaluate("""
                document.querySelectorAll('script, style, nav, footer, header')
                    .forEach(el => el.remove())
            """)

            text = page.inner_text("body")
            page.close()

            # Clean up whitespace
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            clean = "\n".join(lines)

            # Cap at 4000 chars
            if len(clean) > 4000:
                clean = clean[:4000] + "\n... (content truncated)"

            return clean
        except Exception as e:
            logger.error(f"scrape_text failed: {e}")
            return f"Error scraping {url}: {e}"

    def take_screenshot(self, url: str, save_path: str = None) -> str:
        """Take a screenshot of a webpage and save it."""
        logger.info(f"take_screenshot: {url}")

        if not url.startswith("http"):
            url = "https://" + url

        if not save_path:
            from pathlib import Path
            import time
            Path("data").mkdir(exist_ok=True)
            save_path = f"data/screenshot_{int(time.time())}.png"

        try:
            page = self._get_page(headless=True)
            page.goto(url, timeout=15000, wait_until="networkidle")
            page.screenshot(path=save_path, full_page=True)
            page.close()
            return f"Screenshot saved: {save_path}"
        except Exception as e:
            logger.error(f"take_screenshot failed: {e}")
            return f"Error taking screenshot: {e}"

    def click_element(self, selector: str) -> str:
        """Click an element on the current page."""
        logger.info(f"click_element: {selector}")
        try:
            if self._browser is None:
                return "Error: no browser is open. Open a URL first."

            page = self._browser.contexts[0].pages[-1]

            # Try CSS selector first, then text
            try:
                page.click(selector, timeout=5000)
            except Exception:
                page.get_by_text(selector).first.click(timeout=5000)

            return f"Clicked: {selector}"
        except Exception as e:
            logger.error(f"click_element failed: {e}")
            return f"Error clicking '{selector}': {e}"

    def fill_form(self, selector: str, value: str) -> str:
        """Fill a form field on the current page."""
        logger.info(f"fill_form: {selector} = {value}")
        try:
            if self._browser is None:
                return "Error: no browser is open. Open a URL first."

            page = self._browser.contexts[0].pages[-1]
            page.fill(selector, value, timeout=5000)
            return f"Filled '{selector}' with '{value}'"
        except Exception as e:
            logger.error(f"fill_form failed: {e}")
            return f"Error filling form: {e}"

    def get_page_title(self) -> str:
        """Get the title of the current page."""
        logger.info("get_page_title called")
        try:
            if self._browser is None:
                return "No browser is currently open."
            page = self._browser.contexts[0].pages[-1]
            return f"Current page: {page.title()} — {page.url}"
        except Exception as e:
            logger.error(f"get_page_title failed: {e}")
            return f"Error getting title: {e}"