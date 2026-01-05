"""
系统图片模板服务

用于加载/管理外部的“系统模板图片”（例如 x-auto-publisher 的 output/templates 目录），并将其
用于生成发布所需的封面/内容图片。
"""

from __future__ import annotations

from dataclasses import dataclass
import os
import random
import re
import shutil
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw

from src.config.config import Config
from src.core.services.font_manager import font_manager


@dataclass(frozen=True)
class ContentPack:
    """一组内容模板（通常包含 page1~pageN）。"""

    id: str
    pages: List[Path]

    @property
    def preview(self) -> Optional[Path]:
        return self.pages[0] if self.pages else None


class SystemImageTemplateService:
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()

    @staticmethod
    def _get_repo_root() -> Path:
        try:
            return Path(__file__).resolve().parents[3]
        except Exception:
            return Path.cwd()

    @staticmethod
    def _format_cover_template_display(style: str, theme: str) -> str:
        style_map = {
            "clean": "简洁",
            "cute": "可爱",
            "natural": "自然",
            "professional": "专业",
            "trendy": "潮流",
            "modern": "现代",
        }
        theme_map = {
            "pink": "粉",
            "blue": "蓝",
            "green": "绿",
            "purple": "紫",
            "orange": "橙",
            "neutral": "灰",
        }
        style_label = style_map.get(style, style)
        theme_label = theme_map.get(theme, theme)
        return f"{style_label}·{theme_label}" if theme_label else style_label

    def get_local_templates_dir(self) -> Path:
        return Path(os.path.expanduser("~")) / ".xhs_system" / "system_templates"

    def _normalize_source_dir(self, value: str) -> Optional[Path]:
        if not value:
            return None

        p = Path(os.path.expanduser(value)).resolve()
        if p.is_file():
            p = p.parent

        candidates = [
            p,
            p / "backend" / "output" / "templates",
            p / "backend" / "templates",
            p / "output" / "templates",
            p / "templates",
        ]
        for c in candidates:
            if c.exists() and c.is_dir():
                return c

        return None

    def _auto_detect_x_auto_publisher_templates_dir(self) -> Optional[Path]:
        try:
            repo_root = Path(__file__).resolve().parents[3]
        except Exception:
            repo_root = Path.cwd()

        candidates = [
            repo_root.parent / "x-auto-publisher" / "backend" / "output" / "templates",
            repo_root.parent / "x-auto-publisher" / "backend" / "templates",
        ]
        for c in candidates:
            if c.exists() and c.is_dir():
                return c

        return None

    def resolve_templates_dir(self) -> Optional[Path]:
        """解析系统模板目录（优先级：配置 > 环境变量 > 本地导入目录 > 自动探测）。"""
        try:
            self.config.load_config()
        except Exception:
            pass

        templates_cfg = self.config.get_templates_config()
        configured = (templates_cfg.get("system_templates_dir") or "").strip()
        configured_dir = self._normalize_source_dir(configured)
        if configured_dir:
            return configured_dir

        env_dir = self._normalize_source_dir(os.environ.get("XHS_SYSTEM_TEMPLATES_DIR", "").strip())
        if env_dir:
            return env_dir

        local_dir = self.get_local_templates_dir()
        if local_dir.exists() and local_dir.is_dir():
            return local_dir

        return self._auto_detect_x_auto_publisher_templates_dir()

    def list_content_packs(self) -> List[ContentPack]:
        base_dir = self.resolve_templates_dir()
        if not base_dir:
            return []

        packs: Dict[str, Dict[int, Path]] = {}
        for path in base_dir.glob("content_*_page*.png"):
            stem = path.stem  # e.g., content_clean_blue_page1
            if "_page" not in stem:
                continue
            pack_id, page_str = stem.rsplit("_page", 1)
            if not page_str.isdigit():
                continue
            page_num = int(page_str)
            packs.setdefault(pack_id, {})[page_num] = path

        result: List[ContentPack] = []
        for pack_id, page_map in packs.items():
            pages = [page_map[i] for i in sorted(page_map.keys())]
            result.append(ContentPack(id=pack_id, pages=pages))
        result.sort(key=lambda p: p.id)
        return result

    def list_cover_templates(self) -> List[Dict[str, str]]:
        """列出系统封面模板图片（cover_*.png）。"""
        base_dir = self.resolve_templates_dir()
        if not base_dir:
            return []

        results: List[Dict[str, str]] = []
        for path in base_dir.glob("cover_*.png"):
            stem = path.stem  # e.g. cover_clean_pink
            parts = stem.split("_")
            style = parts[1] if len(parts) >= 3 else "cover"
            theme = parts[2] if len(parts) >= 3 else ""
            results.append(
                {
                    "id": stem,
                    "style": style,
                    "theme": theme,
                    "path": str(path),
                    "display": self._format_cover_template_display(style, theme),
                }
            )

        results.sort(key=lambda t: (t.get("style") or "", t.get("theme") or "", t.get("id") or ""))
        return results

    def resolve_showcase_dir(self) -> Optional[Path]:
        """解析 showcase 模板目录（优先项目内置模板）。"""
        repo_root = self._get_repo_root()
        bundled = repo_root / "assets" / "system_templates" / "template_showcase"
        if bundled.exists() and bundled.is_dir() and any(bundled.glob("showcase_*.png")):
            return bundled

        base_dir = self.resolve_templates_dir()
        if base_dir:
            candidate = base_dir.parent / "template_showcase"
            if candidate.exists() and candidate.is_dir():
                return candidate

            # 兼容旧结构：showcase 直接放在 output/templates
            if any(base_dir.glob("showcase_*.png")):
                return base_dir

        candidates = [
            repo_root.parent / "x-auto-publisher" / "backend" / "output" / "template_showcase",
            repo_root.parent / "x-auto-publisher" / "backend" / "output" / "templates",
        ]
        for c in candidates:
            if c.exists() and c.is_dir():
                if c.name == "template_showcase" or any(c.glob("showcase_*.png")):
                    return c

        return None

    def resolve_template_showcase_dir(self) -> Optional[Path]:
        """兼容旧调用：等同 resolve_showcase_dir()."""
        return self.resolve_showcase_dir()

    @staticmethod
    def _format_showcase_variant(variant: str) -> str:
        if not variant:
            return ""

        style_map = {
            "professional": "专业",
            "warm": "温暖",
            "cool": "冷色",
            "tech": "科技",
            "vibrant": "活力",
            "elegant": "优雅",
            "nature": "自然",
            "monochrome": "黑白",
        }

        parts = [p for p in (variant or "").split("_") if p]
        alt_label = ""
        style_label = ""
        rest: List[str] = []

        for p in parts:
            if p.startswith("alt") and p[3:].isdigit():
                alt_label = f"方案{p[3:]}"
                continue
            if p in style_map:
                style_label = style_map[p]
                continue
            rest.append(p)

        label_parts: List[str] = []
        if alt_label:
            label_parts.append(alt_label)
        if style_label:
            label_parts.append(style_label)
        if rest:
            label_parts.append("_".join(rest))

        return "·".join(label_parts) if label_parts else variant

    def list_showcase_templates(self) -> List[Dict[str, str]]:
        """列出 x-auto-publisher 的 showcase 模板（showcase_*.png）。"""
        showcase_dir = self.resolve_showcase_dir()
        if not showcase_dir:
            return []

        # metadata（用于补充中文名/分类）
        id_to_meta: Dict[str, Dict[str, str]] = {}
        meta_candidates = [
            showcase_dir / "templates_metadata.json",
        ]

        base_dir = self.resolve_templates_dir()
        if base_dir:
            meta_candidates.append(base_dir / "templates_metadata.json")

        for meta_file in meta_candidates:
            if not meta_file.exists():
                continue
            try:
                import json

                data = json.loads(meta_file.read_text(encoding="utf-8")) or {}
                for t in data.get("templates", []) or []:
                    template_id = str(t.get("id") or "").strip()
                    if template_id:
                        id_to_meta[template_id] = {
                            "name": str(t.get("name") or "").strip(),
                            "category": str(t.get("category") or "").strip(),
                        }
                if id_to_meta:
                    break
            except Exception:
                continue

        base_ids = sorted(id_to_meta.keys(), key=len, reverse=True)

        results: List[Dict[str, str]] = []
        for path in sorted(showcase_dir.glob("showcase_*.png")):
            try:
                if not path.is_file():
                    continue
                if path.stat().st_size <= 0:
                    continue
            except Exception:
                continue

            stem = path.stem  # showcase_xxx
            key = stem[len("showcase_") :] if stem.startswith("showcase_") else stem

            matched_base = ""
            for base_id in base_ids:
                if key == base_id or key.startswith(base_id + "_"):
                    matched_base = base_id
                    break

            base_id = matched_base or key
            variant = key[len(base_id) + 1 :] if matched_base and key != base_id else ""

            meta = id_to_meta.get(base_id, {})
            name = meta.get("name") or base_id
            category = meta.get("category") or ""
            variant_display = self._format_showcase_variant(variant)
            display = f"{name}·{variant_display}" if variant_display else name

            results.append(
                {
                    "id": stem,
                    "base_id": base_id,
                    "variant": variant,
                    "name": name,
                    "category": category,
                    "path": str(path),
                    "display": display,
                }
            )

        results.sort(key=lambda t: (t.get("category") or "zzz", t.get("name") or "", t.get("variant") or ""))
        return results

    def get_selected_pack_id(self) -> str:
        try:
            self.config.load_config()
        except Exception:
            pass
        templates_cfg = self.config.get_templates_config()
        return str(templates_cfg.get("default_content_pack") or "").strip()

    def choose_pack(self, pack_id: str = "") -> Optional[ContentPack]:
        packs = self.list_content_packs()
        if not packs:
            return None

        pack_id = (pack_id or "").strip()
        if pack_id:
            for p in packs:
                if p.id == pack_id:
                    return p

        # 未指定模板包时：优先选择更“默认/干净”的模板，避免随机出现过于花哨的配色（如紫色）
        preferred = [
            "content_clean_neutral",
            "content_clean_blue",
            "content_professional_neutral",
            "content_natural_neutral",
            "content_trendy_neutral",
        ]
        for pid in preferred:
            for p in packs:
                if p.id == pid:
                    return p

        return random.choice(packs)

    def import_from_source(self, source_dir: str) -> Tuple[bool, str]:
        """将外部模板目录复制到本地 ~/.xhs_system/system_templates（便于跨平台/打包使用）。"""
        src = self._normalize_source_dir(source_dir or "")
        if not src:
            return False, "未找到可用的模板目录"

        dst = self.get_local_templates_dir()
        try:
            dst.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return False, f"创建本地模板目录失败: {e}"

        patterns = [
            "content_*.png",
            "cover_*.png",
            "template_*.png",
            "showcase_*.png",
            "templates_metadata.json",
            "template_index.json",
        ]

        copied = 0
        for pattern in patterns:
            for file_path in src.glob(pattern):
                try:
                    if file_path.is_dir():
                        continue
                    target = dst / file_path.name
                    shutil.copy2(file_path, target, follow_symlinks=True)
                    copied += 1
                except Exception:
                    continue

        if copied <= 0:
            return False, "未在源目录中找到可复制的模板文件"

        # 写入配置，优先使用本地模板目录
        try:
            cfg = self.config.get_templates_config()
            cfg["system_templates_dir"] = str(dst)
            self.config.update_templates_config(cfg)
        except Exception:
            pass

        return True, f"已导入 {copied} 个模板文件到 {dst}"

    @staticmethod
    def _resize_with_letterbox(img: Image.Image, target_size: Tuple[int, int]) -> Image.Image:
        """等比缩放并居中留白，避免拉伸变形。"""
        if img.size == target_size:
            return img

        src_w, src_h = img.size
        dst_w, dst_h = target_size

        if src_w <= 0 or src_h <= 0:
            return img.resize(target_size, Image.Resampling.LANCZOS)

        try:
            center_color = img.getpixel((src_w // 2, src_h // 2))
        except Exception:
            center_color = (245, 245, 245)

        if isinstance(center_color, tuple) and len(center_color) >= 3:
            center_color = center_color[:3]

        scale = min(dst_w / src_w, dst_h / src_h)
        new_w = max(1, int(round(src_w * scale)))
        new_h = max(1, int(round(src_h * scale)))
        resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        canvas = Image.new("RGB", (dst_w, dst_h), color=center_color)
        paste_x = (dst_w - new_w) // 2
        paste_y = (dst_h - new_h) // 2
        canvas.paste(resized, (paste_x, paste_y))
        return canvas

    @staticmethod
    def _clean_text(text: str) -> str:
        if not text:
            return ""

        # 移除 emoji（尽量不误伤中文）
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

        return text.strip()

    @staticmethod
    def _luminance(color: Tuple[int, int, int]) -> float:
        try:
            r, g, b = color[:3]
        except Exception:
            return 255.0
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    @staticmethod
    def _extract_tags(body: str) -> Tuple[str, List[str]]:
        """从正文中提取「话题标签/标签」并返回 (clean_body, tags)。"""
        text = (body or "").strip()
        if not text:
            return "", []

        tag_pattern = re.compile(r"^(?:话题标签|标签|话题)[:：]\s*(.+)$")
        tags: List[str] = []
        kept: List[str] = []

        for raw in (text.splitlines() or []):
            line = str(raw or "").strip()
            if not line:
                kept.append("")
                continue

            if line in {"标签", "话题标签", "话题"}:
                continue

            m = tag_pattern.match(line)
            if m:
                raw_tags = (m.group(1) or "").strip()
                raw_tags = raw_tags.replace("#", " ")
                raw_tags = re.sub(r"[，,、/|]+", " ", raw_tags)
                parts = [p.strip() for p in raw_tags.split() if p.strip()]
                tags.extend(parts)
                continue

            kept.append(line)

        # 去重（保序）
        seen = set()
        uniq: List[str] = []
        for t in tags:
            t = str(t or "").strip()
            if not t or t in seen:
                continue
            seen.add(t)
            uniq.append(t)

        clean_body = "\n".join(kept).strip()
        return clean_body, uniq[:12]

    @staticmethod
    def _auto_paragraphize(text: str) -> str:
        """将一整段的长文本自动分段，提升“小红书”阅读节奏。"""
        raw = (text or "").strip()
        if not raw:
            return ""

        # 已经有明显分段就不强制处理
        if "\n\n" in raw or raw.count("\n") >= 2:
            return raw

        # 句子切分（优先按句号/问号/感叹号/分号）
        sentences: List[str] = []
        buff = ""
        for ch in raw:
            buff += ch
            if ch in "。！？；":
                s = buff.strip()
                if s:
                    sentences.append(s)
                buff = ""
        rest = buff.strip()
        if rest:
            sentences.append(rest)

        used_comma_split = False
        if len(sentences) <= 1:
            # 再尝试按逗号轻拆（避免一整段太“糊”），并尽量保留标点
            comma_breaks = set("，,、")
            parts: List[str] = []
            buff = ""
            for ch in raw:
                buff += ch
                if ch in comma_breaks:
                    s = buff.strip()
                    if s:
                        parts.append(s)
                    buff = ""
            rest2 = buff.strip()
            if rest2:
                parts.append(rest2)

            if len(parts) > 1:
                sentences = parts
                used_comma_split = True
            else:
                sentences = [raw]

        # 分组：每段 1-2 句（逗号拆分的更碎，允许 1-3 句），并控制段落长度
        paras: List[str] = []
        cur: List[str] = []
        cur_len = 0
        max_sent = 3 if used_comma_split else 2
        max_len = 56 if used_comma_split else 44
        for s in sentences:
            s = s.strip()
            if not s:
                continue
            s_len = len(s)
            if cur and (len(cur) >= max_sent or cur_len + s_len > max_len):
                paras.append("".join(cur).strip())
                cur = [s]
                cur_len = s_len
            else:
                cur.append(s)
                cur_len += s_len
        if cur:
            paras.append("".join(cur).strip())

        # 合并过短段落（例如“效果才会出来。”单独成段会很怪）
        merged: List[str] = []
        for p in paras:
            p = (p or "").strip()
            if not p:
                continue
            if merged and len(p) <= 10:
                merged[-1] = (merged[-1].rstrip() + p).strip()
            else:
                merged.append(p)
        paras = merged

        # 最终至少 2 段才生效，否则保持原样
        if len(paras) >= 2:
            return "\n\n".join([p for p in paras if p]).strip()
        return raw

    @staticmethod
    def _pick_accent_color(img: Image.Image) -> Tuple[int, int, int]:
        """尝试从模板边框采样一个强调色，失败则回退为蓝色。"""
        try:
            w, h = img.size
            samples = [
                img.getpixel((w // 2, 6)),
                img.getpixel((6, h // 2)),
                img.getpixel((w - 7, h // 2)),
                img.getpixel((w // 2, h - 7)),
            ]
            best = None
            best_score = -1.0
            for c in samples:
                if not isinstance(c, tuple) or len(c) < 3:
                    continue
                rgb = tuple(int(x) for x in c[:3])
                lum = SystemImageTemplateService._luminance(rgb)
                # 排除接近白/黑
                if lum > 245 or lum < 10:
                    continue
                saturation = max(rgb) - min(rgb)
                score = saturation + (255 - abs(lum - 140)) * 0.05
                if score > best_score:
                    best_score = score
                    best = rgb
            if best:
                return best
        except Exception:
            pass
        return (74, 144, 226)

    @staticmethod
    def _smart_wrap(text: str, draw: ImageDraw.ImageDraw, font, max_width: int) -> List[str]:
        """中文友好的逐字换行。"""
        text = (text or "").strip()
        if not text:
            return []

        lines: List[str] = []
        current = ""
        break_chars = set("，。！？；、,.!?")

        for i, ch in enumerate(text):
            test = current + ch
            bbox = draw.textbbox((0, 0), test, font=font)
            width = bbox[2] - bbox[0]
            if width > max_width and current:
                # 优先在标点断行
                if i > 0 and text[i - 1] in break_chars:
                    lines.append(current)
                    current = ch
                    continue

                last_break = -1
                for j in range(len(current) - 1, -1, -1):
                    if current[j] in break_chars:
                        last_break = j
                        break
                if last_break > 0 and len(current) - last_break < 10:
                    lines.append(current[: last_break + 1])
                    current = current[last_break + 1 :] + ch
                else:
                    lines.append(current)
                    current = ch
            else:
                current = test

        if current:
            lines.append(current)

        # 处理“标点单独成行”的情况：尽量把标点合并到上一行，避免出现“。”独占一行
        if len(lines) >= 2:
            punct = break_chars
            fixed: List[str] = []
            for ln in lines:
                if not fixed:
                    fixed.append(ln)
                    continue
                s = str(ln or "")
                if not s:
                    fixed.append(s)
                    continue

                moved = ""
                while s and s[0] in punct:
                    moved += s[0]
                    s = s[1:]
                if moved:
                    fixed[-1] = (fixed[-1] or "") + moved
                    if s:
                        fixed.append(s)
                    continue

                # 整行只有一个标点
                if len(s) == 1 and s in punct:
                    fixed[-1] = (fixed[-1] or "") + s
                    continue

                fixed.append(s)

            lines = [x for x in fixed if x is not None]

        return lines

    @staticmethod
    def _parse_page(text: str) -> Tuple[str, str]:
        raw_lines = [ln.rstrip("\r\n") for ln in (text or "").splitlines()]

        # 找到第一行非空内容（保留中间空行用于“分段换行”）
        first_idx = -1
        for i, ln in enumerate(raw_lines):
            if str(ln or "").strip():
                first_idx = i
                break

        if first_idx < 0:
            return "", ""

        first = str(raw_lines[first_idx] or "").lstrip()
        if first.startswith("#"):
            page_title = first.lstrip("#").strip()
            body_lines = raw_lines[first_idx + 1 :]
        else:
            page_title = ""
            body_lines = raw_lines[first_idx:]

        # 去掉正文前后空行，但保留中间空行
        while body_lines and not str(body_lines[0] or "").strip():
            body_lines.pop(0)
        while body_lines and not str(body_lines[-1] or "").strip():
            body_lines.pop()

        body = "\n".join([str(x) for x in body_lines]).strip()
        return page_title, body

    @staticmethod
    def _split_into_pages(text: str, count: int = 3) -> List[str]:
        text = (text or "").strip()
        if not text:
            return []

        paras = [p.strip() for p in text.split("\n\n") if p.strip()]
        if len(paras) >= count:
            pages: List[str] = []
            per = max(1, len(paras) // count)
            for i in range(count):
                chunk = paras[i * per : (i + 1) * per] if i < count - 1 else paras[i * per :]
                pages.append("\n\n".join(chunk).strip())
            return [p for p in pages if p]

        # fallback：按长度切分
        size = max(1, len(text) // count)
        pages = []
        for i in range(count):
            chunk = text[i * size : (i + 1) * size] if i < count - 1 else text[i * size :]
            pages.append(chunk.strip())
        return [p for p in pages if p]

    def generate_post_images(
        self,
        title: str,
        content: str,
        content_pages: Optional[Sequence[str]] = None,
        pack_id: str = "",
        page_count: int = 3,
        target_size: Tuple[int, int] = (1080, 1440),
        bg_image_path: str = "",
        cover_bg_image_path: str = "",
    ) -> Optional[Tuple[str, List[str]]]:
        """基于系统模板生成封面 + 内容图（返回本地路径）。"""
        bg_override: Optional[Path] = None
        cover_override: Optional[Path] = None
        try:
            candidate = Path(os.path.expanduser(str(bg_image_path or "").strip()))
            if candidate.exists() and candidate.is_file():
                bg_override = candidate
        except Exception:
            bg_override = None

        try:
            candidate = Path(os.path.expanduser(str(cover_bg_image_path or "").strip()))
            if candidate.exists() and candidate.is_file():
                cover_override = candidate
        except Exception:
            cover_override = None

        # 兼容旧参数：若只传了 bg_image_path，则封面也使用该背景
        if not cover_override and bg_override:
            cover_override = bg_override

        pack: Optional[ContentPack] = None
        # 内容页：只有在未指定 bg_override 时才使用模板包
        if not bg_override:
            pack = self.choose_pack(pack_id or self.get_selected_pack_id())
            if not pack or not pack.pages:
                return None

        pages = [str(x) for x in (content_pages or []) if str(x).strip()]
        if not pages:
            pages = self._split_into_pages(content, count=page_count)
        if not pages:
            pages = [content.strip()] if content.strip() else []

        pages = pages[: max(1, int(page_count))]

        output_dir = Path(os.path.expanduser("~")) / ".xhs_system" / "generated_imgs"
        output_dir.mkdir(parents=True, exist_ok=True)

        ts = int(time.time())
        unique = uuid.uuid4().hex[:8]
        pack_tag = ""
        try:
            if pack:
                pack_tag = str(pack.id or "").strip()
            elif bg_override:
                pack_tag = f"bg_{bg_override.stem}"
        except Exception:
            pack_tag = ""
        pack_tag = pack_tag or "tpl"
        pack_tag = re.sub(r"[^a-zA-Z0-9_\\-]+", "_", pack_tag)[:40]

        def _open_bg(path: Path) -> Image.Image:
            img = Image.open(str(path)).convert("RGB")
            return self._resize_with_letterbox(img, target_size)

        cover_bg = cover_override if cover_override else (pack.pages[0] if pack else None)
        if not cover_bg:
            return None
        cover_img = _open_bg(cover_bg)
        cover_draw = ImageDraw.Draw(cover_img)

        # Cover: title
        w, h = cover_img.size
        cover_title = self._clean_text(title) or "小红书笔记"
        font_title = font_manager.get_font("chinese", "bold", size=max(28, int(h * 0.06)))
        max_w = w - 160
        lines = self._smart_wrap(cover_title, cover_draw, font_title, max_w)[:3]
        line_h = int(font_title.size * 1.35) if getattr(font_title, "size", None) else 52
        total_h = line_h * max(1, len(lines))
        start_y = max(80, (h - total_h) // 3)
        for line in lines:
            bbox = cover_draw.textbbox((0, 0), line, font=font_title)
            text_w = bbox[2] - bbox[0]
            x = (w - text_w) // 2
            cover_draw.text(
                (x, start_y),
                line,
                fill=(20, 20, 20),
                font=font_title,
                stroke_width=4,
                stroke_fill=(255, 255, 255),
            )
            start_y += line_h

        cover_path = output_dir / f"cover_tpl_{pack_tag}_{ts}_{unique}.jpg"
        cover_img.save(str(cover_path), format="JPEG", quality=92)

        content_paths: List[str] = []
        for idx, page_text in enumerate(pages):
            if bg_override:
                bg_path = bg_override
            else:
                bg_index = min(idx + 1, len(pack.pages) - 1) if pack and len(pack.pages) > 1 else 0
                bg_path = pack.pages[bg_index] if pack else cover_bg
            img = _open_bg(bg_path)
            draw = ImageDraw.Draw(img)
            w, h = img.size

            page_title, body = self._parse_page(page_text)
            page_title = self._clean_text(page_title)
            body = self._clean_text(body or page_text)

            # 从正文中提取标签（用于更美观的标签胶囊渲染）
            body, tags = self._extract_tags(body)
            body = self._auto_paragraphize(body)

            # 安全边距（尽量兼容不同模板，避免贴边/遮挡页码）
            left = int(w * 0.10)
            right = int(w * 0.10)
            top = int(h * 0.14)
            bottom = int(h * 0.12)
            max_text_w = max(1, w - left - right)
            max_text_h = max(1, h - top - bottom)

            # 采样背景亮度，决定文字配色（减少粗描边导致的“脏”感）
            try:
                sample_color = img.getpixel((w // 2, min(h - 2, max(2, top + 20))))
                sample_rgb = tuple(int(x) for x in (sample_color[:3] if isinstance(sample_color, tuple) else (255, 255, 255)))
            except Exception:
                sample_rgb = (255, 255, 255)

            dark_bg = self._luminance(sample_rgb) < 140
            title_fill = (250, 250, 250) if dark_bg else (18, 18, 18)
            body_fill = (245, 245, 245) if dark_bg else (55, 55, 55)
            stroke_w_title = 2 if dark_bg else 0
            stroke_w_body = 1 if dark_bg else 0
            stroke_fill = (10, 10, 10) if dark_bg else (255, 255, 255)

            accent = self._pick_accent_color(img)

            # 根据正文长度给一个更合理的初始字号，再用 fit-to-box 微调
            plain_len = len(re.sub(r"\s+", "", body or ""))
            if plain_len <= 60:
                body_size = int(h * 0.038)
            elif plain_len <= 120:
                body_size = int(h * 0.034)
            elif plain_len <= 180:
                body_size = int(h * 0.031)
            else:
                body_size = int(h * 0.028)

            body_size = max(24, min(56, body_size))
            title_size = max(34, min(86, max(int(h * 0.048), body_size + 10)))

            min_body, min_title = 24, 34
            max_body, max_title = 56, 86

            def _layout_for(size_title: int, size_body: int):
                font_title = font_manager.get_font("chinese", "bold", size=size_title)
                font_body = font_manager.get_font("chinese", "regular", size=size_body)
                font_body_bold = font_manager.get_font("chinese", "bold", size=max(20, int(size_body * 0.96)))

                t_lines = self._smart_wrap(page_title, draw, font_title, max_text_w)[:2] if page_title else []
                title_line_h = int(getattr(font_title, "size", size_title) * 1.22)

                # 正文分段 + 换行：尽量呈现“小红书”常见的段落节奏
                raw_body = (body or "").strip()
                blocks: List[str] = []
                if raw_body:
                    if "\n\n" in raw_body:
                        blocks = [b.strip() for b in re.split(r"\n\s*\n", raw_body) if b.strip()]
                    else:
                        lines = [ln.strip() for ln in raw_body.splitlines() if ln.strip()]
                        blocks = lines if len(lines) > 1 else [raw_body]

                body_items: List[Dict[str, object]] = []
                for block in blocks:
                    block = str(block or "").strip()
                    if not block:
                        continue

                    # 兼容「小标题\\n正文」结构：小标题用加粗，正文用常规
                    seg_lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
                    if len(seg_lines) >= 2 and len(seg_lines[0]) <= 12:
                        sub = seg_lines[0]
                        # 保留正文的换行节奏（不要直接 join 成一段）
                        body_raw_lines = [ln.rstrip() for ln in block.splitlines()[1:]]
                        paras: List[str] = []
                        buf: List[str] = []
                        for ln in body_raw_lines:
                            if not str(ln or "").strip():
                                if buf:
                                    paras.append(" ".join([x.strip() for x in buf if str(x).strip()]).strip())
                                    buf = []
                                continue
                            buf.append(str(ln).strip())
                        if buf:
                            paras.append(" ".join([x.strip() for x in buf if str(x).strip()]).strip())
                        sub_lines = self._smart_wrap(sub, draw, font_body_bold, max_text_w)[:2]
                        for i, ln in enumerate(sub_lines):
                            body_items.append({"text": ln, "kind": "sub", "para_start": i == 0})
                        if paras:
                            for pi, para in enumerate(paras):
                                para = self._auto_paragraphize(str(para or "").strip())
                                parts = (
                                    [p.strip() for p in re.split(r"\n\s*\n", para) if p.strip()]
                                    if "\n\n" in para
                                    else [para]
                                )
                                for pj, part in enumerate(parts):
                                    rest_lines = self._smart_wrap(part, draw, font_body, max_text_w)
                                    for ln in rest_lines:
                                        body_items.append({"text": ln, "kind": "body", "para_start": False})
                                    if (pj < len(parts) - 1) or (pi < len(paras) - 1):
                                        body_items.append({"text": "", "kind": "blank", "para_start": False})
                    else:
                        para_text = " ".join(seg_lines).strip() if seg_lines else block
                        para_text = self._auto_paragraphize(para_text)
                        parts = (
                            [p.strip() for p in re.split(r"\n\s*\n", para_text) if p.strip()]
                            if "\n\n" in para_text
                            else [para_text]
                        )
                        for pi, part in enumerate(parts):
                            # 兼容「关键词：解释」的单行结构，做成更小红书的“要点卡”
                            m = re.match(r"^(.{2,10})[：:](.+)$", part)
                            if m:
                                key = str(m.group(1) or "").strip()
                                val = str(m.group(2) or "").strip()
                                if key:
                                    key_lines = self._smart_wrap(key, draw, font_body_bold, max_text_w)[:2]
                                    for i, ln in enumerate(key_lines):
                                        body_items.append({"text": ln, "kind": "sub", "para_start": i == 0})
                                if val:
                                    val = self._auto_paragraphize(val)
                                    val_parts = (
                                        [p.strip() for p in re.split(r"\n\s*\n", val) if p.strip()]
                                        if "\n\n" in val
                                        else [val]
                                    )
                                    for vpi, vpart in enumerate(val_parts):
                                        v_lines = self._smart_wrap(vpart, draw, font_body, max_text_w)
                                        for ln in v_lines:
                                            body_items.append({"text": ln, "kind": "body", "para_start": False})
                                        if vpi < len(val_parts) - 1:
                                            body_items.append({"text": "", "kind": "blank", "para_start": False})
                                if pi < len(parts) - 1:
                                    body_items.append({"text": "", "kind": "blank", "para_start": False})
                                continue

                            part_lines = self._smart_wrap(part, draw, font_body, max_text_w)
                            for i, ln in enumerate(part_lines):
                                body_items.append({"text": ln, "kind": "body", "para_start": i == 0})
                            if pi < len(parts) - 1:
                                body_items.append({"text": "", "kind": "blank", "para_start": False})

                    # 段落间距
                    body_items.append({"text": "", "kind": "blank", "para_start": False})

                while body_items and str(body_items[-1].get("kind")) == "blank":
                    body_items.pop()

                body_line_h = int(getattr(font_body, "size", size_body) * 1.62)
                body_h = 0
                for it in body_items:
                    if str(it.get("kind")) == "blank":
                        body_h += int(body_line_h * 0.98)
                    else:
                        body_h += body_line_h

                # 段落引导点（小红书常见的“要点”感）
                bullet_r = max(4, int(size_body * 0.18))
                bullet_x = max(18, left - max(18, int(size_body * 0.60)))

                # 标签胶囊区域
                tag_font = font_manager.get_font("chinese", "regular", size=max(20, int(size_body * 0.78)))
                pad_x = 16
                pad_y = 8
                pill_h = int(getattr(tag_font, "size", 28) + pad_y * 2)
                row_gap = 10
                col_gap = 10

                rows = 0
                if tags:
                    x = 0
                    rows = 1
                    for t in tags:
                        bbox = draw.textbbox((0, 0), t, font=tag_font)
                        tw = bbox[2] - bbox[0]
                        pill_w = tw + pad_x * 2
                        if x > 0 and x + pill_w > max_text_w:
                            rows += 1
                            x = 0
                        x += pill_w + col_gap

                tags_h = 0
                tags_gap = 0
                if rows > 0:
                    tags_h = rows * pill_h + (rows - 1) * row_gap
                    tags_gap = int(body_line_h * 0.75)

                divider_h = 0
                divider_gap = 0
                if t_lines:
                    divider_h = 4
                    divider_gap = int(body_line_h * 0.55)

                title_h = len(t_lines) * title_line_h
                gap_title_body = int(body_line_h * 0.55) if t_lines and (body_items or tags) else 0
                total_h = title_h + divider_h + divider_gap + gap_title_body + body_h + tags_gap + tags_h

                return {
                    "font_title": font_title,
                    "font_body": font_body,
                    "font_body_bold": font_body_bold,
                    "font_tag": tag_font,
                    "title_lines": t_lines,
                    "body_items": body_items,
                    "title_line_h": title_line_h,
                    "body_line_h": body_line_h,
                    "bullet_r": bullet_r,
                    "bullet_x": bullet_x,
                    "pill_h": pill_h,
                    "pad_x": pad_x,
                    "pad_y": pad_y,
                    "row_gap": row_gap,
                    "col_gap": col_gap,
                    "divider_h": divider_h,
                    "divider_gap": divider_gap,
                    "gap_title_body": gap_title_body,
                    "tags_gap": tags_gap,
                    "tags_rows": rows,
                    "total_h": total_h,
                }

            layout = _layout_for(title_size, body_size)

            # 先收缩到能放下
            for _ in range(28):
                if layout["total_h"] <= max_text_h:
                    break
                if body_size > min_body:
                    body_size = max(min_body, body_size - 2)
                elif title_size > min_title:
                    title_size = max(min_title, title_size - 2)
                else:
                    break
                title_size = max(min_title, min(max_title, max(title_size, body_size + 8)))
                layout = _layout_for(title_size, body_size)

            # 如果太空，尝试略微放大（但不超过 max）
            for _ in range(18):
                if layout["total_h"] >= max_text_h * 0.66:
                    break
                next_body = min(max_body, body_size + 2)
                next_title = min(max_title, max(title_size, next_body + 8, title_size + 2))
                if next_body == body_size and next_title == title_size:
                    break
                next_layout = _layout_for(next_title, next_body)
                if next_layout["total_h"] > max_text_h:
                    break
                body_size, title_size = next_body, next_title
                layout = next_layout

            # 计算起始 y（略偏上居中，避免整体下坠）
            slack = max(0, max_text_h - int(layout["total_h"]))
            y = top + int(slack * 0.32)
            y_start = y

            # 先绘制一层“内容卡片”底（更像小红书图文卡片）
            try:
                card_pad_x = max(26, int(body_size * 1.15))
                card_pad_y = max(22, int(body_size * 1.10))
                card_left = max(16, left - card_pad_x)
                card_right = min(w - 16, w - right + card_pad_x)
                card_top = max(16, y_start - int(body_size * 1.10))
                card_bottom = min(h - 16, y_start + int(layout["total_h"]) + int(body_size * 1.20))

                radius = max(26, int(body_size * 1.20) + 18)
                overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
                od = ImageDraw.Draw(overlay)

                shadow_alpha = 32 if not dark_bg else 48
                od.rounded_rectangle(
                    (card_left + 6, card_top + 8, card_right + 6, card_bottom + 8),
                    radius=radius,
                    fill=(0, 0, 0, shadow_alpha),
                )

                fill_alpha = 212 if not dark_bg else 150
                fill_color = (255, 255, 255, fill_alpha) if not dark_bg else (18, 18, 18, fill_alpha)
                border_alpha = 90 if not dark_bg else 120
                border_color = (accent[0], accent[1], accent[2], border_alpha)
                od.rounded_rectangle(
                    (card_left, card_top, card_right, card_bottom),
                    radius=radius,
                    fill=fill_color,
                    outline=border_color,
                    width=2,
                )

                img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
                draw = ImageDraw.Draw(img)
            except Exception:
                pass

            # 绘制标题（居中）
            if layout["title_lines"]:
                for line in layout["title_lines"]:
                    bbox = draw.textbbox((0, 0), line, font=layout["font_title"])
                    tw = bbox[2] - bbox[0]
                    x = (w - tw) // 2
                    draw.text(
                        (x, y),
                        line,
                        fill=title_fill,
                        font=layout["font_title"],
                        stroke_width=stroke_w_title,
                        stroke_fill=stroke_fill,
                    )
                    y += layout["title_line_h"]

                # 分割线
                if layout["divider_h"] > 0:
                    y += int(layout["divider_gap"] * 0.45)
                    line_w = min(200, int(max_text_w * 0.28))
                    x0 = (w - line_w) // 2
                    y0 = y
                    draw.rounded_rectangle(
                        (x0, y0, x0 + line_w, y0 + layout["divider_h"]),
                        radius=3,
                        fill=accent,
                    )
                    y += layout["divider_h"] + int(layout["divider_gap"] * 0.55)

                y += layout["gap_title_body"]

            # 绘制正文（左对齐）
            bottom_limit = h - bottom
            # 小标题更“跳”，更像小红书的要点卡片
            if dark_bg:
                sub_fill = (255, 255, 255)
                sub_bg = (0, 0, 0)
            else:
                sub_fill = tuple(max(0, int(c * 0.85)) for c in accent)
                sub_bg = tuple(int(c * 0.12 + 255 * 0.88) for c in accent)

            dot_fill = (accent[0], accent[1], accent[2]) if not dark_bg else (235, 235, 235)
            for it in layout["body_items"]:
                if y > bottom_limit - 30:
                    break
                kind = str(it.get("kind") or "")
                ln = str(it.get("text") or "")
                if kind == "blank":
                    y += int(layout["body_line_h"] * 0.98)
                    continue
                para_start = bool(it.get("para_start"))

                font = layout["font_body_bold"] if kind == "sub" else layout["font_body"]
                fill = sub_fill if kind == "sub" else body_fill

                if para_start and ln.strip():
                    try:
                        cy = y + int(getattr(font, "size", 28) * 0.58)
                        r = int(layout.get("bullet_r") or 5)
                        bx = int(layout.get("bullet_x") or left)

                        if kind == "sub":
                            # 小标题：左侧强调条 + 轻底色
                            bar_w = max(6, int(r * 1.4))
                            bar_h = max(18, int(getattr(font, "size", 28) * 0.95))
                            x0 = max(16, bx - bar_w)
                            y0 = int(cy - bar_h * 0.55)
                            draw.rounded_rectangle((x0, y0, x0 + bar_w, y0 + bar_h), radius=4, fill=accent)

                            bbox = draw.textbbox((0, 0), ln, font=font)
                            tw = bbox[2] - bbox[0]
                            th = bbox[3] - bbox[1]
                            pad_x = max(10, int(getattr(font, "size", 28) * 0.40))
                            pad_y = max(6, int(getattr(font, "size", 28) * 0.22))
                            bg_x0 = left - pad_x
                            bg_y0 = y - pad_y
                            bg_x1 = min(w - right, left + tw + pad_x)
                            bg_y1 = y + th + pad_y
                            draw.rounded_rectangle((bg_x0, bg_y0, bg_x1, bg_y1), radius=18, fill=sub_bg)
                        else:
                            draw.ellipse((bx - r, cy - r, bx + r, cy + r), fill=dot_fill)
                    except Exception:
                        pass

                draw.text(
                    (left, y),
                    ln,
                    fill=fill,
                    font=font,
                    stroke_width=stroke_w_body,
                    stroke_fill=stroke_fill,
                )
                y += layout["body_line_h"]

            # 绘制标签胶囊（如果有）
            if tags and layout["tags_rows"] > 0 and y < bottom_limit - layout["pill_h"]:
                y += layout["tags_gap"]

                tag_bg = (255, 255, 255) if dark_bg else (245, 246, 248)
                tag_border = accent if not dark_bg else (220, 220, 220)
                tag_text = (50, 50, 50) if not dark_bg else (20, 20, 20)

                x = left
                row_y = y
                for t in tags:
                    bbox = draw.textbbox((0, 0), t, font=layout["font_tag"])
                    tw = bbox[2] - bbox[0]
                    pill_w = tw + layout["pad_x"] * 2
                    if x > left and x + pill_w > w - right:
                        row_y += layout["pill_h"] + layout["row_gap"]
                        x = left
                    if row_y > bottom_limit - layout["pill_h"]:
                        break
                    rect = (x, row_y, x + pill_w, row_y + layout["pill_h"])
                    draw.rounded_rectangle(rect, radius=int(layout["pill_h"] / 2), fill=tag_bg, outline=tag_border, width=2)
                    tx = x + layout["pad_x"]
                    ty = row_y + (layout["pill_h"] - getattr(layout["font_tag"], "size", 24)) // 2 - 2
                    draw.text((tx, ty), t, fill=tag_text, font=layout["font_tag"])
                    x += pill_w + layout["col_gap"]

            out_path = output_dir / f"content_tpl_{idx+1}_{pack_tag}_{ts}_{unique}.jpg"
            img.save(str(out_path), format="JPEG", quality=92)
            content_paths.append(str(out_path))

        return str(cover_path), content_paths


system_image_template_service = SystemImageTemplateService()
