from PyQt5.QtCore import QThread, pyqtSignal
import asyncio
import os
import random
import re
import sys
import time
from functools import partial

from src.core.write_xiaohongshu import XiaohongshuPoster


class BrowserThread(QThread):
    # 添加信号
    login_status_changed = pyqtSignal(str, bool)  # 用于更新登录按钮状态
    preview_status_changed = pyqtSignal(str, bool)  # 用于更新预览按钮状态
    login_success = pyqtSignal(object)  # 用于传递poster对象
    login_error = pyqtSignal(str)  # 用于传递错误信息
    preview_success = pyqtSignal()  # 用于通知预览成功
    preview_error = pyqtSignal(str)  # 用于传递预览错误信息
    scheduled_task_result = pyqtSignal(str, bool, str)  # (task_id, success, error_msg)

    def __init__(self):
        super().__init__()
        self.poster = None
        self.action_queue = []
        self.is_running = True
        self.loop = None

    def run(self):
        # 创建新的事件循环
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # 在事件循环中运行主循环
        self.loop.run_until_complete(self.async_run())
        
        # 关闭事件循环
        self.loop.close()
        
    async def async_run(self):
        """异步主循环"""
        while self.is_running:
            if self.action_queue:
                action = self.action_queue.pop(0)
                try:
                    if action['type'] == 'login':
                        phone = (action.get('phone') or "").strip()
                        country_code = str(action.get('country_code') or "+86").strip() or "+86"
                        if not phone:
                            raise ValueError("手机号不能为空")

                        # 根据手机号匹配/创建用户，并作为当前用户
                        try:
                            from src.core.services.user_service import user_service
                        except Exception:
                            user_service = None

                        current_user = None
                        if user_service:
                            current_user = user_service.get_user_by_phone(phone)
                            if current_user:
                                user_service.switch_user(current_user.id)
                            else:
                                normalized_phone = "".join([c for c in phone if c.isdigit()]) or phone
                                username_base = f"user_{normalized_phone}"
                                username = username_base
                                suffix = 1
                                while user_service.get_user_by_username(username):
                                    username = f"{username_base}_{suffix}"
                                    suffix += 1
                                current_user = user_service.create_user(
                                    username=username,
                                    phone=phone,
                                    display_name=phone,
                                    set_current=True,
                                )

                        # 如果已存在浏览器会话，先关闭避免残留进程导致“偶发启动失败”
                        if self.poster:
                            try:
                                await self.poster.close(force=True)
                            except Exception:
                                pass
                            self.poster = None

                        # 读取当前用户的默认环境（代理/指纹）
                        browser_env = None
                        try:
                            from src.core.services.browser_environment_service import browser_environment_service

                            if current_user:
                                browser_env = browser_environment_service.get_default_environment(current_user.id)
                                if not browser_env:
                                    browser_environment_service.create_preset_environments(current_user.id)
                                    browser_env = browser_environment_service.get_default_environment(current_user.id)

                                # 若默认环境与当前系统不匹配，优先选择同用户下更贴近当前系统的环境（仅本次会话，不修改默认设置）
                                if browser_env and sys.platform == "darwin":
                                    ua = (browser_env.user_agent or "")
                                    platform = (browser_env.platform or "")
                                    if "Windows NT" in ua or platform == "Win32":
                                        browser_environment_service.create_preset_environments(current_user.id)
                                        envs = browser_environment_service.get_user_environments(current_user.id, active_only=True) or []
                                        for env in envs:
                                            if (env.platform or "") == "MacIntel" or "Macintosh" in (env.user_agent or ""):
                                                print(f"检测到 macOS 系统，默认环境为 Windows 指纹；本次登录临时切换到环境: {env.name}")
                                                browser_env = env
                                                break
                                elif browser_env and sys.platform == "win32":
                                    ua = (browser_env.user_agent or "")
                                    platform = (browser_env.platform or "")
                                    if "Macintosh" in ua or platform == "MacIntel":
                                        browser_environment_service.create_preset_environments(current_user.id)
                                        envs = browser_environment_service.get_user_environments(current_user.id, active_only=True) or []
                                        for env in envs:
                                            if (env.platform or "") == "Win32" or "Windows NT" in (env.user_agent or ""):
                                                print(f"检测到 Windows 系统，默认环境为 Mac 指纹；本次登录临时切换到环境: {env.name}")
                                                browser_env = env
                                                break
                        except Exception:
                            browser_env = None

                        self.poster = XiaohongshuPoster(
                            user_id=(current_user.id if current_user else None),
                            browser_environment=browser_env,
                        )
                        await self.poster.initialize()
                        await self.poster.login(phone, country_code=country_code)

                        if user_service and current_user:
                            user_service.update_login_status(current_user.id, True)

                        self.login_success.emit(self.poster)
                    elif action['type'] == 'preview' and self.poster:
                        await self.poster.post_article(
                            action['title'],
                            action['content'],
                            action['images'],
                            auto_publish=False,
                        )
                        self.preview_success.emit()
                    elif action['type'] == 'scheduled_publish':
                        await self._run_scheduled_publish(action)
                except Exception as e:
                    if action['type'] == 'login':
                        # 登录阶段失败时，尽量释放浏览器资源，避免后续启动不稳定
                        try:
                            if self.poster:
                                await self.poster.close(force=True)
                        except Exception:
                            pass
                        finally:
                            self.poster = None

                        # 登录失败：更新数据库状态（不影响错误上报）
                        try:
                            from src.core.services.user_service import user_service

                            phone = (action.get('phone') or "").strip()
                            if phone:
                                u = user_service.get_user_by_phone(phone)
                                if u:
                                    user_service.update_login_status(u.id, False)
                        except Exception:
                            pass

                        msg = str(e)
                        if "Executable doesn't exist" in msg:
                            msg += "\n\n可能原因：Playwright 浏览器未安装/被杀毒清理。"
                            msg += "\n解决："
                            msg += "\n  - macOS/Linux："
                            msg += "\n    PLAYWRIGHT_BROWSERS_PATH=\"$HOME/.xhs_system/ms-playwright\" python -m playwright install chromium"
                            msg += "\n  - Windows（PowerShell）："
                            msg += "\n    $env:PLAYWRIGHT_BROWSERS_PATH=\"$HOME\\.xhs_system\\ms-playwright\"; python -m playwright install chromium"
                        self.login_error.emit(msg)
                    elif action['type'] == 'preview':
                        self.preview_error.emit(str(e))
                    elif action['type'] == 'scheduled_publish':
                        task_id = str(action.get('task_id') or "")
                        self.scheduled_task_result.emit(task_id, False, str(e))
            # 使用异步sleep而不是QThread.msleep
            await asyncio.sleep(0.1)  # 避免CPU占用过高

    async def _run_scheduled_publish(self, action: dict):
        """执行定时发布（无人值守，自动点击发布）。"""
        task_id = str(action.get("task_id") or "")
        user_id = action.get("user_id")
        task_type = str(action.get("task_type") or "fixed").strip() or "fixed"
        title = str(action.get("title") or "")
        content = str(action.get("content") or "")
        images = action.get("images") or []

        if isinstance(images, (list, tuple)):
            images = [p for p in images if isinstance(p, str) and p and os.path.isfile(p)]
        else:
            images = []

        if task_type == "hotspot":
            loop = asyncio.get_running_loop()
            payload = await loop.run_in_executor(None, partial(self._build_hotspot_payload_sync, action))
            title = str(payload.get("title") or "").strip()
            content = str(payload.get("content") or "").strip()
            images = payload.get("images") or []
            if isinstance(images, (list, tuple)):
                images = [p for p in images if isinstance(p, str) and p and os.path.isfile(p)]
            else:
                images = []

            if not title and not content:
                raise RuntimeError("热点任务生成文案失败：标题/内容为空")
            if not images:
                raise RuntimeError("热点任务生成图片失败：图片为空")
        else:
            if not title and not content:
                raise RuntimeError("发布失败：标题/正文为空")

            # 固定内容任务：若未提供图片，则到点自动生成模板图/占位图
            if not images:
                cover_template_id = str(action.get("cover_template_id") or "").strip()
                try:
                    page_count = int(action.get("page_count") or 3)
                except Exception:
                    page_count = 3
                page_count = max(1, page_count)
                images = self._generate_images_for_text(title=title, content=content, cover_template_id=cover_template_id, page_count=page_count)
                if isinstance(images, (list, tuple)):
                    images = [p for p in images if isinstance(p, str) and p and os.path.isfile(p)]
                else:
                    images = []

        # 默认使用当前用户
        if not user_id:
            try:
                from src.core.services.user_service import user_service

                current_user = user_service.get_current_user()
                user_id = current_user.id if current_user else None
            except Exception:
                user_id = None

        # 读取该用户默认浏览器环境（代理/指纹）
        browser_env = None
        try:
            from src.core.services.browser_environment_service import browser_environment_service

            if user_id:
                browser_env = browser_environment_service.get_default_environment(int(user_id))
                if not browser_env:
                    browser_environment_service.create_preset_environments(int(user_id))
                    browser_env = browser_environment_service.get_default_environment(int(user_id))

                # 定时任务同样优先使用与当前系统匹配的环境（避免 UA/platform 与 OS 不一致触发风控）
                if browser_env and sys.platform == "darwin":
                    ua = (browser_env.user_agent or "")
                    platform = (browser_env.platform or "")
                    if "Windows NT" in ua or platform == "Win32":
                        browser_environment_service.create_preset_environments(int(user_id))
                        envs = browser_environment_service.get_user_environments(int(user_id), active_only=True) or []
                        for env in envs:
                            if (env.platform or "") == "MacIntel" or "Macintosh" in (env.user_agent or ""):
                                browser_env = env
                                break
                elif browser_env and sys.platform == "win32":
                    ua = (browser_env.user_agent or "")
                    platform = (browser_env.platform or "")
                    if "Macintosh" in ua or platform == "MacIntel":
                        browser_environment_service.create_preset_environments(int(user_id))
                        envs = browser_environment_service.get_user_environments(int(user_id), active_only=True) or []
                        for env in envs:
                            if (env.platform or "") == "Win32" or "Windows NT" in (env.user_agent or ""):
                                browser_env = env
                                break
        except Exception:
            browser_env = None

        if not images:
            raise RuntimeError("发布失败：缺少图片（小红书图文发布需要图片）")

        poster = None
        poster_is_ephemeral = False
        try:
            target_uid = int(user_id) if user_id else None

            # 优先复用当前线程已登录的 poster，避免 persistent profile 目录被同时打开导致启动失败。
            if self.poster and getattr(self.poster, "user_id", None) == target_uid:
                poster = self.poster
            else:
                poster = XiaohongshuPoster(user_id=target_uid, browser_environment=browser_env)
                poster_is_ephemeral = True

            await poster.initialize()
            await poster.post_article(title, content, images, auto_publish=True)
            self.scheduled_task_result.emit(task_id, True, "")
        except Exception as e:
            self.scheduled_task_result.emit(task_id, False, str(e))
        finally:
            try:
                if poster and poster_is_ephemeral:
                    await poster.close(force=True)
            except Exception:
                pass

    @classmethod
    def _generate_images_for_text(cls, *, title: str, content: str, cover_template_id: str = "", page_count: int = 3):
        """为固定内容任务生成图片（优先系统模板，失败则回退占位图）。"""
        title = str(title or "").strip()
        content = str(content or "").strip()
        cover_template_id = str(cover_template_id or "").strip()
        try:
            page_count = int(page_count or 3)
        except Exception:
            page_count = 3
        page_count = max(1, page_count)

        images = []
        try:
            from pathlib import Path
            from src.core.services.system_image_template_service import system_image_template_service

            cover_bg = ""
            try:
                if cover_template_id:
                    showcase_dir = system_image_template_service.resolve_showcase_dir()
                    if showcase_dir:
                        candidate = Path(showcase_dir) / f"{cover_template_id}.png"
                        if candidate.exists():
                            cover_bg = str(candidate)
            except Exception:
                cover_bg = ""

            generated = system_image_template_service.generate_post_images(
                title=title or content or "标题",
                content=content or title or "内容",
                page_count=page_count,
                bg_image_path=cover_bg,
                cover_bg_image_path=cover_bg,
            )
            if generated:
                cover_path, content_paths = generated
                images = [cover_path] + list(content_paths or [])
        except Exception:
            images = []

        if not images:
            try:
                cover_path, content_paths = cls._generate_local_placeholder_images(title or content or "内容", count=max(2, page_count))
                images = [cover_path] + list(content_paths or [])
            except Exception:
                images = []

        return images

    @staticmethod
    def _fallback_generate_xhs_content(topic: str) -> dict:
        topic = str(topic or "").strip() or "这个话题"
        base = re.sub(r"\s+", "", topic)[:10] or "这个话题"

        title_templates = [
            f"{base}真的有用吗 先看这3点",
            f"{base}别再踩坑 这份清单够用",
            f"{base}新手必看 3步就能上手",
            f"{base}想提升 先把这件事做对",
            f"{base}怎么做更稳 关键在这里",
        ]
        title = random.choice(title_templates)[:20]
        if len(title) < 15:
            title = (title + "实用版").strip()[:20]

        tips = [
            f"先把结论说清楚：你为什么要关注「{topic}」",
            "不要一上来堆信息，先抓住最关键的 1-2 个点",
            "把能坚持的动作做成日常，比一次性爆发更有效",
        ]
        actions = [
            "今天就开始：写下你的现状和一个可执行的小目标",
            "用 7 天做一次复盘：哪里有效，哪里需要调整",
            "只保留最有效的 2 个习惯，其它先放一放",
        ]

        tags = [topic, "热点", "干货", "实用", "方法"]
        seen = set()
        uniq = []
        for t in tags:
            t = re.sub(r"\s+", "", str(t))
            if not t or t in seen:
                continue
            seen.add(t)
            uniq.append(t)
        uniq = uniq[:10]

        content = "\n\n".join(
            [
                f"今天刷到「{topic}」，我快速整理了一个更好上手的思路：",
                "先看重点：\n" + "\n".join([f"{i+1}. {x}" for i, x in enumerate(tips)]),
                "你可以这样做：\n" + "\n".join([f"{i+1}. {x}" for i, x in enumerate(actions)]),
                "话题标签：" + " ".join(uniq),
            ]
        ).strip()

        return {"title": title, "content": content}

    @staticmethod
    def _generate_local_placeholder_images(title: str, count: int = 3):
        try:
            from PIL import Image, ImageDraw, ImageFont
        except Exception as e:
            raise RuntimeError(f"Pillow 不可用: {e}")

        base_dir = os.path.join(os.path.expanduser("~"), ".xhs_system", "generated_imgs")
        os.makedirs(base_dir, exist_ok=True)

        def _make(path: str, label: str):
            width, height = 1080, 1440
            img = Image.new("RGB", (width, height), (245, 245, 245))
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.load_default()
            except Exception:
                font = None
            text = f"{label}\n{(title or '').strip()[:40]}"
            draw.multiline_text((60, 80), text, fill=(30, 30, 30), font=font, spacing=10)
            img.save(path, format="JPEG", quality=90)

        ts = int(time.time())
        unique = f"{ts}_{random.randint(1000, 9999)}"
        cover_path = os.path.join(base_dir, f"cover_{unique}.jpg")
        _make(cover_path, "封面")

        content_paths = []
        for i in range(max(1, int(count))):
            p = os.path.join(base_dir, f"content_{i+1}_{unique}.jpg")
            _make(p, f"内容图{i+1}")
            content_paths.append(p)

        return cover_path, content_paths

    @classmethod
    def _build_hotspot_payload_sync(cls, action: dict) -> dict:
        """生成热点定时任务的标题/内容/图片（同步，便于放入线程池执行）。"""
        source = str(action.get("hotspot_source") or "weibo").strip().lower() or "weibo"
        try:
            rank = int(action.get("hotspot_rank") or 1)
        except Exception:
            rank = 1
        rank = max(1, rank)

        use_ctx = bool(action.get("use_hotspot_context", True))
        cover_template_id = str(action.get("cover_template_id") or "").strip()
        try:
            page_count = int(action.get("page_count") or 3)
        except Exception:
            page_count = 3
        page_count = max(1, page_count)

        from src.config.config import Config
        from src.core.services.hotspot_service import hotspot_service

        items = hotspot_service.fetch(source, limit=max(50, rank))
        if not items:
            raise RuntimeError(f"热点抓取失败：{source} 无数据")
        item = items[rank - 1] if len(items) >= rank else items[0]
        topic = str(getattr(item, "title", "") or "").strip()
        if not topic:
            raise RuntimeError("热点抓取失败：标题为空")

        context_text = ""
        if use_ctx:
            try:
                snippets = hotspot_service.fetch_baidu_search_snippets(topic, limit=3, timeout=10)
                parts = []
                for s in snippets:
                    snip = str((s or {}).get("snippet") or "").strip()
                    if snip:
                        parts.append(snip)
                context_text = "\n".join(parts).strip()
            except Exception:
                context_text = ""

        cfg = Config()
        title_cfg = cfg.get_title_config() if hasattr(cfg, "get_title_config") else {}
        header_title = str((title_cfg or {}).get("title") or "").strip()
        author = str((title_cfg or {}).get("author") or "").strip()

        llm_topic = topic
        if context_text:
            llm_topic = f"{topic}\n\n参考信息（百度搜索摘要）：\n{context_text}".strip()

        generated_title = ""
        generated_content = ""
        try:
            from src.core.services.llm_service import llm_service

            resp = llm_service.generate_xiaohongshu_content(
                topic=llm_topic,
                header_title=header_title,
                author=author,
            )
            generated_title = str(getattr(resp, "title", "") or "").strip()
            generated_content = str(getattr(resp, "content", "") or "").strip()
        except Exception:
            fallback = cls._fallback_generate_xhs_content(topic)
            generated_title = str(fallback.get("title") or "").strip()
            generated_content = str(fallback.get("content") or "").strip()

        if not generated_title and not generated_content:
            raise RuntimeError("生成失败：标题/内容为空")

        # 生成图片：优先使用封面模板（含营销海报特殊逻辑），否则使用系统模板；最后回退本地占位图
        images = []
        if cover_template_id == "showcase_marketing_poster":
            try:
                from src.core.services.llm_service import llm_service
                from src.core.services.marketing_poster_service import marketing_poster_service

                poster_content = llm_service.generate_marketing_poster_content(topic=topic)
                try:
                    asset_path = str(Config().get_templates_config().get("marketing_poster_asset_path") or "").strip()
                except Exception:
                    asset_path = ""
                asset_path = os.path.expanduser(asset_path) if asset_path else ""
                if asset_path and os.path.exists(asset_path):
                    try:
                        poster_content["asset_image_path"] = asset_path
                    except Exception:
                        pass
                cover_path, content_paths = marketing_poster_service.generate_to_local_paths(poster_content)
                t = str((poster_content or {}).get("title") or "").strip()
                if t:
                    generated_title = t

                caption = str((poster_content or {}).get("caption") or "").strip()
                subtitle = str((poster_content or {}).get("subtitle") or "").strip()
                if caption or subtitle:
                    generated_content = caption or subtitle

                images = [cover_path] + list(content_paths or [])
            except Exception:
                images = []

        if not images:
            try:
                from pathlib import Path
                from src.core.services.system_image_template_service import system_image_template_service

                cover_bg = ""
                try:
                    if cover_template_id:
                        showcase_dir = system_image_template_service.resolve_showcase_dir()
                        if showcase_dir:
                            candidate = Path(showcase_dir) / f"{cover_template_id}.png"
                            if candidate.exists():
                                cover_bg = str(candidate)
                except Exception:
                    cover_bg = ""

                generated = system_image_template_service.generate_post_images(
                    title=generated_title or topic,
                    content=generated_content or topic,
                    page_count=page_count,
                    bg_image_path=cover_bg,
                    cover_bg_image_path=cover_bg,
                )
                if generated:
                    cover_path, content_paths = generated
                    images = [cover_path] + list(content_paths or [])
            except Exception:
                images = []

        if not images:
            cover_path, content_paths = cls._generate_local_placeholder_images(generated_title or topic, count=max(2, page_count))
            images = [cover_path] + list(content_paths or [])

        return {"title": generated_title, "content": generated_content, "images": images, "hotspot_title": topic, "hotspot_source": source, "hotspot_rank": rank}

    def stop(self):
        self.is_running = False
        # 确保浏览器资源被释放
        if self.poster and self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self.poster.close(force=True), self.loop)
