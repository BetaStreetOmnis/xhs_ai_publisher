#!/usr/bin/env python3
"""
修复数据库中的损坏数据
"""

import os
import sqlite3

def fix_database():
    """修复数据库中的损坏数据"""
    try:
        print("🔧 开始修复数据库...")
        
        # 获取数据库路径
        home_dir = os.path.expanduser('~')
        app_config_dir = os.path.join(home_dir, '.xhs_system')
        db_path = os.path.join(app_config_dir, 'xhs_data.db')
        
        if not os.path.exists(db_path):
            print(f"❌ 数据库文件不存在: {db_path}")
            return False
        
        print(f"📁 数据库路径: {db_path}")
        
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查并删除损坏的用户数据
        print("\n🔍 检查损坏的用户数据...")
        cursor.execute("SELECT * FROM users WHERE username = '' OR phone = ''")
        damaged_users = cursor.fetchall()
        
        if damaged_users:
            print(f"⚠️ 发现 {len(damaged_users)} 条损坏的用户数据:")
            for user in damaged_users:
                print(f"  - ID: {user[0]}, 用户名: '{user[1]}', 手机: '{user[2]}', 显示名: '{user[3]}'")
            
            # 删除损坏的用户数据
            print("🗑️ 删除损坏的用户数据...")
            cursor.execute("DELETE FROM users WHERE username = '' OR phone = ''")
            deleted_count = cursor.rowcount
            print(f"✅ 删除了 {deleted_count} 条损坏的用户记录")
            
            # 重新设置默认用户为当前用户
            cursor.execute("UPDATE users SET is_current = 1 WHERE username = 'default_user'")
            print("✅ 重新设置默认用户为当前用户")
        else:
            print("✅ 没有发现损坏的用户数据")
        
        # 检查并删除孤立的配置数据
        print("\n🔍 检查孤立的配置数据...")
        
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
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"  - 用户数量: {user_count}")
        
        cursor.execute("SELECT COUNT(*) FROM proxy_configs")
        proxy_count = cursor.fetchone()[0]
        print(f"  - 代理配置数量: {proxy_count}")
        
        cursor.execute("SELECT COUNT(*) FROM browser_fingerprints")
        fp_count = cursor.fetchone()[0]
        print(f"  - 浏览器指纹数量: {fp_count}")
        
        # 显示当前用户
        cursor.execute("SELECT * FROM users WHERE is_current = 1")
        current_user = cursor.fetchone()
        if current_user:
            print(f"  - 当前用户: {current_user[1]} ({current_user[3] or current_user[1]})")
        else:
            print("  - 当前用户: 无")
        
        conn.close()
        print("\n🎉 数据库修复完成！")
        return True
        
    except Exception as e:
        print(f"❌ 修复数据库失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def reset_database():
    """重置数据库（删除所有数据并重新创建）"""
    try:
        print("⚠️ 开始重置数据库...")
        
        # 获取数据库路径
        home_dir = os.path.expanduser('~')
        app_config_dir = os.path.join(home_dir, '.xhs_system')
        db_path = os.path.join(app_config_dir, 'xhs_data.db')
        
        if os.path.exists(db_path):
            # 备份原数据库
            backup_path = db_path + '.backup'
            import shutil
            shutil.copy2(db_path, backup_path)
            print(f"📋 已备份原数据库到: {backup_path}")
            
            # 删除原数据库
            os.remove(db_path)
            print("🗑️ 已删除原数据库文件")
        
        # 重新初始化数据库
        print("🔄 重新初始化数据库...")
        from init_db import init_database
        success = init_database()
        
        if success:
            print("🎉 数据库重置完成！")
            return True
        else:
            print("❌ 数据库重置失败！")
            return False
            
    except Exception as e:
        print(f"❌ 重置数据库失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "reset":
        reset_database()
    else:
        fix_database() 