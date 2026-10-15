"""
系统图片模板服务

用于加载/管理外部的“系统模板图片”（例如 x-auto-publisher 的 output/templates 目录），并将其
用于生成发布所需的封面/内容图片。
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
import random
import re
import shutil
import time
import unicodedata
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
    def _env_bool(name: str, *, default: bool = False) -> bool:
        val = (os.environ.get(name) or "").strip().lower()
        if not val:
            return default
        return val in {"1", "true", "yes", "y", "on"}

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
        from src.core.services.poster_catalog import LAYOUT_TEMPLATES, RETIRED_REPLACEMENTS
        bundled = Path(__file__).resolve().parents[3] / 'assets/system_templates/template_showcase'
        if showcase_dir.resolve() == bundled.resolve():
            results = [t for t in results if t['id'] not in RETIRED_REPLACEMENTS]
        order = {key:n for n,key in enumerate(LAYOUT_TEMPLATES)}
        results.sort(key=lambda t: (0,order[t['id']]) if t['id'] in order else (1,t.get('display') or ''))
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
    def _create_builtin_background(
        size: Tuple[int, int],
        *,
        seed_text: str,
        variant: int = 0,
    ) -> Tuple[Image.Image, Tuple[int, int, int]]:
        """生成一个内置的“干净渐变”背景（无外部模板时兜底使用）。"""
        w, h = size
        seed_src = (seed_text or "").strip() or "xhs"
        base_seed = int(hashlib.md5(seed_src.encode("utf-8", errors="ignore")).hexdigest()[:8], 16)
        rng_seed = base_seed + int(variant or 0) * 97
        rng = random.Random(rng_seed)

        themes = [
            # (top, bottom, accent)
            ((245, 250, 255), (236, 245, 255), (59, 130, 246)),   # blue
            ((246, 255, 252), (236, 253, 245), (16, 185, 129)),   # green
            ((255, 248, 250), (255, 236, 239), (236, 72, 153)),   # pink
            ((255, 250, 240), (255, 243, 230), (245, 158, 11)),   # orange
            ((248, 247, 255), (240, 236, 255), (139, 92, 246)),   # purple
            ((250, 250, 250), (245, 245, 245), (79, 70, 229)),    # neutral/indigo
        ]
        top, bottom, accent = themes[base_seed % len(themes)]

        # 轻微扰动颜色，避免每次都一模一样
        def _jitter(c: Tuple[int, int, int], j: int = 10) -> Tuple[int, int, int]:
            return tuple(max(0, min(255, int(x + rng.randint(-j, j)))) for x in c)

        top = _jitter(top, 8)
        bottom = _jitter(bottom, 10)

        img = Image.new("RGB", (w, h), color=top)
        draw = ImageDraw.Draw(img)

        # vertical gradient
        for y in range(h):
            t = y / max(1, h - 1)
            r = int(top[0] * (1 - t) + bottom[0] * t)
            g = int(top[1] * (1 - t) + bottom[1] * t)
            b = int(top[2] * (1 - t) + bottom[2] * t)
            draw.line([(0, y), (w, y)], fill=(r, g, b))

        # soft blobs
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        for _ in range(4):
            rr = rng.randint(int(min(w, h) * 0.18), int(min(w, h) * 0.36))
            cx = rng.randint(-rr // 3, w + rr // 3)
            cy = rng.randint(int(h * 0.05), int(h * 0.85))
            alpha = rng.randint(18, 36)
            color = (accent[0], accent[1], accent[2], alpha)
            od.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=color)

        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        return img, accent

    @staticmethod
    def _clean_text(text: str) -> str:
        if not text:
            return ""

        text = str(text)
        # 一些“信息/编号”符号在常见中文字体里会显示为方块（tofu），这里做归一化替换。
        # 说明：这里尽量用「常见可显示」的符号替代，而不是直接删除。
        try:
            circled_map = {
                "\u2139": "※",  # ℹ INFORMATION SOURCE
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
        # 常见不可见空格（避免出现在图片里像“乱码/方块”）
        try:
            text = text.replace("\u00A0", " ")  # nbsp
        except Exception:
            pass

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

        # 过滤掉 emoji 组合残留的「变体选择符 / ZWJ」等格式控制字符，避免渲染成方块
        try:
            cleaned: List[str] = []
            for ch in text:
                if ch in {"\n", "\t"}:
                    cleaned.append(ch)
                    continue
                code = ord(ch)
                # 变体选择符（常见于 emoji + VS16），会以“方块/乱码”出现
                if 0xFE00 <= code <= 0xFE0F:
                    continue
                # Variation Selectors Supplement
                if 0xE0100 <= code <= 0xE01EF:
                    continue
                cat = unicodedata.category(ch)
                # Cf: 格式控制（ZWJ/变体选择符/方向控制等），在图片文本中一般不需要
                if cat == "Cf":
                    continue
                # M*: 各类组合附加符号（keycap/重音等），在图片正文中经常造成“方块/乱码”
                if cat.startswith("M"):
                    continue
                # C*: 控制/私用/未分配等字符（保留换行/制表）
                if cat.startswith("C"):
                    continue
                cleaned.append(ch)
            text = "".join(cleaned)
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

            # 兼容直接的 hashtag 行：#话题1 #话题2 ...
            # 注意：图片分页常用 "# 标题" 作为 Markdown 标题，因此这里排除 "# " 开头的情况
            if line.startswith("#") and not line.startswith("# "):
                if line.count("#") >= 2:
                    raw_tags = line.replace("#", " ")
                    raw_tags = re.sub(r"[，,、/|]+", " ", raw_tags)
                    parts = [p.strip() for p in raw_tags.split() if p.strip()]
                    tags.extend(parts)
                    continue
                # 单个 hashtag：#话题（仅在整行看起来像标签时提取）
                if re.fullmatch(r"#[0-9A-Za-z_\-\u4e00-\u9fff]{2,20}", line):
                    tags.append(line.lstrip("#").strip())
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
        # 仅将「# 标题 / ## 标题」识别为标题；避免把「#话题1 #话题2」当成标题导致出现“标签页”
        heading_re = re.compile(r"^#{1,6}\s+")
        if heading_re.match(first):
            page_title = heading_re.sub("", first).strip()
            body_lines = raw_lines[first_idx + 1 :]
        else:
            # 兼容「#标题/##标题」这种无空格写法（常见于大模型分页输出）。
            # 仅在该行后面还有正文时，才视为标题；避免把单独的「#话题」页误判为标题页。
            page_title = ""
            body_lines = raw_lines[first_idx:]
            if first.startswith("#"):
                m = re.match(r"^(#{1,6})(.*)$", first)
                if m:
                    rest = (m.group(2) or "").strip()
                    has_body = any(str(x or "").strip() for x in raw_lines[first_idx + 1 :])
                    # 若 rest 内还包含 #，通常是「#话题1 #话题2」这种标签行
                    if has_body and rest and ("#" not in rest):
                        page_title = rest
                        body_lines = raw_lines[first_idx + 1 :]

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

    @staticmethod
    def _split_blocks(text: str) -> List[str]:
        raw = (text or "").strip()
        if not raw:
            return []
        return [b.strip() for b in re.split(r"\n\s*\n", raw) if b and b.strip()]

    @staticmethod
    def _strip_md_inline(text: str) -> str:
        s = str(text or "")
        s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)  # [text](url) -> text
        s = re.sub(r"`+", "", s)
        s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
        s = re.sub(r"__(.+?)__", r"\1", s)
        s = re.sub(r"~~(.+?)~~", r"\1", s)
        return s

    @classmethod
    def _normalize_md_line(cls, line: str) -> str:
        s = str(line or "").strip()
        if not s:
            return ""
        s = re.sub(r"^>\s*", "", s).strip()
        # 仅移除「# 」「## 」这类标题写法，不影响「#话题」标签（标签会在 _extract_tags 里处理）
        s = re.sub(r"^#{1,6}\s+", "", s).strip()
        s = cls._strip_md_inline(s).strip()
        return s

    @staticmethod
    def _strip_list_prefix(line: str, *, keep_number: bool = False) -> str:
        s = str(line or "").strip()
        if not s:
            return ""
        m = re.match(r"^(\d{1,2})[.)、]\s*(.+)$", s)
        if m:
            num = str(m.group(1) or "").strip()
            rest = str(m.group(2) or "").strip()
            return f"{num}. {rest}".strip() if keep_number else rest
        s = re.sub(r"^[-*•]\s+", "", s).strip()
        return s

    @staticmethod
    def _looks_like_footer_text(text: str) -> bool:
        s = (text or "").strip()
        if not s:
            return False
        if len(s) > 220:
            return False
        # 避免把“步骤列表”误判为 footer（例如：1. 下单购买 / 2. ...）
        lines = [ln.strip() for ln in s.splitlines() if ln.strip()]
        if len(lines) >= 2:
            list_prefix = 0
            for ln in lines:
                if re.match(r"^(\d{1,2})[.)、]\s*", ln) or re.match(r"^[-*•]\s+", ln):
                    list_prefix += 1
            # 多行“列表块”更可能是正文而不是 footer；直接排除，避免误伤时间线/步骤内容
            if list_prefix >= 2:
                return False
        keywords = [
            "私信",
            "咨询",
            "领取",
            "获取",
            "预览",
            "扫码",
            "价格",
            "元",
            "你会得到",
            "你会拿到",
            "你会获得",
        ]
        if any(k in s for k in keywords):
            return True
        if re.search(r"(?:￥|¥)\s*\d+(?:\.\d{1,2})?", s):
            return True
        if re.search(r"\d+(?:\.\d{1,2})?\s*(?:元|块)", s):
            return True
        return False

    def _extract_footer_lines(self, blocks: List[str]) -> Tuple[List[str], List[str]]:
        kept = list(blocks or [])
        footer_blocks: List[str] = []
        while kept and len(footer_blocks) < 2:
            cand = (kept[-1] or "").strip()
            if not cand:
                kept.pop()
                continue
            if not self._looks_like_footer_text(cand):
                break
            footer_blocks.insert(0, cand)
            kept.pop()

        footer_text = "\n".join([b for b in footer_blocks if str(b or "").strip()]).strip()
        footer_lines = [ln.strip() for ln in footer_text.splitlines() if ln.strip()]
        return kept, footer_lines[:2]

    def _parse_cards_layout(self, body: str) -> Tuple[str, List[Tuple[str, str]], List[str]]:
        blocks = self._split_blocks(body)
        blocks, footer_lines = self._extract_footer_lines(blocks)

        subtitle = ""
        if blocks:
            first = blocks[0]
            first_lines = [self._strip_list_prefix(self._normalize_md_line(x)) for x in str(first).splitlines()]
            first_lines = [x for x in first_lines if x]
            if len(first_lines) == 1 and 10 <= len(first_lines[0]) <= 60:
                # 若第一段是“副标题”样式，且后面还有内容，则拿来当 subtitle
                if len(blocks) >= 2:
                    subtitle = first_lines[0]
                    blocks = blocks[1:]

        items: List[Tuple[str, str]] = []
        for blk in blocks:
            raw_lines = [self._normalize_md_line(x) for x in str(blk).splitlines()]
            lines = [self._strip_list_prefix(x) for x in raw_lines if x]
            lines = [x for x in lines if x]
            if not lines:
                continue

            if len(lines) >= 2 and len(lines[0]) <= 12:
                head = lines[0].strip()
                desc = " ".join([x.strip() for x in lines[1:] if x.strip()]).strip()
                if head and desc:
                    items.append((head, desc))
                continue

            one = " ".join([x.strip() for x in lines if x.strip()]).strip()
            m = re.match(r"^(.{2,12})[：:]\s*(.+)$", one)
            if m:
                head = str(m.group(1) or "").strip()
                desc = str(m.group(2) or "").strip()
                if head and desc:
                    items.append((head, desc))

        return subtitle, items, footer_lines

    def _parse_timeline_layout(self, body: str) -> Tuple[str, List[str], List[str]]:
        blocks = self._split_blocks(body)
        blocks, footer_lines = self._extract_footer_lines(blocks)

        lines: List[str] = []
        for blk in blocks:
            for ln in str(blk or "").splitlines():
                s = self._normalize_md_line(ln)
                if s:
                    lines.append(s)

        if not lines:
            return "", [], footer_lines

        number_re = re.compile(r"^(\d{1,2})[.)、]\s*(.+)$")
        bullet_re = re.compile(r"^[-*•]\s+(.+)$")

        subtitle = ""
        first = lines[0].strip()
        first_is_step = bool(number_re.match(first) or bullet_re.match(first))
        if (not first_is_step) and (("→" in first) or ("->" in first) or ("—" in first) or ("-" in first and " " in first)):
            subtitle = first
            lines = lines[1:]
        elif (not first_is_step) and len(first) <= 46 and len(lines) >= 4:
            # 兼容「一句引导语 + 步骤列表」
            subtitle = first
            lines = lines[1:]

        steps: List[str] = []
        saw_list_prefix = False
        for ln in lines:
            s = ln.strip()
            if not s:
                continue
            m = number_re.match(s)
            if m:
                saw_list_prefix = True
                steps.append(str(m.group(2) or "").strip())
                continue
            m2 = bullet_re.match(s)
            if m2:
                saw_list_prefix = True
                steps.append(str(m2.group(1) or "").strip())
                continue
            steps.append(self._strip_list_prefix(s))

        steps = [x for x in steps if x]

        # 若完全没有列表前缀，且行本身不够短，则不按时间线渲染
        if not saw_list_prefix:
            if not (3 <= len(steps) <= 6):
                return subtitle, [], footer_lines
            if any(len(x) > 26 for x in steps):
                return subtitle, [], footer_lines

        return subtitle, steps[:8], footer_lines

    def _render_cards_layout(
        self,
        img: Image.Image,
        *,
        header: str,
        subtitle: str,
        items: Sequence[Tuple[str, str]],
        footer_lines: Sequence[str],
        accent: Tuple[int, int, int],
        dark_bg: bool,
        boxed: bool = False,
    ) -> Optional[Image.Image]:
        items = [(str(a or "").strip(), str(b or "").strip()) for a, b in (items or []) if str(a or "").strip() and str(b or "").strip()]
        if len(items) < 3:
            return None

        w, h = img.size
        header = (header or "").strip() or "要点"
        subtitle = (subtitle or "").strip()
        footer_lines = [str(x or "").strip() for x in (footer_lines or []) if str(x or "").strip()][:2]

        draw = ImageDraw.Draw(img)

        outer_x = int(w * 0.10)
        top_y = int(h * 0.08)
        bottom_margin = int(h * 0.08)

        # 初始字号（过长会逐步缩小）
        header_size = max(44, int(h * 0.060))
        subtitle_size = max(24, int(h * 0.024))
        card_title_size = max(30, int(h * 0.038))
        card_desc_size = max(24, int(h * 0.024))
        footer_main_size = max(26, int(h * 0.028))
        footer_sub_size = max(22, int(h * 0.021))

        def _measure_layout(
            hs: int,
            ss: int,
            cts: int,
            cds: int,
            fms: int,
            fss: int,
        ):
            font_header = font_manager.get_font("chinese", "bold", size=hs)
            font_subtitle = font_manager.get_font("chinese", "regular", size=ss)
            font_card_title = font_manager.get_font("chinese", "bold", size=cts)
            font_card_desc = font_manager.get_font("chinese", "regular", size=cds)
            font_footer_main = font_manager.get_font("chinese", "bold", size=fms)
            font_footer_sub = font_manager.get_font("chinese", "regular", size=fss)

            max_w = w - outer_x * 2
            header_lines = self._smart_wrap(header, draw, font_header, max_w)[:2]
            header_lh = int(getattr(font_header, "size", hs) * 1.18)
            header_h = len(header_lines) * header_lh

            subtitle_lines: List[str] = []
            subtitle_h = 0
            subtitle_gap = 0
            if subtitle:
                subtitle_lines = self._smart_wrap(subtitle, draw, font_subtitle, max_w)[:2]
                sub_lh = int(getattr(font_subtitle, "size", ss) * 1.36)
                subtitle_h = len(subtitle_lines) * sub_lh
                subtitle_gap = int(sub_lh * 0.60)

            header_gap = max(24, int(h * 0.020))

            card_left = outer_x
            card_right = w - outer_x
            card_w = max(1, card_right - card_left)
            pad_x = max(42, int(card_w * 0.055))
            pad_y = max(26, int(cts * 0.72))
            title_lh = int(getattr(font_card_title, "size", cts) * 1.16)
            desc_lh = int(getattr(font_card_desc, "size", cds) * 1.52)
            title_desc_gap = max(10, int(desc_lh * 0.55))
            card_gap = max(18, int(h * 0.018))

            max_desc_w = max(1, card_w - pad_x * 2)

            cards = []
            total_cards_h = 0
            for title, desc in items[:6]:
                t = self._strip_md_inline(title).strip()
                d = self._strip_md_inline(desc).strip()
                d_lines = self._smart_wrap(d, draw, font_card_desc, max_desc_w)[:2]
                card_h = pad_y + title_lh + title_desc_gap + len(d_lines) * desc_lh + int(pad_y * 0.90)
                card_h = max(card_h, int(h * 0.112))
                cards.append((t, d_lines, card_h))
                total_cards_h += card_h

            total_cards_h += card_gap * max(0, len(cards) - 1)

            footer_h = 0
            footer_gap = 0
            footer_lines_wrapped: List[str] = []
            footer_sub_wrapped: List[str] = []
            if footer_lines:
                footer_gap = max(18, int(h * 0.020))
                main = footer_lines[0]
                sub = footer_lines[1] if len(footer_lines) >= 2 else ""
                footer_lines_wrapped = self._smart_wrap(main, draw, font_footer_main, max_w)[:1]
                footer_main_lh = int(getattr(font_footer_main, "size", fms) * 1.22)
                footer_sub_lh = int(getattr(font_footer_sub, "size", fss) * 1.34)
                if sub:
                    footer_sub_wrapped = self._smart_wrap(sub, draw, font_footer_sub, max_w)[:2]
                footer_h = (
                    max(24, int(h * 0.018))
                    + len(footer_lines_wrapped) * footer_main_lh
                    + (int(footer_sub_lh * 0.55) if footer_sub_wrapped else 0)
                    + len(footer_sub_wrapped) * footer_sub_lh
                    + max(22, int(h * 0.017))
                )
                footer_h = max(footer_h, int(h * 0.10))

            total_h = header_h + subtitle_gap + subtitle_h + header_gap + total_cards_h + footer_gap + footer_h

            return {
                "fonts": {
                    "header": font_header,
                    "subtitle": font_subtitle,
                    "card_title": font_card_title,
                    "card_desc": font_card_desc,
                    "footer_main": font_footer_main,
                    "footer_sub": font_footer_sub,
                },
                "header_lines": header_lines,
                "header_lh": header_lh,
                "subtitle_lines": subtitle_lines,
                "subtitle_lh": int(getattr(font_subtitle, "size", ss) * 1.36) if subtitle_lines else 0,
                "subtitle_gap": subtitle_gap,
                "header_gap": header_gap,
                "card_left": card_left,
                "card_right": card_right,
                "card_pad_x": pad_x,
                "card_pad_y": pad_y,
                "title_lh": title_lh,
                "desc_lh": desc_lh,
                "title_desc_gap": title_desc_gap,
                "card_gap": card_gap,
                "cards": cards,
                "footer_gap": footer_gap,
                "footer_h": footer_h,
                "footer_main_wrapped": footer_lines_wrapped,
                "footer_sub_wrapped": footer_sub_wrapped,
                "total_h": total_h,
            }

        layout = None
        for _ in range(22):
            layout = _measure_layout(
                header_size,
                subtitle_size,
                card_title_size,
                card_desc_size,
                footer_main_size,
                footer_sub_size,
            )
            if top_y + int(layout["total_h"]) <= h - bottom_margin:
                break
            # shrink
            if card_desc_size > 20:
                card_desc_size = max(20, card_desc_size - 2)
            if card_title_size > 26:
                card_title_size = max(26, card_title_size - 2)
            if header_size > 36:
                header_size = max(36, header_size - 2)
            if subtitle_size > 18:
                subtitle_size = max(18, subtitle_size - 1)
            if footer_main_size > 22:
                footer_main_size = max(22, footer_main_size - 1)
            if footer_sub_size > 18:
                footer_sub_size = max(18, footer_sub_size - 1)
        if not layout or top_y + int(layout["total_h"]) > h - bottom_margin:
            return None

        header_fill = (250, 250, 250) if dark_bg else (20, 20, 20)
        subtitle_fill = (215, 215, 215) if dark_bg else (120, 120, 120)
        if boxed:
            card_title_fill = (20, 20, 20)
            card_desc_fill = (95, 95, 95)
        else:
            card_title_fill = (250, 250, 250) if dark_bg else (20, 20, 20)
            card_desc_fill = (230, 230, 230) if dark_bg else (80, 80, 80)

        card_bg = (255, 255, 255, 245)
        shadow_alpha = 34 if not dark_bg else 52
        border_rgba = (0, 0, 0, 26) if not dark_bg else (255, 255, 255, 22)

        highlight_fill = (255, 234, 168)
        highlight_border = (235, 212, 140)
        right_pill_fill = (255, 238, 182)

        # draw cards + shadows on overlay for transparency（可选）
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)

        y = top_y
        # header and subtitle drawn later on RGB
        y += len(layout["header_lines"]) * layout["header_lh"]
        if layout["subtitle_lines"]:
            y += layout["subtitle_gap"] + len(layout["subtitle_lines"]) * layout["subtitle_lh"]
        y += layout["header_gap"]

        card_left = int(layout["card_left"])
        card_right = int(layout["card_right"])
        pad_x = int(layout["card_pad_x"])
        pad_y = int(layout["card_pad_y"])
        radius = max(26, int(card_desc_size * 1.15) + 18)

        card_rects: List[Tuple[int, int, int, int]] = []
        for _title, _desc_lines, card_h in layout["cards"]:
            x0, x1 = card_left, card_right
            y0, y1 = int(y), int(y + card_h)
            card_rects.append((x0, y0, x1, y1))
            if boxed:
                od.rounded_rectangle((x0 + 4, y0 + 7, x1 + 4, y1 + 7), radius=radius, fill=(0, 0, 0, shadow_alpha))
                od.rounded_rectangle((x0, y0, x1, y1), radius=radius, fill=card_bg, outline=border_rgba, width=2)
            y += card_h + layout["card_gap"]

        footer_rect: Optional[Tuple[int, int, int, int]] = None
        if layout["footer_h"] > 0:
            y += max(0, int(layout["footer_gap"]) - int(layout["card_gap"]))
            x0, x1 = card_left, card_right
            y0, y1 = int(y), int(y + layout["footer_h"])
            footer_rect = (x0, y0, x1, y1)
            if boxed:
                od.rounded_rectangle((x0 + 4, y0 + 7, x1 + 4, y1 + 7), radius=radius, fill=(0, 0, 0, shadow_alpha))
                od.rounded_rectangle((x0, y0, x1, y1), radius=radius, fill=card_bg, outline=border_rgba, width=2)

        if boxed:
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(img)

        # header
        y_header = top_y
        for line in layout["header_lines"]:
            draw.text((outer_x, y_header), line, fill=header_fill, font=layout["fonts"]["header"])
            y_header += layout["header_lh"]

        # subtitle
        if layout["subtitle_lines"]:
            y_header += layout["subtitle_gap"]
            for line in layout["subtitle_lines"]:
                draw.text((outer_x, y_header), line, fill=subtitle_fill, font=layout["fonts"]["subtitle"])
                y_header += layout["subtitle_lh"]

        # cards content
        for (title, desc_lines, _card_h), rect in zip(layout["cards"], card_rects):
            x0, y0, x1, y1 = rect

            # title highlight pill
            t_font = layout["fonts"]["card_title"]
            t_bbox = draw.textbbox((0, 0), title, font=t_font)
            tw = t_bbox[2] - t_bbox[0]
            th = t_bbox[3] - t_bbox[1]
            pill_pad_x = max(14, int(th * 0.42))
            pill_pad_y = max(8, int(th * 0.28))
            pill_x0 = x0 + pad_x
            pill_y0 = y0 + pad_y - int(pill_pad_y * 0.2)
            pill_x1 = min(x1 - pad_x, pill_x0 + tw + pill_pad_x * 2)
            pill_y1 = pill_y0 + th + pill_pad_y * 2
            draw.rounded_rectangle(
                (pill_x0, pill_y0, pill_x1, pill_y1),
                radius=int((pill_y1 - pill_y0) / 2),
                fill=highlight_fill,
                outline=highlight_border,
                width=2,
            )
            draw.text((pill_x0 + pill_pad_x, pill_y0 + pill_pad_y - 2), title, fill=card_title_fill, font=t_font)

            # right decorative pill
            sp_w = max(80, int((x1 - x0) * 0.12))
            sp_h = max(28, int(th * 1.05))
            sp_x1 = x1 - max(26, int(pad_x * 0.55))
            sp_x0 = sp_x1 - sp_w
            sp_y0 = y0 + max(22, int(pad_y * 0.55))
            sp_y1 = sp_y0 + sp_h
            draw.rounded_rectangle((sp_x0, sp_y0, sp_x1, sp_y1), radius=int(sp_h / 2), fill=right_pill_fill, outline=highlight_border, width=2)

            # desc
            y_text = pill_y1 + int(layout["title_desc_gap"] * 0.70)
            d_font = layout["fonts"]["card_desc"]
            for ln in desc_lines:
                draw.text((x0 + pad_x, y_text), ln, fill=card_desc_fill, font=d_font)
                y_text += layout["desc_lh"]

        # footer lines
        if footer_rect and footer_lines:
            x0, y0, x1, y1 = footer_rect
            pad = max(28, int(h * 0.022))
            y_text = y0 + pad
            if layout["footer_main_wrapped"]:
                main = layout["footer_main_wrapped"][0]
                draw.text((x0 + pad, y_text), main, fill=card_title_fill, font=layout["fonts"]["footer_main"])
                y_text += int(getattr(layout["fonts"]["footer_main"], "size", footer_main_size) * 1.26)
            if layout["footer_sub_wrapped"]:
                y_text += max(8, int(getattr(layout["fonts"]["footer_sub"], "size", footer_sub_size) * 0.35))
                for ln in layout["footer_sub_wrapped"]:
                    draw.text((x0 + pad, y_text), ln, fill=card_desc_fill, font=layout["fonts"]["footer_sub"])
                    y_text += int(getattr(layout["fonts"]["footer_sub"], "size", footer_sub_size) * 1.34)

        return img

    def _render_timeline_layout(
        self,
        img: Image.Image,
        *,
        header: str,
        subtitle: str,
        steps: Sequence[str],
        footer_lines: Sequence[str],
        accent: Tuple[int, int, int],
        dark_bg: bool,
        boxed: bool = False,
    ) -> Optional[Image.Image]:
        steps = [str(x or "").strip() for x in (steps or []) if str(x or "").strip()]
        if len(steps) < 3:
            return None

        w, h = img.size
        header = (header or "").strip() or "步骤"
        subtitle = (subtitle or "").strip()
        footer_lines = [str(x or "").strip() for x in (footer_lines or []) if str(x or "").strip()][:2]

        draw = ImageDraw.Draw(img)

        outer_x = int(w * 0.10)
        top_y = int(h * 0.08)
        bottom_margin = int(h * 0.08)

        header_size = max(44, int(h * 0.060))
        subtitle_size = max(24, int(h * 0.024))
        step_size = max(30, int(h * 0.038))
        footer_main_size = max(26, int(h * 0.028))
        footer_sub_size = max(22, int(h * 0.021))

        number_font_scale = 0.62

        def _measure(
            hs: int,
            ss: int,
            st: int,
            fms: int,
            fss: int,
        ):
            font_header = font_manager.get_font("chinese", "bold", size=hs)
            font_subtitle = font_manager.get_font("chinese", "regular", size=ss)
            font_step = font_manager.get_font("chinese", "bold", size=st)
            font_num = font_manager.get_font("chinese", "bold", size=max(18, int(st * number_font_scale)))
            font_footer_main = font_manager.get_font("chinese", "bold", size=fms)
            font_footer_sub = font_manager.get_font("chinese", "regular", size=fss)

            max_w = w - outer_x * 2
            header_lines = self._smart_wrap(header, draw, font_header, max_w)[:2]
            header_lh = int(getattr(font_header, "size", hs) * 1.18)
            header_h = len(header_lines) * header_lh

            subtitle_lines: List[str] = []
            subtitle_h = 0
            subtitle_gap = 0
            subtitle_lh = 0
            if subtitle:
                subtitle_lines = self._smart_wrap(subtitle, draw, font_subtitle, max_w)[:2]
                subtitle_lh = int(getattr(font_subtitle, "size", ss) * 1.36)
                subtitle_h = len(subtitle_lines) * subtitle_lh
                subtitle_gap = int(subtitle_lh * 0.55)

            header_gap = max(24, int(h * 0.020))

            footer_h = 0
            footer_gap = 0
            footer_main_wrapped: List[str] = []
            footer_sub_wrapped: List[str] = []
            if footer_lines:
                footer_gap = max(18, int(h * 0.020))
                main = footer_lines[0]
                sub = footer_lines[1] if len(footer_lines) >= 2 else ""
                footer_main_wrapped = self._smart_wrap(main, draw, font_footer_main, max_w)[:1]
                footer_main_lh = int(getattr(font_footer_main, "size", fms) * 1.22)
                footer_sub_lh = int(getattr(font_footer_sub, "size", fss) * 1.34)
                if sub:
                    footer_sub_wrapped = self._smart_wrap(sub, draw, font_footer_sub, max_w)[:2]
                footer_h = (
                    max(24, int(h * 0.018))
                    + len(footer_main_wrapped) * footer_main_lh
                    + (int(footer_sub_lh * 0.55) if footer_sub_wrapped else 0)
                    + len(footer_sub_wrapped) * footer_sub_lh
                    + max(22, int(h * 0.017))
                )
                footer_h = max(footer_h, int(h * 0.10))

            # timeline card size
            card_left = outer_x
            card_right = w - outer_x
            card_w = max(1, card_right - card_left)

            pad_x = max(56, int(card_w * 0.070))
            pad_y = max(44, int(st * 1.05))

            row_h = int(getattr(font_step, "size", st) * 1.75)
            circle_r = max(18, int(row_h * 0.28))

            max_step_w = max(1, card_w - pad_x * 2 - circle_r * 2 - int(circle_r * 1.25))
            step_lines: List[List[str]] = []
            used_h = 0
            for s in steps[:8]:
                wrapped = self._smart_wrap(s, draw, font_step, max_step_w)[:2]
                step_lines.append(wrapped)
                used_h += max(row_h, len(wrapped) * int(getattr(font_step, "size", st) * 1.18))
            used_h += max(0, len(step_lines) - 1) * int(row_h * 0.55)
            card_h = pad_y * 2 + used_h
            card_h = max(card_h, int(h * 0.36))

            total_h = header_h + subtitle_gap + subtitle_h + header_gap + card_h + footer_gap + footer_h
            return {
                "fonts": {
                    "header": font_header,
                    "subtitle": font_subtitle,
                    "step": font_step,
                    "num": font_num,
                    "footer_main": font_footer_main,
                    "footer_sub": font_footer_sub,
                },
                "header_lines": header_lines,
                "header_lh": header_lh,
                "subtitle_lines": subtitle_lines,
                "subtitle_lh": subtitle_lh,
                "subtitle_gap": subtitle_gap,
                "header_gap": header_gap,
                "card_left": card_left,
                "card_right": card_right,
                "card_pad_x": pad_x,
                "card_pad_y": pad_y,
                "row_h": row_h,
                "circle_r": circle_r,
                "step_lines": step_lines,
                "step_gap": int(row_h * 0.55),
                "footer_gap": footer_gap,
                "footer_h": footer_h,
                "footer_main_wrapped": footer_main_wrapped,
                "footer_sub_wrapped": footer_sub_wrapped,
                "card_h": card_h,
                "total_h": total_h,
            }

        layout = None
        for _ in range(22):
            layout = _measure(header_size, subtitle_size, step_size, footer_main_size, footer_sub_size)
            if top_y + int(layout["total_h"]) <= h - bottom_margin:
                break
            # shrink
            if step_size > 26:
                step_size = max(26, step_size - 2)
            if header_size > 36:
                header_size = max(36, header_size - 2)
            if subtitle_size > 18:
                subtitle_size = max(18, subtitle_size - 1)
            if footer_main_size > 22:
                footer_main_size = max(22, footer_main_size - 1)
            if footer_sub_size > 18:
                footer_sub_size = max(18, footer_sub_size - 1)
        if not layout or top_y + int(layout["total_h"]) > h - bottom_margin:
            return None

        header_fill = (250, 250, 250) if dark_bg else (20, 20, 20)
        subtitle_fill = (215, 215, 215) if dark_bg else (120, 120, 120)
        if boxed:
            step_fill = (20, 20, 20)
            footer_fill = (95, 95, 95)
        else:
            step_fill = (245, 245, 245) if dark_bg else (20, 20, 20)
            footer_fill = (225, 225, 225) if dark_bg else (80, 80, 80)

        card_bg = (255, 255, 255, 245)
        shadow_alpha = 34 if not dark_bg else 52
        border_rgba = (0, 0, 0, 26) if not dark_bg else (255, 255, 255, 22)

        # overlay: card + shadow（可选）
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)

        # header area height (for placement)
        y = top_y
        y += len(layout["header_lines"]) * layout["header_lh"]
        if layout["subtitle_lines"]:
            y += layout["subtitle_gap"] + len(layout["subtitle_lines"]) * layout["subtitle_lh"]
        y += layout["header_gap"]

        radius = max(30, int(layout["circle_r"] * 1.35) + 22)

        card_left = int(layout["card_left"])
        card_right = int(layout["card_right"])
        card_top = int(y)
        card_bottom = int(y + layout["card_h"])

        if boxed:
            od.rounded_rectangle((card_left + 4, card_top + 7, card_right + 4, card_bottom + 7), radius=radius, fill=(0, 0, 0, shadow_alpha))
            od.rounded_rectangle((card_left, card_top, card_right, card_bottom), radius=radius, fill=card_bg, outline=border_rgba, width=2)

        footer_rect: Optional[Tuple[int, int, int, int]] = None
        if layout["footer_h"] > 0:
            y_footer = card_bottom + int(layout["footer_gap"])
            x0, x1 = card_left, card_right
            y0, y1 = int(y_footer), int(y_footer + layout["footer_h"])
            footer_rect = (x0, y0, x1, y1)
            if boxed:
                od.rounded_rectangle((x0 + 4, y0 + 7, x1 + 4, y1 + 7), radius=radius, fill=(0, 0, 0, shadow_alpha))
                od.rounded_rectangle((x0, y0, x1, y1), radius=radius, fill=card_bg, outline=border_rgba, width=2)

        if boxed:
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(img)

        # header text
        y_header = top_y
        for line in layout["header_lines"]:
            draw.text((outer_x, y_header), line, fill=header_fill, font=layout["fonts"]["header"])
            y_header += layout["header_lh"]
        if layout["subtitle_lines"]:
            y_header += layout["subtitle_gap"]
            for line in layout["subtitle_lines"]:
                draw.text((outer_x, y_header), line, fill=subtitle_fill, font=layout["fonts"]["subtitle"])
                y_header += layout["subtitle_lh"]

        # steps inside card
        pad_x = int(layout["card_pad_x"])
        pad_y = int(layout["card_pad_y"])
        row_h = int(layout["row_h"])
        gap = int(layout["step_gap"])
        r = int(layout["circle_r"])
        cx = card_left + pad_x + r

        # line segments
        centers: List[int] = []
        y_step = card_top + pad_y
        for wrapped in layout["step_lines"]:
            centers.append(int(y_step + r))
            block_h = max(row_h, len(wrapped) * int(getattr(layout["fonts"]["step"], "size", step_size) * 1.18))
            y_step += block_h + gap

        if len(centers) >= 2:
            line_color = (25, 25, 25) if not dark_bg else (235, 235, 235)
            line_alpha = 100 if not dark_bg else 120
            line_overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ld = ImageDraw.Draw(line_overlay)
            for y0, y1 in zip(centers[:-1], centers[1:]):
                ld.line([(cx, y0 + r), (cx, y1 - r)], fill=(line_color[0], line_color[1], line_color[2], line_alpha), width=max(4, int(r * 0.24)))
            img = Image.alpha_composite(img.convert("RGBA"), line_overlay).convert("RGB")
            draw = ImageDraw.Draw(img)

        y_step = card_top + pad_y
        step_font = layout["fonts"]["step"]
        num_font = layout["fonts"]["num"]
        text_x = cx + r + int(r * 1.25)
        for i, wrapped in enumerate(layout["step_lines"], start=1):
            cy = int(y_step + r)
            # circle
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=accent)
            num = str(i)
            nb = draw.textbbox((0, 0), num, font=num_font)
            nw = nb[2] - nb[0]
            nh = nb[3] - nb[1]
            draw.text((cx - nw // 2, cy - nh // 2 - 1), num, fill=(255, 255, 255), font=num_font)

            # step text (top aligned to block)
            ty = int(y_step - int(r * 0.15))
            for ln in wrapped:
                draw.text((text_x, ty), ln, fill=step_fill, font=step_font)
                ty += int(getattr(step_font, "size", step_size) * 1.18)

            block_h = max(row_h, len(wrapped) * int(getattr(step_font, "size", step_size) * 1.18))
            y_step += block_h + gap

        # footer text
        if footer_rect and footer_lines:
            x0, y0, x1, y1 = footer_rect
            pad = max(28, int(h * 0.022))
            y_text = y0 + pad
            if layout["footer_main_wrapped"]:
                draw.text((x0 + pad, y_text), layout["footer_main_wrapped"][0], fill=step_fill, font=layout["fonts"]["footer_main"])
                y_text += int(getattr(layout["fonts"]["footer_main"], "size", footer_main_size) * 1.26)
            if layout["footer_sub_wrapped"]:
                y_text += max(8, int(getattr(layout["fonts"]["footer_sub"], "size", footer_sub_size) * 0.35))
                for ln in layout["footer_sub_wrapped"]:
                    draw.text((x0 + pad, y_text), ln, fill=footer_fill, font=layout["fonts"]["footer_sub"])
                    y_text += int(getattr(layout["fonts"]["footer_sub"], "size", footer_sub_size) * 1.34)

        return img

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
        cover_heading: str = "",
        cover_description: str = "",
        cover_asset_image_path: str = "",
        page_asset_paths: Optional[Sequence[str]] = None,
    ) -> Optional[Tuple[str, List[str]]]:
        """基于系统模板生成封面 + 内容图（返回本地路径）。"""
        show_tags = self._env_bool("XHS_IMG_SHOW_TAGS", default=False)
        show_content_card = self._env_bool("XHS_IMG_SHOW_CONTENT_CARD", default=False)
        boxed_list_cards = self._env_bool("XHS_IMG_BOXED_LIST_CARDS", default=False)

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

        # Bundled images are previews of measured layouts, not backgrounds to
        # paint over. Imported images and packs retain their original behavior.
        from src.core.services.poster_template_renderer import bundled_template_id, PosterTemplateRenderer
        from src.core.services.poster_catalog import bundled_layout
        template_id = bundled_template_id(cover_override or bg_override)
        layout = bundled_layout(cover_override or bg_override)
        if layout or template_id or (not pack and not bg_override and not cover_override):
            page_sources = [str(x) for x in (content_pages or []) if str(x).strip()]
            parsed_pages = []
            for source in page_sources:
                heading, body = self._parse_page(source)
                body, _tags = self._extract_tags(self._clean_text(body))
                if body.strip():
                    parsed_pages.append((self._clean_text(heading), body))
            if not parsed_pages:
                body, _tags = self._extract_tags(self._clean_text(content))
                if body:
                    parsed_pages = [("", body)]
            output_dir = Path(os.path.expanduser("~")) / ".xhs_system" / "generated_imgs"
            if layout:
                from src.core.services.marketing_poster_layout import render_marketing
                payload = {
                    'poster_layout': layout,
                    'title': self._clean_text(cover_heading or title) or '小红书笔记',
                    'subtitle': self._clean_text(cover_description),
                    'pages': [{'title': heading, 'body': body} for heading, body in parsed_pages],
                    'page_asset_paths': list(page_asset_paths or []),
                }
                if cover_asset_image_path:
                    payload['asset_image_path'] = str(Path(cover_asset_image_path).expanduser())
                images = render_marketing(payload, output_dir / f'{int(time.time())}_{uuid.uuid4().hex[:8]}', font_manager.get_font, target_size)
                return images[0]['image_path'], [item['image_path'] for item in images[1:]]
            renderer = PosterTemplateRenderer(font_manager.get_font, target_size, template_id)
            if page_asset_paths:
                return renderer.save_illustrated(
                    output_dir, f"{int(time.time())}_{uuid.uuid4().hex[:8]}",
                    self._clean_text(cover_heading or title) or "小红书笔记",
                    self._clean_text(cover_description), parsed_pages,
                    list(page_asset_paths), str(Path(cover_asset_image_path).expanduser()) if cover_asset_image_path else '',
                )
            result = renderer.save(
                output_dir, f"{int(time.time())}_{uuid.uuid4().hex[:8]}",
                self._clean_text(cover_heading or title) or "小红书笔记",
                self._clean_text(cover_description), parsed_pages,
            )
            if cover_asset_image_path:
                renderer.render_asset_cover(
                    self._clean_text(cover_heading or title), self._clean_text(cover_description),
                    str(Path(cover_asset_image_path).expanduser()), len(result[1])+1,
                ).save(result[0], quality=95)
            return result

        raw_pages = [str(x) for x in (content_pages or []) if str(x).strip()]
        pages = list(raw_pages)
        if not pages:
            pages = self._split_into_pages(content, count=page_count)
        if not pages:
            pages = [content.strip()] if content.strip() else []

        pages = pages[: max(1, int(page_count))]

        # 若用户/模型提供的分页只有标题/标签（导致渲染时被跳过或没有正文），
        # 则回退用完整正文自动分页，避免出现“只有封面，没有内容页”的情况。
        if raw_pages and (content or "").strip():
            try:
                has_meaningful_body = False
                for p in pages:
                    _t, _b = self._parse_page(p)
                    _b = self._clean_text(_b or p)
                    _b, _tags = self._extract_tags(_b)
                    _b = self._auto_paragraphize(_b)
                    if str(_b or "").strip():
                        has_meaningful_body = True
                        break

                if not has_meaningful_body:
                    fallback_pages = self._split_into_pages(content, count=page_count) or ([content.strip()] if content.strip() else [])
                    if fallback_pages:
                        pages = [str(x) for x in fallback_pages if str(x).strip()]
                        pages = pages[: max(1, int(page_count))]
            except Exception:
                pass

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
            elif cover_override:
                pack_tag = f"bg_{cover_override.stem}"
        except Exception:
            pack_tag = ""
        pack_tag = pack_tag or "tpl"
        pack_tag = re.sub(r"[^a-zA-Z0-9_\\-]+", "_", pack_tag)[:40]

        builtin_seed_text = f"{(title or '').strip()}|{(content or '').strip()}"
        builtin_accent: Optional[Tuple[int, int, int]] = None

        def _open_bg(path: Optional[Path], *, variant: int = 0) -> Image.Image:
            nonlocal builtin_accent
            if path:
                img = Image.open(str(path)).convert("RGB")
                return self._resize_with_letterbox(img, target_size)

            img, accent = self._create_builtin_background(target_size, seed_text=builtin_seed_text, variant=variant)
            if accent and builtin_accent is None:
                builtin_accent = accent
            return img

        cover_bg = cover_override if cover_override else (pack.pages[0] if pack else None)
        cover_img = _open_bg(cover_bg, variant=0)
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
            elif pack and pack.pages:
                bg_index = min(idx + 1, len(pack.pages) - 1) if pack and len(pack.pages) > 1 else 0
                bg_path = pack.pages[bg_index] if pack else cover_bg
            else:
                bg_path = None

            img = _open_bg(bg_path, variant=idx + 1)
            draw = ImageDraw.Draw(img)
            w, h = img.size

            page_title, body = self._parse_page(page_text)
            page_title = self._clean_text(page_title)
            body = self._clean_text(body or page_text)

            # 从正文中提取标签（用于更美观的标签胶囊渲染）
            body, tags = self._extract_tags(body)
            body = self._auto_paragraphize(body)
            # 只包含标签的页（如“#话题1 #话题2”或“话题标签”页）直接跳过，避免出现“最后一张标签图”
            if not (body or "").strip() and not (page_title or "").strip():
                continue

            tag_titles = {"标签", "话题标签", "话题", "hashtags", "hashtag", "tags", "tag"}
            is_tag_page = (page_title or "").strip().lower() in tag_titles
            if is_tag_page and not (body or "").strip():
                if not show_tags or not tags:
                    continue
            if (not (body or "").strip()) and tags and (is_tag_page or not (page_title or "").strip()):
                if not show_tags:
                    continue

            if not show_tags:
                tags = []

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

            accent = builtin_accent or self._pick_accent_color(img)

            # 尝试更“远程风格”的内容页：卡片列表 / 时间线（失败则回退到默认排版）
            page_header = page_title or self._clean_text(title) or "要点"
            try:
                tl_subtitle, tl_steps, tl_footer = self._parse_timeline_layout(body)
                if tl_steps and len(tl_steps) >= 3:
                    rendered = self._render_timeline_layout(
                        img,
                        header=page_header,
                        subtitle=tl_subtitle,
                        steps=tl_steps,
                        footer_lines=tl_footer,
                        accent=accent,
                        dark_bg=dark_bg,
                        boxed=boxed_list_cards,
                    )
                    if rendered:
                        out_path = output_dir / f"content_tpl_{idx+1}_{pack_tag}_{ts}_{unique}.jpg"
                        rendered.save(str(out_path), format="JPEG", quality=92)
                        content_paths.append(str(out_path))
                        continue
            except Exception:
                pass

            try:
                card_subtitle, card_items, card_footer = self._parse_cards_layout(body)
                if card_items and len(card_items) >= 3:
                    rendered = self._render_cards_layout(
                        img,
                        header=page_header,
                        subtitle=card_subtitle,
                        items=card_items,
                        footer_lines=card_footer,
                        accent=accent,
                        dark_bg=dark_bg,
                        boxed=boxed_list_cards,
                    )
                    if rendered:
                        out_path = output_dir / f"content_tpl_{idx+1}_{pack_tag}_{ts}_{unique}.jpg"
                        rendered.save(str(out_path), format="JPEG", quality=92)
                        content_paths.append(str(out_path))
                        continue
            except Exception:
                pass

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
                # 额外做一层 Markdown 清理，避免出现「##」「-」「**加粗**」等符号导致排版变丑
                list_bullet_re = re.compile(r"^[-*•]\s+")
                list_number_re = re.compile(r"^(\d{1,2})[.)、]\s*")
                md_heading_re = re.compile(r"^#{1,6}\s+")
                md_quote_re = re.compile(r"^>\s*")
                md_link_re = re.compile(r"\[([^\]]+)\]\([^)]+\)")

                def _strip_md_inline(text: str) -> str:
                    s = str(text or "")
                    s = md_link_re.sub(r"\1", s)
                    s = re.sub(r"`+", "", s)
                    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
                    s = re.sub(r"__(.+?)__", r"\1", s)
                    s = re.sub(r"~~(.+?)~~", r"\1", s)
                    return s

                def _normalize_line(line: str) -> str:
                    s = str(line or "").strip()
                    if not s:
                        return ""
                    s = md_quote_re.sub("", s).strip()
                    # 仅移除「# 」「## 」这类标题写法，不影响「#话题」标签
                    s = md_heading_re.sub("", s).strip()
                    s = _strip_md_inline(s).strip()
                    return s

                def _is_list_line(line: str) -> bool:
                    s = str(line or "").strip()
                    if not s:
                        return False
                    return bool(list_bullet_re.match(s) or list_number_re.match(s))

                def _normalize_list_line(line: str) -> str:
                    s = str(line or "").strip()
                    if not s:
                        return ""
                    s = md_quote_re.sub("", s).strip()
                    m = list_number_re.match(s)
                    if m:
                        rest = s[m.end() :].strip()
                        rest = md_heading_re.sub("", rest).strip()
                        rest = _strip_md_inline(rest).strip()
                        return f"{m.group(1)}. {rest}".strip()
                    s = list_bullet_re.sub("", s).strip()
                    s = md_heading_re.sub("", s).strip()
                    s = _strip_md_inline(s).strip()
                    return s

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
                        sub = _normalize_line(seg_lines[0])
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
                            if _is_list_line(ln):
                                if buf:
                                    paras.append(" ".join([x.strip() for x in buf if str(x).strip()]).strip())
                                    buf = []
                                cleaned = _normalize_list_line(ln)
                                if cleaned:
                                    paras.append(cleaned)
                                continue

                            cleaned = _normalize_line(ln)
                            if cleaned:
                                buf.append(cleaned)
                        if buf:
                            paras.append(" ".join([x.strip() for x in buf if str(x).strip()]).strip())
                        sub_lines = self._smart_wrap(sub, draw, font_body_bold, max_text_w)[:2] if sub else []
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
                                    for li, ln in enumerate(rest_lines):
                                        body_items.append({"text": ln, "kind": "body", "para_start": li == 0})
                                    if (pj < len(parts) - 1) or (pi < len(paras) - 1):
                                        body_items.append({"text": "", "kind": "blank", "para_start": False})
                    else:
                        # 处理纯列表块：保持每一条独立成段，避免「- A - B - C」挤在一行
                        if seg_lines and len(seg_lines) >= 2 and all(_is_list_line(x) for x in seg_lines):
                            for li, raw_ln in enumerate(seg_lines):
                                cleaned = _normalize_list_line(raw_ln)
                                if not cleaned:
                                    continue
                                part_lines = self._smart_wrap(cleaned, draw, font_body, max_text_w)
                                for i, ln in enumerate(part_lines):
                                    body_items.append({"text": ln, "kind": "body", "para_start": i == 0})
                                if li < len(seg_lines) - 1:
                                    body_items.append({"text": "", "kind": "blank", "para_start": False})
                            body_items.append({"text": "", "kind": "blank", "para_start": False})
                            continue

                        if seg_lines and len(seg_lines) == 1 and _is_list_line(seg_lines[0]):
                            para_text = _normalize_list_line(seg_lines[0])
                        else:
                            seg_norm = [_normalize_line(x) for x in (seg_lines or [])]
                            para_text = " ".join([x for x in seg_norm if x]).strip() if seg_norm else ""
                            if not para_text:
                                para_text = _normalize_line(block)

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

            # 可选：内容卡片底（白色包裹）。默认关闭，避免“包裹感”太重。
            if show_content_card:
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
