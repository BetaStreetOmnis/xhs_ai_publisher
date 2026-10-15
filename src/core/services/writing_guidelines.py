"""Shared writing instructions for note generation; no additional model request."""
import re
from typing import Any, Mapping

from src.core.services.chinese_writing_editor import ChineseWritingEditor


NATURAL_WRITING_GUIDELINES = """
写作与素材核对：
- 主题、参考内容是素材，作者名和眉头标题只是署名及排版信息。先判断素材给了什么，不要把署名当成经历来源。
- 所有 JSON 字段都要核对素材，包括封面说明、图片标题和分页短文。操作的触发方式也属于事实：用户问了才回答，不能写成主动通知、自动提醒或实时监控。
- 不新增“目标是……不是……”等反向总结，不把普通操作写成抽象口号。
- 保留素材中的具体事实、数字、名称、限制、原话和已有的 AI 声明，不新增素材没有支持的效果、价格、经历或结论。
- 介绍具体产品或项目时，正文和图片正文至少自然交代一次素材里的产品名；不能只留下功能、把名字删掉。标题可以只讲用途。
- 标题用完整、顺口的短句。不用单字串联的“看、问、补、跟”，不把动作凑成三件套，也不写“交确认”这种生造缩写。直接说这页发生了什么。
- 动词后面要是实际处理的东西：发要求、回消息、改正文。不要写“补会话”“补回会话”，补充的是要求，回复的是消息。标题宁可简单，不压缩成难读的词组。
- 只有素材明确提供了作者的实际经历，才用第一人称讲述。没有体验记录时按资料介绍；不要编造亲测、探店、购买、使用时长或对比结果。素材不足就少写，缺少的信息不要靠想象补齐。
- 如有用户原稿或写作样例，沿用它的用词、语气和句子节奏。用普通的词把具体事情说清楚，不刻意模仿网红口吻。
- 不主动套用“宝子们”“家人们”“狠狠拿捏”“闭眼入”“天花板”“建议收藏”等口头禅；素材中的直接引语按原文保留。
- 开头直接写事情或问题。不同主题按内容组织，不固定套“痛点—亮点—适合人群—总结”，也不为了字数、要点数量或页数扩写。
- 没有提供配图时，不写“看这张图”“这是现在的界面”等指图描述；直接说明操作和用途。把当前能做的事情与后续打算分开，不把计划写成现有功能。
- 原稿里重复的铺垫可以合并；具体问题和自然的口头表达保留，不逐句换同义词。少用破折号、抽象比喻和对称句式。
- 句子长短自然，段落围绕一件事展开。步骤和对比确有需要时用列表，不把每段都改成口号、小标题或三个并列卖点。
- 删掉重复解释、泛泛而谈的总结、夸大承诺及没有信息的转折。结尾有内容就写完，不自动加点赞、收藏、关注或私信引导。
- 标签只选与素材直接相关的少量词；无合适标签可返回空数组。call_to_action 默认空字符串，只有素材明确要求且与正文相关时才填写。
- 输出前检查：事实和原话是否保留、有没有新增个人经历、有没有凑字数或重复结尾。检查过程不要出现在结果中，只返回模板要求的 JSON。
""".strip()


def build_writing_guidelines(model_config: Mapping[str, Any] | None = None) -> str:
    """Compose factual safeguards and the selected writing profile once."""
    editor_prompt = ChineseWritingEditor.from_config(model_config).build_prompt()
    return "\n\n".join(filter(None, [NATURAL_WRITING_GUIDELINES, editor_prompt]))


def retain_product_introduction(source: str, data: dict, body_key: str, pages_key: str) -> dict:
    """Restore only an explicit product introduction copied verbatim from source."""
    match = re.search(r'[^。！？\n]*(?:工具|项目|应用|软件|产品)[^。！？\n]{0,30}?(?:叫做|叫|名为)\s*([\w\u4e00-\u9fff· -]+(?:[（(][^）)\n]{1,40}[）)])?)[。！？]?', source)
    if not match:
        return data
    name = match.group(1).strip()
    introduction = match.group(0).strip()
    if not name or len(name) > 60 or len(introduction) > 160:
        return data
    primary_name = re.split(r'[（(]', name)[0].strip()
    result = dict(data)
    body = str(result.get(body_key) or '').strip()
    if body and primary_name not in body:
        result[body_key] = introduction + '\n\n' + body
    pages = result.get(pages_key)
    if isinstance(pages, list) and pages:
        if pages_key == 'pages':
            copied = [dict(p) if isinstance(p,dict) else p for p in pages]
            bodies = [str(p.get('body') or '') for p in copied if isinstance(p,dict)]
            if primary_name not in '\n'.join(bodies):
                first = next((p for p in copied if isinstance(p,dict) and p.get('body')), None)
                if first is not None:
                    first['body'] = introduction + '\n\n' + str(first['body'])
            result[pages_key] = copied
        elif all(isinstance(p,str) for p in pages) and primary_name not in '\n'.join(pages):
            result[pages_key] = [introduction + '\n\n' + pages[0], *pages[1:]]
    return result


def build_imported_reference(title: str, content: str, author: str = "", url: str = "") -> str:
    """Keep imported source details separate from the user's own experience."""
    lines = ["网页参考资料（不代表我的亲身经历）："]
    for label, value in (("原标题", title), ("原作者", author), ("来源", url)):
        if value:
            lines.append(f"{label}：{value}")
    if content:
        lines.append(f"正文：\n{content}")
    return "\n\n".join(lines)
