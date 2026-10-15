"""Check bundled fonts, writing rules and rendered templates without publishing."""

import json
from pathlib import Path
import tempfile

from PIL import Image, ImageFont

from src.core.services.marketing_poster_layout import render_marketing
from src.core.services.poster_catalog import LAYOUT_TEMPLATES
from src.core.services.system_image_template_service import SystemImageTemplateService
from src.version import __version__


def run_release_smoke() -> None:
    root = Path(__file__).resolve().parents[3]
    font_path = root / "assets/fonts/NotoSansSC.ttf"
    rules = root / "templates/writing/humanizer-chinese.md"
    if not rules.is_file() or rules.stat().st_size < 1000:
        raise RuntimeError("Bundled Chinese writing rules are missing")

    def font_factory(_family, _style, size):
        return ImageFont.truetype(str(font_path), size)

    # Load the variable font now, so missing fonts cannot silently fall back.
    font_factory("chinese", "regular", 30)
    service = SystemImageTemplateService()
    templates = service.list_showcase_templates()
    if len(templates) != 13:
        raise RuntimeError(f"Expected 13 bundled templates, got {len(templates)}")

    rendered = []
    with tempfile.TemporaryDirectory(prefix="xhs-release-smoke-") as directory:
        for layout, _label in LAYOUT_TEMPLATES.values():
            pages = render_marketing({
                "poster_layout": layout, "title": "新版排版检查",
                "pages": [{"title": "本地预览", "body": "保留自己的文字和图片。发布前由作者核对。"}],
            }, Path(directory) / layout, font_factory)
            if len(pages) < 2:
                raise RuntimeError(f"Missing content pages for {layout}")
            for page in pages:
                with Image.open(page["image_path"]) as image:
                    if image.size != (1080, 1440):
                        raise RuntimeError(f"Invalid output dimensions for {layout}")
            rendered.append(layout)

    print(json.dumps({"version": __version__, "templates": len(templates),
                      "rendered_layouts": rendered, "status": "ok"}, ensure_ascii=False))
