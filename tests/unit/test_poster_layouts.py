"""Bundled layout routing, copy preservation, asset handling and pagination."""
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image
from src.core.services.poster_template_renderer import (
    PosterTemplateRenderer, TEMPLATE_FAMILIES, bundled_template_id,
)
from src.core.services.marketing_poster_layout import marketing_sections, render_marketing
from tests.unit.test_note_images import font_factory, compact


@pytest.mark.parametrize('template_id',TEMPLATE_FAMILIES)
def test_every_template_can_render_long_copy_without_losing_facts(template_id,tmp_path):
    renderer=PosterTemplateRenderer(font_factory,template_id=template_id)
    body=('暂时不能离线同步，实际花费39元。\n\n'*40)+'最后一条记录。'
    pages=renderer.prepare_pages([('使用记录',body)])
    assert len(pages)>3
    assert compact(''.join(row for page in pages for row in page.rows))==compact(body)
    for i,page in enumerate(pages,2):
        assert renderer.render_page(page,i,len(pages)+1).size==(1080,1440)
    assert renderer.render_cover('实际使用记录','保留原稿的限制。',pages).size==(1080,1440)


def test_unknown_uploaded_image_is_not_recognized_as_bundled(tmp_path):
    uploaded=tmp_path/'showcase_pink_note.png'
    Image.new('RGB',(1080,1440),'red').save(uploaded)
    assert not bundled_template_id(uploaded)
    # Resolve from the project root (tests/unit is two directory levels below).
    bundled=Path(__file__).resolve().parents[2]/'assets/system_templates/template_showcase/showcase_pink_note.png'
    assert bundled_template_id(bundled)=='showcase_pink_note'


def test_marketing_retains_all_entries_and_adds_no_filler():
    original=[f'原文条目{i}' for i in range(14)]
    sections=marketing_sections({'outline_items':original,'delivery_steps':['确认需求','按要求修改'],'audience':[{'title':'开发者','bullets':original}]})
    combined='\n'.join(section[1] for section in sections)
    assert all(item in combined for item in original)
    assert '下单' not in combined and '私信' not in combined and '亮点 1' not in combined
    assert marketing_sections({})==[]


def test_marketing_overflow_is_saved_in_extra_images(tmp_path):
    content={'title':'原稿','outline_items':['暂时不能离线同步。'*20 for _ in range(9)]}
    output=render_marketing(content,tmp_path,font_factory)
    assert len(output)>6
    assert all(Path(item['image_path']).exists() for item in output)


def test_price_units_and_contact_prompts_are_not_invented(monkeypatch,tmp_path):
    calls=[]
    original=PosterTemplateRenderer.render_cover
    def cover(renderer,title,desc,pages):
        calls.append(desc)
        return original(renderer,title,desc,pages)
    monkeypatch.setattr(PosterTemplateRenderer,'render_cover',cover)
    render_marketing({'title':'原稿','price':'USD 39 / month','keyword':'咨询','subtitle':'暂时不能离线同步。'},tmp_path,font_factory)
    assert calls==['暂时不能离线同步。\n\nUSD 39 / month']


def test_asset_is_contained_and_transparency_is_preserved(tmp_path):
    source=tmp_path/'asset.png'
    Image.new('RGBA',(200,400),(210,30,60,255)).save(source)
    renderer=PosterTemplateRenderer(font_factory,template_id='showcase_mkt_product_showcase_professional')
    cover=renderer.render_asset_cover('产品','真实素材',str(source),2)
    # Portrait products use the larger sidebar layout, retaining the ratio.
    assert cover.getpixel((770,950))==(210,30,60)
    assert cover.getpixel((100,950))!=(210,30,60)
    assert Image.open(source).size==(200,400)


def test_ordered_body_images_preserve_overflow_and_do_not_repeat(tmp_path):
    source = tmp_path/'phone.png'
    Image.new('RGB',(200,400),(210,30,60)).save(source)
    renderer = PosterTemplateRenderer(font_factory,template_id='showcase_pink_note')
    body = '第一句保留。\n\n' + 'Codex 原会话继续，管家没有全部上下文。'*70 + '最后一句也保留。'
    pages = renderer.prepare_illustrated_pages([('查看任务',body),('另一段','这段不配图。')],[str(source),''])
    assert compact(''.join(row for page in pages[:-1] for row in page.rows)) == compact(body)
    assert pages[0].asset_path == str(source)
    assert all(not p.asset_path for p in pages[1:])
    image = renderer.render_page(pages[0],2,len(pages)+1)
    assert image.getpixel((770,700)) == (210,30,60)


def test_body_image_selection_reaches_marketing_adapter(tmp_path):
    source = tmp_path/'photo.png'
    Image.new('RGB',(800,400),(40,180,80)).save(source)
    result = render_marketing({'title':'查看原会话','pages':[{'title':'实际输出','body':'这是我提供的正文。'}],'page_asset_paths':[str(source)]},tmp_path/'out',font_factory)
    assert len(result) == 2
    image = Image.open(result[1]['image_path'])
    assert image.getpixel((540,500)) == (40,180,80)


def test_missing_selected_image_does_not_shift_later_images(tmp_path):
    renderer = PosterTemplateRenderer(font_factory)
    with pytest.raises(FileNotFoundError):
        renderer.prepare_illustrated_pages([('原文','第一段。')],[str(tmp_path/'missing.png')])


@pytest.mark.parametrize('template_id', ['showcase_grid_2x2_professional', 'showcase_tech_comparison_cool', 'showcase_biz_metrics_card_warm'])
def test_cover_columns_keep_all_supplied_facts_and_fit_canvas(template_id, monkeypatch):
    renderer = PosterTemplateRenderer(font_factory, template_id=template_id)
    title = '两种使用记录'
    description = '第一组\n暂时不能离线，费用39元。\n\n第二组\nCodex 原会话继续，需要自己配置。'
    drawn, boxes = [], []
    original = renderer.text
    def capture(draw, xy, text, font, fill):
        drawn.append(text)
        boxes.append(draw.textbbox(xy,text,font=font,anchor='lt'))
        return original(draw, xy, text, font, fill)
    monkeypatch.setattr(renderer, 'text', capture)
    renderer.render_cover(title, description, [])
    assert compact(description) in compact(''.join(drawn))
    assert all(0 <= b[0] <= b[2] <= 1080 and 0 <= b[1] <= b[3] <= 1440 for b in boxes)


@pytest.mark.parametrize('heading', ['', '查看任务', '查看任务\n实际输出'])
def test_body_starts_below_wide_image_with_and_without_heading(tmp_path, monkeypatch, heading):
    source = tmp_path / 'wide.png'
    color = (210, 30, 60)
    Image.new('RGB', (800, 400), color).save(source)
    renderer = PosterTemplateRenderer(font_factory, template_id='showcase_pink_note')
    body = '这行正文应当在截图下方。'
    page = renderer.prepare_illustrated_pages([(heading, body)], [str(source)])[0]
    positions = []
    original = renderer.text
    def capture(draw, xy, line, font, fill):
        if line == page.rows[0]:
            positions.append(xy[1])
        return original(draw, xy, line, font, fill)
    monkeypatch.setattr(renderer, 'text', capture)
    image = renderer.render_page(page, 2, 2)
    image_bottom = max(y for y in range(image.height) if image.getpixel((540, y)) == color)
    assert positions == [page.body_top]
    assert positions[0] >= image_bottom + renderer.px(50)


@pytest.mark.parametrize('source,returned,expected',[
    ('我做了一个项目，叫办公小镇。','所有功能均基于素材，未添加未经提及的承诺。',''),
    ('我做了一个项目，叫办公小镇（agentBridge）。','办公小镇（agentBridge）',''),
    ('我做了一个项目，叫办公小镇。本文由 AI 辅助整理。','本文由 AI 辅助整理。','本文由 AI 辅助整理。'),
])
def test_model_checklist_does_not_become_a_disclaimer(monkeypatch,tmp_path,source,returned,expected):
    import json
    from src.core.services.llm_service import LLMService
    service=LLMService.__new__(LLMService)
    service.config=SimpleNamespace(load_config=lambda:None,get_model_config=lambda:{})
    monkeypatch.setattr(service,'is_model_configured',lambda _:(True,''))
    monkeypatch.setattr(service,'_call_model',lambda *_:json.dumps({'title':'手机回复','caption':source,'pages':[{'title':'手机回复','body':source}],'disclaimer':returned},ensure_ascii=False))
    assert service.generate_marketing_poster_content(source)['disclaimer']==expected


def test_body_image_selection_reaches_note_adapter(monkeypatch,tmp_path):
    from src.core.services import system_image_template_service as module
    monkeypatch.setenv('XHS_DATA_DIR',str(tmp_path/'settings'))
    service = module.SystemImageTemplateService(config=SimpleNamespace())
    monkeypatch.setattr(module,'font_manager',SimpleNamespace(get_font=font_factory))
    monkeypatch.setattr(service,'choose_pack',lambda _:None)
    monkeypatch.setattr(service,'get_selected_pack_id',lambda:'')
    original = module.os.path.expanduser
    monkeypatch.setattr(module.os.path,'expanduser',lambda p:str(tmp_path) if p=='~' else original(p))
    source = tmp_path/'phone.png'
    Image.new('RGB',(200,400),(210,30,60)).save(source)
    cover,pages = service.generate_post_images('产品介绍','真实正文。',content_pages=['# 查看输出\n\n真实正文。'],page_asset_paths=[str(source)])
    assert len(pages)==1 and Path(cover).exists()
    image=Image.open(pages[0])
    # JPEG tolerance, since the ordinary note adapter saves JPEG images.
    assert all(abs(a-b)<5 for a,b in zip(image.getpixel((770,700)),(210,30,60)))


def test_bundled_selection_routes_to_layout_with_all_content_pages(monkeypatch,tmp_path):
    from src.core.services import system_image_template_service as module
    monkeypatch.setenv('XHS_DATA_DIR',str(tmp_path/'config'))
    service=module.SystemImageTemplateService(config=SimpleNamespace())
    monkeypatch.setattr(module,'font_manager',SimpleNamespace(get_font=font_factory))
    monkeypatch.setattr(service,'choose_pack',lambda _:None)
    monkeypatch.setattr(service,'get_selected_pack_id',lambda:'')
    calls=[]
    def save(renderer,output,prefix,title,desc,pages):
        calls.append((renderer.template_id,title,desc,pages))
        return 'cover', [f'page{i}' for i in range(len(pages))]
    monkeypatch.setattr(PosterTemplateRenderer,'save',save)
    path=Path(module.__file__).resolve().parents[3]/'assets/system_templates/template_showcase/showcase_pink_note.png'
    _,pages=service.generate_post_images('标题','正文',content_pages=[f'原稿{i}' for i in range(5)],page_count=3,cover_bg_image_path=str(path),cover_heading='原稿封面',cover_description='真实说明')
    assert len(pages)==5
    assert calls[0][:3]==('showcase_pink_note','原稿封面','真实说明')


def test_llm_marketing_normalizer_keeps_sparse_source_without_padding(monkeypatch,tmp_path):
    import json
    monkeypatch.setenv('XHS_DATA_DIR',str(tmp_path/'settings'))
    from src.core.services.llm_service import LLMService
    service=LLMService.__new__(LLMService)
    service.config=SimpleNamespace(load_config=lambda:None,get_model_config=lambda:{'system_prompt':''})
    monkeypatch.setattr(service,'_apply_env_model_config_overrides',lambda value:value)
    monkeypatch.setattr(service,'is_model_configured',lambda _: (True,''))
    prompts=[]
    def call(_config,messages):
        prompts.extend(messages)
        return json.dumps({'title':'原稿','cover_bullets':['原有功能'],'outline_items':['保留这一条'],'highlights':[],'audience':[]},ensure_ascii=False)
    monkeypatch.setattr(service,'_call_model',call)
    result=service.generate_marketing_poster_content('这是我提供的素材')
    assert result['cover_bullets']==['原有功能']
    assert result['outline_items']==['保留这一条']
    assert result['delivery_steps']==[] and result['audience']==[] and result['highlights']==[]
    assert result['cta']=='' and result['disclaimer']==''
    assert '不要求凑满六页' in prompts[1]['content']


def test_offline_marketing_preview_is_the_original_source():
    from src.core.services.llm_service import LLMService
    source='最近在做一个小项目。\n暂时不能离线同步，实际花费39元。'
    result=LLMService._generate_default_marketing_poster_content(source)
    assert result['caption']==source
    assert not result['outline_items'] and not result['cover_bullets']
    assert not result['delivery_steps'] and not result['audience']


def test_home_keeps_marketing_images_instead_of_regenerating(monkeypatch,tmp_path):
    monkeypatch.setenv('XHS_DATA_DIR',str(tmp_path/'settings'))
    from src.core.pages import home
    from src.core.services import system_image_template_service as module
    calls=[]
    regenerated=[]
    def unexpected(**kwargs):
        regenerated.append(kwargs)
        return None
    monkeypatch.setattr(module.system_image_template_service,'generate_post_images',unexpected)
    monkeypatch.setattr('src.config.config.Config',lambda:SimpleNamespace(get_templates_config=lambda:{'selected_cover_template_id':'showcase_marketing_poster'}))
    signal=SimpleNamespace(connect=lambda _:None)
    def thread(cover,pages):
        calls.append((cover,pages))
        return SimpleNamespace(finished=signal,error=signal,start=lambda:None)
    monkeypatch.setattr(home,'ImageProcessorThread',thread)
    field=SimpleNamespace(setText=lambda _:None,clear=lambda:None,setPlainText=lambda _:None,setPixmap=lambda _:None)
    page=SimpleNamespace(parent=SimpleNamespace(),title_input=field,subtitle_input=field,input_text=field,image_label=field,image_title=field,placeholder_photo=None,handle_image_processing_result=lambda _:None,handle_image_processing_error=lambda _:None)
    home.HomePage.update_ui_after_generate(page,'原稿','原文','cover.png',['page1.png','page2.png'],'素材',preserve_generated_images=True)
    assert calls==[('cover.png',['page1.png','page2.png'])]
    assert regenerated==[]


def test_home_dispatch_passes_marketing_preservation_flag(monkeypatch):
    from src.core.pages.home import HomePage
    calls=[]
    page=SimpleNamespace(update_ui_after_generate=lambda *args,**kwargs:calls.append(kwargs))
    HomePage.handle_generation_result(page,{'title':'原稿','content':'原文','cover_image':'cover.png','content_images':['page.png'],'input_text':'素材','generator':'marketing_poster'})
    assert calls==[{'preserve_generated_images':True}]


def test_model_story_pages_reach_renderer_without_category_rewrite(monkeypatch, tmp_path):
    import json
    from src.core.services.llm_service import LLMService
    source = '手机上回复，电脑上的原会话继续。自动跟进还是后续计划。'
    service = LLMService.__new__(LLMService)
    service.config = SimpleNamespace(load_config=lambda: None, get_model_config=lambda: {})
    monkeypatch.setattr(service, 'is_model_configured', lambda _: (True, ''))
    prompts = []
    def call(config, messages):
        prompts.extend(messages)
        return json.dumps({'title': '手机上接着处理', 'pages': [
            {'title': '原会话继续', 'body': source},
            {'title': '下一步', 'body': '自动跟进还是后续计划。'}], 'caption': source}, ensure_ascii=False)
    monkeypatch.setattr(service, '_call_model', call)
    result = service.generate_marketing_poster_content(source)
    sections = marketing_sections(result)
    assert [entry[0] for entry in sections] == ['原会话继续', '下一步']
    assert sections[0][1] == source
    assert result['caption'] == source and result['keyword'] == ''
    # This generation route previously omitted the shared factual safeguards.
    assert '用户问了才回答' in prompts[0]['content']
    assert '不把计划写成现有功能' in prompts[0]['content']
    output = render_marketing(result, tmp_path, font_factory)
    assert [entry['title'] for entry in output] == ['封面', '原会话继续', '下一步']


def test_story_layout_paginates_every_supplied_paragraph(tmp_path):
    body = '暂时不能离线同步。' * 300 + '原稿的最后一句。'
    sections = marketing_sections({'pages': [{'title': '实际限制', 'body': body}],
                                    'pain_points': ['遗留栏目不重复渲染']})
    assert len(sections) == 1 and sections[0][1] == body
    renderer = PosterTemplateRenderer(font_factory, template_id=sections[0][2])
    pages = renderer.prepare_pages([(sections[0][0], sections[0][1])])
    assert compact(''.join(row for page in pages for row in page.rows)) == compact(body)
    assert len(render_marketing({'title': '实际限制', 'pages': [{'title': '实际限制', 'body': body}]}, tmp_path, font_factory)) == len(pages) + 1


def test_story_portrait_is_larger_and_preserves_the_whole_source(tmp_path):
    source = tmp_path / 'phone.png'
    image = Image.new('RGBA', (200, 400), (210, 30, 60, 255))
    # Top and bottom markers verify that neither end of a screenshot is cut off.
    from PIL import ImageDraw
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 199, 19), fill=(30, 190, 70, 255))
    draw.rectangle((0, 380, 199, 399), fill=(20, 80, 200, 255))
    image.save(source)
    renderer = PosterTemplateRenderer(font_factory, template_id='showcase_pink_note')
    cover = renderer.render_story_cover('手机上接着处理', '电脑上的原会话继续。', str(source), 3)
    green = [y for y in range(1440) if cover.getpixel((770, y)) == (30, 190, 70)]
    blue = [y for y in range(1440) if cover.getpixel((770, y)) == (20, 80, 200)]
    assert green and blue and min(green) < 600 and max(blue) > 1200
    assert max(blue) - min(green) > 780
    assert cover.getpixel((770, 700)) == (210, 30, 60)
    assert Image.open(source).size == (200, 400)
