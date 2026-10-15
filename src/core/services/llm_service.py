"""
LLM 文本生成服务

从 ~/.xhs_system/settings.json 读取“模型配置”，并用其生成小红书文案。
支持：
- OpenAI 兼容接口：/v1/chat/completions
- Anthropic Claude：/v1/messages
- Ollama：/api/chat
"""

from __future__ import annotations

from dataclasses import dataclass
import ast
import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests

from src.config.config import Config
from src.core.services.writing_guidelines import (
    NATURAL_WRITING_GUIDELINES, build_writing_guidelines, retain_product_introduction,
)
from src.core.services.chinese_writing_editor import (
    ChineseWritingEditor, group_reviewed_paragraphs, validate_review,
)
from src.core.ai_integration.api_key_manager import api_key_manager


class LLMServiceError(RuntimeError):
    pass


@dataclass(frozen=True)
class LLMResponse:
    title: str
    content: str
    raw_text: str
    raw_json: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class PromptTemplate:
    id: str
    name: str
    description: str
    user_prompt: str
    system_prompt: str = ""


class LLMService:
    """可配置的大模型调用封装。"""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()

    @staticmethod
    def _env_flag(name: str, *, default: bool = False) -> bool:
        val = (os.environ.get(name) or "").strip().lower()
        if not val:
            return default
        return val in {"1", "true", "yes", "y", "on"}

    def _apply_env_model_config_overrides(self, model_config: Dict[str, Any]) -> Dict[str, Any]:
        """用环境变量补全/覆盖模型端点与模型名（OpenAI-compatible）。"""
        if not isinstance(model_config, dict):
            return {}

        base_url = (os.environ.get("XHS_LLM_BASE_URL") or "").strip()
        model = (os.environ.get("XHS_LLM_MODEL") or "").strip()
        if not base_url and not model:
            return model_config

        override = self._env_flag("XHS_LLM_OVERRIDE", default=False)
        if not override:
            provider = (model_config.get("provider") or "").strip()
            endpoint = (model_config.get("api_endpoint") or "").strip()
            model_name = (model_config.get("model_name") or "").strip()

            looks_default_openai = (
                (provider in {"OpenAI", "OpenAI GPT-3.5", "OpenAI GPT-4", ""})
                and (endpoint in {"", "https://api.openai.com/v1/chat/completions"})
                and (model_name in {"", "gpt-3.5-turbo"})
            )
            if not looks_default_openai:
                return model_config

        updated = dict(model_config)
        if base_url:
            updated["api_endpoint"] = base_url
        if model:
            updated["model_name"] = model
        return updated

    @staticmethod
    def _is_bigmodel_endpoint(endpoint: str) -> bool:
        s = (endpoint or "").strip().lower()
        return ("open.bigmodel.cn" in s) or ("bigmodel" in s) or ("zhipu" in s)

    @staticmethod
    def _is_kimi_code_endpoint(endpoint: str) -> bool:
        parsed = urlparse(endpoint or "")
        return (
            parsed.scheme == "https"
            and parsed.netloc in {"api.kimi.com", "api.kimi.ai"}
            and (parsed.path == "/coding" or parsed.path.startswith("/coding/"))
            and not parsed.query and not parsed.fragment
        )

    @classmethod
    def _is_kimi_k3(cls, endpoint: str, model_name: str) -> bool:
        parsed = urlparse(endpoint or "")
        return (
            cls._is_kimi_code_endpoint(endpoint) and model_name in {"k3", "k3-256k"}
        ) or (
            parsed.scheme == "https"
            and parsed.netloc in {"api.moonshot.cn", "api.moonshot.ai"}
            and model_name == "kimi-k3"
        )

    def _load_claude_code_env(self) -> Dict[str, str]:
        """从 Claude Code 配置读取 env（用于复用本机已有模型密钥/代理配置）。"""
        try:
            path = Path(os.path.expanduser("~")) / ".claude" / "settings.json"
            if not path.exists():
                return {}
            data = json.loads(path.read_text(encoding="utf-8")) or {}
            env = data.get("env") or {}
            if not isinstance(env, dict):
                return {}
            out: Dict[str, str] = {}
            for k, v in env.items():
                key = str(k or "").strip()
                if not key:
                    continue
                val = str(v or "").strip()
                if val:
                    out[key] = val
            return out
        except Exception:
            return {}

    def _provider_aliases_for_key(self, provider: str) -> List[str]:
        provider = (provider or "").strip()
        if not provider:
            return []

        aliases = {
            "OpenAI": ["OpenAI GPT-3.5", "OpenAI GPT-4"],
            "OpenAI GPT-3.5": ["OpenAI"],
            "OpenAI GPT-4": ["OpenAI"],
            "Anthropic（Claude）": ["Claude 3.5", "Claude 3"],
            "Claude 3.5": ["Anthropic（Claude）"],
            "Claude 3": ["Anthropic（Claude）"],
            "阿里云（通义千问）": ["Qwen3"],
            "Qwen3": ["阿里云（通义千问）"],
            "月之暗面（Kimi）": ["Kimi2"],
            "Kimi2": ["月之暗面（Kimi）"],
        }

        return aliases.get(provider, [])

    def _resolve_api_key(self, model_config: Dict[str, Any]) -> str:
        api_key = (model_config.get("api_key") or "").strip()
        if api_key:
            return api_key

        provider = (model_config.get("provider") or "").strip()
        provider_lower = provider.lower()
        api_key_name = (model_config.get("api_key_name") or "").strip() or "default"
        if provider and api_key_name:
            key = api_key_manager.get_key(provider, api_key_name)
            if key:
                return key.strip()
            for alias_provider in self._provider_aliases_for_key(provider):
                alias_key = api_key_manager.get_key(alias_provider, api_key_name)
                if alias_key:
                    return alias_key.strip()

        model_config = self._apply_env_model_config_overrides(model_config)
        endpoint = (model_config.get("api_endpoint") or "").strip()

        if self._is_kimi_code_endpoint(endpoint):
            key = (os.environ.get("KIMI_CODE_API_KEY") or "").strip()
            if key:
                return key
            cc_env = self._load_claude_code_env()
            # Reuse only the same Kimi Code origin, never a different provider's token.
            saved_endpoint = (cc_env.get("ANTHROPIC_BASE_URL") or "").strip()
            if (self._is_kimi_code_endpoint(saved_endpoint)
                    and urlparse(saved_endpoint).netloc == urlparse(endpoint).netloc):
                return (cc_env.get("ANTHROPIC_AUTH_TOKEN")
                        or cc_env.get("ANTHROPIC_API_KEY") or "").strip()
            return ""

        # BigModel（智谱 GLM）常用于 OpenAI-compatible 端点；
        # 若本机已配置 Claude Code（~/.claude/settings.json），优先复用其中的 token，避免被 OPENAI_API_KEY 干扰。
        if self._is_bigmodel_endpoint(endpoint) or ("glm" in provider_lower) or ("智谱" in provider):
            # 1) 明确的 GLM 环境变量
            key = (
                os.environ.get("ZHIPUAI_API_KEY", "")
                or os.environ.get("BIGMODEL_API_KEY", "")
                or os.environ.get("GLM_API_KEY", "")
                or ""
            ).strip()
            if key:
                return key

            # 2) 项目级 OpenAI-compatible Key（避免污染全局 OPENAI_API_KEY）
            key = (os.environ.get("XHS_LLM_API_KEY", "") or "").strip()
            if key:
                return key

            # 3) Claude Code 配置（如 ANTHROPIC_AUTH_TOKEN）
            cc_env = self._load_claude_code_env()
            key = (
                (cc_env.get("XHS_LLM_API_KEY") or "").strip()
                or (cc_env.get("ZHIPUAI_API_KEY") or "").strip()
                or (cc_env.get("BIGMODEL_API_KEY") or "").strip()
                or (cc_env.get("GLM_API_KEY") or "").strip()
                or (cc_env.get("OPENAI_API_KEY") or "").strip()
                or (cc_env.get("ANTHROPIC_API_KEY") or "").strip()
                or (cc_env.get("ANTHROPIC_AUTH_TOKEN") or "").strip()
            )
            if key:
                return key

            # 4) 兜底：兼容 OpenAI-compatible 的常用变量名
            key = (os.environ.get("OPENAI_API_KEY", "") or os.environ.get("API_KEY", "") or "").strip()
            return key

        env_key = self._api_key_from_env(provider, endpoint)
        return (env_key or "").strip()

    def _api_key_from_env(self, provider: str, endpoint: str) -> str:
        provider = (provider or "").strip()
        endpoint = (endpoint or "").strip()
        provider_lower = provider.lower()
        endpoint_lower = endpoint.lower()

        if "anthropic" in endpoint_lower or "claude" in provider_lower:
            return os.environ.get("ANTHROPIC_API_KEY", "") or os.environ.get("ANTHROPIC_AUTH_TOKEN", "") or ""
        if "openai" in endpoint_lower or "openai" in provider_lower:
            return os.environ.get("XHS_LLM_API_KEY", "") or os.environ.get("OPENAI_API_KEY", "") or ""
        if "dashscope" in endpoint_lower or "qwen" in provider_lower or "通义" in provider or "阿里" in provider:
            return os.environ.get("DASHSCOPE_API_KEY", "") or os.environ.get("XHS_LLM_API_KEY", "") or ""
        if "moonshot" in endpoint_lower or "kimi" in provider_lower or "月之暗面" in provider:
            return (os.environ.get("MOONSHOT_API_KEY", "")
                    or os.environ.get("KIMI_API_KEY", "")
                    or os.environ.get("XHS_LLM_API_KEY", "") or "")
        if "volces" in endpoint_lower or "doubao" in provider_lower or "豆包" in provider or "字节" in provider or "火山" in provider:
            return (
                os.environ.get("ARK_API_KEY", "")
                or os.environ.get("VOLC_API_KEY", "")
                or os.environ.get("VOLCENGINE_API_KEY", "")
                or os.environ.get("DOUBAO_API_KEY", "")
                or os.environ.get("XHS_LLM_API_KEY", "")
                or ""
            )
        if "tencent" in endpoint_lower or "hunyuan" in provider_lower or "混元" in provider or "腾讯" in provider or "lkeap" in endpoint_lower:
            return (
                os.environ.get("TENCENT_API_KEY", "")
                or os.environ.get("HUNYUAN_API_KEY", "")
                or os.environ.get("LKEAP_API_KEY", "")
                or os.environ.get("XHS_LLM_API_KEY", "")
                or ""
            )

        # 兜底：兼容 OpenAI-compatible 的常用变量名
        return os.environ.get("XHS_LLM_API_KEY", "") or os.environ.get("OPENAI_API_KEY", "") or os.environ.get("API_KEY", "") or ""

    def is_model_configured(self, model_config: Dict[str, Any]) -> Tuple[bool, str]:
        model_config = self._apply_env_model_config_overrides(model_config)
        endpoint = (model_config.get("api_endpoint") or "").strip()
        model_name = (model_config.get("model_name") or "").strip()
        provider = (model_config.get("provider") or "").strip()

        if not endpoint or not model_name:
            return False, "未配置模型端点或模型名称"

        # 本地模型允许无 key；其他默认需要 key
        if provider == "本地模型":
            return True, ""

        parsed = urlparse(endpoint)
        if parsed.hostname in {"localhost", "127.0.0.1"}:
            return True, ""

        if not self._resolve_api_key(model_config):
            return False, "缺少 API Key"

        return True, ""

    def generate_xiaohongshu_content(
        self,
        topic: str,
        header_title: str = "",
        author: str = "",
    ) -> LLMResponse:
        # 配置可能在 UI 中被用户修改；每次调用前重新加载一次
        try:
            self.config.load_config()
        except Exception:
            pass

        model_config = self._apply_env_model_config_overrides(self.config.get_model_config())
        ok, reason = self.is_model_configured(model_config)
        if not ok:
            raise LLMServiceError(f"模型配置不可用: {reason}")

        system_prompt = (model_config.get("system_prompt") or "").strip()

        template_id = (model_config.get("prompt_template") or "").strip()
        user_prompt = self.build_prompt_from_template(
            template_id=template_id or "xiaohongshu_default",
            topic=topic,
            header_title=header_title,
            author=author,
        )

        messages: List[Dict[str, str]] = []
        system = f"{system_prompt}\n\n{build_writing_guidelines(model_config)}".strip()
        messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user_prompt})

        raw_text = self._call_model(model_config, messages)
        parsed = self._try_parse_json(raw_text)
        if isinstance(parsed, dict):
            parsed = self._review_generated_copy(model_config, topic, parsed, 'full_content', 'content_pages')
            parsed = retain_product_introduction(topic, parsed, 'full_content', 'content_pages')

        title, content = self._extract_title_content(topic, header_title, author, raw_text, parsed)
        return LLMResponse(title=title, content=content, raw_text=raw_text, raw_json=parsed)

    def generate_marketing_poster_content(
        self,
        topic: str,
        *,
        price: str = "",
        keyword: str = "",
    ) -> Dict[str, Any]:
        """生成“营销海报”渲染器所需的结构化 JSON。"""
        topic = (topic or "").strip() or "营销海报"
        price_text = (price or "").strip()
        keyword_text = (keyword or "").strip()

        # 配置可能在 UI 中被用户修改；每次调用前重新加载一次
        try:
            self.config.load_config()
        except Exception:
            pass

        model_config = self._apply_env_model_config_overrides(self.config.get_model_config())
        ok, reason = self.is_model_configured(model_config)
        if not ok:
            fallback = self._generate_default_marketing_poster_content(topic, price=price_text, keyword=keyword_text)
            fallback["__source"] = "default"
            fallback["__error"] = f"模型配置不可用: {reason}"
            return fallback

        system_prompt = (model_config.get("system_prompt") or "").strip()
        extra_system = (
            "根据作者提供的素材编辑小红书图文，提炼具体用途并保留作者的口吻。"
            "严格只返回 JSON 对象，不要输出解释、不要 markdown、不要 emoji。"
        )
        system = "\n\n".join(filter(None, [system_prompt, extra_system, build_writing_guidelines(model_config)]))

        user = f"""
根据以下素材整理小红书图文，保留原稿语气与事实，不要求凑满六页。
素材：
{topic}

编辑要求：
- 封面优先写素材中最具体的操作能力，让读者一眼看出能拿来做什么；起因放进正文。不要用“信息太多、管理太难”这样的背景问题代替已有用途，也不要只用产品名或“我的小项目”。
- 正文先写成一篇连贯的介绍，再按内容分页。原稿有作者起因和使用过程时，保留它的叙述顺序，允许从起因开始；不强行改成逐项介绍功能。沿用作者的词和口头表达，不能增加亲测经历、场景细节、效果或功能，不添加自创体验总结。
- 标题通常8–16字，最多20字。用一个具体动作的顺口短句；不把几种能力挤到同一句。副标题最多40字，可以留空，正文自然交代产品名字。
- pages沿用审过的完整正文，按文章的阅读顺序分段；不为图片另外生成一套说法。一页可以保留相关的几个自然段，标题简单交代内容，也可以留空。不套“内容一览、痛点、亮点、适合人群”这些栏目。
- 内容足够时可分2–5个正文页，每页通常约60–120字；完整自然段更长时可保留，由排版器续页。相关操作和条件连着讲，不为每个功能硬凑一页。短素材用一页也可以，长素材增加页数以保留事实。
- 页标题通常6–14字，写一句自然的话，不用“如何：查、拟、交”这种格式。正文按意思分段，避免一个长段把几种操作连起来。
- caption是完整发布正文，不能只返回开头一句。当前功能、使用限制和后续计划都要保留，图片与caption的说法一致。
- 步骤只有原稿明确提供时才写。用户问了管家才回答，不能说主动提醒；后续打算不能说成现有能力。
- 原稿没有的价格、人群、私信领取、购买和交付承诺不要补写。不要emoji或Markdown。
- 写作约束用于核对，不是正文内容。不要把“不能主动提醒、没有实时监控”等提示里的例子写进稿子；只有素材自己明确说到的限制才保留。每句话都要在素材里找到依据，包括小标题和副标题。
- 若用户明确要求只改错字或保留全文，遵循用户的编辑范围。

以下附加信息若提供，原样保留：price="{price_text}"；keyword="{keyword_text}"。
返回严格JSON：
{{
  "title": "封面切入点",
  "subtitle": "补充一句或留空",
  "price": "提供的价格或空字符串",
  "keyword": "提供的关键词或空字符串",
  "pages": [{{"title": "这一页具体讲什么", "body": "自然段正文，用\\n\\n分段"}}],
  "caption": "完整发布正文",
  "cta": "仅使用原稿明确要求的行动引导，否则留空",
  "disclaimer": "原稿已有声明或空字符串"
}}
""".strip()

        try:
            raw_text = self._call_model(
                model_config,
                [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
        except Exception as e:
            fallback = self._generate_default_marketing_poster_content(topic, price=price_text, keyword=keyword_text)
            fallback["__source"] = "default"
            fallback["__error"] = f"模型请求失败: {str(e)}"
            return fallback
        data = self._try_parse_json(raw_text) or {}
        if not isinstance(data, dict):
            fallback = self._generate_default_marketing_poster_content(topic, price=price_text, keyword=keyword_text)
            fallback["__source"] = "default"
            fallback["__error"] = "模型返回无法解析为 JSON"
            return fallback

        data = self._review_generated_copy(model_config, topic, data, 'caption', 'pages')
        data = retain_product_introduction(topic, data, 'caption', 'pages')

        def _to_str(v: Any) -> str:
            return str(v).strip() if v is not None else ""

        def _clean(v: Any) -> str:
            return self._remove_emoji(_to_str(v)).strip()

        title = _clean(data.get("title")) or (topic[:18] if topic else "营销海报")
        subtitle = _clean(data.get("subtitle"))
        accent = _to_str(data.get("accent")).strip().lower() or "blue"

        out_price = _clean(data.get("price"))
        if price_text:
            out_price = price_text

        out_keyword = _clean(data.get("keyword"))
        if keyword_text:
            out_keyword = keyword_text

        def _norm_list(value: Any) -> List[str]:
            if not isinstance(value, list):
                return []
            return [cleaned for item in value if (cleaned := _clean(item))]

        cover_bullets = _norm_list(data.get("cover_bullets"))
        outline_items = _norm_list(data.get("outline_items"))
        highlights: List[Dict[str, str]] = []
        if isinstance(data.get("highlights"), list):
            for item in data["highlights"]:
                if isinstance(item, dict):
                    h_title = _clean(item.get("title"))
                    h_desc = _clean(item.get("desc") or item.get("description"))
                    if h_title or h_desc:
                        highlights.append({"title": h_title, "desc": h_desc})
        delivery_steps = _norm_list(data.get("delivery_steps"))
        pain_points = _norm_list(data.get("pain_points"))
        audience: List[Dict[str, Any]] = []
        if isinstance(data.get("audience"), list):
            for item in data["audience"]:
                if isinstance(item, dict):
                    a_title = _clean(item.get("title"))
                    bullets = _norm_list(item.get("bullets"))
                    if a_title or bullets:
                        audience.append({"title": a_title, "bullets": bullets})

        pages = []
        for item in data.get("pages") or []:
            if isinstance(item, dict) and (body := _clean(item.get("body"))):
                pages.append({"title": _clean(item.get("title")), "body": body})

        caption = _clean(data.get("caption"))
        disclaimer = _clean(data.get("disclaimer"))
        # Keep only a disclaimer the author actually supplied. Models sometimes
        # echo their own compliance checklist into this optional display field.
        declaration_words = ('声明', '仅供参考', '不构成', 'AI 辅助', 'AI辅助', '版权', '风险提示')
        if disclaimer and (disclaimer not in topic or not any(word in disclaimer for word in declaration_words)):
            disclaimer = ''

        return {
            "title": title,
            "subtitle": subtitle,
            "price": out_price,
            "keyword": out_keyword,
            "accent": accent,
            "pages": pages,
            "cover_bullets": cover_bullets,
            "outline_items": outline_items,
            "highlights": highlights,
            "delivery_steps": delivery_steps,
            "pain_points": pain_points,
            "audience": audience,
            "caption": caption,
            "cta": _clean(data.get("cta")),
            "disclaimer": disclaimer,
            "__source": "llm",
            "writing_review": data.get('writing_review', {}),
        }

    def _review_generated_copy(self, model_config, source, data, body_key, pages_key):
        """Edit separately, retry one rejected revision, otherwise keep the draft."""
        result = dict(data)
        editor = ChineseWritingEditor.from_config(model_config)
        body = result.get(body_key)
        if not editor.enabled or not isinstance(body, str) or not body.strip():
            return result
        if re.search(r'只改错字|仅改错字|不要改写|保留全文|原样保留', source):
            return result
        try:
            path = self._get_prompt_templates_dir().parent / 'writing' / 'humanizer-chinese.md'
            skill = path.read_text(encoding='utf-8')
            messages = editor.review_messages(skill, source, body)
            for attempt in range(2):
                raw = self._call_model(model_config, messages)
                try:
                    title, paragraphs = validate_review(source, self._try_parse_json(raw))
                    break
                except ValueError as error:
                    if attempt:
                        raise
                    messages = messages + [
                        {'role': 'assistant', 'content': raw},
                        {'role': 'user', 'content': '上版未通过核对：' + str(error) + '。请对照原始素材修正，再返回同样的JSON。不能增加场景、体验或功能，也不能遗漏原始信息。'},
                    ]
            result['title'] = title
            result[body_key] = '\n\n'.join(paragraphs)
            groups = group_reviewed_paragraphs(paragraphs)
            result[pages_key] = [{'title': '', 'body': group} for group in groups] if pages_key == 'pages' else groups
            if body_key == 'full_content':
                # A stale draft cover must not contradict the edited article.
                result['image_brief'] = {'cover_heading': title, 'cover_description': ''}
            else:
                result['subtitle'] = ''
                result['cover_bullets'] = []
            result['writing_review'] = {'status': 'edited', 'message': '已完成中文改稿；请核对内容', 'attempts': attempt + 1}
        except Exception:
            # Do not expose provider exception bodies or discard a usable draft.
            result['writing_review'] = {'status': 'failed', 'message': '中文改稿未完成，当前保留初稿；请检查后再用'}
        return result

    @staticmethod
    def _generate_default_marketing_poster_content(topic: str, *, price: str = "", keyword: str = "") -> Dict[str, Any]:
        # Preview the supplied source when the model is unavailable; invented
        # selling points must not appear in a publishable draft.
        source = (topic or "").strip()
        title = source.splitlines()[0][:18] if source else "未命名海报"
        return {
            "title": title, "subtitle": "", "price": (price or "").strip(),
            "keyword": (keyword or "").strip(), "accent": "blue",
            "cover_bullets": [], "outline_items": [], "highlights": [],
            "delivery_steps": [], "pain_points": [], "audience": [],
            "caption": source, "cta": "", "disclaimer": "",
        }

    def list_prompt_templates(self) -> List[PromptTemplate]:
        templates: List[PromptTemplate] = []
        for path in self._get_prompt_templates_dir().glob("*.json"):
            tpl = self._load_prompt_template_file(path)
            if tpl:
                templates.append(tpl)
        templates.sort(key=lambda t: t.name)
        return templates

    def get_prompt_templates_dir(self) -> Path:
        """返回当前 prompt 模板目录路径（用于 UI 展示/打开目录）。"""
        return self._get_prompt_templates_dir()

    def get_prompt_template(self, template_id: str) -> Optional[PromptTemplate]:
        template_id = (template_id or "").strip()
        if not template_id:
            return None

        # 按 id 精确匹配
        for tpl in self.list_prompt_templates():
            if tpl.id == template_id:
                return tpl

        return None

    def build_prompt_from_template(self, template_id: str, topic: str, header_title: str, author: str) -> str:
        tpl = self.get_prompt_template(template_id)
        if not tpl:
            prompt = self._build_xiaohongshu_prompt(topic, header_title, author)
        else:
            prompt = self._render_template(
                tpl.user_prompt,
                {
                    "topic": (topic or "").strip(),
                    "header_title": (header_title or "").strip(),
                    "author": (author or "").strip(),
                },
            ).strip()
        return f"{prompt}\n\n{NATURAL_WRITING_GUIDELINES}"

    def _render_template(self, template_text: str, mapping: Dict[str, str]) -> str:
        """简单模板渲染：将 {{key}} 替换为值，避免与 JSON 花括号冲突。"""
        # Render once so placeholder-looking text inside source material stays literal.
        return re.sub(
            r"\{\{(topic|header_title|author)\}\}",
            lambda match: mapping.get(match.group(1), match.group(0)),
            template_text or "",
        )

    def _get_prompt_templates_dir(self) -> Path:
        """获取 prompt 模板目录。"""
        # 打包版：优先使用可执行文件旁的 templates/prompts
        if getattr(sys, "frozen", False):
            base_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
            candidate = base_dir / "templates" / "prompts"
            if candidate.exists():
                return candidate

            candidate2 = Path(sys.executable).parent / "templates" / "prompts"
            return candidate2

        # 源码运行：repo_root/templates/prompts
        repo_root = Path(__file__).resolve().parents[3]
        return repo_root / "templates" / "prompts"

    def _load_prompt_template_file(self, path: Path) -> Optional[PromptTemplate]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return None

        template_id = str(data.get("id") or "").strip()
        name = str(data.get("name") or data.get("title") or path.stem).strip()
        user_prompt_value = data.get("user_prompt") or data.get("prompt")
        if not user_prompt_value and isinstance(data.get("user_prompt_lines"), list):
            user_prompt_value = "\n".join([str(x) for x in data.get("user_prompt_lines")])

        user_prompt = str(user_prompt_value or "").strip()
        if not template_id or not user_prompt:
            return None

        description = str(data.get("description") or "").strip()
        system_prompt = str(data.get("system_prompt") or "").strip()
        return PromptTemplate(
            id=template_id,
            name=name,
            description=description,
            user_prompt=user_prompt,
            system_prompt=system_prompt,
        )

    def _build_xiaohongshu_prompt(self, topic: str, header_title: str, author: str) -> str:
        header_title = header_title.strip()
        author = author.strip()

        extra_lines = []
        if header_title:
            extra_lines.append(f"- 眉头标题：{header_title}")
        if author:
            extra_lines.append(f"- 作者：{author}")
        extra = "\n".join(extra_lines) if extra_lines else "- （无）"

        # 参考 x-auto-publisher 的输出风格：结构化 JSON + 可直接粘贴的小红书正文
        return f"""
请为小红书生成一篇图文笔记文案。

主题：{topic}
附加信息：
{extra}

要求：
1. 标题：20字以内，概括具体内容，不夸张；短素材可以用短标题
2. 正文：最多700字，按素材的信息量写；不用凑字数、要点数量或互动结尾
3. 话题标签：0-5个，只写与素材直接相关的 #话题
4. 返回“严格 JSON”，不要使用 ``` 包裹，不要输出多余解释文字

返回 JSON 格式（字段允许扩展，但至少包含这些）：
{{
  "title": "标题",
  "full_content": "完整正文（不含话题标签也可以）",
  "content_pages": [
    "# 页面标题\\n\\n本页正文（按正文信息量分1-3页，不补造内容）"
  ],
  "hashtags": ["#话题1", "#话题2"],
  "call_to_action": ""
}}
""".strip()

    def _call_model(self, model_config: Dict[str, Any], messages: List[Dict[str, str]]) -> str:
        model_config = self._apply_env_model_config_overrides(model_config)
        endpoint = (model_config.get("api_endpoint") or "").strip()
        provider = (model_config.get("provider") or "").strip()

        advanced = model_config.get("advanced") or {}
        temperature = float(advanced.get("temperature", 0.7))
        max_tokens = int(advanced.get("max_tokens", 1000))
        timeout = float(advanced.get("timeout", 30))

        max_tokens_env = (os.environ.get("XHS_LLM_MAX_TOKENS") or "").strip()
        if max_tokens_env:
            try:
                max_tokens_val = int(float(max_tokens_env))
                if max_tokens_val > 0:
                    max_tokens = max_tokens_val
            except Exception:
                pass

        # Allow env override for timeout (seconds)
        timeout_env = (os.environ.get("XHS_LLM_TIMEOUT") or "").strip()
        if timeout_env:
            try:
                timeout_val = float(timeout_env)
                if timeout_val > 0:
                    timeout = timeout_val
            except Exception:
                pass

        # BigModel/GLM requests can be slower; bump minimum timeout to avoid frequent fallback.
        try:
            if self._is_bigmodel_endpoint(endpoint) or ("glm" in provider.lower()) or ("智谱" in provider):
                timeout = max(timeout, 120.0)
                # GLM-5 默认会返回较长的 reasoning_content，max_tokens 过小会导致 content 为空
                max_tokens = max(max_tokens, 3200)
        except Exception:
            pass

        # Claude / Anthropic
        if provider.startswith("Claude") or endpoint.rstrip("/").endswith("/v1/messages") or "api.anthropic.com" in endpoint:
            return self._call_anthropic(endpoint, model_config, messages, temperature, max_tokens, timeout)

        # Ollama (native)
        if endpoint.rstrip("/").endswith("/api/chat") or "/api/chat" in endpoint:
            return self._call_ollama(endpoint, model_config, messages, temperature, max_tokens, timeout)

        # Default: OpenAI compatible
        url = self._normalize_openai_chat_completions_endpoint(endpoint)
        return self._call_openai_compatible(url, model_config, messages, temperature, max_tokens, timeout)

    def _normalize_openai_chat_completions_endpoint(self, endpoint: str) -> str:
        endpoint = endpoint.strip().rstrip("/")
        if not endpoint:
            return endpoint

        if endpoint.endswith("/v1/chat/completions") or endpoint.endswith("/chat/completions"):
            return endpoint

        # 常见：只填 base_url 或 /v1
        if endpoint.endswith("/v1"):
            return f"{endpoint}/chat/completions"

        # 一些 OpenAI-compatible 实现的 base_url 末尾是 /v3、/v4 等（如豆包/GLM），无需再拼 /v1
        try:
            parsed = urlparse(endpoint)
            path = (parsed.path or "").rstrip("/")
            if re.search(r"/v\d+$", path):
                return f"{endpoint}/chat/completions"
        except Exception:
            pass

        # 兜底：如果末尾没有 /v1，假设它是 OpenAI 风格 base_url
        return f"{endpoint}/v1/chat/completions"

    def _call_openai_compatible(
        self,
        url: str,
        model_config: Dict[str, Any],
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        timeout: float,
    ) -> str:
        api_key = self._resolve_api_key(model_config)
        model_name = (model_config.get("model_name") or "").strip()

        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload: Dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        if self._is_kimi_code_endpoint(url):
            headers["User-Agent"] = "xhs-ai-publisher/local-client"
        is_kimi_k3 = self._is_kimi_k3(url, model_name)
        if is_kimi_k3:
            # K3 fixes temperature at 1.0 and includes reasoning in the output budget.
            payload.pop("temperature")
            payload["max_completion_tokens"] = payload.pop("max_tokens")
            effort = (model_config.get("advanced") or {}).get("reasoning_effort", "high")
            if effort not in {"low", "high", "max"}:
                raise LLMServiceError("Kimi K3 思考强度只能为 low、high 或 max")
            payload["reasoning_effort"] = effort

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        except requests.exceptions.RequestException as e:
            raise LLMServiceError(f"模型请求失败: {e}") from e

        if resp.status_code != 200:
            detail = (resp.text or "")[:500]
            raise LLMServiceError(f"模型接口返回错误: HTTP {resp.status_code}: {detail}")

        try:
            data = resp.json()
        except Exception as e:
            raise LLMServiceError("模型接口返回非 JSON 响应") from e

        # OpenAI chat.completions
        try:
            choices = data.get("choices") or []
            if not choices:
                raise KeyError("choices")
            first = choices[0] or {}
            if is_kimi_k3 and first.get("finish_reason") == "length":
                raise LLMServiceError("Kimi K3 输出被截断，请增大最大 Token 数后再试")
            message = first.get("message") or {}
            content = message.get("content")
            if content:
                return str(content)

            # 一些兼容实现可能返回 text
            if first.get("text"):
                return str(first["text"])
        except LLMServiceError:
            raise
        except Exception as e:
            raise LLMServiceError(f"无法解析模型响应: {str(e)}")

        raise LLMServiceError("模型响应为空")

    def _call_anthropic(
        self,
        url: str,
        model_config: Dict[str, Any],
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        timeout: float,
    ) -> str:
        api_key = self._resolve_api_key(model_config)
        model_name = (model_config.get("model_name") or "").strip()

        system_prompt = ""
        normalized_messages: List[Dict[str, Any]] = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content") or ""
            if role == "system":
                system_prompt = content
            elif role in {"user", "assistant"}:
                normalized_messages.append({"role": role, "content": content})

        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }

        payload: Dict[str, Any] = {
            "model": model_name,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": normalized_messages,
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        except requests.exceptions.RequestException as e:
            raise LLMServiceError(f"Claude 请求失败: {e}") from e

        if resp.status_code != 200:
            detail = (resp.text or "")[:500]
            raise LLMServiceError(f"Claude 接口返回错误: HTTP {resp.status_code}: {detail}")

        try:
            data = resp.json()
        except Exception as e:
            raise LLMServiceError("Claude 接口返回非 JSON 响应") from e

        # Anthropic messages API: content is a list of blocks
        content_blocks = data.get("content") or []
        if isinstance(content_blocks, list) and content_blocks:
            first = content_blocks[0] or {}
            text = first.get("text")
            if text:
                return str(text)

        if isinstance(content_blocks, str) and content_blocks.strip():
            return content_blocks

        raise LLMServiceError("Claude 响应为空")

    def _call_ollama(
        self,
        url: str,
        model_config: Dict[str, Any],
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        timeout: float,
    ) -> str:
        model_name = (model_config.get("model_name") or "").strip()

        payload: Dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        try:
            resp = requests.post(url, json=payload, timeout=timeout)
        except requests.exceptions.RequestException as e:
            raise LLMServiceError(f"Ollama 请求失败: {e}") from e

        if resp.status_code != 200:
            detail = (resp.text or "")[:500]
            raise LLMServiceError(f"Ollama 接口返回错误: HTTP {resp.status_code}: {detail}")

        try:
            data = resp.json()
        except Exception as e:
            raise LLMServiceError("Ollama 接口返回非 JSON 响应") from e

        message = data.get("message") or {}
        content = message.get("content")
        if content:
            return str(content)

        # 兼容 /api/generate 等返回
        if data.get("response"):
            return str(data["response"])

        raise LLMServiceError("Ollama 响应为空")

    def _try_parse_json(self, text: str) -> Optional[Dict[str, Any]]:
        if not text:
            return None

        cleaned = text.strip()

        # 去掉 ```json ... ``` 包裹
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            # 去掉第一行 ``` 或 ```json
            if lines:
                lines = lines[1:]
            # 去掉最后一行 ```
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()

        try:
            return json.loads(cleaned)
        except Exception:
            pass

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            snippet = cleaned[start : end + 1]
            try:
                return json.loads(snippet)
            except Exception:
                # 兼容模型偶尔返回的“伪 JSON”（例如单引号/尾逗号）
                try:
                    obj = ast.literal_eval(snippet)
                    return obj if isinstance(obj, dict) else None
                except Exception:
                    return None

        return None

    @staticmethod
    def _remove_emoji(text: str) -> str:
        if not text:
            return ""
        text = str(text)
        # 归一化一些在中文字体里常见的“方块/叉号”符号
        try:
            circled_map = {
                "\u2139": "※",  # ℹ
                "\u24EA": "0",  # ⓪
                "\u24FF": "0",  # ⓿
                "\u24F5": "1",  # ⓵
                "\u24F6": "2",
                "\u24F7": "3",
                "\u24F8": "4",
                "\u24F9": "5",
                "\u24FA": "6",
                "\u24FB": "7",
                "\u24FC": "8",
                "\u24FD": "9",
                "\u24FE": "10",  # ⓾
            }
            for k, v in circled_map.items():
                if k in text:
                    text = text.replace(k, v)
        except Exception:
            pass
        try:
            emoji_pattern = re.compile(
                "["
                "\U0001F600-\U0001F64F"
                "\U0001F300-\U0001F5FF"
                "\U0001F680-\U0001F6FF"
                "\U0001F1E0-\U0001F1FF"
                "\U0001F900-\U0001F9FF"
                "\U0001FA00-\U0001FAFF"
                "\u2600-\u27BF"
                "]+",
                flags=re.UNICODE,
            )
            text = emoji_pattern.sub("", text)
        except Exception:
            pass

        # 清理 emoji 组合残留（变体选择符、ZWJ、方向控制等），避免出现不可见乱码
        try:
            cleaned: List[str] = []
            for ch in text:
                if ch in {"\n", "\t"}:
                    cleaned.append(ch)
                    continue
                code = ord(ch)
                if 0xFE00 <= code <= 0xFE0F:
                    continue
                if 0xE0100 <= code <= 0xE01EF:
                    continue
                cat = unicodedata.category(ch)
                if cat == "Cf":
                    continue
                if cat.startswith("M"):
                    continue
                if cat.startswith("C"):
                    continue
                cleaned.append(ch)
            text = "".join(cleaned)
        except Exception:
            pass
        return text.strip()

    def _extract_title_content(
        self,
        topic: str,
        header_title: str,
        author: str,
        raw_text: str,
        parsed: Optional[Dict[str, Any]],
    ) -> Tuple[str, str]:
        if not parsed:
            # 没拿到 JSON，直接兜底使用原文
            title = header_title.strip() or topic.strip()[:20]
            return title, raw_text.strip()

        title = self._remove_emoji(str(parsed.get("title") or parsed.get("main_title") or header_title or topic).strip())
        if not title:
            title = self._remove_emoji(header_title.strip() or topic.strip())

        # 新模板：title1 + content(list)，更适合图片排版
        subtitle = self._remove_emoji(str(parsed.get("title1") or parsed.get("subtitle") or parsed.get("sub_title") or "").strip())

        content_value = parsed.get("content")
        if isinstance(content_value, list):
            blocks: List[str] = []
            if subtitle:
                blocks.append(subtitle)
            for it in content_value:
                s = self._remove_emoji(str(it or "").strip())
                if not s:
                    continue
                if "~~~" in s:
                    head, body = s.split("~~~", 1)
                    head = self._remove_emoji(head.strip())
                    body = self._remove_emoji(body.strip())
                    segment = "\n".join([x for x in [head, body] if x])
                else:
                    segment = s
                if segment:
                    blocks.append(segment)
            content = "\n\n".join([self._remove_emoji(x) for x in blocks]).strip()
        else:
            full_content = self._remove_emoji(str(content_value or parsed.get("full_content") or "").strip())
            if not full_content and isinstance(parsed.get("content_pages"), list):
                pages = [self._remove_emoji(str(x).strip()) for x in parsed.get("content_pages") if str(x).strip()]
                full_content = "\n\n".join([p for p in pages if p])

            content = full_content.strip() if full_content else self._remove_emoji(raw_text.strip())

        hashtags = parsed.get("hashtags") or parsed.get("tags") or []
        if isinstance(hashtags, str):
            hashtags = [x.strip() for x in hashtags.split() if x.strip()]

        # 去掉标签中的 #，避免“特殊符号”影响排版
        normalized_tags: List[str] = []
        if isinstance(hashtags, list):
            for tag in hashtags:
                t = str(tag or "").strip()
                if not t:
                    continue
                if t.startswith("#"):
                    t = t.lstrip("#").strip()
                if t:
                    normalized_tags.append(t)

        call_to_action = self._remove_emoji(str(parsed.get("call_to_action") or "").strip())

        extra_parts: List[str] = []
        if normalized_tags:
            extra_parts.append(" ".join([f"#{t}" for t in normalized_tags if t]).strip())
        if call_to_action:
            extra_parts.append(call_to_action)

        if extra_parts:
            content = f"{content}\n\n" + "\n\n".join([self._remove_emoji(x) for x in extra_parts if self._remove_emoji(x)])

        return title, content


llm_service = LLMService()
