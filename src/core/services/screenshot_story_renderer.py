"""Screenshot-led reading pages using the established warm paper palette."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from src.core.services.poster_template_renderer import PosterTemplateRenderer


class ScreenshotStoryRenderer(PosterTemplateRenderer):
    def __init__(self, font_factory, size=(1080, 1440)):
        super().__init__(font_factory, size, 'showcase_creative_poster_nature')
        self.paper, self.ink, self.muted, self.accent = '#FBF7EE', '#342A20', '#675541', '#204837'

    def chunks(self, heading, body, illustrated):
        """Keep the entire supplied text; only the first continuation has images."""
        rows = self.wrap(self.clean_body(body), self.font(40), self.size[0] - self.px(144))
        groups, chunk, used = [], [], 0
        capacity = self.px(600 if illustrated else 780)
        for row in rows:
            height = self.px(64 if row else 28)
            if chunk and used + height > capacity:
                groups.append(chunk)
                chunk, used = [], 0
                capacity = self.px(780)
            chunk.append(row)
            used += height
        if chunk or not groups:
            groups.append(chunk)
        return groups

    def draw_page(self, heading, rows, assets, brand, index, total):
        image = Image.new('RGB', self.size, self.paper)
        draw = ImageDraw.Draw(image)
        p = self.px
        left, width = p(72), self.size[0] - p(144)
        size = 108 if index == 1 else 90
        while True:
            headings = self.title_lines(heading, size, width) if heading else []
            if len(headings) * p(size * 1.28) <= p(285):
                break
            if size <= 32:
                raise ValueError('图文标题过长，请缩短标题')
            size -= 4
        y = p(74)
        for n, line in enumerate(headings):
            color = self.accent if len(headings) > 1 and n == len(headings) - 1 else self.ink
            self.text(draw, (left, y), line, self.font(size, True), color)
            y += p(size * 1.28)
        y += p(32) if headings and rows else 0
        for row in rows:
            if row:
                self.text(draw, (left, y), row, self.font(40), self.muted)
            y += p(64 if row else 28)
        if assets:
            y += p(36)
            loaded = []
            label_height = 0
            for asset in assets:
                with Image.open(Path(asset['path']).expanduser()) as source:
                    photo = ImageOps.exif_transpose(source).convert('RGBA')
                label = str(asset.get('label') or '').strip()
                label_rows = self.wrap(label, self.font(30), width) if label else []
                label_height += len(label_rows) * p(45) + (p(16) if label_rows else 0)
                loaded.append((photo, label_rows))
            available = self.size[1] - p(126) - y - label_height - p(32) * (len(loaded) - 1)
            natural_height = sum(photo.height * width / photo.width for photo, _ in loaded)
            if available < p(160):
                raise ValueError('配图说明过长，请缩短说明或减少图片')
            factor = min(1, available / natural_height)
            for photo, label_rows in loaded:
                for line in label_rows:
                    self.text(draw, (left, y), line, self.font(30, True), self.accent)
                    y += p(45)
                if label_rows:
                    y += p(16)
                fitted = ImageOps.contain(photo, (round(width * factor), round(photo.height * width / photo.width * factor)))
                image.paste(fitted, (left + (width - fitted.width) // 2, y), fitted)
                y += fitted.height + p(32)
        if brand:
            self.text(draw, (left, self.size[1] - p(74)), brand, self.font(28), self.muted)
        self.footer(draw, index, total)
        return image


def render_screenshot_story(content, out_dir, font_factory, size=(1080, 1440), *, renderer_type=ScreenshotStoryRenderer):
    from src.core.services.marketing_poster_layout import items, marketing_sections, text
    renderer = renderer_type(font_factory, size)
    brand = str(content.get('brand') or '').strip()
    selections = content.get('page_asset_paths') or []
    description = '\n\n'.join(filter(None, [text(content.get('subtitle')), '\n'.join(items(content.get('cover_bullets'))),
                                           text(content.get('price')), text(content.get('cta')), text(content.get('disclaimer'))]))
    authored = [(str(content.get('title') or '未命名图文'), description,
                 [{'path': content['asset_image_path']}] if content.get('asset_image_path') else [])]
    for n, page in enumerate(content.get('pages') or []):
        if not isinstance(page, dict) or not str(page.get('body') or '').strip():
            continue
        assets = page.get('images')
        if assets is None:
            assets = [{'path': selections[n]}] if n < len(selections) and selections[n] else []
        if not isinstance(assets, list) or any(not isinstance(a, dict) or not a.get('path') for a in assets):
            raise ValueError('正文图片格式无效')
        authored.append((str(page.get('title') or ''), str(page['body']), assets))
    if len(authored) == 1:
        authored.extend((heading, body, []) for heading, body, _ in marketing_sections(content))
        if len(authored) == 1 and content.get('caption'):
            authored.append(('', str(content['caption']), []))
    prepared = []
    for heading, body, assets in authored:
        for n, rows in enumerate(renderer.chunks(heading, body, bool(assets))):
            prepared.append((heading, rows, assets if n == 0 else []))
    out_dir.mkdir(parents=True, exist_ok=True)
    result = []
    for n, (heading, rows, assets) in enumerate(prepared, 1):
        path = out_dir / ('01_cover.png' if n == 1 else f'{n:02d}_content.png')
        renderer.draw_page(heading, rows, assets, brand, n, len(prepared)).save(path, optimize=True)
        result.append({'title': '封面' if n == 1 else heading, 'image_path': str(path)})
    return result
