import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from typing import Generator

# 数据库基类
Base = declarative_base()

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        # 获取用户主目录
        home_dir = os.path.expanduser('~')
        # 创建应用配置目录
        app_config_dir = os.path.join(home_dir, '.xhs_system')
        if not os.path.exists(app_config_dir):
            os.makedirs(app_config_dir)
        
        # 数据库文件路径
        self.db_path = os.path.join(app_config_dir, 'xhs_data.db')
        
        # 创建数据库引擎
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            poolclass=StaticPool,
            connect_args={
                "check_same_thread": False,
                "timeout": 30
            },
            echo=False  # 设置为True可以看到SQL语句
        )
        
        # 创建会话工厂
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        # 创建所有表
        self.create_tables()
    
    def create_tables(self):
        """创建数据库表"""
        try:
            Base.metadata.create_all(bind=self.engine)
            print("数据库表创建成功")
        except Exception as e:
            print(f"创建数据库表失败: {str(e)}")
    
    def get_session(self) -> Generator:
        """获取数据库会话"""
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()
    
    def get_session_direct(self):
        """直接获取数据库会话（需要手动关闭）"""
        return self.SessionLocal()

# 全局数据库管理器实例
db_manager = DatabaseManager()

# 便捷函数
def get_db():
    """获取数据库会话的便捷函数"""
    return next(db_manager.get_session()) 