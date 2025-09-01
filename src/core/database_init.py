"""
数据库初始化脚本
用于创建表结构和初始化基础数据
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.config.database import DatabaseManager
from src.core.models import Base, User, ProxyConfig, BrowserFingerprint, BrowserEnvironment, ContentTemplate, PublishHistory, ScheduledTask
from src.core.services.browser_environment_service import browser_environment_service
from src.core.services.fingerprint_service import fingerprint_service


def init_database():
    """初始化数据库"""
    try:
        print("🚀 开始初始化数据库...")
        
        # 获取数据库管理器实例
        db_manager = DatabaseManager()
        
        # 创建所有表
        print("📋 创建数据库表...")
        Base.metadata.create_all(db_manager.engine)
        print("✅ 数据库表创建完成")
        
        # 创建默认用户
        create_default_user()
        
        print("🎉 数据库初始化完成！")
        return True
        
    except Exception as e:
        print(f"❌ 数据库初始化失败: {str(e)}")
        return False


def create_default_user():
    """创建默认用户"""
    try:
        print("👤 创建默认用户...")
        
        # 检查是否已存在用户
        db_manager = DatabaseManager()
        session = db_manager.get_session_direct()
        try:
            from src.core.models.user import User
            existing_users = session.query(User).all()
            if existing_users:
                print(f"ℹ️ 已存在 {len(existing_users)} 个用户，跳过默认用户创建")
                return
            
            # 创建默认用户
            default_user = User(
                username="default_user",
                phone="13800138000",
                display_name="默认用户"
            )
            session.add(default_user)
            session.commit()
            
            print(f"✅ 默认用户创建成功: {default_user.username}")
            
            # 为默认用户创建预设浏览器指纹
            create_default_fingerprints(default_user.id)
            
        finally:
            session.close()
        
    except Exception as e:
        print(f"❌ 创建默认用户失败: {str(e)}")


def create_default_fingerprints(user_id):
    """为用户创建默认浏览器指纹配置"""
    try:
        print("🔍 创建默认浏览器指纹配置...")
        
        # 创建预设指纹配置
        created_fingerprints = fingerprint_service.create_preset_fingerprints(user_id)
        
        print(f"✅ 创建了 {len(created_fingerprints)} 个默认浏览器指纹配置")
        
    except Exception as e:
        print(f"❌ 创建默认浏览器指纹配置失败: {str(e)}")


def reset_database():
    """重置数据库（删除所有表并重新创建）"""
    try:
        print("⚠️ 开始重置数据库...")
        
        # 获取数据库管理器实例
        db_manager = DatabaseManager()
        
        # 删除所有表
        print("🗑️ 删除现有数据库表...")
        Base.metadata.drop_all(db_manager.engine)
        print("✅ 现有表删除完成")
        
        # 重新初始化
        return init_database()
        
    except Exception as e:
        print(f"❌ 数据库重置失败: {str(e)}")
        return False


def check_database_status():
    """检查数据库状态"""
    try:
        print("🔍 检查数据库状态...")
        
        db_manager = DatabaseManager()
        
        # 检查表是否存在
        session = db_manager.get_session_direct()
        try:
            # 检查用户表
            result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = [row[0] for row in result.fetchall()]
            
            print(f"📋 数据库中的表: {', '.join(tables)}")
            
            # 检查用户数量
            if 'users' in tables:
                result = session.execute(text("SELECT COUNT(*) FROM users"))
                user_count = result.scalar()
                print(f"👤 用户数量: {user_count}")
                
                # 检查第一个用户
                if user_count > 0:
                    from src.core.models.user import User
                    first_user = session.query(User).first()
                    print(f"🟢 当前用户: {first_user.username}")
                else:
                    print("⚪ 无当前用户")
            
            # 检查代理配置数量
            if 'proxy_configs' in tables:
                result = session.execute(text("SELECT COUNT(*) FROM proxy_configs"))
                proxy_count = result.scalar()
                print(f"🌐 代理配置数量: {proxy_count}")
            
            # 检查浏览器指纹数量
            if 'browser_fingerprints' in tables:
                result = session.execute(text("SELECT COUNT(*) FROM browser_fingerprints"))
                fingerprint_count = result.scalar()
                print(f"🔍 浏览器指纹数量: {fingerprint_count}")
        finally:
            session.close()
        
        print("✅ 数据库状态检查完成")
        return True
        
    except Exception as e:
        print(f"❌ 数据库状态检查失败: {str(e)}")
        return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="数据库管理工具")
    parser.add_argument('action', choices=['init', 'reset', 'status'], 
                       help='操作类型: init=初始化, reset=重置, status=检查状态')
    
    args = parser.parse_args()
    
    if args.action == 'init':
        success = init_database()
    elif args.action == 'reset':
        success = reset_database()
    elif args.action == 'status':
        success = check_database_status()
    else:
        print("❌ 未知操作类型")
        success = False
    
    if success:
        print("🎉 操作完成！")
        sys.exit(0)
    else:
        print("❌ 操作失败！")
        sys.exit(1)


if __name__ == "__main__":
    main()