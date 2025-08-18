from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import os
import json
import uuid
from pathlib import Path
import aiofiles

# 导入我们重构后的核心模块
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.browser_manager import BrowserManager
from core.write_xiaohongshu import XiaohongshuPoster
from core.auth_manager import AuthManager
from core.content_manager import ContentManager, ContentItem
from core.session_manager import SessionManager
from core.logger import logger
from core.config import config

app = FastAPI(
    title="小红书AI发布器",
    description="基于Web的小红书自动发布工具",
    version="2.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局管理器实例
browser_manager: Optional[BrowserManager] = None
auth_manager: Optional[AuthManager] = None
content_manager: Optional[ContentManager] = None
session_manager: Optional[SessionManager] = None
publisher: Optional[XiaohongshuPoster] = None

# Pydantic模型
class LoginRequest(BaseModel):
    phone: str
    country_code: str = "+86"

class ContentCreateRequest(BaseModel):
    title: str
    content: str
    tags: Optional[List[str]] = []
    images: Optional[List[str]] = []

class PublishRequest(BaseModel):
    content_id: str

class SessionResponse(BaseModel):
    session_id: str
    status: str
    message: str

class LoginStatusResponse(BaseModel):
    logged_in: bool
    user_info: Optional[Dict[str, Any]] = None
    session_active: bool
    error: Optional[str] = None

# 静态文件服务
app.mount("/static", StaticFiles(directory="src/web/static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """返回主页面"""
    html_file = Path("src/web/templates/index.html")
    if html_file.exists():
        async with aiofiles.open(html_file, encoding='utf-8') as f:
            content = await f.read()
        return HTMLResponse(content=content)
    else:
        return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>小红书AI发布器</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
                .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .title { color: #333; text-align: center; margin-bottom: 30px; }
                .error { color: #e74c3c; text-align: center; margin: 20px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1 class="title">小红书AI发布器</h1>
                <div class="error">前端页面文件缺失，请检查 src/web/templates/index.html 文件</div>
                <p>API文档：<a href="/docs">/docs</a></p>
            </div>
        </body>
        </html>
        """)

@app.get("/api/status")
async def get_status():
    """获取系统状态"""
    try:
        # 获取各种统计信息
        content_stats = content_manager.get_content_stats() if content_manager else {}
        session_stats = session_manager.get_session_stats() if session_manager else {}
        
        current_session = session_manager.get_current_session() if session_manager else None
        
        status = {
            'browser_ready': browser_manager is not None and browser_manager.page is not None,
            'logged_in': False,
            'current_session': current_session.to_dict() if current_session else None,
            'content_stats': content_stats,
            'session_stats': session_stats,
            'user_info': None
        }
        
        # 检查登录状态
        if auth_manager and browser_manager:
            status['logged_in'] = await auth_manager.is_logged_in()
            if status['logged_in']:
                status['user_info'] = await auth_manager.get_user_info()
        
        return {
            'success': True,
            'data': status
        }
        
    except Exception as e:
        logger.error(f"获取状态失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth/login")
async def login(request: LoginRequest):
    """登录"""
    try:
        if not auth_manager:
            raise HTTPException(status_code=500, detail="认证管理器未初始化")
        
        # 执行登录
        success = await auth_manager.login(request.phone, request.country_code)
        
        if success:
            # 创建新会话
            session_id = session_manager.create_session(f"登录会话_{request.phone}")
            
            # 获取用户信息
            user_info = await auth_manager.get_user_info()
            if user_info:
                session_manager.update_session_user_info(session_id, user_info)
            
            return {
                'success': True,
                'message': '登录成功',
                'data': {
                    'session_id': session_id,
                    'user_info': user_info
                }
            }
        else:
            raise HTTPException(status_code=400, detail="登录失败，请检查手机号或重试")
        
    except Exception as e:
        logger.error(f"登录失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")

@app.post("/api/auth/logout")
async def logout():
    """登出"""
    try:
        if not auth_manager:
            raise HTTPException(status_code=500, detail="认证管理器未初始化")
        
        success = await auth_manager.logout()
        
        if success:
            # 清理当前会话
            current_session = session_manager.get_current_session()
            if current_session:
                session_manager.update_session_status(current_session.id, "completed")
            
            return {
                'success': True,
                'message': '登出成功'
            }
        else:
            raise HTTPException(status_code=400, detail="登出失败")
        
    except Exception as e:
        logger.error(f"登出失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"登出失败: {str(e)}")

@app.post("/api/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """上传文件"""
    try:
        if not content_manager:
            raise HTTPException(status_code=500, detail="内容管理器未初始化")
        
        uploaded_files = []
        
        for file in files:
            if file.filename == '':
                continue
            
            if file and allowed_file(file.filename):
                # 读取文件数据
                file_data = await file.read()
                
                # 保存文件
                file_path = content_manager.save_image(file_data, file.filename)
                
                uploaded_files.append({
                    'filename': file.filename,
                    'path': file_path,
                    'size': len(file_data)
                })
        
        return {
            'success': True,
            'message': f'成功上传 {len(uploaded_files)} 个文件',
            'data': uploaded_files
        }
        
    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

def allowed_file(filename):
    """检查文件类型是否允许"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.post("/api/content")
async def create_content(request: ContentCreateRequest):
    """创建内容"""
    try:
        if not content_manager:
            raise HTTPException(status_code=500, detail="内容管理器未初始化")
        
        if not request.title.strip():
            raise HTTPException(status_code=400, detail="请输入标题")
        
        if not request.content.strip():
            raise HTTPException(status_code=400, detail="请输入内容")
        
        # 创建内容
        content_id = content_manager.create_content(request.title, request.content, request.tags)
        
        # 添加图片
        if request.images:
            for image_path in request.images:
                content_manager.add_image_to_content(content_id, image_path)
        
        content_item = content_manager.get_content(content_id)
        
        return {
            'success': True,
            'message': '内容创建成功',
            'data': content_item.to_dict()
        }
        
    except Exception as e:
        logger.error(f"创建内容失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建内容失败: {str(e)}")

@app.get("/api/content/{content_id}")
async def get_content(content_id: str):
    """获取内容"""
    try:
        if not content_manager:
            raise HTTPException(status_code=500, detail="内容管理器未初始化")
        
        content_item = content_manager.get_content(content_id)
        
        if not content_item:
            raise HTTPException(status_code=404, detail="内容不存在")
        
        return {
            'success': True,
            'data': content_item.to_dict()
        }
        
    except Exception as e:
        logger.error(f"获取内容失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取内容失败: {str(e)}")

@app.get("/api/content")
async def list_contents(status: Optional[str] = None, limit: Optional[int] = None):
    """列出内容"""
    try:
        if not content_manager:
            raise HTTPException(status_code=500, detail="内容管理器未初始化")
        
        contents = content_manager.list_contents(status, limit)
        
        return {
            'success': True,
            'data': [content.to_dict() for content in contents]
        }
        
    except Exception as e:
        logger.error(f"列出内容失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"列出内容失败: {str(e)}")

@app.post("/api/publish")
async def publish_content(request: PublishRequest, background_tasks: BackgroundTasks):
    """发布内容"""
    try:
        if not content_manager or not auth_manager or not publisher:
            raise HTTPException(status_code=500, detail="管理器未初始化")
        
        content_item = content_manager.get_content(request.content_id)
        if not content_item:
            raise HTTPException(status_code=404, detail="内容不存在")
        
        # 验证内容
        is_valid, errors = content_manager.validate_content(content_item)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"内容验证失败: {', '.join(errors)}")
        
        # 检查登录状态
        is_logged_in = await auth_manager.is_logged_in()
        if not is_logged_in:
            raise HTTPException(status_code=401, detail="请先登录")
        
        # 在后台执行发布任务
        async def publish_task():
            try:
                # 更新内容状态为发布中
                content_manager.update_content_status(request.content_id, "publishing")
                
                # 执行发布
                success = await publisher.post_article(
                    title=content_item.title,
                    content=content_item.content,
                    images=content_item.images
                )
                
                if success:
                    content_manager.update_content_status(request.content_id, "published")
                    logger.info(f"内容发布成功: {request.content_id}")
                else:
                    content_manager.update_content_status(request.content_id, "failed", "发布失败")
                    logger.error(f"内容发布失败: {request.content_id}")
                    
            except Exception as e:
                content_manager.update_content_status(request.content_id, "failed", str(e))
                logger.error(f"内容发布异常: {request.content_id}, {str(e)}", exc_info=True)
        
        background_tasks.add_task(publish_task)
        
        return {
            'success': True,
            'message': '发布任务已启动，请稍后查看发布状态'
        }
        
    except Exception as e:
        logger.error(f"发布内容失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"发布失败: {str(e)}")

@app.get("/api/sessions")
async def list_sessions(status: Optional[str] = None, limit: Optional[int] = None):
    """列出会话"""
    try:
        if not session_manager:
            raise HTTPException(status_code=500, detail="会话管理器未初始化")
        
        sessions = session_manager.list_sessions(status, limit)
        
        return {
            'success': True,
            'data': [session.to_dict() for session in sessions]
        }
        
    except Exception as e:
        logger.error(f"列出会话失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"列出会话失败: {str(e)}")

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    try:
        if not session_manager:
            raise HTTPException(status_code=500, detail="会话管理器未初始化")
        
        success = session_manager.delete_session(session_id)
        
        if success:
            return {
                'success': True,
                'message': '会话删除成功'
            }
        else:
            raise HTTPException(status_code=404, detail="会话不存在")
        
    except Exception as e:
        logger.error(f"删除会话失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除会话失败: {str(e)}")

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化管理器"""
    global browser_manager, auth_manager, content_manager, session_manager, publisher
    
    try:
        logger.info("正在初始化管理器...")
        
        # 初始化管理器
        browser_manager = BrowserManager()
        auth_manager = AuthManager()
        content_manager = ContentManager()
        session_manager = SessionManager()
        
        # 初始化浏览器
        await browser_manager.initialize()
        
        # 初始化认证管理器
        await auth_manager.initialize(browser_manager)
        
        # 初始化发布器
        publisher = XiaohongshuPoster()
        await publisher.initialize()
        
        logger.info("所有管理器初始化完成")
        
    except Exception as e:
        logger.error(f"管理器初始化失败: {str(e)}", exc_info=True)
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理资源"""
    global browser_manager, auth_manager, content_manager, session_manager, publisher
    
    try:
        logger.info("正在清理资源...")
        
        if publisher:
            await publisher.cleanup()
        
        if auth_manager:
            await auth_manager.cleanup()
        
        if browser_manager:
            await browser_manager.cleanup()
        
        logger.info("资源清理完成")
        
    except Exception as e:
        logger.error(f"资源清理失败: {str(e)}", exc_info=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=config.web.host,
        port=config.web.port,
        reload=config.web.debug
    ) 