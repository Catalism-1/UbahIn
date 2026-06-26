"""Native desktop window setup for the bundled Ubahin WebView UI."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DesktopWindowConfig:
    title: str = "Ubahin"
    width: int = 1440
    height: int = 900
    min_size: tuple[int, int] = (1100, 700)
    background_color: str = "#F8F7F4"


DEFAULT_WINDOW_CONFIG = DesktopWindowConfig()


def build_window_options(index_html: Path, bridge: Any, config: DesktopWindowConfig = DEFAULT_WINDOW_CONFIG) -> dict[str, Any]:
    """Return pywebview options for the native Ubahin application window.

    The UI is loaded directly from the bundled local HTML file. No local HTTP
    server or external browser is involved.
    """
    html_path = index_html.resolve()
    if not html_path.exists():
        raise FileNotFoundError(f"GUI Ubahin tidak ditemukan: {html_path}")
    return {
        "title": config.title,
        "url": html_path.as_uri(),
        "js_api": bridge,
        "width": config.width,
        "height": config.height,
        "min_size": config.min_size,
        "background_color": config.background_color,
        "text_select": False,
        "zoomable": False,
        "frameless": True,
        "easy_drag": True,
        "shadow": True,
    }


def create_main_window(webview_module: Any, index_html: Path, bridge: Any, config: DesktopWindowConfig = DEFAULT_WINDOW_CONFIG) -> Any:
    """Create the pywebview-hosted native Windows shell for Ubahin."""
    return webview_module.create_window(**build_window_options(index_html, bridge, config))
