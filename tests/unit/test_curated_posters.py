"""Curated choices, compatible retirement and real image generation routes."""
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from src.core.services.curated_poster_renderer import CuratedPosterRenderer
from src.core.services.marketing_poster_layout import render_marketing
from src.core.services.poster_catalog import LAYOUT_TEMPLATES, RETIRED_REPLACEMENTS, resolve_template_selection, bundled_layout
from src.core.services.poster_template_renderer import TEMPLATE_FAMILIES, bundled_template_id
from src.core.services.system_image_template_service import SystemImageTemplateService
from tests.unit.test_note_images import compact, font_factory


STYLES = ['editorial_cream','checklist_lemon','paper_mint']
ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('layout', STYLES)
def test_long_copy_keeps_facts_and_only_first_chunk_has_an_image(layout,tmp_path,monkeypatch):
    calls=[]
    original=CuratedPosterRenderer.draw_page
    def capture(self,heading,rows,assets,brand,index,total):
        calls.append((heading,rows,assets))
        return original(self,heading,rows,assets,brand,index,total)
    monkeypatch.setattr(CuratedPosterRenderer,'draw_page',capture)
    body=('暂时不能离线同步。\n\n'*22)+'实际花费39元，最后需要我确认。'
    page={'title':'真实记录','body':body}
    data={'poster_layout':layout,'title':'自己的项目','price':'USD 39 / month','disclaimer':'发布前需确认。','pages':[page]}
    result=render_marketing(data,tmp_path,font_factory)
    drawn=compact(''.join(''.join(rows) for _,rows,_ in calls))
    assert compact(body) in drawn and compact('USD 39 / month') in drawn
    assert '发布前需确认。' in drawn and '私信' not in drawn
    assert len(result)>3 and calls[0][2] and calls[1][2]
    assert all(not assets for _,_,assets in calls[2:])
    assert 'images' not in page and 'asset_image_path' not in data


@pytest.mark.parametrize('layout',STYLES)
@pytest.mark.parametrize('size',[(1080,1440),(540,720)])
def test_source_images_unchanged_and_text_fits(layout,size,tmp_path,monkeypatch):
    photo=tmp_path/'image.png'
    Image.new('RGBA',(600,400),(40,180,80,255)).save(photo)
    digest=hashlib.sha256(photo.read_bytes()).hexdigest()
    boxes=[]
    original=CuratedPosterRenderer.text
    def capture(self,draw,xy,line,font,fill):
        if line:
            boxes.append(draw.textbbox(xy,line,font=font,anchor='lt'))
        return original(self,draw,xy,line,font,fill)
    monkeypatch.setattr(CuratedPosterRenderer,'text',capture)
    output=render_marketing({'poster_layout':layout,'title':'离开电脑\n也能接着改代码','subtitle':'手机补要求，电脑原会话继续。','pages':[{'title':'实际输出','body':'结果由我确认。'}],'page_asset_paths':[str(photo)]},tmp_path/'out',font_factory,size)
    assert all(0<=b[0]<=b[2]<=size[0] and 0<=b[1]<=b[3]<=size[1] for b in boxes)
    assert hashlib.sha256(photo.read_bytes()).hexdigest()==digest
    im=Image.open(output[1]['image_path'])
    green=[y for y in range(im.height) if im.getpixel((im.width//2,y))==(40,180,80)]
    assert green and max(green)<size[1]-round(138*size[0]/1080)


def test_catalog_is_curated_but_legacy_assets_still_render(monkeypatch,tmp_path):
    service=SystemImageTemplateService(config=SimpleNamespace())
    monkeypatch.setattr(service,'resolve_templates_dir',lambda:None)
    templates=service.list_showcase_templates()
    ids={t['id'] for t in templates}
    assert len(ids)==13 and set(LAYOUT_TEMPLATES)<=ids
    assert not ids.intersection(RETIRED_REPLACEMENTS)
    for old,new in RETIRED_REPLACEMENTS.items():
        assert new in ids and old in TEMPLATE_FAMILIES
        path=ROOT/'assets/system_templates/template_showcase'/(old+'.png')
        assert path.is_file() and bundled_template_id(path)==old
    custom=tmp_path/'showcase_lavender_wave.png'
    Image.new('RGB',(10,10),'white').save(custom)
    monkeypatch.setattr(service,'resolve_showcase_dir',lambda:tmp_path)
    assert [t['id'] for t in service.list_showcase_templates()]==['showcase_lavender_wave']
    assert resolve_template_selection('my_uploaded_template')=='my_uploaded_template'
    assert not bundled_layout(tmp_path/'showcase_paper_mint.png')
    for tid,(layout,_) in LAYOUT_TEMPLATES.items():
        assert resolve_template_selection('showcase_marketing_poster',layout)==tid


@pytest.mark.parametrize('template_id',LAYOUT_TEMPLATES)
def test_selected_template_drives_marketing_route_and_overrides_stale_style(template_id,tmp_path,monkeypatch):
    from src.core.processor import content as module
    from src.core.services.marketing_poster_service import marketing_poster_service
    finished,errors,rendered=[],[],[]
    settings={'selected_cover_template_id':template_id,'poster_layout':'orange_paper','poster_page_asset_paths':['']}
    monkeypatch.setattr(module,'Config',lambda:SimpleNamespace(get_templates_config=lambda:settings))
    payload={'title':'自己的标题','caption':'自己的正文','pages':[{'title':'记录','body':'保留来源事实。'}]}
    monkeypatch.setattr(module.llm_service,'generate_marketing_poster_content',lambda **kwargs:dict(payload))
    def render(data):
        rendered.append(data)
        return 'cover.png',['page.png']
    monkeypatch.setattr(marketing_poster_service,'generate_to_local_paths',render)
    button=SimpleNamespace(setText=lambda _:None,setEnabled=lambda _:None)
    thread=SimpleNamespace(input_text='原稿',generate_btn=button,error=SimpleNamespace(emit=errors.append),finished=SimpleNamespace(emit=finished.append),_extract_price_value=module.ContentGeneratorThread._extract_price_value,_format_marketing_poster_info_reason=module.ContentGeneratorThread._format_marketing_poster_info_reason)
    thread._generate_marketing_poster=lambda:module.ContentGeneratorThread._generate_marketing_poster(thread)
    module.ContentGeneratorThread.run(thread)
    assert not errors and len(rendered)==1 and len(finished)==1
    assert rendered[0]['poster_layout']==LAYOUT_TEMPLATES[template_id][0]
    assert rendered[0]['page_asset_paths']==['']
    assert finished[0]['content']=='自己的正文' and finished[0]['generator']=='marketing_poster'


@pytest.mark.parametrize('template_id',LAYOUT_TEMPLATES)
def test_direct_image_service_renders_content_instead_of_painting_on_preview(template_id,tmp_path,monkeypatch):
    from src.core.services import system_image_template_service as module
    from src.core.services import marketing_poster_layout as renderer_module
    monkeypatch.setattr(module,'font_manager',SimpleNamespace(get_font=font_factory))
    service=SystemImageTemplateService(config=SimpleNamespace())
    monkeypatch.setattr(service,'choose_pack',lambda _:None)
    monkeypatch.setattr(service,'get_selected_pack_id',lambda:'')
    expanduser=module.os.path.expanduser
    monkeypatch.setattr(module.os.path,'expanduser',lambda p:str(tmp_path) if p=='~' else str(tmp_path/p[2:]) if p.startswith('~/') else expanduser(p))
    captured=[]
    original=renderer_module.render_marketing
    def capture(data,*args,**kwargs):
        captured.append(data)
        return original(data,*args,**kwargs)
    monkeypatch.setattr(renderer_module,'render_marketing',capture)
    preview=ROOT/'assets/system_templates/template_showcase'/(template_id+'.png')
    result=service.generate_post_images('自己的新内容','实际使用39元，还需要自己确认。',cover_bg_image_path=str(preview),target_size=(540,720),page_asset_paths=[''])
    assert captured[0]['title']=='自己的新内容'
    assert captured[0]['poster_layout']==LAYOUT_TEMPLATES[template_id][0]
    assert captured[0]['pages']==[{'title':'','body':'实际使用39元，还需要自己确认。'}]
    assert result and len(result[1])==1
    assert Image.open(result[0]).size==(540,720)
