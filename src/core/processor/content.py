import json
import re
import time
import os
import uuid
from PyQt5.QtCore import QThread, pyqtSignal

# 导入备用生成器
from .content_backup import BackupContentGenerator
from src.config.config import Config
from src.core.services.llm_service import llm_service, LLMServiceError
from src.core.services.system_image_template_service import system_image_template_service
from src.core.services.poster_catalog import LAYOUT_TEMPLATES, layout_for_template


class ContentGeneratorThread(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, input_text, header_title, author, generate_btn):
        super().__init__()
        self.input_text = input_text
        self.header_title = header_title
        self.author = author
        self.generate_btn = generate_btn
        self._last_llm_error = ""
        self._backup_info_reason = ""

    def run(self):
        """主运行方法，包含重试逻辑和故障转移"""
        selected_cover_tpl = ""
        try:
            selected_cover_tpl = str(Config().get_templates_config().get("selected_cover_template_id") or "").strip()
        except Exception:
            selected_cover_tpl = ""

        # 图文版式使用海报生成流程；页数由内容决定。
        if selected_cover_tpl == "showcase_marketing_poster" or selected_cover_tpl in LAYOUT_TEMPLATES:
            try:
                self.generate_btn.setText("🪧 生成营销海报中...")
                self.generate_btn.setEnabled(False)
            except Exception:
                pass

            try:
                self._generate_marketing_poster()
            except Exception as e:
                self.error.emit(f"营销海报生成失败: {str(e)}")
            finally:
                try:
                    self.generate_btn.setText("✨ 生成内容")
                    self.generate_btn.setEnabled(True)
                except Exception:
                    pass
            return

        # 默认允许回退到“本地备用生成器”，避免模型未配置/调用失败导致完全不可用；
        # 如需严格模式（不回退），可设置：XHS_ALLOW_FALLBACK=0/false/off
        allow_fallback = os.environ.get("XHS_ALLOW_FALLBACK", "").strip().lower() not in {
            "0",
            "false",
            "no",
            "n",
            "off",
        }

        def _try_llm() -> bool:
            try:
                return bool(self._try_generate_with_custom_model())
            except Exception as e:
                print(f"⚠️ 自定义模型生成失败，将回退到其他方案: {str(e)}")
                self._last_llm_error = str(e)
                return False

        def _try_backup(reason: str) -> bool:
            try:
                self._use_backup_generator(info_reason=reason)
                return True
            except Exception as e:
                error_msg = f"本地备用生成器失败: {str(e)}"
                print(f"❌ {error_msg}")
                self.error.emit(error_msg)
                try:
                    self.generate_btn.setText("✨ 生成内容")
                    self.generate_btn.setEnabled(True)
                except Exception:
                    pass
                return False

        # ✅ 优先使用用户配置的大模型（含本地模型）；失败时可回退到本地备用生成器（离线可用）。
        if _try_llm():
            return

        if allow_fallback:
            # 兜底：走本地备用生成器（离线可用）
            last = getattr(self, "_last_llm_error", "")
            last_text = (str(last or "").strip() or "")

            def _summarize_error(text: str) -> str:
                s = (text or "").strip()
                if not s:
                    return ""
                if ("HTTP 401" in s) or ("invalid_api_key" in s) or ("Incorrect API key" in s):
                    return "模型鉴权失败（401）：API Key 无效/过期，请到「后台配置 → 模型配置」更新"
                if ("HTTP 403" in s) or ("forbidden" in s.lower()):
                    return "模型鉴权失败（403）：无权限访问，请检查 Key/权限"
                if ("HTTP 429" in s) or ("rate limit" in s.lower()):
                    return "模型接口限流/额度不足（429），请稍后重试或更换模型"
                if ("HTTP 5" in s) or ("server error" in s.lower()):
                    return "模型服务端异常（5xx），请稍后重试"
                if ("Connection refused" in s) or ("连接" in s and "失败" in s) or ("模型请求失败" in s):
                    return "无法连接模型端点，请检查端点地址与本地服务是否已启动"

                # 兜底：只截取第一段，避免弹窗展示大段 JSON
                first_line = s.splitlines()[0].strip() if s.splitlines() else s
                if len(first_line) > 120:
                    first_line = first_line[:120] + "..."
                return first_line

            short = _summarize_error(last_text)
            reason = "⚠️ 模型不可用，当前为原文预览，未生成新文案"
            if short:
                reason += f"\n{short}"
            _try_backup(reason=reason)
            return

        # 严格模式：不回退，直接报错
        last = getattr(self, "_last_llm_error", "")
        self.error.emit(last or "生成失败：未配置可用的大模型")
        return

    def _generate_marketing_poster(self) -> None:
        """生成“营销海报”所需的文案与图片，并通过 finished 信号返回。"""
        from src.core.services.marketing_poster_service import marketing_poster_service

        price_override = os.environ.get("XHS_MARKETING_POSTER_PRICE", "").strip()
        keyword_override = os.environ.get("XHS_MARKETING_POSTER_KEYWORD", "").strip()

        extracted_price = self._extract_price_value(self.input_text)
        price_hint = price_override or extracted_price
        keyword_hint = keyword_override

        content = llm_service.generate_marketing_poster_content(
            topic=self.input_text,
            price=price_hint,
            keyword=keyword_hint,
        )

        # 可选：注入用户选择的“营销海报素材”（透明 PNG）
        try:
            asset_config = Config().get_templates_config()
            asset_path = str(asset_config.get("marketing_poster_asset_path") or "").strip()
            content['page_asset_paths'] = asset_config.get('poster_page_asset_paths') or []
            content['poster_layout'] = layout_for_template(asset_config.get('selected_cover_template_id') or '', asset_config.get('poster_layout') or '')
        except Exception:
            asset_path = ""
        asset_path = os.path.expanduser(asset_path) if asset_path else ""
        if asset_path and os.path.exists(asset_path):
            try:
                content["asset_image_path"] = asset_path
            except Exception:
                pass

        # 不再使用任何远程兜底：只走本地/大模型生成（避免风控/波动导致生成失败）

        cover_path, content_paths = marketing_poster_service.generate_to_local_paths(content)
        if not cover_path or not content_paths:
            raise RuntimeError("营销海报图片生成失败")

        title = str(content.get("title") or "").strip()
        caption = str(content.get("caption") or "").strip()
        subtitle = str(content.get("subtitle") or "").strip()
        shown_content = caption or subtitle

        result = {
            "title": title,
            "content": shown_content,
            "cover_image": cover_path,
            "content_images": content_paths,
            "input_text": self.input_text,
            "content_pages": [],
            "generator": "marketing_poster",
            "info_reason": self._format_marketing_poster_info_reason(content),
        }
        self.finished.emit(result)

    @staticmethod
    def _extract_price_value(text: str) -> str:
        """从文本中提取价格数字（不带单位）。"""
        s = str(text or "")
        patterns = [
            r"(?:￥|¥)\s*(\d+(?:\.\d{1,2})?)",
            r"(\d+(?:\.\d{1,2})?)\s*(?:元|块|¥|￥)",
        ]
        for pat in patterns:
            m = re.search(pat, s)
            if m:
                return str(m.group(1) or "").strip()
        return ""

    @staticmethod
    def _format_marketing_poster_info_reason(content: dict) -> str:
        source = str((content or {}).get("__source") or "").strip().lower()
        if source == "llm":
            reason = "🪧 营销海报：大模型 AI 文案 + 本地渲染"
            review = (content or {}).get('writing_review') or {}
            if review.get('message'):
                reason += '\n' + review['message']
            return reason
        return "🪧 营销海报：默认文案 + 本地渲染"

    def _use_backup_generator(self, info_reason: str = ""):
        """使用备用生成器"""
        print("🔄 启动备用内容生成器...")

        # 创建备用生成器实例
        backup_generator = BackupContentGenerator(
            self.input_text,
            self.header_title,
            self.author,
            self.generate_btn
        )
        self._backup_info_reason = info_reason or ""
        if info_reason:
            backup_generator.info_reason = info_reason
        
        # 连接信号
        backup_generator.finished.connect(self._handle_backup_result)
        backup_generator.error.connect(self._handle_backup_error)
        
        # 运行备用生成器（同步运行）
        backup_generator.run()

    def _handle_backup_result(self, result):
        """处理备用生成器的结果"""
        print("✅ 备用内容生成成功，发送结果...")
        # 给 UI 一个提示：当前结果来自备用生成器
        try:
            if isinstance(result, dict):
                info_reason = getattr(self, "_backup_info_reason", "") or result.get("info_reason") or ""
                if info_reason:
                    result["info_reason"] = info_reason
                result.setdefault("generator", "backup")
        except Exception:
            pass
        self.finished.emit(result)

    def _handle_backup_error(self, error_msg):
        """处理备用生成器的错误"""
        print(f"❌ 备用生成器也失败了: {error_msg}")
        self.error.emit(error_msg)

    def _try_generate_with_custom_model(self) -> bool:
        """如果用户已配置模型，则使用自定义模型生成文案，并生成本地占位图片。"""
        try:
            model_config = Config().get_model_config()
            ok, _reason = llm_service.is_model_configured(model_config)
            if not ok:
                return False

            self.generate_btn.setText("🤖 AI生成中...")
            self.generate_btn.setEnabled(False)

            llm_resp = llm_service.generate_xiaohongshu_content(
                topic=self.input_text,
                header_title=self.header_title,
                author=self.author,
            )

            cover_path = ""
            content_paths = []
            image_source = "placeholder"
            image_brief = (llm_resp.raw_json or {}).get("image_brief", {})
            if not isinstance(image_brief, dict):
                image_brief = {}
            image_brief = {key: str(image_brief.get(key) or "").strip()
                           for key in ("cover_heading", "cover_description")}

            # 优先使用系统模板图片（如 x-auto-publisher），生成更真实的封面/内容图
            try:
                pages = None
                page_count = 3
                if isinstance(llm_resp.raw_json, dict):
                    raw_pages = llm_resp.raw_json.get("content_pages")
                    if isinstance(raw_pages, list):
                        pages = [str(x) for x in raw_pages if str(x).strip()]
                    else:
                        raw_list = llm_resp.raw_json.get("content")
                        if isinstance(raw_list, list):
                            pages = self._build_pages_from_content_list(raw_list)

                if pages:
                    # 避免生成过多图片导致卡顿
                    page_count = max(1, len(pages))

                asset_config = Config().get_templates_config()

                generated = system_image_template_service.generate_post_images(
                    title=llm_resp.title,
                    content=llm_resp.content,
                    content_pages=pages,
                    page_count=page_count,
                    cover_heading=image_brief["cover_heading"],
                    cover_description=image_brief["cover_description"],
                    cover_asset_image_path=str(asset_config.get('marketing_poster_asset_path') or ''),
                    page_asset_paths=asset_config.get('poster_page_asset_paths') or [],
                )
                if generated:
                    cover_path, content_paths = generated
                    image_source = "system_templates"
                    print("🧩 已使用系统模板图片生成封面/内容图")
            except Exception as e:
                print(f"⚠️ 系统模板图片生成失败，将回退到占位图: {e}")

            if not cover_path or not content_paths:
                page_count = max(1, len(pages)) if pages else 3
                cover_path, content_paths = self._generate_local_placeholder_images(
                    title=llm_resp.title,
                    count=page_count,
                )
                image_source = "placeholder"

            result = {
                'title': llm_resp.title,
                'content': llm_resp.content,
                'cover_image': cover_path,
                'content_images': content_paths,
                'content_pages': pages or [],
                'input_text': self.input_text,
                'generator': 'llm',
                'image_brief': image_brief,
                'info_reason': (
                    "🤖 已使用大模型生成文案"
                    + ("（图片：系统模板）" if image_source == "system_templates" else "（图片：占位图）")
                    + ('\n' + (llm_resp.raw_json or {}).get('writing_review', {}).get('message', '')
                       if (llm_resp.raw_json or {}).get('writing_review', {}).get('message') else '')
                ),
            }

            print("✅ 自定义模型生成成功")
            self.finished.emit(result)
            return True

        except LLMServiceError as e:
            # 明确的模型错误直接抛出，交给上层回退
            raise e
        finally:
            if hasattr(self, 'generate_btn'):
                self.generate_btn.setText("✨ 生成内容")
                self.generate_btn.setEnabled(True)

    @staticmethod
    def _build_pages_from_content_list(items, max_pages: int = 3):
        """将 content(list) 转换为系统图片模板的 page 文本格式。

        默认会把多个短段落合并为更少的页面，避免“每页只有一两行字”导致画面太空。
        """
        if not isinstance(items, list):
            return []

        sections = []
        for it in items:
            s = str(it or "").strip()
            if not s:
                continue
            if "~~~" in s:
                head, body = s.split("~~~", 1)
                head = str(head or "").strip()
                body = str(body or "").strip()
            else:
                head, body = "", s
            if head or body:
                sections.append((head, body))

        if not sections:
            return []

        # 将“标签/话题”放到最后，避免占用前面页面标题位置
        def _is_tag(h: str) -> bool:
            h = (h or "").strip()
            return h in {"标签", "话题", "话题标签"} or ("标签" in h) or ("话题" in h)

        normal = [s for s in sections if not _is_tag(s[0])]
        tags = [s for s in sections if _is_tag(s[0])]
        sections = normal + tags

        # 若段落数不多，保持“一段一页”
        if len(sections) <= max(1, int(max_pages)):
            pages = []
            for head, body in sections:
                if head and body:
                    pages.append(f"# {head}\n\n{body}")
                elif head:
                    pages.append(f"# {head}")
                else:
                    pages.append(body)
            return [p for p in pages if str(p).strip()]

        target_pages = max(1, int(max_pages))
        # 简单按数量平均分组
        per = (len(sections) + target_pages - 1) // target_pages
        groups = [sections[i : i + per] for i in range(0, len(sections), per)]

        chinese_nums = ["一", "二", "三", "四", "五", "六", "七", "八"]
        pages = []
        for idx, group in enumerate(groups):
            if not group:
                continue
            first_head, first_body = group[0]
            page_title = first_head.strip() if first_head.strip() else f"要点{chinese_nums[idx] if idx < len(chinese_nums) else str(idx+1)}"

            blocks = []
            if first_body.strip():
                blocks.append(first_body.strip())

            for head, body in group[1:]:
                head = (head or "").strip()
                body = (body or "").strip()
                if head and body:
                    blocks.append(f"{head}\n{body}")
                elif head:
                    blocks.append(head)
                elif body:
                    blocks.append(body)

            body_text = "\n\n".join([b for b in blocks if b.strip()]).strip()
            if body_text:
                pages.append(f"# {page_title}\n\n{body_text}")
            else:
                pages.append(f"# {page_title}")

        return [p for p in pages if str(p).strip()]

    @staticmethod
    def _format_content_text(content_value, contentlist_value) -> str:
        """将接口返回的内容格式化为更适合小红书发布的分段文本。"""
        def _as_str(v) -> str:
            try:
                return str(v or "").strip()
            except Exception:
                return ""

        def _format_head(head: str) -> str:
            h = (head or "").strip()
            if not h:
                return ""
            # 去掉 markdown 标题前缀
            h = re.sub(r"^#+\\s*", "", h).strip()
            if not h:
                return ""
            if (h.startswith("【") and h.endswith("】")) or (h.startswith("[") and h.endswith("]")):
                return h
            # 短标题用「【】」更像小红书的分段样式
            if len(h) <= 18 and not re.search(r"[。！？!?，,;；]", h):
                return f"【{h}】"
            return h

        def _is_tag_head(h: str) -> bool:
            h = (h or "").strip()
            return h in {"标签", "话题", "话题标签"} or ("标签" in h) or ("话题" in h)

        def _extract_tags(text: str):
            t = (text or "").strip().replace("#", " ")
            t = re.sub(r"[，,、/|]+", " ", t)
            parts = [p.strip() for p in t.split() if p.strip()]
            # 去重保序
            seen = set()
            out = []
            for p in parts:
                if p in seen:
                    continue
                seen.add(p)
                out.append(p)
            return out[:12]

        def _auto_paragraphize(raw: str) -> str:
            raw = (raw or "").strip()
            if not raw:
                return ""
            # 已经有换行则保留，并把单换行转成段落换行（更清爽）
            if "\n" in raw:
                lines = [ln.rstrip() for ln in raw.splitlines()]
                # 规范化：连续空行压成一个空行
                normalized = []
                blank = False
                for ln in lines:
                    if not ln.strip():
                        if not blank:
                            normalized.append("")
                        blank = True
                        continue
                    blank = False
                    normalized.append(ln.strip())
                # 若原文本没有用空行分段，则把每行当作一段（更符合小红书阅读节奏）
                if "" not in normalized and len([x for x in normalized if str(x).strip()]) >= 2:
                    return "\n\n".join([x for x in normalized if str(x).strip()]).strip()
                return "\n".join(normalized).strip()

            # 无换行：按句号/问号/感叹号切分，控制每段 1-2 句
            sents = []
            buf = ""
            for ch in raw:
                buf += ch
                if ch in "。！？；":
                    s = buf.strip()
                    if s:
                        sents.append(s)
                    buf = ""
            rest = buf.strip()
            if rest:
                sents.append(rest)

            if len(sents) <= 1:
                # 退化：按逗号切分并保留标点
                parts = []
                buf = ""
                for ch in raw:
                    buf += ch
                    if ch in "，,、":
                        s = buf.strip()
                        if s:
                            parts.append(s)
                        buf = ""
                rest2 = buf.strip()
                if rest2:
                    parts.append(rest2)
                if len(parts) > 1:
                    sents = parts

            # 仍然是一整段且缺少标点：按长度硬拆（提升可读性）
            if len(sents) <= 1 and len(raw) > 90:
                tag_cluster = ""
                text_part = raw
                try:
                    m = re.search(r"(#[^#\s]{1,24}){2,}$", raw)
                except Exception:
                    m = None
                if m:
                    try:
                        tag_cluster = str(m.group(0) or "").strip()
                    except Exception:
                        tag_cluster = ""
                    text_part = (raw[: m.start()] or "").strip()

                para_size = 56
                paras = []
                for i in range(0, len(text_part), para_size):
                    p = (text_part[i : i + para_size] or "").strip()
                    if p:
                        paras.append(p)
                out = "\n\n".join(paras).strip() if paras else text_part.strip()

                if tag_cluster:
                    tags = [t.strip() for t in tag_cluster.split("#") if t.strip()]
                    if tags:
                        out = (out + "\n\n" + " ".join([f"#{t}" for t in tags])).strip()

                return out or raw

            paras = []
            cur = []
            cur_len = 0
            for s in sents:
                s = s.strip()
                if not s:
                    continue
                if cur and (len(cur) >= 2 or cur_len + len(s) > 44):
                    paras.append("".join(cur).strip())
                    cur = [s]
                    cur_len = len(s)
                else:
                    cur.append(s)
                    cur_len += len(s)
            if cur:
                paras.append("".join(cur).strip())

            # 合并过短段落
            merged = []
            for p in paras:
                if merged and len(p) <= 10:
                    merged[-1] = (merged[-1].rstrip() + p).strip()
                else:
                    merged.append(p)
            paras = merged

            if len(paras) >= 2:
                return "\n\n".join([p for p in paras if p]).strip()
            return raw

        # 优先使用 contentlist
        raw_list = contentlist_value
        try:
            if isinstance(raw_list, str) and raw_list.strip().startswith("["):
                raw_list = json.loads(raw_list)
        except Exception:
            raw_list = contentlist_value

        sections = []
        tags = []
        if isinstance(raw_list, list) and raw_list:
            for it in raw_list:
                s = _as_str(it)
                if not s:
                    continue
                if "~~~" in s:
                    head, body = s.split("~~~", 1)
                    head = _as_str(head)
                    body = _as_str(body)
                else:
                    head, body = "", s

                if _is_tag_head(head):
                    tags.extend(_extract_tags(body))
                    continue

                block_lines = []
                if head:
                    block_lines.append(_format_head(head))
                if body:
                    block_lines.append(_auto_paragraphize(body))
                block = "\n".join([x for x in block_lines if x]).strip()
                if block:
                    sections.append(block)

        base = _as_str(content_value)
        base_formatted = _auto_paragraphize(base)

        from_list = "\n\n".join(sections).strip()

        # 去重标签
        if tags:
            seen = set()
            uniq = []
            for t in tags:
                t = _as_str(t)
                if not t or t in seen:
                    continue
                seen.add(t)
                uniq.append(t)
            tags = uniq[:12]

        tag_line = ""
        if tags:
            tag_line = " ".join([f"#{t}" for t in tags if _as_str(t)]).strip()

        # 排版优先用 contentlist（有分段/小标题更好读）；拿不到再用 content 的自动分段
        body = ""
        if from_list:
            body = from_list
            # contentlist 只有 1 段且太短时，优先用完整正文
            try:
                if len(sections) <= 1 and base_formatted and len(base_formatted) >= 180 and len(body) < 120:
                    body = base_formatted
            except Exception:
                pass
        else:
            body = base_formatted

        if tag_line and body and not re.search(r"#\S", body):
            body = (body.rstrip() + "\n\n" + tag_line).strip()

        return (body or "").strip()

    def _generate_local_placeholder_images(self, title: str, count: int = 3):
        """生成本地占位图片，避免依赖外部图片服务。"""
        try:
            from PIL import Image, ImageDraw, ImageFont
        except Exception as e:
            raise Exception(f"Pillow 未安装或不可用: {e}")

        base_dir = os.path.join(os.path.expanduser('~'), '.xhs_system', 'generated_imgs')
        os.makedirs(base_dir, exist_ok=True)

        def _make_image(path: str, label: str):
            width, height = 1080, 1440
            bg = (245, 245, 245)
            img = Image.new('RGB', (width, height), bg)
            draw = ImageDraw.Draw(img)

            # 使用默认字体；若系统缺少中文字体，文字可能不显示但图片仍有效
            try:
                font = ImageFont.load_default()
            except Exception:
                font = None

            text = f"{label}\n{(title or '').strip()[:40]}"
            draw.multiline_text((60, 80), text, fill=(30, 30, 30), font=font, spacing=10)
            img.save(path, format='JPEG', quality=90)

        unique = uuid.uuid4().hex[:8]
        cover_path = os.path.join(base_dir, f'cover_{int(time.time())}_{unique}.jpg')
        _make_image(cover_path, "封面")

        content_paths = []
        for i in range(max(1, int(count))):
            p = os.path.join(base_dir, f'content_{i+1}_{int(time.time())}_{unique}.jpg')
            _make_image(p, f"内容图{i+1}")
            content_paths.append(p)

        return cover_path, content_paths
