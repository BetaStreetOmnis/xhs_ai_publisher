#!/usr/bin/env python3
"""
简单的数据库检查脚本
"""

import os
import sqlite3

def check_database():
    """检查数据库内容"""
    try:
        # 获取数据库路径
        home_dir = os.path.expanduser('~')
        app_config_dir = os.path.join(home_dir, '.xhs_system')
        db_path = os.path.join(app_config_dir, 'xhs_data.db')
        
        if not os.path.exists(db_path):
            print(f"❌ 数据库文件不存在: {db_path}")
            return
        
        print(f"📁 数据库路径: {db_path}")
        
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查用户表
        print("\n👤 用户表内容:")
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
        for user in users:
            print(f"  {user}")
        
        # 检查代理配置表
        print("\n🌐 代理配置表内容:")
        cursor.execute("SELECT * FROM proxy_configs")
        proxies = cursor.fetchall()
        for proxy in proxies:
            print(f"  {proxy}")
        
        # 检查浏览器指纹表
        print("\n🔍 浏览器指纹表内容:")
        cursor.execute("SELECT * FROM browser_fingerprints")
        fingerprints = cursor.fetchall()
        for fp in fingerprints:
            print(f"  {fp}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 检查数据库失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_database() 