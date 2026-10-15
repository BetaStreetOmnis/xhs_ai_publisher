from pathlib import Path

import pytest
from PIL import Image

from src.core.services.marketing_poster_layout import render_marketing
from src.core.services.screenshot_story_renderer import ScreenshotStoryRenderer
from tests.unit.test_note_images import compact, font_factory


def test_overflow_keeps_all_source_text_and_only_first_page_has_picture(tmp_path, monkeypatch):
    asset = tmp_path / 'screenshot.png'
    Image.new('RGB', (1000, 500), (210, 30, 60)).save(asset)
    body = ('原会话继续工作，离线时不能同步。\n\n' * 60) + '最后一条记录。'
    calls = []
    original = ScreenshotStoryRenderer.draw_page
    def capture(self, heading, rows, assets, brand, index, total):
        calls.append((rows, assets))
        return original(self, heading, rows, assets, brand, index, total)
    monkeypatch.setattr(ScreenshotStoryRenderer, 'draw_page', capture)
    result = render_marketing({'poster_layout': 'screenshot_story', 'title': '查看输出', 'pages': [{'title': '任务记录', 'body': body}], 'page_asset_paths': [str(asset)]}, tmp_path / 'output', font_factory)
    assert len(result) > 3
    assert compact(''.join(row for rows, _ in calls[1:] for row in rows)) == compact(body)
    assert calls[1][1] and not any(assets for _, assets in calls[2:])
    assert all(Image.open(item['image_path']).size == (1080, 1440) for item in result)


@pytest.mark.parametrize('size', [(1080, 1440), (540, 720)])
def test_multiple_images_labels_and_text_fit_above_footer(tmp_path, monkeypatch, size):
    asset = tmp_path / 'wide.png'
    Image.new('RGBA', (1200, 350), (210, 30, 60, 255)).save(asset)
    renderer = ScreenshotStoryRenderer(font_factory, size)
    positions = []
    original = renderer.text
    def capture(draw, xy, text, font, fill):
        if text:
            positions.append(draw.textbbox(xy, text, font=font, anchor='lt'))
        return original(draw, xy, text, font, fill)
    monkeypatch.setattr(renderer, 'text', capture)
    rows = renderer.chunks('手机补充要求', '消息发回原会话。', True)[0]
    image = renderer.draw_page('手机补充要求', rows, [{'path': str(asset), 'label': '发送后提示'}, {'path': str(asset), 'label': '查看最近回复'}], '项目', 2, 3)
    assert all(0 <= b[0] <= b[2] <= size[0] and 0 <= b[1] <= b[3] <= size[1] for b in positions)
    red_rows = [y for y in range(size[1]) if image.getpixel((size[0] // 2, y)) == (210, 30, 60)]
    assert max(red_rows) < size[1] - renderer.px(126)
    assert Image.open(asset).size == (1200, 350)


def test_invalid_selected_asset_stops_generation(tmp_path):
    with pytest.raises(FileNotFoundError):
        render_marketing({'poster_layout': 'screenshot_story', 'title': '原稿', 'asset_image_path': str(tmp_path / 'missing.png')}, tmp_path / 'output', font_factory)


def test_existing_price_disclaimer_and_legacy_entries_are_kept(tmp_path, monkeypatch):
    drawn = []
    original = ScreenshotStoryRenderer.draw_page
    def capture(self, heading, rows, assets, brand, index, total):
        drawn.extend(rows)
        return original(self, heading, rows, assets, brand, index, total)
    monkeypatch.setattr(ScreenshotStoryRenderer, 'draw_page', capture)
    render_marketing({'poster_layout': 'screenshot_story', 'title': '原稿', 'price': 'USD 39 / month',
                      'disclaimer': '暂时不能离线同步。', 'outline_items': ['保留原文条目。']}, tmp_path / 'output', font_factory)
    body = compact(''.join(drawn))
    assert compact('USD 39 / month') in body
    assert '暂时不能离线同步。' in body and '保留原文条目。' in body
