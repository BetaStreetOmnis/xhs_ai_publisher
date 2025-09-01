import requests
import json
import time
from typing import Dict, Optional, List

class KimiAdapter:
    """Kimi AI图片生成适配器"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.moonshot.cn/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def generate_image(self, prompt: str, model: str = "kimi-image", 
                      size: str = "1024x1024", quality: str = "standard") -> Optional[Dict]:
        """生成图片"""
        try:
            url = f"{self.base_url}/images/generations"
            
            payload = {
                "model": model,
                "prompt": prompt,
                "n": 1,
                "size": size,
                "quality": quality,
                "response_format": "url"
            }
            
            response = requests.post(url, headers=self.headers, json=payload, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "url": result["data"][0]["url"],
                    "revised_prompt": result["data"][0].get("revised_prompt", "")
                }
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
    
    def get_balance(self) -> Optional[Dict]:
        """查询API余额"""
        try:
            url = f"{self.base_url}/users/me"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "balance": data.get("balance", 0),
                    "currency": data.get("currency", "CNY")
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
    
    def get_usage(self) -> Optional[Dict]:
        """获取使用量信息"""
        try:
            url = f"{self.base_url}/usage"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None
    
    def build_xiaohongshu_prompt(self, content_type: str, title: str, 
                                style: str = "cute", keywords: List[str] = None) -> str:
        """构建小红书专用提示词"""
        base_prompts = {
            "cover": {
                "cute": f"小红书风格封面图，标题\"{title}\"，可爱少女风，马卡龙色调，精致排版，高清",
                "clean": f"小红书封面图，标题\"{title}\"，简约现代风，留白设计，高级感，高清",
                "professional": f"小红书封面图，标题\"{title}\"，商务专业风，深色系，精致，高清",
                "trendy": f"小红书封面图，标题\"{title}\"，时尚潮流风，流行配色，ins风，高清"
            },
            "content": {
                "cute": f"小红书内容页，{title}，可爱插画风格，粉色系，少女向，清晰易读，竖版",
                "clean": f"小红书内容页，{title}，简约排版，留白设计，现代感，清晰易读，竖版",
                "professional": f"小红书内容页，{title}，商务风格，深色系，专业感，清晰易读，竖版",
                "trendy": f"小红书内容页，{title}，时尚潮流，流行元素，ins风，清晰易读，竖版"
            }
        }
        
        prompt = base_prompts.get(content_type, {}).get(style, "")
        if keywords:
            prompt += f"，关键词：{', '.join(keywords)}"
        
        return prompt