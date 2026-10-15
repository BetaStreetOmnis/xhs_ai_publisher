"""Measured layouts for bundled posters. User-supplied backgrounds stay external."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from PIL import Image, ImageDraw, ImageFont, ImageOps

from src.core.services.note_image_renderer import NoteImageRenderer, NotePage


@dataclass(frozen=True)
class PosterStyle:
    family: str
    paper: str
    ink: str
    muted: str
    accent: str
    tint: str


# Every bundled ID is explicit: a similarly named uploaded image is not a template.
TEMPLATE_FAMILIES = {
    'showcase_pink_note': 'memo',
    'showcase_lavender_wave': 'memo',
    'showcase_mint_dots_wave': 'memo',
    'showcase_minimal_lines': 'editorial',
    'showcase_creative_poster_nature': 'editorial',
    'showcase_biz_announcement_cool': 'announcement',
    'showcase_edu_course_intro_elegant': 'course',
    'showcase_edu_exam_focus_vibrant': 'course',
    'showcase_edu_grade_card_professional': 'course',
    'showcase_edu_grade_card_alt1_warm': 'course',
    'showcase_edu_grade_card_alt2_nature': 'course',
    'showcase_biz_metrics_card_warm': 'metrics',
    'showcase_biz_metrics_card_alt1_nature': 'metrics',
    'showcase_biz_metrics_card_alt2_professional': 'metrics',
    'showcase_mkt_promo_banner_nature': 'promo',
    'showcase_mkt_product_showcase_professional': 'product',
    'showcase_marketing_poster': 'product',
    'showcase_social_quote_card_vibrant': 'quote',
    'showcase_social_quote_card_alt1_professional': 'quote',
    'showcase_social_quote_card_alt2_elegant': 'quote',
    'showcase_social_story_card_tech': 'editorial',
    'showcase_grid_2x2_professional': 'grid',
    'showcase_tech_comparison_cool': 'comparison',
    'showcase_timeline_vertical_elegant': 'timeline',
    'showcase_cert_achievement_tech': 'certificate',
}


def style_for(template_id: str) -> PosterStyle:
    family = TEMPLATE_FAMILIES.get(template_id, 'memo')
    palette = ('#FBF7EE', '#342A20', '#675541', '#946037', '#F4E8CF')
    if any(x in template_id for x in ('nature', 'mint')):
        palette = ('#F4F7F1', '#233B32', '#53685D', '#356852', '#E0EBE0')
    elif any(x in template_id for x in ('professional', 'cool', 'tech')):
        palette = ('#F1F4F6', '#22394C', '#536779', '#365D7D', '#E0E8EF')
    elif 'pink' in template_id:
        palette = ('#FBF4F3', '#4B3034', '#78575C', '#9B485D', '#F4DFE1')
    elif 'lavender' in template_id:
        palette = ('#F6F3F8', '#41344D', '#6E6078', '#795887', '#E9E0EF')
    elif 'vibrant' in template_id:
        palette = ('#FFF7EE', '#4B3025', '#755646', '#A94C2A', '#F8E1C9')
    return PosterStyle(family, *palette)


def bundled_template_id(path: Path | None) -> str:
    if not path:
        return ''
    bundled = Path(__file__).resolve().parents[3] / 'assets/system_templates/template_showcase'
    resolved = path.resolve()
    if resolved.parent == bundled and resolved.stem in TEMPLATE_FAMILIES:
        return resolved.stem
    return ''


class PosterTemplateRenderer(NoteImageRenderer):
    """Keep measured text flow; style the cover and its accompanying reading pages."""

    def __init__(self, font_factory: Callable, size=(1080, 1440), template_id=''):
        super().__init__(font_factory, size)
        self.template_id = template_id
        self.style = style_for(template_id)
        for name in ('paper', 'ink', 'muted', 'accent', 'tint'):
            setattr(self, name, getattr(self.style, name))

    def font(self, size: int, bold: bool = False):
        # Keep the reading/quote identity; functional covers need stronger type.
        if not bold or self.style.family in ('course', 'metrics', 'announcement', 'promo', 'product', 'grid', 'comparison', 'timeline'):
            path = Path(__file__).resolve().parents[3] / 'assets/fonts/NotoSansSC.ttf'
            if path.exists():
                weight = (900 if self.style.family in ('product', 'promo') else 800) if bold else 400
                key = ('template-sans', size, weight)
                if key not in self._fonts:
                    font = ImageFont.truetype(str(path), self.px(size))
                    font.set_variation_by_axes([weight])
                    self._fonts[key] = font
                return self._fonts[key]
        if bold:
            path = Path('/System/Library/Fonts/Supplemental/Songti.ttc')
            if path.exists():
                key = ('poster-display', size)
                if key not in self._fonts:
                    self._fonts[key] = ImageFont.truetype(str(path), self.px(size), index=1)
                return self._fonts[key]
        return super().font(size, bold)

    def surface(self, *, cover=False):
        img = Image.new('RGB', self.size, self.paper)
        d = ImageDraw.Draw(img)
        w, h = self.size
        p = self.px
        family = self.style.family
        if family == 'memo':
            d.rounded_rectangle((p(44), p(100), w-p(44), h-p(125)), radius=p(20), fill='#FFFDFA')
            d.rounded_rectangle((w//2-p(118), p(64), w//2+p(118), p(116)), radius=p(4), fill=self.tint)
        elif family == 'certificate':
            d.rectangle((p(40), p(40), w-p(40), h-p(40)), outline=self.accent, width=p(2))
            d.rectangle((p(55), p(55), w-p(55), h-p(55)), outline=self.tint, width=p(1))
        elif cover and family in ('product', 'promo', 'metrics'):
            d.rectangle((0, int(h*.54), w, h), fill=self.tint)
        elif family == 'course':
            d.rectangle((0, 0, p(28), h), fill=self.accent)
            d.line((p(88), p(107), w-p(88), p(107)), fill=self.accent, width=p(2))
        elif cover and family == 'announcement':
            d.rectangle((0, 0, w, int(h*.54)), fill=self.tint)
        elif cover and family == 'quote':
            d.line((w//2-p(54), p(220), w//2+p(54), p(220)), fill=self.accent, width=p(2))
        elif cover and family == 'timeline':
            d.line((p(60), p(200), p(60), h-p(200)), fill=self.accent, width=p(2))
        else:
            d.line((p(88), p(107), w-p(88), p(107)), fill=self.accent, width=p(2))
        return img

    def render_cover(self, title: str, description: str, pages: Sequence[NotePage]):
        img = self.surface(cover=True)
        d = ImageDraw.Draw(img)
        left = self.px(88)
        width = self.size[0]-2*left
        family = self.style.family
        size = 148 if family in ('promo', 'product', 'editorial', 'metrics') else 124
        while True:
            lines = self.title_lines(title, size, width)
            height = len(lines)*self.px(size*1.3)
            if height <= self.px(420) or size <= 30:
                break
            size -= 4
        if height > self.px(420):
            raise ValueError('封面标题过长，请缩短标题后生成图片')
        y = self.px(350 if family == 'quote' else 185)
        for line in lines:
            x = left
            if family in ('quote', 'certificate'):
                x = (self.size[0]-self.width(line, self.font(size, True))) / 2
            self.text(d, (x,y), line, self.font(size,True), self.ink)
            y += self.px(size*1.3)
        if family in ('product', 'promo', 'metrics', 'announcement'):
            y = max(y+self.px(65), self.px(855))
        else:
            y += self.px(70)
            if family not in ('grid', 'comparison'):
                d.line((left, y-self.px(30), left+self.px(108), y-self.px(30)), fill=self.accent, width=self.px(2))
        description = self.clean_body(description)
        blocks = [block.strip() for block in description.split('\n\n') if block.strip()]
        if family in ('grid', 'comparison', 'metrics') and 2 <= len(blocks) <= 4:
            if self.draw_cover_columns(d, blocks, y, left, width):
                self.footer(d, 1, len(pages)+1)
                return img
        sequence_top = y if family in ('course', 'timeline') and 2 <= len(blocks) <= 5 else None
        body_size = 52
        while description:
            rows = self.wrap(description, self.font(body_size), width)
            if y+len(rows)*self.px(body_size*1.55) <= self.size[1]-self.px(185):
                break
            if body_size <= 28:
                raise ValueError('封面说明过长，请缩短说明后生成图片')
            body_size -= 2
        for line in self.wrap(description, self.font(body_size), width) if description else []:
            x = (self.size[0]-self.width(line,self.font(body_size)))/2 if self.style.family in ('quote','certificate') else left
            self.text(d, (x,y), line, self.font(body_size), self.muted)
            y += self.px(body_size*1.55)
        if sequence_top is not None:
            # Connect authored steps only, ending alongside the last text row.
            marker_x = left-self.px(26)
            d.line((marker_x, sequence_top, marker_x, y-self.px(body_size*.65)), fill=self.tint, width=self.px(2))
        self.footer(d, 1, len(pages)+1)
        return img

    def draw_cover_columns(self, draw, blocks, top, left, width):
        gap = self.px(56)
        column = (width-gap)//2
        rows_count = (len(blocks)+1)//2
        cell_height = (self.size[1]-self.px(175)-top)//rows_count
        for size in range(48, 29, -2):
            layouts = [self.wrap(block, self.font(size), column) for block in blocks]
            if all(len(rows)*self.px(size*1.55) <= cell_height-self.px(48) for rows in layouts):
                break
        else:
            return False
        for n, rows in enumerate(layouts):
            x = left+(n%2)*(column+gap)
            y = top+(n//2)*cell_height
            draw.line((x, y-self.px(18), x+self.px(64), y-self.px(18)), fill=self.accent, width=self.px(2))
            for row_index, line in enumerate(rows):
                bold = row_index == 0 and '\n' in blocks[n] and self.width(line, self.font(size,True)) <= column
                self.text(draw, (x,y), line, self.font(size,bold), self.ink)
                y += self.px(size*1.55)
        return True

    def render_page(self, page: NotePage, index: int, total: int):
        if page.asset_path:
            return self.render_illustrated_page(page, index, total)
        img = self.surface()
        d = ImageDraw.Draw(img)
        left = self.px(88)
        width = self.size[0]-2*left
        y = self.px(170)
        for line in self.title_lines(page.title, page.title_size, width) if page.title.strip() else []:
            self.text(d,(left,y),line,self.font(page.title_size,True),self.ink)
            y += self.px(page.title_size*1.3)
        y = page.body_top
        blocks = []
        for row in page.rows:
            if row:
                if not blocks:
                    blocks.append([])
                blocks[-1].append(row)
            elif blocks and blocks[-1]:
                blocks.append([])
        blocks = [block for block in blocks if block]
        if self.style.family in ('grid', 'comparison') and 2 <= len(blocks) <= 4:
            gap = self.px(48)
            col_width = (width-gap)//2
            cell_height = (self.size[1]-self.px(185)-y)//2
            laid_out = [self.wrap('\n'.join(block),self.font(42),col_width) for block in blocks]
            if all(len(rows)*self.px(67) <= cell_height-self.px(40) for rows in laid_out):
                for i,rows in enumerate(laid_out):
                    x = left+(i%2)*(col_width+gap)
                    top = y+(i//2)*cell_height
                    d.line((x,top-self.px(20),x+col_width,top-self.px(20)),fill=self.accent,width=self.px(2))
                    for row in rows:
                        self.text(d,(x,top),row,self.font(42),self.ink)
                        top += self.px(67)
                self.footer(d,index,total)
                return img
        if self.style.family == 'timeline':
            # The existing authored step numbers carry sequence; the line is a
            # quiet connector and does not add steps or labels to the content.
            d.line((left-self.px(28),y,left-self.px(28),self.size[1]-self.px(190)),fill=self.tint,width=self.px(2))
        for row in page.rows:
            if row:
                self.text(d,(left,y),row,self.font(page.body_size),self.ink)
                y += self.px(page.body_size*1.6)
            else:
                y += self.px(page.body_size*.68)
        self.footer(d,index,total)
        return img

    def render_asset_cover(self, title: str, description: str, asset_path: str, total: int):
        """An optional uploaded product image occupies a separate, contained area."""
        with Image.open(asset_path) as source:
            source = ImageOps.exif_transpose(source)
            portrait = source.width / source.height < .8
        if portrait:
            return self.render_story_cover(title, description, asset_path, total)
        img = self.surface(cover=True)
        d = ImageDraw.Draw(img)
        left = self.px(88)
        width = self.size[0]-2*left
        size = 104
        while True:
            rows = self.title_lines(title,size,width)
            if len(rows)*self.px(size*1.3) <= self.px(260):
                break
            if size <= 30:
                raise ValueError('有素材时封面标题过长，请缩短标题')
            size -= 4
        y = self.px(135)
        for row in rows:
            self.text(d,(left,y),row,self.font(size,True),self.ink)
            y += self.px(size*1.3)
        desc_size = 40
        while True:
            rows = self.wrap(self.clean_body(description),self.font(desc_size),width)
            if y+self.px(30)+len(rows)*self.px(desc_size*1.45) <= self.px(590):
                break
            if desc_size <= 24:
                raise ValueError('素材封面说明过长，请缩短说明')
            desc_size -= 2
        y += self.px(30)
        for row in rows:
            self.text(d,(left,y),row,self.font(desc_size),self.muted)
            y += self.px(desc_size*1.45)
        asset_top = max(self.px(565), y+self.px(45))
        asset_height = self.size[1]-self.px(160)-asset_top
        with Image.open(asset_path) as source:
            asset = ImageOps.exif_transpose(source).convert('RGBA')
            asset = ImageOps.contain(asset,(width,asset_height))
            img.paste(asset,((self.size[0]-asset.width)//2,asset_top+(asset_height-asset.height)//2),asset)
        self.footer(d,1,total)
        return img

    def render_story_cover(self, title: str, description: str, asset_path: str, total: int):
        """Give a portrait screenshot space beside the copy; never crop its UI."""
        with Image.open(asset_path) as source:
            asset = ImageOps.exif_transpose(source).convert('RGBA')
        # Wide images keep the existing contained layout. Portraits need more
        # height to remain readable at phone size, rather than a tiny thumbnail.
        if asset.width / asset.height >= .8:
            return self.render_asset_cover(title, description, asset_path, total)
        img = self.surface(cover=True)
        d = ImageDraw.Draw(img)
        left = self.px(88)
        width = self.size[0] - 2*left
        size = 88
        while True:
            rows = self.title_lines(title, size, width)
            height = len(rows) * self.px(size * 1.3)
            if height <= self.px(230):
                break
            if size <= 30:
                raise ValueError('封面标题过长，请缩短标题')
            size -= 4
        y = self.px(170)
        for row in rows:
            self.text(d, (left, y), row, self.font(size, True), self.ink)
            y += self.px(size * 1.3)
        image_top = max(self.px(430), y + self.px(70))
        y = image_top + self.px(60)
        width = self.px(404)
        desc_size = 46
        description = self.clean_body(description)
        while True:
            rows = self.wrap(description, self.font(desc_size), width)
            if y + len(rows) * self.px(desc_size * 1.5) <= self.size[1] - self.px(200):
                break
            if desc_size <= 28:
                raise ValueError('封面说明过长，请缩短说明')
            desc_size -= 2
        for row in rows:
            self.text(d, (left, y), row, self.font(desc_size), self.muted)
            y += self.px(desc_size * 1.5)
        asset_height = self.size[1] - self.px(160) - image_top
        asset = ImageOps.contain(asset, (self.px(444), asset_height))
        img.paste(asset, (self.px(548) + (self.px(444) - asset.width)//2,
                          image_top + (asset_height - asset.height)//2), asset)
        self.footer(d, 1, total)
        return img

    def prepare_illustrated_pages(self, pages, asset_paths):
        """One ordered user-selected image per source page; overflow remains text."""
        prepared = []
        for i, (heading, body) in enumerate(pages):
            asset_path = str(asset_paths[i] or '') if i < len(asset_paths) else ''
            if not asset_path:
                prepared.extend(self.prepare_pages([(heading, body)]))
                continue
            path = Path(asset_path).expanduser()
            # Invalid assets stop generation instead of silently shifting images.
            with Image.open(path) as source:
                source = ImageOps.exif_transpose(source)
                portrait = source.width / source.height < .8
                asset_height = ImageOps.contain(source,(self.size[0]-self.px(176),self.px(460))).height
            title_size = 64
            width = self.size[0] - self.px(176)
            while True:
                title_rows = self.title_lines(heading, title_size, width) if heading else []
                header_height = len(title_rows)*self.px(title_size*1.3)
                if header_height <= self.px(240):
                    break
                if title_size <= 32:
                    raise ValueError('页面标题过长，请缩短标题后生成图片')
                title_size -= 4
            top = self.px(170)+header_height+self.px(65)
            body_top = top if portrait else top+asset_height+self.px(50)
            text_width = self.px(404) if portrait else width
            body_size = 42 if portrait else 46
            capacity = self.size[1]-self.px(175)-body_top
            rows = self.wrap(self.clean_body(body),self.font(body_size),text_width)
            chunk, used, overflow = [], 0, []
            for n, row in enumerate(rows):
                height = self.px(body_size*(1.6 if row else .68))
                if used+height > capacity:
                    overflow = rows[n:]
                    break
                chunk.append(row)
                used += height
            if not chunk and rows:
                raise ValueError('配图页标题过长，请缩短标题')
            prepared.append(NotePage(heading,chunk,title_size,body_size,body_top,str(path)))
            if overflow:
                # Reassemble wrapped lines without inserting paragraph breaks.
                remainder = ''.join(row if row else '\n\n' for row in overflow).strip()
                prepared.extend(self.prepare_pages([(heading,remainder)]))
        return prepared

    def render_illustrated_page(self, page, index, total):
        img = self.surface()
        d = ImageDraw.Draw(img)
        left = self.px(88)
        width = self.size[0]-2*left
        y = self.px(170)
        for row in self.title_lines(page.title,page.title_size,width) if page.title.strip() else []:
            self.text(d,(left,y),row,self.font(page.title_size,True),self.ink)
            y += self.px(page.title_size*1.3)
        top = y+self.px(65)
        with Image.open(page.asset_path) as source:
            asset = ImageOps.exif_transpose(source).convert('RGBA')
        portrait = asset.width / asset.height < .8
        if portrait:
            asset = ImageOps.contain(asset,(self.px(444),self.size[1]-self.px(175)-top))
            x = self.px(548)+(self.px(444)-asset.width)//2
        else:
            asset = ImageOps.contain(asset,(width,self.px(460)))
            x = (self.size[0]-asset.width)//2
        img.paste(asset,(x,top),asset)
        y = page.body_top
        for row in page.rows:
            if row:
                self.text(d,(left,y),row,self.font(page.body_size),self.ink)
            y += self.px(page.body_size*(1.6 if row else .68))
        self.footer(d,index,total)
        return img

    def save_illustrated(self, output_dir, prefix, title, description, pages, asset_paths, cover_asset_path=''):
        prepared = self.prepare_illustrated_pages(pages,asset_paths)
        output_dir.mkdir(parents=True,exist_ok=True)
        cover_path = output_dir/f'cover_note_{prefix}.jpg'
        cover = self.render_asset_cover(title,description,cover_asset_path,len(prepared)+1) if cover_asset_path else self.render_cover(title,description,prepared)
        cover.save(cover_path,quality=95)
        paths = []
        for i,page in enumerate(prepared,2):
            path = output_dir/f'content_note_{i-1}_{prefix}.jpg'
            self.render_page(page,i,len(prepared)+1).save(path,quality=95)
            paths.append(str(path))
        return str(cover_path),paths
