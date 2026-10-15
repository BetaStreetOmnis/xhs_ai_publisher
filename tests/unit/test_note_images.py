"""Text preservation and bounded layout, without keys, Qt windows or model calls."""
import importlib
from pathlib import Path

from PIL import Image, ImageFont
import pytest

from src.core.services.note_image_renderer import NoteImageRenderer


def font_factory(_family, _style, size):
    for path in ['/System/Library/Fonts/Hiragino Sans GB.ttc',
                 '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                 'C:/Windows/Fonts/msyh.ttc']:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


@pytest.fixture
def renderer():
    return NoteImageRenderer(font_factory)


def compact(text):
    return ''.join(text.split())


def test_long_body_flows_onto_more_pages_without_losing_the_ending(renderer):
    body = ('离线时暂时不能同步，这一点还没解决。\n\n' * 90) + '最后一条：实际花费39元。'
    pages = renderer.prepare_pages([('实际体验和限制', body)])
    assert len(pages) > 3
    assert compact(''.join(row for page in pages for row in page.rows)) == compact(body)
    assert '39元。' in ''.join(pages[-1].rows)
    for page in pages:
        height = sum(renderer.px(page.body_size * (1.6 if row else .68)) for row in page.rows)
        assert page.body_top + height <= renderer.size[1] - renderer.px(155)


def test_authored_cover_breaks_keep_words_intact(renderer):
    title = '几个AI会话，\n我放进了办公小镇'
    rows = renderer.title_lines(title, 90, renderer.px(904))
    assert rows == title.splitlines()
    assert any('办公小镇' in row for row in rows)
    assert all(renderer.width(row, renderer.font(90, True)) <= renderer.px(904) for row in rows)


def test_wrapping_keeps_latin_names_and_punctuation(renderer):
    body = '电脑上同时用Codex和Claude，离线模式暂时不支持同步。'
    font = renderer.font(46)
    width = renderer.px(440)
    rows = renderer.wrap(body, font, width)
    assert ''.join(rows) == body
    assert any('Codex' in row for row in rows)
    assert any('Claude' in row for row in rows)
    assert all(not row or row[0] not in renderer.closing for row in rows)
    assert all(renderer.width(row, font) <= width for row in rows)


def test_narrative_stays_paragraphs_and_explicit_steps_stay_steps(renderer):
    body = '第一段讲真实的起因。\n\n1. 打开原会话。\n2. 查看进度。'
    pages = renderer.prepare_pages([('现在的用法', body)])
    rows = [row for page in pages for row in page.rows]
    assert '' in rows
    assert '1. 打开原会话。' in rows
    assert '2. 查看进度。' in rows
    assert all(not row.startswith('•') for row in rows)


def test_saved_images_have_correct_size_and_all_measured_pages(renderer, tmp_path):
    body = '真实经历，花了39元，暂时不能离线同步。\n\n' * 30
    expected = renderer.prepare_pages([('实际记录', body)])
    cover, paths = renderer.save(tmp_path, 'sample', '真实使用记录', '保留限制和实际花费', [('实际记录', body)])
    assert len(paths) == len(expected)
    for path in [cover, *paths]:
        with Image.open(path) as image:
            assert image.size == (1080, 1440)
            assert image.format == 'JPEG'


def test_unreasonably_long_cover_is_rejected_instead_of_clipped(renderer):
    with pytest.raises(ValueError, match='封面标题过长'):
        renderer.render_cover('不能截掉事实' * 100, '', [])


def test_default_template_adapter_preserves_every_supplied_page(monkeypatch, tmp_path):
    from types import SimpleNamespace
    monkeypatch.setenv('XHS_DATA_DIR', str(tmp_path / 'settings'))
    module = importlib.import_module('src.core.services.system_image_template_service')
    monkeypatch.setattr(module, 'font_manager', SimpleNamespace(get_font=font_factory))
    service = module.SystemImageTemplateService(config=SimpleNamespace())
    monkeypatch.setattr(service, 'choose_pack', lambda _: None)
    monkeypatch.setattr(service, 'get_selected_pack_id', lambda: '')
    original_save = NoteImageRenderer.save
    calls = []

    def save(renderer, output, prefix, title, description, pages):
        calls.append((title, description, pages))
        return original_save(renderer, tmp_path / 'images', prefix, title, description, pages)

    monkeypatch.setattr(NoteImageRenderer, 'save', save)
    sources = [f'# 记录{i}\n\n第{i}页原文：39元，暂时不能同步。' for i in range(5)]
    cover, pages = service.generate_post_images(
        '发布标题', '完整正文', content_pages=sources, page_count=3,
        cover_heading='手机上\n接着看进度', cover_description='问管家有哪些待回复任务')
    assert len(pages) == 5
    assert calls[0][0] == '手机上\n接着看进度'
    assert calls[0][1] == '问管家有哪些待回复任务'
    assert calls[0][2][-1][1] == '第4页原文：39元，暂时不能同步。'
    assert Path(cover).exists()


def test_selected_background_keeps_existing_renderer(monkeypatch, tmp_path):
    from types import SimpleNamespace
    monkeypatch.setenv('XHS_DATA_DIR', str(tmp_path / 'settings'))
    module = importlib.import_module('src.core.services.system_image_template_service')
    monkeypatch.setattr(module, 'font_manager', SimpleNamespace(get_font=font_factory))
    service = module.SystemImageTemplateService(config=SimpleNamespace())
    monkeypatch.setattr(service, 'choose_pack', lambda _: None)
    monkeypatch.setattr(service, 'get_selected_pack_id', lambda: '')
    expanduser = module.os.path.expanduser
    monkeypatch.setattr(module.os.path, 'expanduser', lambda value: str(tmp_path) if value == '~' else expanduser(value))

    def unexpected(*args, **kwargs):
        raise AssertionError('Explicit background must use its existing layout')

    monkeypatch.setattr(NoteImageRenderer, 'save', unexpected)
    background = tmp_path / 'background.png'
    Image.new('RGB', (1080, 1440), '#eeeeee').save(background)
    result = service.generate_post_images('原封面', '保留背景。', bg_image_path=str(background), page_count=1)
    assert result and len(result[1]) == 1


def test_untitled_note_keeps_opening_and_does_not_invent_page_headings(monkeypatch, tmp_path):
    from types import SimpleNamespace
    monkeypatch.setenv('XHS_DATA_DIR', str(tmp_path / 'settings'))
    module = importlib.import_module('src.core.services.system_image_template_service')
    monkeypatch.setattr(module, 'font_manager', SimpleNamespace(get_font=font_factory))
    service = module.SystemImageTemplateService(config=SimpleNamespace())
    monkeypatch.setattr(service, 'choose_pack', lambda _: None)
    monkeypatch.setattr(service, 'get_selected_pack_id', lambda: '')
    calls = []

    def save(renderer, output, prefix, title, description, pages):
        calls.append(pages)
        return 'cover.jpg', ['body.jpg']

    monkeypatch.setattr(NoteImageRenderer, 'save', save)
    opening = '最近在做一个小项目。\n\n实际花了39元。'
    service.generate_post_images('发布标题', opening, content_pages=[opening])
    service.generate_post_images('发布标题', opening)
    assert calls == [[('', opening)], [('', opening)]]
