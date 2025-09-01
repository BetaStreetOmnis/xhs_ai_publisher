import requests
import json
import time
from typing import Dict, Optional, List

class QwenAdapter:
    """通义千问AI图片生成适配器"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://dashscope.aliyuncs.com/api/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def generate_image(self, prompt: str, model: str = "wanx-v1", 
                      size: str = "1024*1024", style: str = "\u7efc\u5408") -> Optional[Dict]:
        """生成图片"""
        try:
            url = f"{self.base_url}/services/aigc/text2image/image-synthesis"
            
            payload = {
                "model": model,
                "input": {
                    "prompt": prompt,
                    "negative_prompt": "低质量，模糊，失真"
                },
                "parameters": {
                    "size": size,
                    "style": style,
                    "n": 1
                }
            }
            
            response = requests.post(url, headers=self.headers, json=payload, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                task_id = result.get("output", {}).get("task_id")
                
                if task_id:
                    return self._poll_task_result(task_id)
                else:
                    return {"success": False, "error": "无效的任务ID"}
            else:
                return {
                    "success": False, 
                    "error": f"API错误: {response.status_code} - {response.text}"
                }
                
        except requests.exceptions.Timeout:
            return {"success": False, "error": "请求超时"}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"网络错误: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"未知错误: {str(e)}"}
    
    def _poll_task_result(self, task_id: str, max_wait: int = 60) -> Dict:
        """轮询任务结果"""
        url = f"{self.base_url}/tasks/{task_id}"
        
        for i in range(max_wait):
            try:
                response = requests.get(url, headers=self.headers, timeout=10)
                
                if response.status_code == 200:
                    result = response.json()
                    status = result.get("output", {}).get("task_status")
                    
                    if status == "SUCCEEDED":
                        image_url = result.get("output", {}).get("results", [{}])[0].get("url")
                        return {"success": True, "url": image_url}
                    elif status == "FAILED":
                        return {"success": False, "error": "任务执行失败"}
                    elif status == "RUNNING":
                        time.sleep(2)
                        continue
                    else:
                        return {"success": False, "error": f"未知状态: {status}"}
                        
            except Exception as e:
                return {"success": False, "error": f"轮询失败: {str(e)}"}
        
        return {"success": False, "error": "任务超时"}
    
    def get_balance(self) -> Optional[Dict]:
        """查询API余额"""
        try:
            url = f"{self.base_url}/billing/balance"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "balance": data.get("data", {}).get("balance", 0),
                    "currency": "CNY"
                }
            else:
                return {"success": False, "error": "无法获取余额信息"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def validate_key(self) -> bool:
        """验证API密钥有效性"""
        try:
            balance_result = self.get_balance()
            return balance_result.get("success", False)
        except Exception:
            return False
    
    def get_usage_statistics(self) -> Optional[Dict]:
        """获取使用统计"""
        try:
            url = f"{self.base_url}/billing/usage"
            params = {"start_time": int(time.time()) - 86400, "end_time": int(time.time())}
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None
    
    def build_xiaohongshu_prompt(self, content_type: str, title: str, 
                                style: str = "cute", keywords: List[str] = None) -> str:
        """构建小红书专用提示词"""
        style_mapping = {
            "cute": "\u53ef\u7231\u98ce",
            "clean": "\u7b80\u7ea6\u98ce", 
            "professional": "\u4e13\u4e1a\u98ce",
            "trendy": "\u6f6e\u6d41\u98ce"
        }
        
        if content_type == "cover":
            prompt = f"小红书封面图，标题\"{title}\"，{style_mapping.get(style, '简约')}，竖版9:16，高清"
        else:
            prompt = f"小红书内容页，{title}，{style_mapping.get(style, '简约')}排版，清晰易读，竖版"
        
        if keywords:
            prompt += f"，包含{', '.join(keywords)}"
        
        return prompt