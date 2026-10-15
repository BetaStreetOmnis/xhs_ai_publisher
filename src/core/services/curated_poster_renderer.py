"""Three distinct reusable layouts; source copy and selected images stay intact."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from src.core.services.orange_paper_renderer import ASSETS, OrangePaperRenderer
from src.core.services.screenshot_story_renderer import render_screenshot_story


class CuratedPosterRenderer(OrangePaperRenderer):
    layout = 'editorial_cream'

    def __init__(self, font_factory, size=(1080, 1440)):
        super().__init__(font_factory, size)
        palette = {
            'editorial_cream': ('#FAF6EF', '#29231F', '#574B42', '#EBE2D5'),
            'checklist_lemon': ('#FFF7D6', '#191915', '#403A23', '#FFFFFF'),
            'paper_mint': ('#F0F7F0', '#163D2C', '#365745', '#DEECDF'),
        }[self.layout]
        self.paper, self.ink, self.muted, self.peach = palette

    def font(self, size, bold=False):
        if self.layout == 'editorial_cream' and bold:
            path = Path('/System/Library/Fonts/Supplemental/Songti.ttc')
            if path.exists():
                key = ('cream-display', size)
                if key not in self._fonts:
                    self._fonts[key] = ImageFont.truetype(str(path), self.px(size), index=1)
                return self._fonts[key]
        return super().font(size, bold)

    def chunks(self, heading, body, illustrated):
        width = self.size[0]-self.px(176)
        rows = self.wrap(self.clean_body(body), self.font(40), width)
        groups, chunk, used = [], [], 0
        capacity = self.px(360 if illustrated else 780)
        for row in rows:
            height = self.px(64 if row else 28)
            if chunk and used+height > capacity:
                groups.append(chunk)
                chunk, used, capacity = [], 0, self.px(780)
            chunk.append(row)
            used += height
        if chunk or not groups:
            groups.append(chunk)
        return groups

    def draw_page(self, heading, rows, assets, brand, index, total):
        image = Image.new('RGB', self.size, self.paper)
        draw = ImageDraw.Draw(image)
        p = self.px
        left, width = p(72), self.size[0]-p(144)
        size = 136 if index == 1 else 96
        while True:
            headings = self.title_lines(heading, size, width) if heading else []
            if len(headings)*p(size*1.24) <= p(330):
                break
            if size <= 32:
                raise ValueError('模板标题过长，请缩短标题')
            size -= 4
        y = p(92 if self.layout == 'editorial_cream' else 64)
        for line in headings:
            self.text(draw, (left,y), line, self.font(size,True), self.ink)
            y += p(size*1.24)
        y += p(44) if headings else 0
        bottom = self.size[1]-p(138)
        body_height = sum(p(64 if row else 28) for row in rows)
        if y+body_height+p(24) > bottom:
            raise ValueError('正文超出页面，请缩短标题')
        if self.layout == 'checklist_lemon' and rows:
            draw.rounded_rectangle((left-p(16),y-p(20),left+width+p(16),y+body_height+p(24)),radius=p(20),fill='#FFFFFF')
        if self.layout == 'editorial_cream' and headings:
            draw.line((left,y-p(24),left+width,y-p(24)),fill=self.peach,width=p(2))
        for row in rows:
            if row:
                self.text(draw, (left,y), row, self.font(40), self.muted)
            elif self.layout == 'checklist_lemon':
                draw.line((left,y+p(8),left+width,y+p(8)),fill='#EFE7C9',width=p(1))
            y += p(64 if row else 28)
        if assets:
            self.draw_assets(image,draw,assets,y+p(44),bottom,left,width)
        if brand:
            self.text(draw,(left,self.size[1]-p(74)),brand,self.font(28),self.muted)
        self.footer(draw,index,total)
        return image


class CreamRenderer(CuratedPosterRenderer):
    layout = 'editorial_cream'


class LemonRenderer(CuratedPosterRenderer):
    layout = 'checklist_lemon'


class MintRenderer(CuratedPosterRenderer):
    layout = 'paper_mint'


def render_curated_poster(content, out_dir, font_factory, size=(1080,1440)):
    classes = {'editorial_cream':CreamRenderer,'checklist_lemon':LemonRenderer,'paper_mint':MintRenderer}
    layout = content['poster_layout']
    payload = dict(content)
    default = ASSETS / ('orange_paper/hero.png' if layout == 'editorial_cream' else 'curated_paper/lemon.png' if layout == 'checklist_lemon' else 'curated_paper/mint.png')
    payload.setdefault('asset_image_path', str(default))
    if not payload['asset_image_path']:
        payload['asset_image_path'] = str(default)
    selections = payload.get('page_asset_paths') or []
    if not isinstance(selections,(list,tuple)):
        raise ValueError('正文配图需要按页提供图片列表')
    pages = []
    for n,page in enumerate(payload.get('pages') or []):
        if not isinstance(page,dict):
            continue
        revised = dict(page)
        if 'images' not in revised:
            revised['images'] = ([{'path':selections[n]}] if selections[n] else []) if n < len(selections) else [{'path':str(default)}]
        pages.append(revised)
    payload['pages'] = pages
    return render_screenshot_story(payload,out_dir,font_factory,size,renderer_type=classes[layout])
