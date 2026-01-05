"""
热点数据采集服务

用于从公开接口采集热点榜单数据，并提供简单的本地缓存。
"""

from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
from urllib.parse import quote

import requests


@dataclass(frozen=True)
class HotspotItem:
    source: str
    rank: int
    title: str
    hot: Optional[int]
    url: str


class HotspotServiceError(RuntimeError):
    pass


class HotspotService:
    def __init__(self):
        self._cache_path = Path(os.path.expanduser("~")) / ".xhs_system" / "hotspots_cache.json"

    @staticmethod
    def available_sources() -> Dict[str, str]:
        return {
            "weibo": "微博热搜",
            "baidu": "百度热榜",
            "toutiao": "头条热榜",
            "bilibili": "B站热门",
        }

    @staticmethod
    def _http_get_json(url: str, timeout: int = 10, headers: Optional[dict] = None):
        try:
            resp = requests.get(url, timeout=timeout, headers=headers or {"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            raise HotspotServiceError(f"请求失败: {e}")

    def fetch_weibo_hot(self, limit: int = 50) -> List[HotspotItem]:
        url = "https://weibo.com/ajax/side/hotSearch"
        data = self._http_get_json(url, timeout=10, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://weibo.com/"})

        items: List[HotspotItem] = []
        realtime = ((data or {}).get("data") or {}).get("realtime") or []
        for i, it in enumerate(realtime[: max(1, int(limit))]):
            word = str((it or {}).get("word") or "").strip()
            if not word:
                continue
            hot = (it or {}).get("num")
            try:
                hot_val = int(hot) if hot is not None and str(hot).isdigit() else None
            except Exception:
                hot_val = None

            scheme = str((it or {}).get("word_scheme") or "").strip()
            q = scheme if scheme else word
            search_url = f"https://s.weibo.com/weibo?q={quote(q)}"
            items.append(HotspotItem(source="weibo", rank=i + 1, title=word, hot=hot_val, url=search_url))
        return items

    def fetch_baidu_hot(self, limit: int = 50) -> List[HotspotItem]:
        url = "https://top.baidu.com/api/board?platform=wise&tab=realtime"
        data = self._http_get_json(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})

        items: List[HotspotItem] = []
        cards = ((data or {}).get("data") or {}).get("cards") or []
        for card in cards:
            groups = (card or {}).get("content") or []
            for group in groups:
                for it in (group or {}).get("content") or []:
                    word = str((it or {}).get("word") or "").strip()
                    link = str((it or {}).get("url") or "").strip()
                    if not word:
                        continue
                    items.append(HotspotItem(source="baidu", rank=len(items) + 1, title=word, hot=None, url=link))
                    if len(items) >= max(1, int(limit)):
                        return items
        return items

    def fetch_toutiao_hot(self, limit: int = 50) -> List[HotspotItem]:
        url = "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc"
        data = self._http_get_json(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})

        items: List[HotspotItem] = []
        for it in (data or {}).get("data") or []:
            title = str((it or {}).get("Title") or "").strip()
            link = str((it or {}).get("Url") or "").strip()
            hot_raw = str((it or {}).get("HotValue") or "").strip()
            hot_val: Optional[int]
            try:
                hot_val = int(hot_raw) if hot_raw.isdigit() else None
            except Exception:
                hot_val = None
            if not title:
                continue
            items.append(HotspotItem(source="toutiao", rank=len(items) + 1, title=title, hot=hot_val, url=link))
            if len(items) >= max(1, int(limit)):
                break
        return items

    def fetch_bilibili_hot(self, limit: int = 50) -> List[HotspotItem]:
        url = "https://api.bilibili.com/x/web-interface/popular?ps=50&pn=1"
        data = self._http_get_json(url, timeout=10, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com/"})
        if int((data or {}).get("code") or 0) != 0:
            raise HotspotServiceError(str((data or {}).get("message") or "B站接口返回异常"))

        items: List[HotspotItem] = []
        for it in ((data or {}).get("data") or {}).get("list") or []:
            title = str((it or {}).get("title") or "").strip()
            bvid = str((it or {}).get("bvid") or "").strip()
            if not title or not bvid:
                continue
            link = f"https://www.bilibili.com/video/{bvid}"
            items.append(HotspotItem(source="bilibili", rank=len(items) + 1, title=title, hot=None, url=link))
            if len(items) >= max(1, int(limit)):
                break
        return items

    def fetch(self, source: str, limit: int = 50) -> List[HotspotItem]:
        source = (source or "").strip().lower()
        if source == "weibo":
            return self.fetch_weibo_hot(limit=limit)
        if source == "baidu":
            return self.fetch_baidu_hot(limit=limit)
        if source == "toutiao":
            return self.fetch_toutiao_hot(limit=limit)
        if source == "bilibili":
            return self.fetch_bilibili_hot(limit=limit)
        raise HotspotServiceError(f"不支持的数据源: {source}")

    def fetch_many(self, sources: Sequence[str], limit: int = 50) -> Dict[str, List[HotspotItem]]:
        results: Dict[str, List[HotspotItem]] = {}
        for s in sources:
            try:
                results[s] = self.fetch(s, limit=limit)
            except Exception as e:
                results[s] = []
                # 保留错误信息给上层展示
                results[f"{s}__error"] = [HotspotItem(source=s, rank=0, title=str(e), hot=None, url="")]
        return results

    def fetch_baidu_search_snippets(self, query: str, limit: int = 3, timeout: int = 10) -> List[Dict[str, str]]:
        """使用百度移动搜索页抓取“热点内容摘要”（用于跨平台补全上下文）。"""

        query = (query or "").strip()
        if not query:
            return []

        url = f"https://m.baidu.com/s?word={quote(query)}"
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            resp = requests.get(url, timeout=timeout, headers=headers)
            resp.raise_for_status()
            html = resp.text or ""
        except Exception as e:
            raise HotspotServiceError(f"获取百度搜索摘要失败: {e}")

        class _Stop(Exception):
            pass

        class _Parser(HTMLParser):
            def __init__(self, want: int):
                super().__init__()
                self.want = max(1, int(want))
                self.in_result = False
                # 仅追踪 div 嵌套深度（HTML 中存在大量无闭合标签，避免计数失衡）
                self.depth = 0
                self.skip_depth = 0
                self.current: Dict[str, str] = {}
                self.text_nodes: List[str] = []
                self.items: List[Dict[str, str]] = []

            def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
                attr = dict(attrs)

                if self.in_result and tag in {"script", "style", "noscript"}:
                    self.skip_depth += 1

                if not self.in_result and tag == "div":
                    cls = str(attr.get("class") or "")
                    if "c-result" in cls and "result" in cls:
                        self.in_result = True
                        self.depth = 1
                        self.skip_depth = 0
                        self.current = {"title": "", "snippet": "", "url": ""}
                        self.text_nodes = []

                        data_log = attr.get("data-log") or ""
                        if data_log:
                            try:
                                data_log = unescape(str(data_log))
                                j = json.loads(data_log)
                                mu = str(j.get("mu") or "").strip()
                                if mu:
                                    self.current["url"] = mu
                            except Exception:
                                pass
                        return

                if self.in_result:
                    if tag == "div":
                        self.depth += 1
                    if tag == "a" and not self.current.get("url"):
                        href = str(attr.get("href") or "").strip()
                        if href and not href.startswith("javascript"):
                            self.current["url"] = href

            def handle_endtag(self, tag: str):
                if not self.in_result:
                    return

                if tag in {"script", "style", "noscript"} and self.skip_depth > 0:
                    self.skip_depth -= 1

                if tag != "div":
                    return

                self.depth -= 1
                if self.depth > 0:
                    return

                # finalize
                self.in_result = False
                self.depth = 0

                def _clean(s: str) -> str:
                    s = (s or "").strip()
                    s = " ".join(s.split())
                    return s

                blocks = [_clean(x) for x in self.text_nodes if _clean(x)]

                # pick title: first meaningful segment
                ban = {
                    "百度一下",
                    "相关搜索",
                    "大家还在搜",
                    "更多",
                    "展开",
                    "收起",
                    "百度",
                    "广告",
                }
                title = ""
                for t in blocks:
                    if not t or len(t) < 4:
                        continue
                    if t.isdigit():
                        continue
                    if t in ban:
                        continue
                    title = t
                    break

                if not title:
                    self.current = {}
                    self.text_nodes = []
                    return

                snippet_parts: List[str] = []
                for t in blocks:
                    if t == title:
                        continue
                    if t in ban:
                        continue
                    if len(t) <= 1:
                        continue
                    snippet_parts.append(t)
                    if len(" ".join(snippet_parts)) >= 240:
                        break

                snippet = _clean(" ".join(snippet_parts))
                if len(snippet) > 260:
                    snippet = snippet[:260].rstrip() + "…"

                out = {
                    "title": title,
                    "snippet": snippet,
                    "url": str(self.current.get("url") or "").strip(),
                }

                if out["title"]:
                    self.items.append(out)
                self.current = {}
                self.text_nodes = []

                if len(self.items) >= self.want:
                    raise _Stop()

            def handle_data(self, data: str):
                if not self.in_result:
                    return
                if self.skip_depth > 0:
                    return
                t = (data or "").strip()
                if not t:
                    return
                self.text_nodes.append(t)

        parser = _Parser(want=limit)
        try:
            parser.feed(html)
        except _Stop:
            pass
        except Exception:
            # ignore parsing errors; return best-effort
            pass

        # 过滤掉明显无效项（无链接且无摘要的）
        items = [x for x in parser.items if x.get("title")]
        return items[: max(1, int(limit))]

    def load_cache(self) -> Dict[str, dict]:
        try:
            if not self._cache_path.exists():
                return {}
            return json.loads(self._cache_path.read_text(encoding="utf-8")) or {}
        except Exception:
            return {}

    def save_cache(self, data: Dict[str, dict]) -> None:
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._cache_path.with_suffix(".tmp")
            payload = {"updated_at": int(time.time()), "data": data or {}}
            tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self._cache_path)
        except Exception:
            pass


hotspot_service = HotspotService()
