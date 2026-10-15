"""Generation contracts with isolated settings and no model/account network I/O."""
import importlib
import json
import logging
import sys
from types import ModuleType, SimpleNamespace

import pytest


@pytest.mark.parametrize('endpoint,model', [
    ('https://api.kimi.com/coding/v1/chat/completions', 'k3-256k'),
    ('https://api.moonshot.cn/v1/chat/completions', 'kimi-k3'),
])
def test_k3_request_uses_supported_parameters_and_only_final_answer(writing_runtime, monkeypatch, endpoint, model):
    service = writing_runtime.service
    monkeypatch.setattr(service, '_resolve_api_key', lambda _: 'test-key')
    requests = []

    def post(url, **kwargs):
        requests.append((url, kwargs))
        return SimpleNamespace(status_code=200, json=lambda: {
            'choices': [{'finish_reason': 'stop', 'message': {
                'content': '管家先列出需要回复的事。', 'reasoning_content': 'private reasoning'}}]})

    monkeypatch.setattr(writing_runtime.llm.requests, 'post', post)
    config = {'model_name': model, 'advanced': {'reasoning_effort': 'high'}}
    result = service._call_openai_compatible(endpoint, config, [], 0.7, 8192, 180)
    payload = requests[0][1]['json']
    assert result == '管家先列出需要回复的事。'
    assert 'temperature' not in payload and 'max_tokens' not in payload
    assert payload['max_completion_tokens'] == 8192
    assert payload['reasoning_effort'] == 'high'
    if 'api.kimi.com' in endpoint:
        assert requests[0][1]['headers']['User-Agent'].startswith('xhs-ai-publisher/')


def test_k3_truncated_answer_is_not_used_as_finished_copy(writing_runtime, monkeypatch):
    service = writing_runtime.service
    monkeypatch.setattr(service, '_resolve_api_key', lambda _: 'test-key')
    monkeypatch.setattr(writing_runtime.llm.requests, 'post', lambda *args, **kwargs:
        SimpleNamespace(status_code=200, json=lambda: {'choices': [{
            'finish_reason': 'length', 'message': {'content': '只有半篇'}}]}))
    with pytest.raises(writing_runtime.llm.LLMServiceError, match='截断'):
        service._call_openai_compatible('https://api.kimi.com/coding/v1/chat/completions',
                                       {'model_name': 'k3-256k'}, [], 0.7, 1000, 30)


def test_other_models_keep_existing_sampling_and_budget(writing_runtime, monkeypatch):
    service = writing_runtime.service
    monkeypatch.setattr(service, '_resolve_api_key', lambda _: 'test-key')
    captured = []
    monkeypatch.setattr(writing_runtime.llm.requests, 'post', lambda *args, **kwargs:
        captured.append(kwargs['json']) or SimpleNamespace(status_code=200, json=lambda: {
            'choices': [{'message': {'content': '原回复'}}]}))
    service._call_openai_compatible('https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions',
                                   {'model_name': 'qwen-plus'}, [], 0.7, 1000, 30)
    assert captured[0]['temperature'] == 0.7 and captured[0]['max_tokens'] == 1000
    assert 'reasoning_effort' not in captured[0]


@pytest.mark.parametrize('configured_endpoint,expected', [
    ('https://api.kimi.com/coding/', 'kimi-token'),
    ('https://api.kimi.ai/coding/', ''),
    ('https://api.anthropic.com', ''),
    ('https://api.kimi.com.attacker.example/coding/', ''),
])
def test_kimi_code_reuses_only_matching_origin_credentials(writing_runtime, monkeypatch, configured_endpoint, expected):
    service = writing_runtime.service
    monkeypatch.delenv('KIMI_CODE_API_KEY', raising=False)
    monkeypatch.setattr(service, '_load_claude_code_env', lambda: {
        'ANTHROPIC_BASE_URL': configured_endpoint, 'ANTHROPIC_AUTH_TOKEN': 'kimi-token'})
    config = {'api_endpoint': 'https://api.kimi.com/coding/v1/chat/completions'}
    assert service._resolve_api_key(config) == expected


def test_product_name_recovery_copies_only_supplied_introduction():
    from src.core.services.writing_guidelines import retain_product_introduction
    source='最近在做一个手机工具，叫办公小镇（agentBridge）。\n离开电脑也能回复。'
    original={'full_content':'离开电脑也能回复。','content_pages':['离开电脑也能回复。']}
    result=retain_product_introduction(source,original,'full_content','content_pages')
    assert result['full_content'].startswith(source.splitlines()[0])
    assert result['content_pages'][0].startswith(source.splitlines()[0])
    assert original['full_content']=='离开电脑也能回复。'
    assert retain_product_introduction('我的朋友叫小陈。',original,'full_content','content_pages')==original


def test_product_name_recovery_checks_caption_and_pages_independently():
    from src.core.services.writing_guidelines import retain_product_introduction
    source='我做了一个项目，叫办公小镇。\n原会话继续工作。'
    data={'caption':'办公小镇可以查看输出。','pages':[{'title':'手机回复','body':'原会话继续工作。'}]}
    result=retain_product_introduction(source,data,'caption','pages')
    assert result['caption']==data['caption']
    assert '办公小镇' in result['pages'][0]['body']
    assert '办公小镇' not in data['pages'][0]['body']


@pytest.fixture
def writing_runtime(monkeypatch, tmp_path):
    monkeypatch.setenv('XHS_DATA_DIR', str(tmp_path))
    monkeypatch.setattr(logging, 'basicConfig', lambda **kwargs: None)
    keys = ModuleType('src.core.ai_integration.api_key_manager')
    keys.api_key_manager = SimpleNamespace()
    monkeypatch.setitem(sys.modules, keys.__name__, keys)
    fonts = ModuleType('src.core.services.font_manager')
    fonts.font_manager = SimpleNamespace()
    monkeypatch.setitem(sys.modules, fonts.__name__, fonts)
    # Import the real service without initializing or reading the user's key store.
    llm = importlib.import_module('src.core.services.llm_service')
    backup = importlib.import_module('src.core.processor.content_backup')
    processor = importlib.import_module('src.core.processor.content')
    service = llm.LLMService(config=SimpleNamespace())
    # Legacy generation/formatting tests isolate the initial draft request.
    monkeypatch.setattr(service, '_review_generated_copy', lambda config, source, data, body_key, pages_key: data)
    return SimpleNamespace(llm=llm, service=service, backup=backup, processor=processor)


@pytest.mark.parametrize('template_id', [
    'xiaohongshu_default', 'xiaohongshu_review',
    'xiaohongshu_tutorial', 'xiaohongshu_image_card', 'missing-template',
])
def test_generation_receives_complete_material_and_writing_rules(writing_runtime, template_id):
    material = '我用了两周，花了 39 元。试了离线模式，暂时还不能同步。本文由 AI 辅助整理。'
    service = writing_runtime.service
    prompt = service.build_prompt_from_template(template_id, material, '真实记录', '小陈')
    assert material in prompt
    assert '小陈' in prompt and '真实记录' in prompt
    assert '没有体验记录时按资料介绍' in prompt
    assert '已有的 AI 声明' in prompt
    assert 'call_to_action 默认空字符串' in prompt
    assert '结尾要有互动引导' not in prompt


def test_custom_template_and_source_placeholders_are_preserved(writing_runtime, monkeypatch):
    service = writing_runtime.service
    template = writing_runtime.llm.PromptTemplate(
        id='custom', name='个人记录', description='',
        user_prompt='参考：{{topic}}\n署名：{{author}}\n眉头：{{header_title}}\nJSON 字段：title、full_content')
    monkeypatch.setattr(service, 'get_prompt_template', lambda _: template)
    source = '代码里保留 {{author}} 和 {{header_title}}，字符串为 $HOME。'
    prompt = service.build_prompt_from_template('custom', source, '开发', '小陈')
    assert source in prompt
    assert '署名：小陈' in prompt and '眉头：开发' in prompt
    assert '只返回模板要求的 JSON' in prompt


def test_single_model_call_keeps_facts_and_no_forced_ending(writing_runtime, monkeypatch):
    service = writing_runtime.service
    config = {'system_prompt': '沿用作者原稿的语气。', 'prompt_template': 'xiaohongshu_review'}
    service.config = SimpleNamespace(load_config=lambda: None, get_model_config=lambda: config)
    monkeypatch.setattr(service, 'is_model_configured', lambda _: (True, ''))
    material = '我用了两周，花了39元，离线模式暂时不能同步。'
    calls = []

    def model_call(settings, messages):
        calls.append(messages)
        return json.dumps({'title': '这两周的使用记录', 'full_content': material,
                           'content_pages': [material], 'hashtags': [], 'call_to_action': ''}, ensure_ascii=False)

    monkeypatch.setattr(service, '_call_model', model_call)
    result = service.generate_xiaohongshu_content(material)
    assert len(calls) == 1
    assert calls[0][0]['role'] == 'system'
    assert '沿用作者原稿的语气。' in calls[0][0]['content']
    assert '没有体验记录时按资料介绍' in calls[0][0]['content']
    assert material in calls[0][1]['content']
    assert result.content == material
    assert result.raw_json['content_pages'] == [material]


@pytest.mark.parametrize('route', ['note', 'poster'])
@pytest.mark.parametrize('enabled', [True, False])
def test_editor_settings_reach_both_routes_once(writing_runtime, monkeypatch, route, enabled):
    service = writing_runtime.service
    service._review_generated_copy = writing_runtime.llm.LLMService._review_generated_copy.__get__(service)
    sample = '我试了三天。名字是参考样本里的产品，不属于这次素材。'
    material = '资料里说售价39元，暂时不能离线同步。'
    config = {'chinese_editor_enabled': enabled, 'writing_sample': sample}
    service.config = SimpleNamespace(load_config=lambda: None, get_model_config=lambda: config)
    monkeypatch.setattr(service, 'is_model_configured', lambda _: (True, ''))
    calls = []

    def model_call(settings, messages):
        calls.append(messages)
        if len(calls) > 1:
            return json.dumps({'title': '离线模式的限制', 'paragraphs': [material]}, ensure_ascii=False)
        return json.dumps({
            'title': '离线模式的限制', 'full_content': material, 'content_pages': [material],
            'caption': material, 'pages': [{'title': '离线模式', 'body': material}],
        }, ensure_ascii=False)

    monkeypatch.setattr(service, '_call_model', model_call)
    result = service.generate_xiaohongshu_content(material) if route == 'note' else service.generate_marketing_poster_content(material)
    assert len(calls) == (2 if enabled else 1)
    combined = '\n'.join(message['content'] for message in calls[0])
    assert combined.count('中文审稿（humanizer-chinese 的规则适配）') == int(enabled)
    assert (sample in combined) == enabled
    assert material in combined and '没有体验记录时按资料介绍' in combined
    if enabled:
        assert '不是本次稿件的事实来源' in combined
    if route == 'note':
        assert result.content == material and result.raw_json['content_pages'] == [material]
    else:
        assert result['caption'] == material and result['pages'][0]['body'] == material


@pytest.mark.parametrize('revision', [
    {'title': '实际记录', 'paragraphs': ['我试过微信，花了39元。']},
    {'title': '实际记录', 'paragraphs': ['花了99元。']},
    {'title': '实际记录', 'paragraphs': ['用了Codex，花了39元。']},
    {'title': '实际记录', 'paragraphs': ['花了39元，说“完全不用操作”。']},
    {'title': '实际记录', 'paragraphs': ['花了39元，管家不越权。']},
])
def test_review_rejects_unsupported_experiences_numbers_names_and_quotes(revision):
    from src.core.services.chinese_writing_editor import validate_review
    with pytest.raises(ValueError):
        validate_review('实际花了39元。', revision)


def test_review_pages_and_caption_share_the_same_edited_article(writing_runtime, monkeypatch):
    service = writing_runtime.service
    paragraphs = ['实际花了39元。', '离线暂时不能同步。' * 30]
    monkeypatch.setattr(service, '_call_model', lambda *_: json.dumps({'title': '这次的使用记录', 'paragraphs': paragraphs}, ensure_ascii=False))
    source = '\n\n'.join(paragraphs)
    original = {'title': '旧标题', 'caption': source, 'pages': [{'title': '旧标题', 'body': source}], 'price': '39', 'keyword': '原有信息'}
    reviewed = writing_runtime.llm.LLMService._review_generated_copy(service, {}, source, original, 'caption', 'pages')
    assert reviewed['caption'] == '\n\n'.join(p['body'] for p in reviewed['pages']) == source
    assert reviewed['price'] == '39' and reviewed['keyword'] == '原有信息'
    assert reviewed['writing_review']['status'] == 'edited'
    assert original['title'] == '旧标题' and original['pages'][0]['title'] == '旧标题'


def test_failed_review_retries_once_and_labels_unchanged_draft(writing_runtime, monkeypatch):
    service = writing_runtime.service
    calls = []
    def call(*args):
        calls.append(args)
        return json.dumps({'title': '虚构经历', 'paragraphs': ['我试过微信，花了99元。']}, ensure_ascii=False)
    monkeypatch.setattr(service, '_call_model', call)
    original = {'title': '初稿', 'caption': '实际花了39元。', 'pages': [{'title': '', 'body': '实际花了39元。'}]}
    result = writing_runtime.llm.LLMService._review_generated_copy(service, {}, original['caption'], original, 'caption', 'pages')
    assert len(calls) == 2 and result['caption'] == original['caption'] and result['pages'] == original['pages']
    assert result['writing_review']['status'] == 'failed'
    reason = writing_runtime.processor.ContentGeneratorThread._format_marketing_poster_info_reason(dict(result, __source='llm'))
    assert '保留初稿' in reason


def test_explicit_copy_edit_request_skips_rewriting(writing_runtime, monkeypatch):
    service = writing_runtime.service
    monkeypatch.setattr(service, '_call_model', lambda *_: pytest.fail('Should not rewrite a copy-edit request'))
    draft = {'caption': '39元。'}
    result = writing_runtime.llm.LLMService._review_generated_copy(service, {}, '只改错字，保留全文：39元。', draft, 'caption', 'pages')
    assert result == draft


def test_editor_accepts_legacy_settings_and_explicit_string_switch():
    from src.core.services.chinese_writing_editor import ChineseWritingEditor
    assert ChineseWritingEditor.from_config({}).enabled
    assert not ChineseWritingEditor.from_config({'chinese_editor_enabled': 'false'}).build_prompt()
    assert ChineseWritingEditor.from_config({'writing_sample': None}).writing_sample == ''


def test_optional_structured_fields_still_work(writing_runtime):
    parsed = {'title': '手机接着改代码', 'full_content': '电脑上的会话还在运行。',
              'hashtags': ['#手机编程'], 'call_to_action': '你更常用手机还是电脑？'}
    title, body = writing_runtime.service._extract_title_content('', '', '', '', parsed)
    assert title == parsed['title']
    assert parsed['full_content'] in body
    assert '#手机编程' in body and parsed['call_to_action'] in body


def test_image_card_format_is_compatible(writing_runtime):
    parsed = {'title': '离线模式的限制', 'title1': '使用两周的记录',
              'content': ['同步~~~离线模式暂时不能同步', '价格~~~39元']}
    title, body = writing_runtime.service._extract_title_content('', '', '', '', parsed)
    assert title == parsed['title']
    assert '离线模式暂时不能同步' in body and '39元' in body
    assert '~~~' not in body


@pytest.mark.parametrize('source', [
    '办公小镇',
    '我用了两周。\n实际花了39元。\n\n离线暂时不能同步。\nAI辅助整理。',
    ('真实记录 39元，不支持离线同步。\n' * 55).strip(),
])
def test_backup_preserves_source_without_canned_claims(writing_runtime, source):
    generator = writing_runtime.backup.BackupContentGenerator(source, '', '', SimpleNamespace())
    body, pages = generator._generate_content_and_pages()
    assert body == source
    assert ''.join(pages) == source
    assert all(0 < len(page) <= 400 for page in pages)
    assert generator._generate_title() == source.splitlines()[0][:20]


def test_backup_run_labels_original_preview(writing_runtime, monkeypatch):
    backup = writing_runtime.backup
    monkeypatch.setattr(backup.system_image_template_service, 'generate_post_images', lambda **kwargs: ('cover.png', ['page.png']))
    button = SimpleNamespace(setText=lambda _: None, setEnabled=lambda _: None)
    generator = backup.BackupContentGenerator('只有这一句话。', '原稿标题', '', button)
    results = []
    generator.finished.connect(results.append)
    generator.run()
    assert len(results) == 1
    assert results[0]['content'] == '只有这一句话。'
    assert results[0]['title'] == '原稿标题'
    assert results[0]['generator'] == 'backup'
    assert '原文预览' in results[0]['info_reason']
    assert '未生成新文案' in results[0]['info_reason']


def test_model_failure_routes_to_original_preview(writing_runtime, monkeypatch):
    monkeypatch.setenv('XHS_ALLOW_FALLBACK', '1')
    processor = writing_runtime.processor
    button = SimpleNamespace(setText=lambda _: None, setEnabled=lambda _: None)
    generator = processor.ContentGeneratorThread('原文', '', '', button)

    def failed():
        raise writing_runtime.llm.LLMServiceError('模型不可用')

    monkeypatch.setattr(generator, '_try_generate_with_custom_model', failed)
    reasons = []
    monkeypatch.setattr(generator, '_use_backup_generator', lambda info_reason: reasons.append(info_reason))
    generator.run()
    assert len(reasons) == 1
    assert '原文预览' in reasons[0] and '未生成新文案' in reasons[0]


def test_empty_source_is_not_replaced_with_fake_advice(writing_runtime):
    generator = writing_runtime.backup.BackupContentGenerator('', '', '', SimpleNamespace())
    with pytest.raises(ValueError, match='请输入正文'):
        generator._generate_content_and_pages()


def test_imported_reference_retains_body_beyond_publish_preview_limit():
    from src.core.services.writing_guidelines import build_imported_reference
    body = '实际测量值为39。\n' * 160 + '最后一项功能暂不支持。'
    reference = build_imported_reference('测试记录', body, '资料作者', 'https://example.com/article')
    assert body in reference
    assert '最后一项功能暂不支持。' in reference
    assert '不代表我的亲身经历' in reference
    assert '原作者：资料作者' in reference
    assert '来源：https://example.com/article' in reference


def test_cover_copy_reaches_images_and_ui_result(writing_runtime, monkeypatch):
    processor = writing_runtime.processor
    asset_settings = {'marketing_poster_asset_path':'cover.png','poster_page_asset_paths':['body.png','']}
    monkeypatch.setattr(processor, 'Config', lambda: SimpleNamespace(get_model_config=lambda: {},get_templates_config=lambda:asset_settings))
    monkeypatch.setattr(processor.llm_service, 'is_model_configured', lambda _: (True, ''))
    brief = {'cover_heading': '手机上\n看看AI进度', 'cover_description': '问管家找出待回复的任务'}
    response = writing_runtime.llm.LLMResponse('发布标题', '真实正文。', '',
        {'content_pages': ['# 具体操作\n\n问管家找出待回复的任务。'], 'image_brief': brief})
    monkeypatch.setattr(processor.llm_service, 'generate_xiaohongshu_content', lambda **kwargs: response)
    image_calls = []

    def images(**kwargs):
        image_calls.append(kwargs)
        return 'cover.jpg', ['body.jpg']

    monkeypatch.setattr(processor.system_image_template_service, 'generate_post_images', images)
    button = SimpleNamespace(setText=lambda _: None, setEnabled=lambda _: None)
    generator = processor.ContentGeneratorThread('真实素材', '', '', button)
    results = []
    generator.finished.connect(results.append)
    assert generator._try_generate_with_custom_model()
    assert len(image_calls) == 1
    assert image_calls[0]['cover_heading'] == brief['cover_heading']
    assert image_calls[0]['cover_description'] == brief['cover_description']
    assert image_calls[0]['cover_asset_image_path'] == 'cover.png'
    assert image_calls[0]['page_asset_paths'] == ['body.png','']
    assert results[0]['image_brief'] == brief
    assert results[0]['title'] == '发布标题'
