"""Marketing pages composed from supplied fields, without fabricated filler or CTAs."""
from pathlib import Path
from typing import Any, Callable

from src.core.services.poster_template_renderer import PosterTemplateRenderer


def text(value: Any) -> str:
    return str(value or '').strip()


def items(value: Any) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [text(item) for item in value if text(item)]
    return [text(value)] if text(value) else []


def marketing_sections(content: dict) -> list[tuple[str, str, str]]:
    sections = []
    # New drafts carry authored page headings and paragraphs. Legacy saved
    # drafts retain their previous fields and remain renderable below.
    for page in content.get('pages') or []:
        if isinstance(page, dict) and (body := text(page.get('body'))):
            sections.append((text(page.get('title')), body, 'showcase_pink_note'))
    if sections:
        return sections
    outline = items(content.get('outline_items'))
    if outline:
        sections.append(('内容一览', '\n\n'.join(outline), 'showcase_minimal_lines'))
    highlights = []
    for item in content.get('highlights') or []:
        if isinstance(item, dict):
            entry = '\n'.join(filter(None, [text(item.get('title')), text(item.get('desc') or item.get('description'))]))
            if entry:
                highlights.append(entry)
    if highlights:
        sections.append(('功能说明', '\n\n'.join(highlights), 'showcase_grid_2x2_professional'))
    steps = items(content.get('delivery_steps'))
    if steps:
        sections.append(('使用步骤', '\n\n'.join(f'{i}. {step}' for i,step in enumerate(steps,1)), 'showcase_timeline_vertical_elegant'))
    points = items(content.get('pain_points'))
    if points:
        sections.append(('遇到的问题', '\n\n'.join(points), 'showcase_pink_note'))
    audience = []
    for item in content.get('audience') or []:
        if isinstance(item, dict):
            entry = '\n'.join(filter(None, [text(item.get('title')), *items(item.get('bullets'))]))
            if entry:
                audience.append(entry)
    if audience:
        sections.append(('适用场景', '\n\n'.join(audience), 'showcase_mint_dots_wave'))
    return sections


def render_marketing(content: dict, out_dir: Path, font_factory: Callable, size=(1080,1440)) -> list[dict[str,str]]:
    if content.get('poster_layout') in ('editorial_cream', 'checklist_lemon', 'paper_mint'):
        from src.core.services.curated_poster_renderer import render_curated_poster
        return render_curated_poster(content, out_dir, font_factory, size)
    if content.get('poster_layout') == 'orange_paper':
        from src.core.services.orange_paper_renderer import render_orange_paper
        return render_orange_paper(content, out_dir, font_factory, size)
    if content.get('poster_layout') == 'screenshot_story':
        from src.core.services.screenshot_story_renderer import render_screenshot_story
        return render_screenshot_story(content, out_dir, font_factory, size)
    out_dir.mkdir(parents=True,exist_ok=True)
    title = text(content.get('title')) or '未命名海报'
    # Only authored fields appear; keyword alone is not consent to invent a CTA.
    description = '\n\n'.join(filter(None, [text(content.get('subtitle')), '\n'.join(items(content.get('cover_bullets'))),
                                            text(content.get('price')), text(content.get('cta')), text(content.get('disclaimer'))]))
    prepared = []
    asset_paths = content.get('page_asset_paths') or []
    if not isinstance(asset_paths, (list,tuple)):
        raise ValueError('正文配图需要按页提供图片列表')
    for n,(heading,body,template_id) in enumerate(marketing_sections(content)):
        renderer = PosterTemplateRenderer(font_factory,size,template_id)
        paths = [asset_paths[n]] if n < len(asset_paths) else []
        pages = renderer.prepare_illustrated_pages([(heading,body)],paths) if paths else renderer.prepare_pages([(heading,body)])
        prepared.extend((renderer,page) for page in pages)
    if not prepared:
        body = text(content.get('caption')) or text(content.get('subtitle'))
        if body:
            renderer = PosterTemplateRenderer(font_factory,size)
            prepared.extend((renderer,page) for page in renderer.prepare_pages([('',body)]))
    story = any(isinstance(page, dict) and text(page.get('body')) for page in content.get('pages') or [])
    renderer = PosterTemplateRenderer(font_factory,size,'showcase_pink_note' if story else 'showcase_mkt_product_showcase_professional')
    asset_path = text(content.get('asset_image_path'))
    if asset_path:
        method = renderer.render_story_cover if story else renderer.render_asset_cover
        cover = method(title,description,str(Path(asset_path).expanduser()),len(prepared)+1)
    else:
        cover = renderer.render_cover(title,description,[page for _,page in prepared])
    cover_path = out_dir/'01_cover.png'
    cover.save(cover_path,optimize=True)
    results = [{'title': '封面', 'image_path':str(cover_path)}]
    for i,(renderer,page) in enumerate(prepared,2):
        path = out_dir/f'{i:02d}_content.png'
        renderer.render_page(page,i,len(prepared)+1).save(path,optimize=True)
        results.append({'title':page.title,'image_path':str(path)})
    return results
