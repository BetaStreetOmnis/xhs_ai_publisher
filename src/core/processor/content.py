import json
import re
import traceback
import time
import os
import uuid
from PyQt5.QtCore import QThread, pyqtSignal
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

# 导入备用生成器
from .content_backup import BackupContentGenerator
from src.config.config import Config
from src.core.services.llm_service import llm_service, LLMServiceError
from src.core.services.system_image_template_service import system_image_template_service


"""历史版本，基于coze生成图片 - 增强版错误处理 + 故障转移"""

class ContentGeneratorThread(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, input_text, header_title, author, generate_btn):
        super().__init__()
        self.input_text = input_text
        self.header_title = header_title
        self.author = author
        self.generate_btn = generate_btn
        self.max_retries = 2  # 减少重试次数，更快切换到备用方案
        self.retry_delay = 2  # 减少重试间隔
        self.use_backup = False

    def run(self):
        """主运行方法，包含重试逻辑和故障转移"""
        selected_cover_tpl = ""
        try:
            selected_cover_tpl = str(Config().get_templates_config().get("selected_cover_template_id") or "").strip()
        except Exception:
            selected_cover_tpl = ""

        allow_fallback = os.environ.get("XHS_ALLOW_FALLBACK", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "y",
            "on",
        }

        # 默认走 8.* 远程接口（用户反馈样式更好）；当用户选择了其他封面模板时，优先走大模型
        prefer_remote_first = not bool(selected_cover_tpl)

        def _try_remote() -> bool:
            if not self._should_use_remote_workflow_api():
                self._last_remote_error = "默认接口不可用：无法连接到远程服务"
                return False

            retry_count = 0
            last_error = ""
            while retry_count < self.max_retries:
                try:
                    print(f"🚀 开始第 {retry_count + 1} 次尝试生成内容...")
                    self._generate_content()
                    return True
                except Exception as e:
                    retry_count += 1
                    error_msg = str(e)
                    last_error = error_msg

                    if retry_count < self.max_retries:
                        print(f"⚠️ 第 {retry_count} 次尝试失败: {error_msg}")
                        print(f"🔄 {self.retry_delay} 秒后进行第 {retry_count + 1} 次重试...")
                        try:
                            self.generate_btn.setText(f"⏳ 重试中({retry_count + 1}/{self.max_retries})...")
                        except Exception:
                            pass
                        time.sleep(self.retry_delay)
                    else:
                        print(f"❌ 主API所有 {self.max_retries} 次尝试都失败了")
                        self._last_remote_error = last_error or "默认接口生成失败"
                        return False

            return False

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

        if prefer_remote_first:
            if _try_remote():
                return
            if allow_fallback:
                if _try_llm():
                    return
                _try_backup(reason="远程服务不可用，已切换为本地生成（图片为占位图）")
                return

            # 不允许回退：直接报错（避免误以为仍在使用默认接口）
            self.error.emit(getattr(self, "_last_remote_error", "") or "默认接口生成失败")
            return

        # 选择了封面模板：优先走大模型；若未配置，则退回 8.* 接口生成文案（图片会在首页按所选封面模板重新生成）
        if _try_llm():
            return
        if _try_remote():
            return
        if allow_fallback:
            _try_backup(reason="未配置可用的大模型/远程服务，已切换为本地生成（图片为占位图）")
            return

        # 不允许回退：优先给出更明确的错误信息
        last = getattr(self, "_last_remote_error", "") or getattr(self, "_last_llm_error", "")
        self.error.emit(last or "生成失败：未配置可用的大模型/远程服务")
        return

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

    def _generate_content(self):
        """实际的内容生成逻辑（主API）"""
        try:
            # 更新按钮状态
            self.generate_btn.setText("⏳ 接口生成中...")
            self.generate_btn.setEnabled(False)

            # 打印详细的输入信息
            print("=" * 60)
            print("🚀 开始生成内容...")
            print(f"📝 输入内容: {self.input_text[:100]}{'...' if len(self.input_text) > 100 else ''}")
            print(f"🏷️ 眉头标题: {self.header_title}")
            print(f"👤 作者: {self.author}")
            print("=" * 60)

            workflow_id = "7431484143153070132"
            parameters = {
                "BOT_USER_INPUT": self.input_text,
                "HEADER_TITLE": self.header_title,
                "AUTHOR": self.author
            }

            api_url = "http://8.137.103.115:8081/workflow/run"
            print(f"🌐 API地址: {api_url}")
            print(f"📦 工作流ID: {workflow_id}")
            print(f"📋 请求参数: {parameters}")

            # 发送API请求
            print("📡 发送API请求...")
            try:
                # 远程工作流偶发较慢（生成图片/排版），默认给更长的读取超时；可用环境变量覆盖
                connect_timeout = float(os.environ.get("XHS_REMOTE_WORKFLOW_CONNECT_TIMEOUT", "5") or 5)
                read_timeout = float(os.environ.get("XHS_REMOTE_WORKFLOW_READ_TIMEOUT", "120") or 120)
                response = requests.post(
                    api_url,
                    json={
                        "workflow_id": workflow_id,
                        "parameters": parameters
                    },
                    timeout=(connect_timeout, read_timeout),
                    headers={
                        'Content-Type': 'application/json',
                        'User-Agent': 'XhsAiPublisher/1.0',
                        'Accept': 'application/json'
                    }
                )
                
                print(f"✅ API请求发送成功")
                print(f"📊 响应状态码: {response.status_code}")
                print(f"📄 响应头信息: {dict(response.headers)}")
                
            except ConnectionError as e:
                error_msg = f"网络连接失败: {str(e)}"
                print(f"❌ {error_msg}")
                raise Exception(error_msg)
            except Timeout as e:
                error_msg = f"API请求超时（{int(read_timeout)}秒）: {str(e)}"
                print(f"❌ {error_msg}")
                raise Exception(error_msg)
            except RequestException as e:
                error_msg = f"API请求异常: {str(e)}"
                print(f"❌ {error_msg}")
                raise Exception(error_msg)

            # 检查HTTP状态码
            if response.status_code != 200:
                error_detail = ""
                try:
                    error_detail = response.text[:200]
                    print(f"❌ API错误响应: {error_detail}")
                except:
                    error_detail = "无法获取错误详情"
                
                error_msg = f"API调用失败，状态码: {response.status_code}"
                if response.status_code == 400:
                    error_msg += " - 请求参数错误或API格式已更改"
                elif response.status_code == 404:
                    error_msg += " - API接口不存在"
                elif response.status_code == 500:
                    error_msg += " - 服务器内部错误"
                elif response.status_code == 502:
                    error_msg += " - 网关错误，服务不可用"
                elif response.status_code == 403:
                    error_msg += " - 访问被拒绝"
                
                raise Exception(error_msg)

            # 解析响应数据
            try:
                response_text = response.text
                print(f"📝 API原始响应长度: {len(response_text)} 字符")
                print(f"📝 API响应前500字符: {response_text[:500]}")
                
                res = response.json()
                print(f"✅ JSON解析成功")
                print(f"📊 响应数据键: {list(res.keys())}")
                
            except json.JSONDecodeError as e:
                error_msg = f"API响应JSON解析失败: {str(e)}"
                print(f"❌ {error_msg}")
                raise Exception(error_msg)

            # 验证响应数据结构
            if 'data' not in res:
                # 兼容错误返回：{code,msg,detail,debug_url}
                if isinstance(res, dict) and res.get("code") is not None:
                    code = res.get("code")
                    msg = str(res.get("msg") or "").strip()
                    debug_url = str(res.get("debug_url") or "").strip()
                    detail = res.get("detail") if isinstance(res.get("detail"), dict) else {}
                    logid = str((detail or {}).get("logid") or "").strip()

                    parts = [f"远程工作流执行失败(code={code})"]
                    if msg:
                        parts.append(msg)
                    if logid:
                        parts.append(f"logid: {logid}")
                    if debug_url:
                        parts.append(f"debug_url: {debug_url}")
                    error_msg = " | ".join(parts)
                    print(f"❌ {error_msg}")
                    raise Exception(error_msg)

                error_msg = f"API响应格式错误，缺少'data'字段"
                print(f"❌ {error_msg}")
                raise Exception(error_msg)
            
            try:
                if isinstance(res['data'], dict):
                    output_data = res['data']
                else:
                    output_data = json.loads(res['data'])
                print(f"✅ 输出数据解析成功")
                print(f"📊 输出数据键: {list(output_data.keys())}")
                
            except json.JSONDecodeError as e:
                error_msg = f"输出数据JSON解析失败: {str(e)}"
                print(f"❌ {error_msg}")
                raise Exception(error_msg)
            
            # 验证必需字段
            required_fields = ['output', 'content']
            missing_fields = []
            for field in required_fields:
                if field not in output_data:
                    missing_fields.append(field)
            
            if missing_fields:
                error_msg = f"输出数据缺少必需字段: {missing_fields}"
                print(f"❌ {error_msg}")
                raise Exception(error_msg)
            
            # 解析标题数据
            try:
                title_data = json.loads(output_data['output'])
                print(f"✅ 标题数据解析成功")
                
                if 'title' not in title_data:
                    error_msg = f"标题数据格式错误，缺少'title'字段"
                    print(f"❌ {error_msg}")
                    raise Exception(error_msg)
                
                title = title_data['title']
                
            except json.JSONDecodeError as e:
                error_msg = f"标题数据JSON解析失败: {str(e)}"
                print(f"❌ {error_msg}")
                raise Exception(error_msg)
            
            # 检查图片相关字段
            try:
                full_data = json.loads(res['data'])
                image_fields = ['image', 'image_content']
                for field in image_fields:
                    if field not in full_data:
                        print(f"⚠️ 警告: 缺少图片字段 '{field}'，将使用空值")
                
                cover_image = full_data.get('image', '')
                content_images = full_data.get('image_content', [])
                
            except Exception as e:
                print(f"⚠️ 图片数据处理警告: {str(e)}")
                cover_image = ''
                content_images = []

            # 构建结果
            content_pages = []
            try:
                raw_list = output_data.get('contentlist')
                if isinstance(raw_list, str) and raw_list.strip().startswith("["):
                    raw_list = json.loads(raw_list)
                if isinstance(raw_list, list):
                    content_pages = self._build_pages_from_content_list(raw_list)
            except Exception:
                content_pages = []

            # 优化内容排版：优先用 contentlist 生成更“小红书”的分段文本
            formatted_content = ""
            try:
                formatted_content = self._format_content_text(
                    output_data.get("content"),
                    output_data.get("contentlist"),
                )
            except Exception:
                formatted_content = str(output_data.get("content") or "").strip()

            result = {
                'title': title,
                'content': formatted_content,
                'cover_image': cover_image,
                'content_images': content_images,
                'input_text': self.input_text,
                'content_pages': content_pages,
                'generator': 'remote',
                'info_reason': '已使用默认生成',
            }
            
            # 打印成功信息
            print("🎉 内容生成成功!")
            print(f"📌 标题: {title}")
            print(f"📄 内容长度: {len(result['content'])} 字符")
            print(f"📄 内容预览: {result['content'][:100]}...")
            print(f"🖼️ 封面图片: {'有' if cover_image else '无'}")
            print(f"📸 内容图片数量: {len(content_images) if isinstance(content_images, list) else 0}")
            print("=" * 60)

            self.finished.emit(result)
                
        except Exception as e:
            error_msg = str(e)
            print(f"❌ 主API生成内容失败: {error_msg}")
            print(f"🔍 详细错误信息:")
            print(traceback.format_exc())
            print("=" * 60)
            raise e
        finally:
            # 只有在不使用备用生成器时才恢复按钮状态
            if not self.use_backup:
                if hasattr(self, 'generate_btn'):
                    self.generate_btn.setText("✨ 生成内容")
                    self.generate_btn.setEnabled(True)

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
                    pages = pages[:8]
                    page_count = max(1, len(pages))

                generated = system_image_template_service.generate_post_images(
                    title=llm_resp.title,
                    content=llm_resp.content,
                    content_pages=pages,
                    page_count=page_count,
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
                'info_reason': (
                    "🤖 已使用大模型生成文案"
                    + ("（图片：系统模板）" if image_source == "system_templates" else "（图片：占位图）")
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
                    block_lines.append(head)
                if body:
                    block_lines.append(_auto_paragraphize(body))
                block = "\n".join([x for x in block_lines if x]).strip()
                if block:
                    sections.append(block)

        # 如果没拿到 contentlist，则退化到 content 字段
        if not sections:
            base = _as_str(content_value)
            return _auto_paragraphize(base)

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

        if tags:
            sections.append("话题标签：" + " ".join(tags))

        return "\n\n".join(sections).strip()

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

    def _should_use_remote_workflow_api(self) -> bool:
        """是否尝试使用远程工作流 API（默认开启，可通过环境变量关闭）。"""
        # 允许强制关闭（优先级更高）
        if os.environ.get("XHS_DISABLE_REMOTE_WORKFLOW", "").strip().lower() in {"1", "true", "yes", "y", "on"}:
            return False

        # 先做一次快速连通性判断，避免卡在 30s 超时
        try:
            import socket
            from urllib.parse import urlparse

            api_url = "http://8.137.103.115:8081/workflow/run"
            parsed = urlparse(api_url)
            host = parsed.hostname or ""
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            if not host:
                return False

            with socket.create_connection((host, port), timeout=2):
                return True
        except Exception:
            return False
