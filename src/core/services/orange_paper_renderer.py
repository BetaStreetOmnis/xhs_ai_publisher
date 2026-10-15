"""Editable orange/white posters with bundled illustration and heavy CJK type."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from src.core.services.screenshot_story_renderer import ScreenshotStoryRenderer, render_screenshot_story


ASSETS = Path(__file__).resolve().parents[3] / 'assets'


class OrangePaperRenderer(ScreenshotStoryRenderer):
    def __init__(self, font_factory, size=(1080, 1440)):
        super().__init__(font_factory, size)
        self.paper = '#FFFFFF'
        self.ink = self.accent = '#111111'
        self.muted = '#3D3028'
        self.peach = '#FFF0E2'

    def font(self, size, bold=False):
        key = ('orange-paper', size, bold)
        if key not in self._fonts:
            path = ASSETS / 'fonts' / 'NotoSansSC.ttf'
            if not path.exists():
                raise FileNotFoundError('橙白模板字体缺失，请重新安装模板资源')
            font = ImageFont.truetype(str(path), self.px(size))
            font.set_variation_by_axes([900 if bold else 500])
            self._fonts[key] = font
        return self._fonts[key]

    def chunks(self, heading, body, illustrated):
        rows = self.wrap(self.clean_body(body), self.font(40), self.size[0] - self.px(176))
        result, chunk, used = [], [], 0
        capacity = self.px(360 if illustrated else 780)
        for row in rows:
            height = self.px(64 if row else 28)
            if chunk and used + height > capacity:
                result.append(chunk)
                chunk, used, capacity = [], 0, self.px(780)
            chunk.append(row)
            used += height
        if chunk or not result:
            result.append(chunk)
        return result

    def draw_page(self, heading, rows, assets, brand, index, total):
        image = Image.new('RGB', self.size, self.paper)
        draw = ImageDraw.Draw(image)
        p = self.px
        left, width = p(64), self.size[0] - p(128)
        size = 148 if index == 1 else 108
        while True:
            headings = self.title_lines(heading, size, width) if heading else []
            if len(headings) * p(size * 1.22) <= p(350):
                break
            if size <= 32:
                raise ValueError('橙白模板标题过长，请缩短标题')
            size -= 4
        y = p(64)
        for line in headings:
            self.text(draw, (left, y), line, self.font(size, True), self.ink)
            y += p(size * 1.22)
        if headings:
            y += p(32)
        body_height = sum(p(64 if row else 28) for row in rows)
        bottom = self.size[1] - p(138)
        # Cover: illustration leads; supplied copy forms a readable bottom strip.
        # Body pages: the source text leads, then the selected screenshot/art.
        if index == 1 and assets:
            photo_bottom = bottom - (body_height + p(64) if rows else 0)
            self.draw_assets(image, draw, assets, y, photo_bottom, left, width)
            y = photo_bottom + p(36)
        if rows:
            panel_bottom = y + body_height + p(24)
            if panel_bottom > bottom:
                raise ValueError('橙白模板正文超出页面，请缩短标题')
            draw.rounded_rectangle((left, y - p(16), left + width, panel_bottom), radius=p(24), fill=self.peach)
            for row in rows:
                if row:
                    self.text(draw, (left + p(24), y), row, self.font(40), self.muted)
                y += p(64 if row else 28)
            y += p(48)
        if index != 1 and assets:
            self.draw_assets(image, draw, assets, y, bottom, left, width)
        if brand:
            self.text(draw, (left, self.size[1] - p(74)), brand, self.font(28), self.muted)
        self.footer(draw, index, total)
        return image

    def draw_assets(self, image, draw, assets, top, bottom, left, width):
        loaded, label_height = [], 0
        for entry in assets:
            with Image.open(Path(entry['path']).expanduser()) as source:
                photo = ImageOps.exif_transpose(source).convert('RGBA')
            label = str(entry.get('label') or '').strip()
            label_rows = self.wrap(label, self.font(30), width) if label else []
            label_height += len(label_rows) * self.px(45) + (self.px(16) if label_rows else 0)
            loaded.append((photo, label_rows))
        available = bottom - top - label_height - self.px(28) * (len(loaded) - 1)
        if available < self.px(120):
            raise ValueError('配图空间不足，请减少文字或图片')
        natural = sum(photo.height * width / photo.width for photo, _ in loaded)
        factor = min(1, available / natural)
        # Center the artwork vertically if it needs less than its reserved space.
        y = top + max(0, round((available - natural * factor) / 2))
        for photo, label_rows in loaded:
            for line in label_rows:
                self.text(draw, (left, y), line, self.font(30, True), self.ink)
                y += self.px(45)
            if label_rows:
                y += self.px(16)
            fitted = ImageOps.contain(photo, (max(1, round(width * factor)), max(1, round(photo.height * width / photo.width * factor))))
            image.paste(fitted, (left + (width - fitted.width) // 2, y), fitted)
            y += fitted.height + self.px(28)


def render_orange_paper(content, out_dir, font_factory, size=(1080, 1440)):
    payload = dict(content)
    if not payload.get('asset_image_path'):
        payload['asset_image_path'] = str(ASSETS / 'orange_paper' / 'hero.png')
    pages, selections = [], payload.get('page_asset_paths') or []
    if not isinstance(selections, (list, tuple)):
        raise ValueError('正文配图需要按页提供图片列表')
    for n, page in enumerate(payload.get('pages') or []):
        if not isinstance(page, dict):
            continue
        revised = dict(page)
        # Explicit empty slots stay empty. Built-in art only fills unset slots.
        if 'images' not in revised:
            if n < len(selections):
                revised['images'] = [{'path': selections[n]}] if selections[n] else []
            else:
                revised['images'] = [{'path': str(ASSETS / 'orange_paper' / 'checklist.png')}]
        pages.append(revised)
    payload['pages'] = pages
    return render_screenshot_story(payload, out_dir, font_factory, size, renderer_type=OrangePaperRenderer)
