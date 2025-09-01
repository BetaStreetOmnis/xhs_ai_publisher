#!/usr/bin/env python3
"""
模板管理器
负责加载和管理所有封面模板
"""

import os
import json
from typing import Dict, List, Optional

class TemplateManager:
    """模板管理器"""
    
    def __init__(self):
        self.templates = {}
        self.categories = {}
        self.load_templates()
    
    def load_templates(self):
        """加载所有模板"""
        # 加载内置模板库
        template_file = os.path.join("templates", "cover_templates_library.json")
        if os.path.exists(template_file):
            with open(template_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.templates = {t["id"]: t for t in data["templates"]}
                self.categories = data.get("categories", {})
    
    def get_templates_by_category(self, category: str = None) -> List[Dict]:
        """按类别获取模板"""
        if category is None or category == "全部":
            return list(self.templates.values())
        
        template_ids = self.categories.get(category, [])
        return [self.templates[tid] for tid in template_ids if tid in self.templates]
    
    def get_template(self, template_id: str) -> Optional[Dict]:
        """获取单个模板"""
        return self.templates.get(template_id)
    
    def get_categories(self) -> List[str]:
        """获取所有类别"""
        return list(self.categories.keys())
    
    def search_templates(self, keyword: str) -> List[Dict]:
        """搜索模板"""
        keyword = keyword.lower()
        results = []
        
        for template in self.templates.values():
            if (keyword in template.get("name", "").lower() or
                keyword in template.get("category", "").lower()):
                results.append(template)
        
        return results
    
    def get_template_preview(self, template_id: str) -> Dict:
        """获取模板预览信息"""
        template = self.get_template(template_id)
        if template:
            return {
                "id": template_id,
                "name": template["name"],
                "category": template["category"],
                "preview": template.get("preview", ""),
                "config": template
            }
        return None

# 全局模板管理器实例
template_manager = TemplateManager()