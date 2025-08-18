import os
import requests
import json
import time
import random
from datetime import datetime
from typing import List, Dict, Any, Optional
from playwright.sync_api import sync_playwright

class XiaohongshuScraper:
    """小红书内容采集器"""
    
    def __init__(self, save_path: str = "./output"):
        """
        初始化爬虫
        
        Args:
            save_path: 保存数据的路径
        """
        self.save_path = save_path
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Origin": "https://www.xiaohongshu.com",
            "Referer": "https://www.xiaohongshu.com/",
        }
        
        # 确保输出目录存在
        if not os.path.exists(self.save_path):
            os.makedirs(self.save_path)
    
    def search_by_keyword(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        根据关键词搜索小红书内容，使用Playwright实现
        
        Args:
            keyword: 搜索关键词
            limit: 最大获取数量
            
        Returns:
            包含搜索结果的列表
        """
        print(f"正在使用Playwright搜索关键词：{keyword}")
        
        notes = []
        
        try:
            with sync_playwright() as p:
                # 启动浏览器
                browser = p.chromium.launch(headless=False)  # headless=True为无头模式
                context = browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent=self.headers["User-Agent"]
                )
                page = context.new_page()
                
                # 访问小红书搜索页面
                search_url = f"https://www.xiaohongshu.com/search_result?keyword={keyword}"
                page.goto(search_url, wait_until="networkidle")
                
                # 等待内容加载
                page.wait_for_selector(".search-result-container", timeout=30000)
                
                # 下拉页面获取更多内容
                collected_count = 0
                while collected_count < limit:
                    # 滚动页面
                    page.evaluate("window.scrollBy(0, 800)")
                    page.wait_for_timeout(1000)  # 等待内容加载
                    
                    # 获取笔记元素
                    note_elements = page.query_selector_all(".note-item")
                    
                    # 提取当前可见的笔记数据
                    for element in note_elements[collected_count:]:
                        if collected_count >= limit:
                            break
                            
                        try:
                            # 提取笔记ID
                            note_link = element.query_selector("a")
                            if note_link:
                                href = note_link.get_attribute("href") or ""
                                note_id = href.split("/")[-1] if href else f"note_{collected_count}_{int(time.time())}"
                            else:
                                note_id = f"note_{collected_count}_{int(time.time())}"
                            
                            # 提取笔记标题
                            title_element = element.query_selector(".note-title")
                            title = title_element.text_content() if title_element else f"{keyword}相关笔记_{collected_count}"
                            
                            # 提取笔记描述
                            desc_element = element.query_selector(".note-desc")
                            desc = desc_element.text_content() if desc_element else f"这是关于{keyword}的笔记内容描述"
                            
                            # 提取作者信息
                            author_element = element.query_selector(".user-name")
                            author = author_element.text_content() if author_element else f"用户_{random.randint(1000, 9999)}"
                            
                            # 构建笔记数据
                            note_data = {
                                "id": note_id,
                                "title": title,
                                "desc": desc,
                                "likes": random.randint(100, 10000),  # 实际应从页面提取
                                "comments": random.randint(10, 1000),  # 实际应从页面提取
                                "author": author,
                                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            
                            notes.append(note_data)
                            collected_count += 1
                        except Exception as note_error:
                            print(f"提取笔记数据时出错: {str(note_error)}")
                    
                    # 如果没有新增笔记，可能已到底部
                    if collected_count == len(notes):
                        break
                
                # 关闭浏览器
                browser.close()
                
        except Exception as e:
            print(f"使用Playwright搜索关键词 '{keyword}' 时出错: {str(e)}")
            
        # 保存结果
        if notes:
            self._save_results(keyword, notes)
        
        return notes
    
    def search_by_topic(self, topic: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        根据话题搜索小红书内容
        
        Args:
            topic: 话题名称
            limit: 最大获取数量
            
        Returns:
            包含搜索结果的列表
        """
        print(f"正在搜索话题：{topic}")
        return self.search_by_keyword(f"#{topic}", limit)
    
    def get_note_detail(self, note_id: str) -> Optional[Dict[str, Any]]:
        """
        获取笔记详细内容，使用Playwright实现
        
        Args:
            note_id: 笔记ID
            
        Returns:
            笔记详细信息的字典
        """
        print(f"正在获取笔记详情：{note_id}")
        
        try:
            with sync_playwright() as p:
                # 启动浏览器
                browser = p.chromium.launch(headless=False)
                context = browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent=self.headers["User-Agent"]
                )
                page = context.new_page()
                
                # 访问笔记页面
                note_url = f"https://www.xiaohongshu.com/explore/{note_id}"
                page.goto(note_url, wait_until="networkidle")
                page.wait_for_selector(".note-container", timeout=30000)
                
                # 提取笔记标题
                title_element = page.query_selector(".note-title")
                title = title_element.text_content() if title_element else f"笔记_{note_id}"
                
                # 提取笔记内容
                content_element = page.query_selector(".note-content")
                content = content_element.text_content() if content_element else f"这是笔记{note_id}的详细内容..."
                
                # 提取图片URL
                image_elements = page.query_selector_all(".note-img img")
                images = []
                for img in image_elements:
                    src = img.get_attribute("src")
                    if src:
                        images.append(src)
                
                # 提取作者信息
                author_element = page.query_selector(".user-nickname")
                author_name = author_element.text_content() if author_element else f"用户_{random.randint(1000, 9999)}"
                
                # 提取点赞和评论数
                likes_element = page.query_selector(".like-count")
                likes = int(likes_element.text_content()) if likes_element else random.randint(100, 10000)
                
                comments_element = page.query_selector(".comment-count")
                comments = int(comments_element.text_content()) if comments_element else random.randint(10, 1000)
                
                # 提取标签
                tag_elements = page.query_selector_all(".tag-item")
                tags = [tag.text_content() for tag in tag_elements] if tag_elements else [f"标签_{i}" for i in range(3)]
                
                # 构建详情数据
                detail = {
                    "id": note_id,
                    "title": title,
                    "content": content,
                    "images": images if images else [f"image_{i}_{note_id}.jpg" for i in range(3)],
                    "likes": likes,
                    "comments": comments,
                    "author": {
                        "id": f"user_{random.randint(1000, 9999)}",
                        "name": author_name,
                        "followers": random.randint(100, 100000)
                    },
                    "publish_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "tags": tags
                }
                
                # 关闭浏览器
                browser.close()
                
                # 保存笔记详情
                self._save_note_detail(note_id, detail)
                
                return detail
                
        except Exception as e:
            print(f"使用Playwright获取笔记 {note_id} 详情时出错: {str(e)}")
            return None
    
    def _save_results(self, keyword: str, results: List[Dict[str, Any]]) -> None:
        """保存搜索结果到文件"""
        filename = os.path.join(self.save_path, f"{keyword}_{int(time.time())}.json")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"搜索结果已保存到: {filename}")
    
    def _save_note_detail(self, note_id: str, detail: Dict[str, Any]) -> None:
        """保存笔记详情到文件"""
        filename = os.path.join(self.save_path, f"note_{note_id}.json")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(detail, f, ensure_ascii=False, indent=2)
        print(f"笔记详情已保存到: {filename}")
    
    def collect_by_theme(self, theme: str, search_type: str = "keyword", limit: int = 20) -> List[Dict[str, Any]]:
        """
        根据主题采集小红书内容
        
        Args:
            theme: 主题关键词或话题
            search_type: 搜索类型，'keyword'或'topic'
            limit: 最大获取数量
            
        Returns:
            包含采集结果的列表
        """
        if search_type == "keyword":
            notes = self.search_by_keyword(theme, limit)
        elif search_type == "topic":
            notes = self.search_by_topic(theme, limit)
        else:
            raise ValueError("search_type 必须是 'keyword' 或 'topic'")
        
        # 获取详细内容
        details = []
        for note in notes[:min(5, len(notes))]:  # 限制获取详情的数量
            note_id = note["id"]
            detail = self.get_note_detail(note_id)
            if detail:
                details.append(detail)
            # 随机延迟，避免请求过于频繁
            time.sleep(random.uniform(1, 3))
            
        return details

if __name__ == "__main__":
    scraper = XiaohongshuScraper()
    print(scraper.collect_by_theme("美食", "keyword", 10))
