"""Local typography for default note images; preserves text and paginates overflow."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Callable, List, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont


@dataclass
class NotePage:
    title: str
    rows: List[str]
    title_size: int
    body_size: int
    body_top: int
    asset_path: str = ''


class NoteImageRenderer:
    """A text-first layout used when no external background has been selected."""

    paper = '#F6F4EF'
    ink = '#182E32'
    muted = '#526466'
    accent = '#2C6465'
    rule = '#CBD4CF'
    tint = '#E5EDE7'
    closing = set('，。！？；：、,.!?;:）】》」』”’')
    opening = set('（【《「『“‘')

    def __init__(self, font_factory: Callable, size: Tuple[int, int] = (1080, 1440)):
        self.font_factory = font_factory
        self.size = size
        self.scale = min(size[0] / 1080, size[1] / 1440)
        self.measure = ImageDraw.Draw(Image.new('RGB', size))
        self._fonts = {}

    def px(self, value: float) -> int:
        return max(1, round(value * self.scale))

    def font(self, size: int, bold: bool = False):
        cache_key = size, bold
        if cache_key not in self._fonts:
            font = self.font_factory('chinese', 'bold' if bold else 'regular', size=self.px(size))
            # macOS fallback is a TTC: W6 is face 2, not the default W3 face.
            path = str(getattr(font, 'path', '') or '')
            if bold and Path(path).name == 'Hiragino Sans GB.ttc':
                font = ImageFont.truetype(path, self.px(size), index=2)
            self._fonts[cache_key] = font
        return self._fonts[cache_key]

    def width(self, text: str, font) -> float:
        return self.measure.textlength(text, font=font)

    def wrap(self, text: str, font, width: int) -> List[str]:
        """Keep Latin words together, and avoid punctuation at the start of a line."""
        rows = []
        for source_line in text.splitlines() or ['']:
            source_start = len(rows)
            if not source_line.strip():
                rows.append('')
                continue
            tokens = re.findall(r'[A-Za-z0-9_]+(?:[./:\-][A-Za-z0-9_]+)*|[^A-Za-z0-9_]', source_line)
            line = ''
            for token in tokens:
                if self.width(token, font) > width:
                    parts = list(token)
                else:
                    parts = [token]
                for part in parts:
                    if line and self.width(line + part, font) > width:
                        if part in self.closing or line[-1:] in self.opening:
                            # Move a preceding character too, so punctuation is not stranded.
                            carry = line[-1:]
                            if len(line) > 1:
                                rows.append(line[:-1].rstrip())
                                line = carry + part
                            else:
                                line += part
                        else:
                            rows.append(line.rstrip())
                            line = part.lstrip()
                    else:
                        line += part
            if line.strip():
                rows.append(line.rstrip())
            # Avoid a final line containing only a couple of characters.
            if len(rows) - source_start >= 2 and self.width(rows[-1], font) < width * .30:
                joined = rows[-2] + rows[-1]
                options = []
                for i in range(1, len(joined)):
                    a, b = joined[:i], joined[i:]
                    if b[0] in self.closing or a[-1] in self.opening:
                        continue
                    if re.match(r'[A-Za-z0-9_]', a[-1]) and re.match(r'[A-Za-z0-9_]', b[0]):
                        continue
                    wa, wb = self.width(a, font), self.width(b, font)
                    if max(wa, wb) <= width:
                        preference = width * .18 if a[-1] in self.closing else 0
                        options.append((abs(wa-wb) - preference, a, b))
                if options:
                    _, a, b = min(options)
                    rows[-2:] = [a, b]
        return rows

    def title_lines(self, text: str, size: int, width: int) -> List[str]:
        """Respect authored line breaks; balance unformatted headlines without clipping."""
        font = self.font(size, True)
        if '\n' in text:
            return [row for row in self.wrap(text, font, width) if row]
        # A colon separates a subject from its description more naturally than a hard wrap.
        parts = re.split(r'(?<=[：:])', text, maxsplit=1)
        if len(parts) == 2 and all(part and self.width(part, font) <= width for part in parts):
            return parts
        lines = self.wrap(text, font, width)
        if len(lines) == 2 and self.width(lines[1], font) < width * .4:
            options = []
            for i in range(1, len(text)):
                a, b = text[:i], text[i:]
                if b[0] in self.closing or a[-1] in self.opening:
                    continue
                if re.match(r'[A-Za-z0-9_]', a[-1]) and re.match(r'[A-Za-z0-9_]', b[0]):
                    continue
                wa, wb = self.width(a, font), self.width(b, font)
                if max(wa, wb) <= width:
                    options.append((abs(wa - wb), a, b))
            if options:
                _, a, b = min(options)
                lines = [a, b]
        return lines

    @staticmethod
    def clean_body(text: str) -> str:
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'`([^`]+)`', r'\1', text)
        text = re.sub(r'(?m)^#{1,6}\s+', '', text)
        text = re.sub(r'(?m)^>\s*', '', text)
        # Explicit list markers remain; ordinary paragraphs are never converted into lists.
        return text.strip()

    def prepare_pages(self, pages: Sequence[Tuple[str, str]]) -> List[NotePage]:
        prepared = []
        width = self.size[0] - self.px(176)
        for heading, body in pages:
            heading = heading.strip()
            body = self.clean_body(body)
            if not body:
                continue
            title_size = 72
            while True:
                title_rows = self.title_lines(heading, title_size, width) if heading else []
                header_height = len(title_rows) * self.px(title_size * 1.3)
                if header_height <= self.px(285) or title_size <= 32:
                    break
                title_size -= 4
            top = self.px(170) + header_height + (self.px(55) if heading else 0)
            capacity = min(self.size[1] - self.px(155) - top, self.px(820))
            if capacity < self.px(150):
                raise ValueError('页面标题过长，请缩短标题后生成图片')
            body_size = 58 if len(body) <= 100 else 50
            font = self.font(body_size)
            rows = self.wrap(body, font, width)
            line_height = self.px(body_size * 1.6)
            paragraph_gap = self.px(body_size * .68)
            chunk, used = [], 0
            for row in rows:
                height = line_height if row else paragraph_gap
                if chunk and used + height > capacity:
                    while chunk and not chunk[-1]:
                        chunk.pop()
                    prepared.append(NotePage(heading, chunk, title_size, body_size, top))
                    chunk, used = [], 0
                if not row and not chunk:
                    continue
                chunk.append(row)
                used += height
            if chunk:
                prepared.append(NotePage(heading, chunk, title_size, body_size, top))
        return prepared

    def text(self, draw, xy, text, font, fill):
        # 'lt' keeps actual glyph tops aligned across Chinese and Latin text.
        draw.text(xy, text, font=font, fill=fill, anchor='lt')

    def footer(self, draw, page: int, total: int):
        label = f'{page} / {total}'
        font = self.font(25)
        right = self.size[0] - self.px(88)
        self.text(draw, (right - self.width(label, font), self.size[1] - self.px(85)),
                  label, font, self.muted)

    def render_cover(self, title: str, description: str, pages: Sequence[NotePage]) -> Image.Image:
        img = Image.new('RGB', self.size, self.paper)
        draw = ImageDraw.Draw(img)
        w, h = self.size
        left, right = self.px(88), w - self.px(88)
        width = right - left
        size = 90
        while True:
            lines = self.title_lines(title, size, width)
            height = len(lines) * self.px(size * 1.27)
            if height <= self.px(420) or size <= 30:
                break
            size -= 4
        if height > self.px(420):
            raise ValueError('封面标题过长，请缩短标题后生成图片')
        y = self.px(210)
        for i, line in enumerate(lines):
            self.text(draw, (left, y), line, self.font(size, True), self.ink)
            y += self.px(size * 1.27)
        y += self.px(43)
        desc_size = 48
        description = description.strip()
        while description:
            desc_rows = self.wrap(description, self.font(desc_size), width)
            if y + len(desc_rows) * self.px(desc_size * 1.55) < h - self.px(155):
                break
            if desc_size <= 26:
                raise ValueError('封面说明过长，请缩短说明后生成图片')
            desc_size -= 2
        for line in self.wrap(description, self.font(desc_size), width) if description else []:
            self.text(draw, (left, y), line, self.font(desc_size), self.muted)
            y += self.px(desc_size * 1.55)
        self.footer(draw, 1, len(pages) + 1)
        return img

    def render_page(self, page: NotePage, index: int, total: int) -> Image.Image:
        img = Image.new('RGB', self.size, self.paper)
        draw = ImageDraw.Draw(img)
        w = self.size[0]
        left, right = self.px(88), w - self.px(88)
        y = self.px(170)
        for line in self.title_lines(page.title, page.title_size, right-left):
            self.text(draw, (left, y), line, self.font(page.title_size, True), self.ink)
            y += self.px(page.title_size * 1.3)
        block_height = sum(self.px(page.body_size * (1.6 if row else .68)) for row in page.rows)
        # Short copy sits closer to the middle; dense copy starts directly below the title.
        spare = self.size[1] - self.px(185) - page.body_top - block_height
        y = page.body_top + max(0, min(self.px(105), int(spare * .22)))
        for row in page.rows:
            if row:
                self.text(draw, (left, y), row, self.font(page.body_size), self.ink)
                y += self.px(page.body_size * 1.6)
            else:
                y += self.px(page.body_size * .68)
        self.footer(draw, index, total)
        return img

    def save(self, output_dir: Path, prefix: str, title: str, description: str,
             pages: Sequence[Tuple[str, str]]) -> Tuple[str, List[str]]:
        prepared = self.prepare_pages(pages)
        output_dir.mkdir(parents=True, exist_ok=True)
        cover_path = output_dir / f'cover_note_{prefix}.jpg'
        self.render_cover(title, description, prepared).save(cover_path, quality=95)
        paths = []
        for i, page in enumerate(prepared, 2):
            path = output_dir / f'content_note_{i-1}_{prefix}.jpg'
            self.render_page(page, i, len(prepared)+1).save(path, quality=95)
            paths.append(str(path))
        return str(cover_path), paths
