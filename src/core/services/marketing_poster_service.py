"""
营销海报图片渲染（本地生成，跨平台字体回退）。
"""

from __future__ import annotations

import os
import platform
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont


POSTER_SIZE: Tuple[int, int] = (1080, 1440)  # XHS 3:4


@dataclass(frozen=True)
class Colors:
    bg_top: Tuple[int, int, int] = (250, 247, 242)
    bg_bottom: Tuple[int, int, int] = (243, 239, 232)
    text: Tuple[int, int, int] = (27, 27, 27)
    sub: Tuple[int, int, int] = (90, 90, 90)
    card: Tuple[int, int, int] = (255, 255, 255)
    blue: Tuple[int, int, int] = (47, 107, 255)
    red: Tuple[int, int, int] = (255, 77, 79)
    yellow: Tuple[int, int, int] = (255, 229, 143)


C = Colors()

ACCENTS: Dict[str, Tuple[int, int, int]] = {
    "blue": (47, 107, 255),
    "purple": (146, 84, 255),
    "orange": (255, 140, 64),
    "red": (255, 77, 79),
    "tape": (255, 229, 143),
}


def _split_env_paths(name: str) -> List[str]:
    raw = os.environ.get(name) or ""
    return [p.strip() for p in raw.split(",") if p.strip()]


def _font_px(font: ImageFont.ImageFont, fallback: int) -> int:
    try:
        return int(getattr(font, "size", fallback) or fallback)
    except Exception:
        return fallback


class PosterFontResolver:
    """
    Cross-platform font resolver for poster rendering.
    Priority:
      1) env overrides (comma-separated paths)
         - X_AUTO_PUBLISHER_POSTER_SANS_FONT
         - X_AUTO_PUBLISHER_POSTER_SERIF_FONT
      2) common system font paths for macOS/Linux/Windows
      3) Pillow default font (may not support CJK)
    """

    def __init__(self) -> None:
        self._cache: Dict[Tuple[str, int, bool], ImageFont.ImageFont] = {}
        self._sans_overrides = _split_env_paths("X_AUTO_PUBLISHER_POSTER_SANS_FONT")
        self._serif_overrides = _split_env_paths("X_AUTO_PUBLISHER_POSTER_SERIF_FONT")

    @staticmethod
    def _try_truetype(path: str, size: int, *, indices: Sequence[int] = (0,)) -> Optional[ImageFont.ImageFont]:
        p = Path(path)
        if not p.exists():
            return None

        for idx in indices:
            try:
                return ImageFont.truetype(str(p), size, index=int(idx))
            except Exception:
                continue

        try:
            return ImageFont.truetype(str(p), size)
        except Exception:
            return None

    def _candidate_fonts(self, *, serif: bool, bold: bool) -> List[Tuple[str, Sequence[int]]]:
        system = platform.system().lower()
        candidates: List[Tuple[str, Sequence[int]]] = []

        if serif:
            # macOS
            candidates.extend(
                [
                    ("/System/Library/Fonts/Supplemental/Songti.ttc", (1 if bold else 6,)),
                    ("/System/Library/Fonts/Supplemental/STSong.ttf", (0,)),
                    ("/System/Library/Fonts/Supplemental/Times New Roman.ttf", (0,)),
                ]
            )
            # Linux
            candidates.extend(
                [
                    ("/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc", (0,)),
                    ("/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc", (0,)),
                    ("/usr/share/fonts/truetype/noto/NotoSerifCJK-Regular.ttc", (0,)),
                ]
            )
            # Windows
            candidates.extend(
                [
                    ("C:\\Windows\\Fonts\\simsun.ttc", (0,)),
                    ("C:\\Windows\\Fonts\\simkai.ttf", (0,)),
                    ("C:\\Windows\\Fonts\\times.ttf", (0,)),
                ]
            )
        else:
            # macOS
            candidates.extend(
                [
                    ("/System/Library/Fonts/Hiragino Sans GB.ttc", (2 if bold else 0,)),
                    ("/System/Library/Fonts/PingFang.ttc", (0,)),
                    ("/System/Library/Fonts/STHeiti Light.ttc", (0,)),
                    ("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", (0,)),
                ]
            )
            # Linux
            candidates.extend(
                [
                    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", (0,)),
                    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", (0,)),
                    ("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", (0,)),
                    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", (0,)),
                ]
            )
            # Windows
            candidates.extend(
                [
                    ("C:\\Windows\\Fonts\\msyh.ttc", (0,)),
                    ("C:\\Windows\\Fonts\\msyhbd.ttc", (0,)),
                    ("C:\\Windows\\Fonts\\simhei.ttf", (0,)),
                    ("C:\\Windows\\Fonts\\arial.ttf", (0,)),
                ]
            )

        if system == "linux":
            candidates.extend(
                [
                    ("/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc", (0,)),
                    ("/usr/share/fonts/google-noto-cjk/NotoSansCJK-Bold.ttc", (0,)),
                ]
            )

        return candidates

    def get(self, *, size: int, bold: bool = False, serif: bool = False) -> ImageFont.ImageFont:
        key = ("serif" if serif else "sans", int(size), bool(bold))
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        overrides = self._serif_overrides if serif else self._sans_overrides
        for path in overrides:
            font = self._try_truetype(path, size, indices=(0,))
            if font is not None:
                self._cache[key] = font
                return font

        for path, indices in self._candidate_fonts(serif=serif, bold=bold):
            font = self._try_truetype(path, size, indices=indices)
            if font is not None:
                self._cache[key] = font
                return font

        font = ImageFont.load_default()
        self._cache[key] = font
        return font


def _lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def gradient_bg(size: Tuple[int, int]) -> Image.Image:
    w, h = size
    img = Image.new("RGB", size, C.bg_top)
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / (h - 1) if h > 1 else 0
        d.line(
            [(0, y), (w, y)],
            fill=(
                _lerp(C.bg_top[0], C.bg_bottom[0], t),
                _lerp(C.bg_top[1], C.bg_bottom[1], t),
                _lerp(C.bg_top[2], C.bg_bottom[2], t),
            ),
        )

    noise = Image.effect_noise(size, 18).convert("L")
    noise = noise.point(lambda p: int(p * 0.10))
    noise_rgb = Image.merge("RGB", (noise, noise, noise))
    img = Image.blend(img, noise_rgb, 0.18)

    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    step = 50
    dot_r = 2
    dot = (0, 0, 0, 12)
    for yy in range(130, h, step):
        for xx in range(70, w, step):
            od.ellipse([xx - dot_r, yy - dot_r, xx + dot_r, yy + dot_r], fill=dot)

    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def card(base: Image.Image, xy: Tuple[int, int, int, int], *, radius: int = 28) -> None:
    x0, y0, x1, y1 = xy
    base_rgba = base.convert("RGBA")

    shadow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle([x0 + 6, y0 + 10, x1 + 6, y1 + 10], radius=radius, fill=(0, 0, 0, 40))
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))
    base_rgba = Image.alpha_composite(base_rgba, shadow)

    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rounded_rectangle(
        [x0, y0, x1, y1],
        radius=radius,
        fill=(C.card[0], C.card[1], C.card[2], 255),
        outline=(0, 0, 0, 14),
        width=2,
    )
    base_rgba = Image.alpha_composite(base_rgba, overlay)
    base.paste(base_rgba)


def clean_text(text: str) -> str:
    if not text:
        return ""

    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U0001F900-\U0001F9FF"
        "\U0001FA00-\U0001FA6F"
        "\U0001FA70-\U0001FAFF"
        "\u2600-\u27BF"
        "]+",
        flags=re.UNICODE,
    )
    return emoji_pattern.sub("", str(text)).strip()


def wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_w: int) -> List[str]:
    lines: List[str] = []
    for para in (text or "").split("\n"):
        if not para:
            lines.append("")
            continue

        if " " in para:
            tokens = para.split(" ")
            line = ""
            for token in tokens:
                test = token if not line else f"{line} {token}"
                if draw.textlength(test, font=font) <= max_w:
                    line = test
                    continue
                if line:
                    lines.append(line)
                    line = token
                else:
                    frag = ""
                    for ch in token:
                        test2 = frag + ch
                        if draw.textlength(test2, font=font) <= max_w:
                            frag = test2
                        else:
                            if frag:
                                lines.append(frag)
                            frag = ch
                    line = frag
            if line:
                lines.append(line)
            continue

        line = ""
        for ch in para:
            test = line + ch
            if draw.textlength(test, font=font) <= max_w:
                line = test
            else:
                if line:
                    lines.append(line)
                line = ch
        if line:
            lines.append(line)

    return lines


def wrap_clipped(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_w: int,
    *,
    max_lines: int,
) -> List[str]:
    """Wrap text and clip to `max_lines` with ellipsis."""
    lines = wrap(draw, text, font, max_w)
    lines = [ln for ln in lines if str(ln).strip()]
    if max_lines <= 0:
        return []
    if len(lines) <= max_lines:
        return lines
    clipped = lines[:max_lines]
    ell = "…"
    last = clipped[-1]
    if last.endswith(ell):
        return clipped
    while draw.textlength(last + ell, font=font) > max_w and len(last) > 1:
        last = last[:-1]
    clipped[-1] = last + ell
    return clipped


def draw_paragraph(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[int, int],
    text: str,
    *,
    font: ImageFont.ImageFont,
    fill: Tuple[int, int, int],
    max_w: int,
    line_h: Optional[int] = None,
    spacing: int = 8,
) -> int:
    x, y = xy
    lines = wrap(draw, text, font, max_w)
    if line_h is None:
        line_h = int(_font_px(font, 28) * 1.28)
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += line_h + spacing
    return y


def draw_bullets(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[int, int],
    bullets: Iterable[str],
    *,
    font: ImageFont.ImageFont,
    fill: Tuple[int, int, int],
    max_w: int,
    dot_color: Tuple[int, int, int],
    dot_r: int = 4,
    gap: int = 12,
) -> int:
    x, y = xy
    text_indent = 20
    line_h = int(_font_px(font, 26) * 1.25)
    for bullet in bullets:
        bullet = clean_text(str(bullet))
        if not bullet:
            continue
        lines = wrap(draw, bullet, font, max_w - text_indent)
        cy = y + int(line_h * 0.45)
        draw.ellipse([x - dot_r, cy - dot_r, x + dot_r, cy + dot_r], fill=dot_color)
        if lines:
            draw.text((x + text_indent, y), lines[0], font=font, fill=fill)
        y += line_h
        for cont in lines[1:]:
            draw.text((x + text_indent, y), cont, font=font, fill=fill)
            y += line_h
        y += gap
    return y


def label_tag(
    base: Image.Image,
    xy: Tuple[int, int, int, int],
    text: str,
    *,
    bg: Tuple[int, int, int],
    fonts: PosterFontResolver,
) -> None:
    x0, y0, x1, y1 = xy
    r = int((y1 - y0) / 2)
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    d.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=(bg[0], bg[1], bg[2], 255))
    base_rgba = Image.alpha_composite(base.convert("RGBA"), overlay)
    d2 = ImageDraw.Draw(base_rgba)
    f = fonts.get(size=28, bold=True, serif=False)
    tw = d2.textlength(text, font=f)
    d2.text((x0 + (x1 - x0 - tw) / 2, y0 + 10), text, font=f, fill=(255, 255, 255))
    base.paste(base_rgba)


def checkbox(draw: ImageDraw.ImageDraw, xy: Tuple[int, int], *, checked: bool = True) -> None:
    x, y = xy
    s = 30
    draw.rounded_rectangle([x, y, x + s, y + s], radius=8, outline=(C.blue[0], C.blue[1], C.blue[2], 255), width=3, fill=(255, 255, 255))
    if checked:
        draw.line([(x + 6, y + 16), (x + 13, y + 23), (x + 25, y + 7)], fill=(C.blue[0], C.blue[1], C.blue[2], 255), width=4)


def highlight_title(
    img: Image.Image,
    xy: Tuple[int, int],
    text: str,
    *,
    font: ImageFont.ImageFont,
    accent: Tuple[int, int, int],
) -> None:
    x, y = xy
    d = ImageDraw.Draw(img)
    tw = d.textlength(text, font=font)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    font_size = _font_px(font, 36)
    h = int(font_size * 0.55)
    od.rounded_rectangle(
        [x - 6, y + int(font_size * 0.60), x + tw + 10, y + int(font_size * 0.60) + h],
        radius=14,
        fill=(accent[0], accent[1], accent[2], 55),
    )
    img_rgba = Image.alpha_composite(img.convert("RGBA"), overlay)
    img.paste(img_rgba)


def _normalize_list(raw: Any, *, min_items: int, max_items: int, fallback: List[str]) -> List[str]:
    items: List[str] = []
    if isinstance(raw, list):
        for v in raw:
            t = clean_text(str(v))
            if t:
                items.append(t)
    items = items[:max_items]
    while len(items) < min_items and len(items) < max_items:
        items.append(fallback[len(items) % len(fallback)])
    return items


class MarketingPosterService:
    def __init__(self, *, size: Tuple[int, int] = POSTER_SIZE) -> None:
        self.size = size
        self.fonts = PosterFontResolver()

    @staticmethod
    def default_output_root() -> Path:
        return Path(os.path.expanduser("~")) / ".xhs_system" / "generated_imgs"

    def generate(self, content: Dict[str, Any], *, out_dir: Path) -> List[Dict[str, str]]:
        out_dir.mkdir(parents=True, exist_ok=True)

        title = clean_text(str(content.get("title") or "营销海报"))
        subtitle = clean_text(str(content.get("subtitle") or ""))
        price = clean_text(str(content.get("price") or ""))
        keyword = clean_text(str(content.get("keyword") or "")) or "咨询"
        accent_name = clean_text(str(content.get("accent") or "blue")).lower()
        accent = ACCENTS.get(accent_name, ACCENTS["blue"])

        cover_bullets = _normalize_list(
            content.get("cover_bullets"),
            min_items=3,
            max_items=3,
            fallback=["核心卖点 1", "核心卖点 2", "核心卖点 3"],
        )
        outline_items = _normalize_list(
            content.get("outline_items"),
            min_items=8,
            max_items=10,
            fallback=["亮点概览", "功能说明", "适用场景", "交付方式", "注意事项"],
        )

        highlights_raw = content.get("highlights")
        highlights: List[Tuple[str, str]] = []
        if isinstance(highlights_raw, list):
            for item in highlights_raw:
                if not isinstance(item, dict):
                    continue
                h_title = clean_text(str(item.get("title") or "亮点"))
                h_desc = clean_text(str(item.get("desc") or item.get("description") or ""))
                if h_title:
                    highlights.append((h_title, h_desc))
        while len(highlights) < 4:
            idx = len(highlights) + 1
            highlights.append((f"亮点 {idx}", "一句话说明它能解决什么问题"))
        highlights = highlights[:4]

        delivery_steps = _normalize_list(
            content.get("delivery_steps"),
            min_items=3,
            max_items=3,
            fallback=["下单购买", "确认需求/领取资料", "开始使用/复盘优化"],
        )
        pain_points = _normalize_list(
            content.get("pain_points"),
            min_items=4,
            max_items=4,
            fallback=["不知道从哪开始", "信息太碎不好整理", "做完效果不稳定", "缺少可复用模板"],
        )

        audience_raw = content.get("audience")
        audience: List[Dict[str, Any]] = []
        if isinstance(audience_raw, list):
            for item in audience_raw:
                if not isinstance(item, dict):
                    continue
                badge = clean_text(str(item.get("badge") or ""))[:1] or "A"
                a_title = clean_text(str(item.get("title") or "适合人群"))
                bullets = _normalize_list(
                    item.get("bullets"),
                    min_items=2,
                    max_items=3,
                    fallback=["痛点清晰", "希望快速上手", "需要可复制模板"],
                )
                audience.append({"badge": badge, "title": a_title, "bullets": bullets})
        while len(audience) < 3:
            idx = len(audience) + 1
            audience.append({"badge": str(idx), "title": f"人群 {idx}", "bullets": ["痛点清晰", "希望快速上手"]})
        audience = audience[:3]

        disclaimer = clean_text(str(content.get("disclaimer") or "仅供参考｜请遵守平台规则"))

        posters: List[Tuple[str, Image.Image]] = [
            (
                "01_cover.png",
                self._poster_cover(
                    title=title,
                    subtitle=subtitle,
                    bullets=cover_bullets,
                    price=price,
                    keyword=keyword,
                    accent=accent,
                    disclaimer=disclaimer,
                ),
            ),
            ("02_outline.png", self._poster_outline(title=title, items=outline_items, keyword=keyword, accent=accent)),
            (
                "03_highlights.png",
                self._poster_highlights(title=title, highlights=highlights, price=price, keyword=keyword, accent=accent),
            ),
            ("04_delivery.png", self._poster_delivery(steps=delivery_steps, price=price, accent=accent)),
            ("05_pain_points.png", self._poster_pain_points(points=pain_points, price=price, keyword=keyword, accent=accent)),
            ("06_audience.png", self._poster_audience(audience=audience, keyword=keyword)),
        ]

        out_paths: List[Dict[str, str]] = []
        for filename, img in posters:
            path = out_dir / filename
            img.save(str(path), format="PNG", optimize=True)
            out_paths.append({"title": Path(filename).stem, "image_path": str(path)})
        return out_paths

    def generate_to_local_paths(self, content: Dict[str, Any]) -> Tuple[str, List[str]]:
        ts = int(time.time())
        unique = uuid.uuid4().hex[:8]
        out_dir = self.default_output_root() / f"marketing_poster_{ts}_{unique}"
        posters = self.generate(content, out_dir=out_dir)
        if not posters:
            return "", []
        cover = posters[0].get("image_path") or ""
        pages = [p.get("image_path") or "" for p in posters[1:] if p.get("image_path")]
        return cover, pages

    def _poster_cover(
        self,
        *,
        title: str,
        subtitle: str,
        bullets: List[str],
        price: str,
        keyword: str,
        accent: Tuple[int, int, int],
        disclaimer: str,
    ) -> Image.Image:
        img = gradient_bg(self.size)
        d = ImageDraw.Draw(img)

        label_tag(img, (70, 68, 320, 118), "营销海报", bg=accent, fonts=self.fonts)
        max_w = self.size[0] - 140
        title_x = 70
        title_y0 = 150
        card_y0 = 350

        title_text = title or "营销海报"
        subtitle_text = subtitle or ""

        subtitle_font = self.fonts.get(size=34, bold=False, serif=False)
        subtitle_h = int(_font_px(subtitle_font, 34) * 1.25)

        available_h = max(80, card_y0 - title_y0 - 12)
        if subtitle_text:
            available_h = max(60, available_h - subtitle_h - 12)

        title_font = self.fonts.get(size=84, bold=True, serif=True)
        title_lines: List[str] = []
        title_step = int(_font_px(title_font, 84) * 1.12)
        for size in range(84, 55, -4):
            candidate = self.fonts.get(size=size, bold=True, serif=True)
            lines = wrap(d, title_text, candidate, max_w)
            lines = [ln for ln in lines if str(ln).strip()]
            step = int(_font_px(candidate, size) * 1.12)
            if len(lines) <= 2 and step * max(1, len(lines)) <= available_h:
                title_font = candidate
                title_lines = lines
                title_step = step
                break

        if not title_lines:
            title_font = self.fonts.get(size=60, bold=True, serif=True)
            title_lines = wrap_clipped(d, title_text, title_font, max_w, max_lines=2)
            title_step = int(_font_px(title_font, 60) * 1.12)

        y = title_y0
        for line in title_lines[:2]:
            d.text((title_x, y), line, font=title_font, fill=C.text)
            y += title_step

        if subtitle_text and y + subtitle_h < card_y0 - 10:
            subtitle_lines = wrap_clipped(d, subtitle_text, subtitle_font, max_w, max_lines=1)
            if subtitle_lines:
                d.text((title_x, y + 10), subtitle_lines[0], font=subtitle_font, fill=C.sub)

        card_xy = (70, 350, 1010, 760)
        card(img, card_xy)

        bullet_font = self.fonts.get(size=40, bold=False, serif=False)
        x_text = 160
        max_w = card_xy[2] - x_text - 70
        y = 402
        for it in bullets:
            checkbox(d, (110, y + 6), checked=True)
            line_h = int(_font_px(bullet_font, 40) * 1.18)
            bullet_lines = wrap_clipped(d, it, bullet_font, max_w, max_lines=2)
            if not bullet_lines:
                continue
            for li, line in enumerate(bullet_lines):
                d.text((x_text, y + li * line_h), line, font=bullet_font, fill=C.text)
            y = y + len(bullet_lines) * line_h + 18

        if price:
            card(img, (70, 810, 520, 960), radius=34)
            d = ImageDraw.Draw(img)
            d.text((110, 838), price, font=self.fonts.get(size=96, bold=True, serif=False), fill=C.red)
            d.text((360, 905), "元", font=self.fonts.get(size=34, bold=True, serif=False), fill=C.sub)

        cta_font = self.fonts.get(size=36, bold=True, serif=False)
        d.text((70, 1025), f"想了解详情：评论/私信「{keyword}」", font=cta_font, fill=C.text)
        d.text((70, 1085), "领取资料/报价/示例（不公开）", font=self.fonts.get(size=26, bold=False, serif=False), fill=C.sub)

        prefix = "想了解详情："
        underline_text = f"评论/私信「{keyword}」"
        x_underline = 70 + d.textlength(prefix, font=cta_font)
        w = d.textlength(underline_text, font=cta_font)
        underline = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ud = ImageDraw.Draw(underline)
        ud.line([(x_underline, 1065), (x_underline + w, 1065)], fill=(accent[0], accent[1], accent[2], 160), width=8)
        underline = underline.filter(ImageFilter.GaussianBlur(1))
        img = Image.alpha_composite(img.convert("RGBA"), underline).convert("RGB")

        d = ImageDraw.Draw(img)
        d.text((70, 1360), disclaimer, font=self.fonts.get(size=22, bold=False, serif=False), fill=(120, 120, 120))
        return img

    def _poster_outline(
        self,
        *,
        title: str,
        items: List[str],
        keyword: str,
        accent: Tuple[int, int, int],
    ) -> Image.Image:
        img = gradient_bg(self.size)
        d = ImageDraw.Draw(img)

        d.text((70, 120), "要点一图看懂", font=self.fonts.get(size=80, bold=True, serif=True), fill=C.text)

        card(img, (70, 250, 1010, 1180))
        item_font = self.fonts.get(size=36, bold=False, serif=False)

        x_dot, x_text = 120, 150
        y = 320
        row_h = 78
        for it in items:
            d.ellipse([x_dot - 14, y + 16, x_dot + 8, y + 38], fill=(accent[0], accent[1], accent[2], 210))
            d.text((x_text, y), it, font=item_font, fill=C.text)
            y += row_h

        card(img, (70, 1220, 1010, 1320), radius=24)
        d.text((110, 1255), f"想看详细方案：私信「{keyword}」", font=self.fonts.get(size=34, bold=True, serif=False), fill=C.text)
        return img

    def _poster_highlights(
        self,
        *,
        title: str,
        highlights: List[Tuple[str, str]],
        price: str,
        keyword: str,
        accent: Tuple[int, int, int],
    ) -> Image.Image:
        img = gradient_bg(self.size)
        d = ImageDraw.Draw(img)

        d.text((70, 120), "你会拿到什么", font=self.fonts.get(size=76, bold=True, serif=True), fill=C.text)

        x0, y0 = 70, 260
        w, h = 940, 240
        gap = 28

        for idx, (t, desc) in enumerate(highlights[:4]):
            y = y0 + idx * (h + gap)
            card(img, (x0, y, x0 + w, y + h), radius=24)

            t_font = self.fonts.get(size=48, bold=True, serif=False)
            tw = int(d.textlength(t, font=t_font))
            d.rounded_rectangle(
                [
                    x0 + 90,
                    y + 30 + _font_px(t_font, 48) * 0.55,
                    x0 + 90 + tw + 20,
                    y + 30 + _font_px(t_font, 48) * 0.55 + 28,
                ],
                radius=16,
                fill=(C.yellow[0], C.yellow[1], C.yellow[2], 255),
            )
            d.text((x0 + 90, y + 30), t, font=t_font, fill=C.text)
            draw_paragraph(
                d,
                (x0 + 90, y + 105),
                desc,
                font=self.fonts.get(size=32, bold=False, serif=False),
                fill=C.sub,
                max_w=w - 160,
                spacing=4,
            )

            tape = Image.new("RGBA", img.size, (0, 0, 0, 0))
            td = ImageDraw.Draw(tape)
            td.rounded_rectangle([x0 + w - 140, y + 18, x0 + w - 24, y + 54], radius=16, fill=(ACCENTS["tape"][0], ACCENTS["tape"][1], ACCENTS["tape"][2], 180))
            tape = tape.filter(ImageFilter.GaussianBlur(1))
            img = Image.alpha_composite(img.convert("RGBA"), tape).convert("RGB")
            d = ImageDraw.Draw(img)

        note_y0 = 1280
        note = f"价格：{price} 元（可私信获取示例/详细清单）" if price else "可私信获取示例/详细清单（不公开）"
        card(img, (70, note_y0, 1010, 1380), radius=24)
        d = ImageDraw.Draw(img)
        d.text((110, note_y0 + 32), f"私信「{keyword}」先看预览", font=self.fonts.get(size=34, bold=True, serif=False), fill=C.text)
        draw_paragraph(
            d,
            (110, note_y0 + 80),
            note,
            font=self.fonts.get(size=30, bold=False, serif=False),
            fill=C.sub,
            max_w=860,
            spacing=6,
        )
        return img

    def _poster_delivery(
        self,
        *,
        steps: List[str],
        price: str,
        accent: Tuple[int, int, int],
    ) -> Image.Image:
        img = gradient_bg(self.size)
        d = ImageDraw.Draw(img)

        d.text((70, 110), "交付/使用路径", font=self.fonts.get(size=72, bold=True, serif=True), fill=C.text)
        d.text((70, 205), "从了解 → 下单 → 交付，三步走完", font=self.fonts.get(size=32, bold=False, serif=False), fill=C.sub)

        card(img, (70, 290, 1010, 1090))

        y = 360
        step_font = self.fonts.get(size=44, bold=True, serif=False)
        for idx, step in enumerate(steps[:3]):
            badge = Image.new("RGBA", img.size, (0, 0, 0, 0))
            bd = ImageDraw.Draw(badge)
            cx, cy = 150, y + 30
            bd.ellipse([cx - 26, cy - 26, cx + 26, cy + 26], fill=(accent[0], accent[1], accent[2], 255))
            img_rgba = Image.alpha_composite(img.convert("RGBA"), badge)
            img.paste(img_rgba)
            d = ImageDraw.Draw(img)
            d.text((cx - 10, cy - 20), str(idx + 1), font=self.fonts.get(size=30, bold=True, serif=False), fill=(255, 255, 255))

            d.text((210, y), clean_text(step), font=step_font, fill=C.text)
            y += 80

            if idx < 2:
                d.line([(150, y + 10), (150, y + 120)], fill=(0, 0, 0, 35), width=4)
                y += 100

        card(img, (70, 1125, 1010, 1320), radius=24)
        d = ImageDraw.Draw(img)
        d.text((110, 1165), "你会得到：海报文案 + 图片模板 + 示例", font=self.fonts.get(size=34, bold=True, serif=False), fill=C.text)
        tail = f"价格：{price} 元｜可私信获取示例" if price else "可私信获取示例"
        d.text((110, 1225), tail, font=self.fonts.get(size=30, bold=False, serif=False), fill=C.sub)
        return img

    def _poster_pain_points(
        self,
        *,
        points: List[str],
        price: str,
        keyword: str,
        accent: Tuple[int, int, int],
    ) -> Image.Image:
        img = gradient_bg(self.size)
        d = ImageDraw.Draw(img)

        d.text((70, 110), "常见卡点", font=self.fonts.get(size=72, bold=True, serif=True), fill=C.text)
        d.text((70, 205), "如果你也遇到这些，这份方案会很省时间", font=self.fonts.get(size=32, bold=False, serif=False), fill=C.sub)

        card(img, (70, 290, 1010, 1060))

        y = 350
        f = self.fonts.get(size=36, bold=False, serif=False)
        for p in points:
            checkbox(d, (110, y + 6), checked=True)
            y = draw_paragraph(d, (160, y), p, font=f, fill=C.text, max_w=820, spacing=4) + 22

        card(img, (70, 1100, 1010, 1320), radius=24)
        d.text((110, 1145), "结论：按步骤走一遍，很多坑会直接避开", font=self.fonts.get(size=34, bold=True, serif=False), fill=C.text)
        tail = f"私信「{keyword}」先看预览｜价格 {price}" if price else f"私信「{keyword}」先看预览"
        d.text((110, 1205), tail, font=self.fonts.get(size=30, bold=False, serif=False), fill=C.sub)
        return img

    def _draw_audience_card(
        self,
        img: Image.Image,
        xy: Tuple[int, int, int, int],
        *,
        accent: Tuple[int, int, int],
        badge_char: str,
        title: str,
        bullets: List[str],
    ) -> None:
        x0, y0, x1, y1 = xy
        card(img, xy, radius=26)
        d = ImageDraw.Draw(img)

        d.rounded_rectangle((x0 + 36, y0 + 36, x0 + 44, y1 - 36), radius=4, fill=accent)

        cx, cy = x0 + 66, y0 + 66
        d.ellipse([cx - 20, cy - 20, cx + 20, cy + 20], fill=accent)
        d.text((cx - 12, cy - 18), badge_char, font=self.fonts.get(size=28, bold=True, serif=False), fill=(255, 255, 255))

        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.rounded_rectangle([x1 - 170, y0 + 18, x1 - 30, y0 + 54], radius=10, fill=(ACCENTS["tape"][0], ACCENTS["tape"][1], ACCENTS["tape"][2], 140))
        img_rgba = Image.alpha_composite(img.convert("RGBA"), overlay)
        img.paste(img_rgba)

        title_font = self.fonts.get(size=44, bold=True, serif=False)
        title_x, title_y = x0 + 110, y0 + 36
        highlight_title(img, (title_x, title_y), title, font=title_font, accent=accent)
        d = ImageDraw.Draw(img)
        d.text((title_x, title_y), title, font=title_font, fill=C.text)

        bullet_font = self.fonts.get(size=30, bold=False, serif=False)
        bullet_x, bullet_y = title_x, y0 + 108
        max_w = x1 - bullet_x - 70
        draw_bullets(d, (bullet_x, bullet_y), bullets, font=bullet_font, fill=C.sub, max_w=max_w, dot_color=accent, gap=10)

    def _poster_audience(self, *, audience: List[Dict[str, Any]], keyword: str) -> Image.Image:
        img = gradient_bg(self.size)
        d = ImageDraw.Draw(img)

        d.text((70, 110), "适合哪些人", font=self.fonts.get(size=72, bold=True, serif=True), fill=C.text)
        d.text((70, 200), "三类人最适合：更快上手 / 更稳落地 / 更省时间", font=self.fonts.get(size=30, bold=False, serif=False), fill=C.sub)

        x0, y0 = 70, 270
        w, h = 940, 230
        gap = 26
        palette = [ACCENTS["blue"], ACCENTS["purple"], ACCENTS["orange"]]
        for idx, item in enumerate(audience[:3]):
            y = y0 + idx * (h + gap)
            accent = palette[idx % len(palette)]
            self._draw_audience_card(
                img,
                (x0, y, x0 + w, y + h),
                accent=accent,
                badge_char=str(item.get("badge") or "")[:1] or str(idx + 1),
                title=str(item.get("title") or f"人群 {idx + 1}"),
                bullets=[str(b) for b in (item.get("bullets") or [])][:3],
            )

        note_y0 = 1135
        card(img, (70, note_y0, 1010, 1320), radius=26)
        d = ImageDraw.Draw(img)

        tag_x0, tag_y0 = 110, note_y0 + 40
        tag_x1, tag_y1 = tag_x0 + 190, tag_y0 + 52
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.rounded_rectangle([tag_x0, tag_y0, tag_x1, tag_y1], radius=26, fill=(ACCENTS["red"][0], ACCENTS["red"][1], ACCENTS["red"][2], 255))
        img_rgba = Image.alpha_composite(img.convert("RGBA"), overlay)
        img.paste(img_rgba)
        d = ImageDraw.Draw(img)
        d.text((tag_x0 + 38, tag_y0 + 10), "不太适合", font=self.fonts.get(size=28, bold=True, serif=False), fill=(255, 255, 255))
        d.text((tag_x1 + 18, tag_y0 + 12), "只想看概念不动手", font=self.fonts.get(size=32, bold=True, serif=False), fill=C.text)
        d.text((110, note_y0 + 112), f"想了解详情：私信「{keyword}」", font=self.fonts.get(size=30, bold=False, serif=False), fill=C.sub)

        return img


marketing_poster_service = MarketingPosterService()
