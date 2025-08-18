#!/usr/bin/env python3
"""
数据库初始化脚本
在应用启动时运行，确保数据库和表结构正确创建
"""

import os
import sys
import sqlite3
from pathlib import Path

def init_database():
    """初始化数据库"""
    try:
        print("🚀 开始初始化数据库...")
        
        # 获取用户主目录
        home_dir = os.path.expanduser('~')
        # 创建应用配置目录
        app_config_dir = os.path.join(home_dir, '.xhs_system')
        if not os.path.exists(app_config_dir):
            os.makedirs(app_config_dir)
            print(f"✅ 创建配置目录: {app_config_dir}")
        
        # 数据库文件路径
        db_path = os.path.join(app_config_dir, 'xhs_data.db')
        print(f"📁 数据库路径: {db_path}")
        
        # 检查数据库文件是否存在
        db_exists = os.path.exists(db_path)
        
        # 创建数据库连接
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 创建用户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                phone TEXT UNIQUE NOT NULL,
                display_name TEXT,
                is_active BOOLEAN DEFAULT 1,
                is_current BOOLEAN DEFAULT 0,
                is_logged_in BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login_at TIMESTAMP
            )
        ''')
        
        # 创建代理配置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS proxy_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                proxy_type TEXT NOT NULL,
                host TEXT NOT NULL,
                port INTEGER NOT NULL,
                username TEXT,
                password TEXT,
                is_active BOOLEAN DEFAULT 1,
                is_default BOOLEAN DEFAULT 0,
                test_url TEXT DEFAULT 'https://httpbin.org/ip',
                test_latency REAL,
                test_success BOOLEAN,
                last_test_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # 创建浏览器指纹表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS browser_fingerprints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                user_agent TEXT,
                viewport_width INTEGER DEFAULT 1920,
                viewport_height INTEGER DEFAULT 1080,
                screen_width INTEGER DEFAULT 1920,
                screen_height INTEGER DEFAULT 1080,
                platform TEXT,
                timezone TEXT DEFAULT 'Asia/Shanghai',
                locale TEXT DEFAULT 'zh-CN',
                webgl_vendor TEXT,
                webgl_renderer TEXT,
                canvas_fingerprint TEXT,
                webrtc_public_ip TEXT,
                webrtc_local_ip TEXT,
                fonts TEXT,
                plugins TEXT,
                is_active BOOLEAN DEFAULT 1,
                is_default BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # 创建内容模板表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS content_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                title_template TEXT,
                content_template TEXT,
                tags_template TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # 创建发布历史表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS publish_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT,
                content TEXT,
                tags TEXT,
                publish_status TEXT,
                publish_time TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # 创建定时任务表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT,
                tags TEXT,
                schedule_time TIMESTAMP NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # 提交更改
        conn.commit()
        print("✅ 数据库表创建完成")
        
        # 检查是否需要创建默认用户
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        if user_count == 0:
            print("👤 创建默认用户...")
            cursor.execute('''
                INSERT INTO users (username, phone, display_name, is_active, is_current, is_logged_in)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ('default_user', '13800138000', '默认用户', True, True, False))
            
            # 获取新创建的用户ID
            user_id = cursor.lastrowid
            
            # 为默认用户创建预设浏览器指纹
            print("🔍 创建默认浏览器指纹...")
            cursor.execute('''
                INSERT INTO browser_fingerprints (user_id, name, platform, viewport_width, viewport_height, timezone, locale)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, '默认指纹', 'Win32', 1920, 1080, 'Asia/Shanghai', 'zh-CN'))
            
            # 为默认用户创建预设代理配置
            print("🌐 创建默认代理配置...")
            cursor.execute('''
                INSERT INTO proxy_configs (user_id, name, proxy_type, host, port, is_default, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, '直连', 'http', '127.0.0.1', 0, True, True))
            
            conn.commit()
            print(f"✅ 默认用户和配置创建完成，用户ID: {user_id}")
        else:
            print(f"ℹ️ 已存在 {user_count} 个用户，跳过默认用户创建")
        
        # 检查表结构
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"📋 数据库中的表: {', '.join(tables)}")
        
        # 检查各表的数据量
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  - {table}: {count} 条记录")
        
        conn.close()
        print("🎉 数据库初始化完成！")
        return True
        
    except Exception as e:
        print(f"❌ 数据库初始化失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def check_database():
    """检查数据库状态"""
    try:
        home_dir = os.path.expanduser('~')
        app_config_dir = os.path.join(home_dir, '.xhs_system')
        db_path = os.path.join(app_config_dir, 'xhs_data.db')
        
        if not os.path.exists(db_path):
            print("❌ 数据库文件不存在")
            return False
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表结构
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"📋 数据库中的表: {', '.join(tables)}")
        
        # 检查各表的数据量
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  - {table}: {count} 条记录")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 数据库检查失败: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        check_database()
    else:
        init_database() 