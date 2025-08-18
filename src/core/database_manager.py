#!/usr/bin/env python3
"""
数据库管理器
集成数据库初始化、修复、健康检查功能
"""

import os
import sqlite3
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime


class DatabaseManager:
    """数据库管理器类"""
    
    def __init__(self):
        # 获取用户主目录
        self.home_dir = os.path.expanduser('~')
        # 创建应用配置目录
        self.app_config_dir = os.path.join(self.home_dir, '.xhs_system')
        # 数据库文件路径
        self.db_path = os.path.join(self.app_config_dir, 'xhs_data.db')
        # 备份目录
        self.backup_dir = os.path.join(self.app_config_dir, 'backups')
        
        # 确保目录存在
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保必要的目录存在"""
        for directory in [self.app_config_dir, self.backup_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
                print(f"✅ 创建目录: {directory}")
    
    def init_database(self, force_recreate: bool = False) -> bool:
        """
        初始化数据库
        
        Args:
            force_recreate: 是否强制重新创建数据库
            
        Returns:
            bool: 初始化是否成功
        """
        try:
            print("🚀 开始初始化数据库...")
            
            # 如果强制重新创建，先备份并删除原数据库
            if force_recreate and os.path.exists(self.db_path):
                self._backup_database()
                os.remove(self.db_path)
                print("🗑️ 已删除原数据库文件")
            
            print(f"📁 数据库路径: {self.db_path}")
            
            # 检查数据库文件是否存在
            db_exists = os.path.exists(self.db_path)
            
            # 创建数据库连接
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建所有表
            self._create_tables(cursor)
            
            # 提交更改
            conn.commit()
            print("✅ 数据库表创建完成")
            
            # 检查是否需要创建默认数据
            if not db_exists or force_recreate:
                self._create_default_data(cursor)
                conn.commit()
            
            # 检查数据库状态
            self._check_database_status(cursor)
            
            conn.close()
            print("🎉 数据库初始化完成！")
            return True
            
        except Exception as e:
            print(f"❌ 数据库初始化失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _create_tables(self, cursor):
        """创建数据库表"""
        
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
                title TEXT,
                content TEXT,
                tags TEXT,
                category TEXT,
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
                template_id INTEGER,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                platform TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                publish_url TEXT,
                error_message TEXT,
                publish_time TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (template_id) REFERENCES content_templates (id) ON DELETE SET NULL
            )
        ''')
        
        # 创建定时任务表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                template_id INTEGER,
                name TEXT NOT NULL,
                platform TEXT NOT NULL,
                schedule_type TEXT DEFAULT 'once',
                schedule_time TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                last_run_time TIMESTAMP,
                next_run_time TIMESTAMP,
                run_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (template_id) REFERENCES content_templates (id) ON DELETE SET NULL
            )
        ''')
    
    def _create_default_data(self, cursor):
        """创建默认数据"""
        # 检查是否已有用户
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
                INSERT INTO browser_fingerprints (user_id, name, platform, viewport_width, viewport_height, timezone, locale, is_default)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, '默认指纹', 'Win32', 1920, 1080, 'Asia/Shanghai', 'zh-CN', True))
            
            # 为默认用户创建预设代理配置
            print("🌐 创建默认代理配置...")
            cursor.execute('''
                INSERT INTO proxy_configs (user_id, name, proxy_type, host, port, is_default, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, '直连', 'direct', '127.0.0.1', 0, True, True))
            
            print(f"✅ 默认用户和配置创建完成，用户ID: {user_id}")
        else:
            print(f"ℹ️ 已存在 {user_count} 个用户，跳过默认用户创建")
    
    def _check_database_status(self, cursor):
        """检查数据库状态"""
        # 检查表结构
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"📋 数据库中的表: {', '.join(tables)}")
        
        # 检查各表的数据量
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  - {table}: {count} 条记录")
    
    def check_database_health(self) -> Dict[str, Any]:
        """
        检查数据库健康状态
        
        Returns:
            Dict[str, Any]: 健康检查结果
        """
        result = {
            'healthy': True,
            'issues': [],
            'stats': {},
            'recommendations': []
        }
        
        try:
            if not os.path.exists(self.db_path):
                result['healthy'] = False
                result['issues'].append("数据库文件不存在")
                result['recommendations'].append("运行数据库初始化")
                return result
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查表结构
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            expected_tables = [
                'users', 'proxy_configs', 'browser_fingerprints', 
                'content_templates', 'publish_history', 'scheduled_tasks'
            ]
            
            missing_tables = set(expected_tables) - set(tables)
            if missing_tables:
                result['healthy'] = False
                result['issues'].append(f"缺少表: {', '.join(missing_tables)}")
                result['recommendations'].append("重新初始化数据库")
            
            # 检查数据完整性
            if 'users' in tables:
                # 检查空用户数据
                cursor.execute("SELECT COUNT(*) FROM users WHERE username = '' OR phone = ''")
                empty_users = cursor.fetchone()[0]
                if empty_users > 0:
                    result['healthy'] = False
                    result['issues'].append(f"发现 {empty_users} 条空用户数据")
                    result['recommendations'].append("运行数据库修复")
                
                # 检查当前用户
                cursor.execute("SELECT COUNT(*) FROM users WHERE is_current = 1")
                current_users = cursor.fetchone()[0]
                if current_users == 0:
                    result['issues'].append("没有设置当前用户")
                    result['recommendations'].append("设置默认当前用户")
                elif current_users > 1:
                    result['issues'].append(f"存在 {current_users} 个当前用户")
                    result['recommendations'].append("修复多个当前用户问题")
            
            # 收集统计信息
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                result['stats'][table] = count
            
            conn.close()
            
        except Exception as e:
            result['healthy'] = False
            result['issues'].append(f"数据库检查失败: {str(e)}")
            result['recommendations'].append("检查数据库文件权限或重新初始化")
        
        return result
    
    def fix_database(self) -> bool:
        """
        修复数据库问题
        
        Returns:
            bool: 修复是否成功
        """
        try:
            print("🔧 开始修复数据库...")
            
            if not os.path.exists(self.db_path):
                print(f"❌ 数据库文件不存在: {self.db_path}")
                print("💡 建议运行数据库初始化")
                return False
            
            # 备份数据库
            self._backup_database()
            
            # 连接数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 修复损坏的用户数据
            print("\n🔍 检查损坏的用户数据...")
            cursor.execute("SELECT * FROM users WHERE username = '' OR phone = ''")
            damaged_users = cursor.fetchall()
            
            if damaged_users:
                print(f"⚠️ 发现 {len(damaged_users)} 条损坏的用户数据")
                cursor.execute("DELETE FROM users WHERE username = '' OR phone = ''")
                deleted_count = cursor.rowcount
                print(f"✅ 删除了 {deleted_count} 条损坏的用户记录")
            else:
                print("✅ 没有发现损坏的用户数据")
            
            # 修复当前用户设置
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_current = 1")
            current_users = cursor.fetchone()[0]
            
            if current_users == 0:
                print("🔧 设置默认当前用户...")
                cursor.execute("UPDATE users SET is_current = 1 WHERE username = 'default_user' LIMIT 1")
                if cursor.rowcount == 0:
                    # 如果没有默认用户，设置第一个活跃用户为当前用户
                    cursor.execute("UPDATE users SET is_current = 1 WHERE is_active = 1 LIMIT 1")
                print("✅ 已设置当前用户")
            elif current_users > 1:
                print("🔧 修复多个当前用户问题...")
                cursor.execute("UPDATE users SET is_current = 0")
                cursor.execute("UPDATE users SET is_current = 1 WHERE username = 'default_user' LIMIT 1")
                if cursor.rowcount == 0:
                    cursor.execute("UPDATE users SET is_current = 1 WHERE is_active = 1 LIMIT 1")
                print("✅ 已修复多个当前用户问题")
            
            # 清理孤立的配置数据
            print("\n🔍 清理孤立的配置数据...")
            
            # 删除没有对应用户的代理配置
            cursor.execute("""
                DELETE FROM proxy_configs 
                WHERE user_id NOT IN (SELECT id FROM users)
            """)
            proxy_deleted = cursor.rowcount
            if proxy_deleted > 0:
                print(f"🗑️ 删除了 {proxy_deleted} 条孤立的代理配置")
            
            # 删除没有对应用户的浏览器指纹
            cursor.execute("""
                DELETE FROM browser_fingerprints 
                WHERE user_id NOT IN (SELECT id FROM users)
            """)
            fp_deleted = cursor.rowcount
            if fp_deleted > 0:
                print(f"🗑️ 删除了 {fp_deleted} 条孤立的浏览器指纹")
            
            # 提交更改
            conn.commit()
            
            # 显示修复后的状态
            print("\n📊 修复后的数据库状态:")
            self._check_database_status(cursor)
            
            conn.close()
            print("\n🎉 数据库修复完成！")
            return True
            
        except Exception as e:
            print(f"❌ 修复数据库失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _backup_database(self) -> str:
        """
        备份数据库
        
        Returns:
            str: 备份文件路径
        """
        if not os.path.exists(self.db_path):
            return ""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"xhs_data_backup_{timestamp}.db"
        backup_path = os.path.join(self.backup_dir, backup_filename)
        
        shutil.copy2(self.db_path, backup_path)
        print(f"📋 已备份数据库到: {backup_path}")
        
        # 清理旧备份（保留最近10个）
        self._cleanup_old_backups()
        
        return backup_path
    
    def _cleanup_old_backups(self):
        """清理旧的备份文件"""
        try:
            backups = []
            for filename in os.listdir(self.backup_dir):
                if filename.startswith("xhs_data_backup_") and filename.endswith(".db"):
                    filepath = os.path.join(self.backup_dir, filename)
                    mtime = os.path.getmtime(filepath)
                    backups.append((mtime, filepath))
            
            # 按修改时间排序，保留最新的10个
            backups.sort(reverse=True)
            for _, filepath in backups[10:]:
                os.remove(filepath)
                print(f"🗑️ 删除旧备份: {os.path.basename(filepath)}")
        except Exception as e:
            print(f"⚠️ 清理备份文件时出错: {str(e)}")
    
    def get_database_info(self) -> Dict[str, Any]:
        """
        获取数据库信息
        
        Returns:
            Dict[str, Any]: 数据库信息
        """
        info = {
            'db_path': self.db_path,
            'backup_dir': self.backup_dir,
            'exists': os.path.exists(self.db_path),
            'size': 0,
            'tables': [],
            'health': None
        }
        
        if info['exists']:
            info['size'] = os.path.getsize(self.db_path)
            
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                info['tables'] = [row[0] for row in cursor.fetchall()]
                
                conn.close()
            except Exception as e:
                info['error'] = str(e)
        
        info['health'] = self.check_database_health()
        
        return info
    
    def ensure_database_ready(self) -> bool:
        """
        确保数据库已准备就绪
        如果有问题会自动尝试修复
        
        Returns:
            bool: 数据库是否就绪
        """
        print("🔍 检查数据库状态...")
        
        # 检查数据库健康状态
        health = self.check_database_health()
        
        if health['healthy']:
            print("✅ 数据库状态正常")
            return True
        
        print("⚠️ 发现数据库问题:")
        for issue in health['issues']:
            print(f"  - {issue}")
        
        # 尝试修复
        if not os.path.exists(self.db_path):
            print("🚀 数据库不存在，开始初始化...")
            return self.init_database()
        else:
            print("🔧 尝试修复数据库...")
            if self.fix_database():
                # 修复后再次检查
                health = self.check_database_health()
                if health['healthy']:
                    print("✅ 数据库修复成功")
                    return True
                else:
                    print("❌ 数据库修复后仍有问题，尝试重新初始化...")
                    return self.init_database(force_recreate=True)
            else:
                print("❌ 数据库修复失败，尝试重新初始化...")
                return self.init_database(force_recreate=True)


# 全局数据库管理器实例
database_manager = DatabaseManager()