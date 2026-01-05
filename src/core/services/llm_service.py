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
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests

from src.config.config import Config
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
        api_key_name = (model_config.get("api_key_name") or "").strip() or "default"
        if provider and api_key_name:
            key = api_key_manager.get_key(provider, api_key_name)
            if key:
                return key.strip()
            for alias_provider in self._provider_aliases_for_key(provider):
                alias_key = api_key_manager.get_key(alias_provider, api_key_name)
                if alias_key:
                    return alias_key.strip()

        endpoint = (model_config.get("api_endpoint") or "").strip()
        env_key = self._api_key_from_env(provider, endpoint)
        return (env_key or "").strip()

    def _api_key_from_env(self, provider: str, endpoint: str) -> str:
        provider = (provider or "").strip()
        endpoint = (endpoint or "").strip()
        provider_lower = provider.lower()
        endpoint_lower = endpoint.lower()

        if "anthropic" in endpoint_lower or "claude" in provider_lower:
            return os.environ.get("ANTHROPIC_API_KEY", "") or ""
        if "openai" in endpoint_lower or "openai" in provider_lower:
            return os.environ.get("OPENAI_API_KEY", "") or ""
        if "dashscope" in endpoint_lower or "qwen" in provider_lower or "通义" in provider or "阿里" in provider:
            return os.environ.get("DASHSCOPE_API_KEY", "") or ""
        if "moonshot" in endpoint_lower or "kimi" in provider_lower or "月之暗面" in provider:
            return os.environ.get("MOONSHOT_API_KEY", "") or ""
        if "volces" in endpoint_lower or "doubao" in provider_lower or "豆包" in provider or "字节" in provider or "火山" in provider:
            return (
                os.environ.get("ARK_API_KEY", "")
                or os.environ.get("VOLC_API_KEY", "")
                or os.environ.get("VOLCENGINE_API_KEY", "")
                or os.environ.get("DOUBAO_API_KEY", "")
                or ""
            )
        if "tencent" in endpoint_lower or "hunyuan" in provider_lower or "混元" in provider or "腾讯" in provider or "lkeap" in endpoint_lower:
            return os.environ.get("TENCENT_API_KEY", "") or os.environ.get("HUNYUAN_API_KEY", "") or os.environ.get("LKEAP_API_KEY", "") or ""

        # 兜底：兼容 OpenAI-compatible 的常用变量名
        return os.environ.get("OPENAI_API_KEY", "") or os.environ.get("API_KEY", "") or ""

    def is_model_configured(self, model_config: Dict[str, Any]) -> Tuple[bool, str]:
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

        model_config = self.config.get_model_config()
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
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        raw_text = self._call_model(model_config, messages)
        parsed = self._try_parse_json(raw_text)

        title, content = self._extract_title_content(topic, header_title, author, raw_text, parsed)
        return LLMResponse(title=title, content=content, raw_text=raw_text, raw_json=parsed)

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
            return self._build_xiaohongshu_prompt(topic, header_title, author)

        return self._render_template(
            tpl.user_prompt,
            {
                "topic": (topic or "").strip(),
                "header_title": (header_title or "").strip(),
                "author": (author or "").strip(),
            },
        ).strip()

    def _render_template(self, template_text: str, mapping: Dict[str, str]) -> str:
        """简单模板渲染：将 {{key}} 替换为值，避免与 JSON 花括号冲突。"""
        rendered = template_text or ""
        for key, value in mapping.items():
            rendered = rendered.replace(f"{{{{{key}}}}}", value)
        return rendered

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
1. 标题：10-20字，吸引人，贴近小红书风格（可适度口语化）
2. 正文：400-700字，分段清晰；包含3-6条要点（可用列表）；结尾要有互动引导
3. 话题标签：给出5-10个相关 #话题 标签
4. 返回“严格 JSON”，不要使用 ``` 包裹，不要输出多余解释文字

返回 JSON 格式（字段允许扩展，但至少包含这些）：
{{
  "title": "标题",
  "full_content": "完整正文（不含话题标签也可以）",
  "content_pages": [
    "# 第1页标题\\n\\n正文...",
    "# 第2页标题\\n\\n正文...",
    "# 第3页标题\\n\\n正文..."
  ],
  "hashtags": ["#话题1", "#话题2"],
  "call_to_action": "互动引导（可为空）"
}}
""".strip()

    def _call_model(self, model_config: Dict[str, Any], messages: List[Dict[str, str]]) -> str:
        endpoint = (model_config.get("api_endpoint") or "").strip()
        provider = (model_config.get("provider") or "").strip()

        advanced = model_config.get("advanced") or {}
        temperature = float(advanced.get("temperature", 0.7))
        max_tokens = int(advanced.get("max_tokens", 1000))
        timeout = float(advanced.get("timeout", 30))

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

        # 兜底：如果末尾没有 /v1，假设它是 base_url
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
            message = first.get("message") or {}
            content = message.get("content")
            if content:
                return str(content)

            # 一些兼容实现可能返回 text
            if first.get("text"):
                return str(first["text"])
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
            text = emoji_pattern.sub("", str(text))
        except Exception:
            text = str(text)
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
            title = header_title.strip() or f"{topic.strip()[:18]}..."
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
            extra_parts.append("标签：" + " ".join(normalized_tags))
        if call_to_action:
            extra_parts.append(call_to_action)

        if extra_parts:
            content = f"{content}\n\n" + "\n".join([self._remove_emoji(x) for x in extra_parts if self._remove_emoji(x)])

        return title, content


llm_service = LLMService()
