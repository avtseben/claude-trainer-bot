"""Рендер HTML-артефактов в PNG через headless Chromium."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from playwright.async_api import Browser, Playwright, async_playwright

log = logging.getLogger(__name__)

# Ограничения Telegram для sendPhoto: сумма сторон <= 10000, соотношение <= 20.
PHOTO_MAX_SIDES_SUM = 10_000
PHOTO_MAX_RATIO = 20


class Renderer:
    def __init__(self, width: int = 800, scale: int = 2):
        self.width = width
        self.scale = scale
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._lock = asyncio.Lock()

    async def _ensure_browser(self) -> Browser:
        if self._browser is None or not self._browser.is_connected():
            self._playwright = self._playwright or await async_playwright().start()
            self._browser = await self._playwright.chromium.launch()
        return self._browser

    async def render(self, html: Path, width: int | None = None) -> tuple[Path, bool]:
        """Возвращает путь к PNG и признак, влезает ли картинка в sendPhoto."""
        async with self._lock:
            browser = await self._ensure_browser()
            page = await browser.new_page(
                viewport={"width": width or self.width, "height": 100},
                device_scale_factor=self.scale,
            )
            try:
                await page.goto(html.as_uri(), wait_until="networkidle")
                # Дать отработать шрифтам и JS-графикам.
                await page.evaluate("document.fonts.ready")
                await page.wait_for_timeout(300)
                out = html.with_suffix(".png")
                await page.screenshot(path=str(out), full_page=True)
                size = await page.evaluate(
                    "({w: document.documentElement.scrollWidth, h: document.documentElement.scrollHeight})"
                )
            finally:
                await page.close()

        w, h = size["w"] * self.scale, size["h"] * self.scale
        fits_photo = w + h <= PHOTO_MAX_SIDES_SUM and max(w, h) / max(min(w, h), 1) <= PHOTO_MAX_RATIO
        log.info("Отрендерен %s (%dx%d, photo=%s)", out.name, w, h, fits_photo)
        return out, fits_photo

    async def close(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
