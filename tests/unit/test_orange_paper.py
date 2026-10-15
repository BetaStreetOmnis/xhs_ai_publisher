from pathlib import Path
import hashlib

from PIL import Image
import pytest

from src.core.services.marketing_poster_layout import render_marketing
from src.core.services.orange_paper_renderer import ASSETS, OrangePaperRenderer
from tests.unit.test_note_images import compact, font_factory


def test_editable_template_keeps_long_copy_price_and_conditions(tmp_path, monkeypatch):
    calls = []
    original = OrangePaperRenderer.draw_page
    def capture(self, heading, rows, assets, brand, index, total):
        calls.append((heading, rows))
        return original(self, heading, rows, assets, brand, index, total)
    monkeypatch.setattr(OrangePaperRenderer, 'draw_page', capture)
    body = ('离线时不能同步，需自己配置模型。\n\n' * 70) + '最后一条仍需确认。'
    result = render_marketing({'poster_layout': 'orange_paper', 'title': '自己的项目', 'price': 'USD 39 / month',
                              'disclaimer': '需确认发布。', 'pages': [{'title': '实际记录', 'body': body}]}, tmp_path, font_factory)
    assert len(result) > 3
    drawn = compact(''.join(''.join(rows) for _, rows in calls))
    assert compact(body) in drawn
    assert compact('USD 39 / month') in drawn and '需确认发布。' in drawn
    assert '私信' not in drawn and '9.90' not in drawn
    assert all(Image.open(item['image_path']).size == (1080, 1440) for item in result)


@pytest.mark.parametrize('size', [(1080, 1440), (540, 720)])
def test_real_text_fits_and_screenshot_stays_unchanged(tmp_path, monkeypatch, size):
    screenshot = tmp_path / 'screenshot.png'
    Image.new('RGBA', (1200, 400), (40, 180, 80, 255)).save(screenshot)
    digest = hashlib.sha256(screenshot.read_bytes()).hexdigest()
    bounds = []
    original = OrangePaperRenderer.text
    def capture(self, draw, xy, text, font, fill):
        if text:
            box = draw.textbbox(xy, text, font=font, anchor='lt')
            bounds.append(box)
        return original(self, draw, xy, text, font, fill)
    monkeypatch.setattr(OrangePaperRenderer, 'text', capture)
    result = render_marketing({'poster_layout': 'orange_paper', 'title': '离开电脑\n也能接着改代码',
                              'pages': [{'title': '实际输出', 'body': '由我确认，电脑原会话继续。'}],
                              'page_asset_paths': [str(screenshot)]}, tmp_path / 'output', font_factory, size)
    assert all(0 <= b[0] <= b[2] <= size[0] and 0 <= b[1] <= b[3] <= size[1] for b in bounds)
    assert hashlib.sha256(screenshot.read_bytes()).hexdigest() == digest
    image = Image.open(result[1]['image_path'])
    green = [y for y in range(image.height) if image.getpixel((image.width // 2, y)) == (40, 180, 80)]
    assert green and max(green) < size[1] - round(138 * size[0] / 1080)


def test_empty_image_slot_stays_empty_and_input_is_not_mutated(tmp_path, monkeypatch):
    calls = []
    original = OrangePaperRenderer.draw_page
    def capture(self, heading, rows, assets, brand, index, total):
        calls.append(assets)
        return original(self, heading, rows, assets, brand, index, total)
    monkeypatch.setattr(OrangePaperRenderer, 'draw_page', capture)
    page = {'title': '实际说明', 'body': '自己的素材。'}
    content = {'poster_layout': 'orange_paper', 'title': '自己的标题', 'pages': [page], 'page_asset_paths': ['']}
    render_marketing(content, tmp_path, font_factory)
    assert calls[0] and calls[1] == []
    assert page == {'title': '实际说明', 'body': '自己的素材。'}
    assert 'asset_image_path' not in content


def test_bundled_illustrations_have_transparency_and_font_license_exists():
    for name in ('hero.png', 'checklist.png'):
        with Image.open(ASSETS / 'orange_paper' / name) as image:
            assert image.mode == 'RGBA' and image.getextrema()[-1] == (0, 255)
    assert (ASSETS / 'fonts' / 'NotoSansSC.ttf').is_file()
    assert 'SIL OPEN FONT LICENSE' in (ASSETS / 'fonts' / 'OFL-NotoSansSC.txt').read_text()
