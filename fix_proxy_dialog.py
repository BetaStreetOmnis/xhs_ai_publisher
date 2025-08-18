#!/usr/bin/env python3
"""
修复ProxyDialog中的无效代码
"""

import re

# 读取文件
with open('src/core/pages/user_management.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 删除无效的return语句
pattern = r'        return \{\s*.*?\s*\} \s*$'
content = re.sub(pattern, '', content, flags=re.DOTALL)

# 写回文件
with open('src/core/pages/user_management.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 已修复ProxyDialog中的无效代码") 