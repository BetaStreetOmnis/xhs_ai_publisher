# xhs_ai_publisher AI增强扩展方案

## 项目目标
在保留现有xhs_ai_publisher全部功能的基础上，增加用户自定义API密钥的AI图片生成和内容创作能力，支持Kimi和Qwen两大AI平台。

## 架构设计原则
1. **零破坏原则**：现有功能100%保留
2. **渐进式升级**：分阶段实施，用户可逐步启用
3. **用户选择权**：用户自主选择使用传统方式还是AI方式
4. **密钥安全**：用户API密钥本地加密存储，不上传服务器

## 技术架构

### 1. 用户API密钥管理模块
```
src/core/ai_integration/
├── api_key_manager.py      # API密钥管理器
├── ai_provider_factory.py   # AI服务工厂
├── kimi_adapter.py         # Kimi API适配器
├── qwen_adapter.py         # Qwen API适配器
└── image_generator.py      # 统一图片生成接口
```

### 2. 新增功能模块
```
src/core/generation/
├── content_analyzer.py     # 内容智能分析
├── prompt_builder.py       # AI提示词构建
├── style_selector.py       # 风格选择器
└── result_processor.py     # 生成结果处理
```

### 3. 用户界面扩展
```
src/core/pages/
├── ai_settings_page.py     # AI设置页面
├── style_preview_page.py   # 风格预览页面
└── generation_monitor.py   # 生成进度监控
```

## 详细实施计划

### Phase 1: 基础架构搭建 (Week 1-2)

#### 1.1 API密钥管理系统
**文件**: `src/core/ai_integration/api_key_manager.py`
```python
class APIKeyManager:
    """用户API密钥管理器"""
    
    def __init__(self):
        self.keys_file = os.path.expanduser('~/.xhs_system/keys.enc')
    
    def add_key(self, provider: str, key_name: str, api_key: str):
        """添加API密钥（本地加密存储）"""
    
    def get_key(self, provider: str, key_name: str) -> str:
        """获取指定服务商的API密钥"""
    
    def list_keys(self) -> dict:
        """列出所有已保存的密钥"""
```

#### 1.2 AI服务工厂
**文件**: `src/core/ai_integration/ai_provider_factory.py`
```python
class AIProviderFactory:
    """AI服务提供商工厂"""
    
    @staticmethod
    def create_provider(provider_type: str, api_key: str):
        """创建对应的AI服务实例"""
        if provider_type == 'kimi':
            return KimiAdapter(api_key)
        elif provider_type == 'qwen':
            return QwenAdapter(api_key)
```

### Phase 2: AI适配器实现 (Week 2-3)

#### 2.1 Kimi适配器
**文件**: `src/core/ai_integration/kimi_adapter.py`
```python
class KimiAdapter:
    """Kimi AI图片生成适配器"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.kimi.com/v1"
    
    def generate_image(self, prompt: str, style: str, size: str) -> str:
        """生成图片并返回URL"""
    
    def get_balance(self) -> float:
        """查询API余额"""
```

#### 2.2 Qwen适配器
**文件**: `src/core/ai_integration/qwen_adapter.py`
```python
class QwenAdapter:
    """通义千问AI图片生成适配器"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://dashscope.aliyuncs.com/api/v1"
    
    def generate_image(self, prompt: str, style: str, size: str) -> str:
        """生成图片并返回URL"""
```

### Phase 3: 智能生成核心 (Week 3-4)

#### 3.1 内容分析器
**文件**: `src/core/generation/content_analyzer.py`
```python
class ContentAnalyzer:
    """小红书内容智能分析器"""
    
    def extract_keywords(self, content: str) -> list:
        """提取关键词用于图片生成"""
    
    def detect_content_type(self, content: str) -> str:
        """识别内容类型：美妆/美食/穿搭/旅行等"""
    
    def generate_image_prompts(self, title: str, content: str) -> dict:
        """生成AI绘图提示词"""
```

#### 3.2 风格选择器
**文件**: `src/core/generation/style_selector.py`
```python
class StyleSelector:
    """小红书视觉风格选择器"""
    
    STYLES = {
        'cute': {'name': '可爱风', 'colors': ['pink', 'pastel']},
        'clean': {'name': '简约风', 'colors': ['white', 'neutral']},
        'professional': {'name': '专业风', 'colors': ['blue', 'dark']},
        'trendy': {'name': '潮流风', 'colors': ['neon', 'gradient']}
    }
```

### Phase 4: UI集成 (Week 4-5)

#### 4.1 AI设置页面
**文件**: `src/core/pages/ai_settings_page.py`
- API密钥添加/管理界面
- 服务商选择（Kimi/Qwen）
- 余额查询显示
- 生成参数设置

#### 4.2 风格预览页面
**文件**: `src/core/pages/style_preview_page.py`
- 实时风格预览
- 参数调整滑块
- 历史生成记录
- 一键应用到发布

## 数据结构扩展

### 数据库表结构（新增）
```sql
-- 用户AI配置表
CREATE TABLE ai_user_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    provider VARCHAR(20),        -- 'kimi' 或 'qwen'
    default_style VARCHAR(20),   -- 默认风格
    quality_setting VARCHAR(10), -- 'standard' 或 'high'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 生成历史记录表
CREATE TABLE generation_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    provider VARCHAR(20),
    prompt TEXT,
    result_url TEXT,
    status VARCHAR(20),         -- 'pending', 'success', 'failed'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## 用户操作流程

### 1. 首次设置流程
1. 打开设置 → AI配置
2. 选择服务商（Kimi/Qwen）
3. 输入API密钥（本地加密存储）
4. 测试连接并验证余额
5. 设置默认风格和参数

### 2. 日常使用方法
1. 创建内容时，选择"AI生成图片"
2. 系统自动分析内容推荐风格
3. 用户可调整风格或接受推荐
4. 一键生成封面和配图
5. 预览确认后自动添加到发布队列

## 兼容性和回退机制

### 向后兼容性
- 现有图片上传功能100%保留
- 现有模板系统继续可用
- 用户可选择传统方式或AI方式

### 错误处理
```python
class GenerationFallback:
    """生成失败回退机制"""
    
    def on_generation_failed(self, error_type: str):
        if error_type == 'api_limit':
            return self.use_template_fallback()
        elif error_type == 'network_error':
            return self.retry_with_backoff()
        else:
            return self.notify_user_manual_upload()
```

## 测试计划

### 单元测试
```python
# 测试API密钥管理
def test_api_key_encryption():
    manager = APIKeyManager()
    manager.add_key('kimi', 'test_key', 'sk-xxx')
    assert manager.get_key('kimi', 'test_key') == 'sk-xxx'

# 测试内容分析
def test_content_analysis():
    analyzer = ContentAnalyzer()
    keywords = analyzer.extract_keywords("夏日清爽护肤分享")
    assert '护肤' in keywords
```

### 集成测试
- Kimi API端到端测试
- Qwen API端到端测试
- UI集成测试
- 数据库操作测试

## 部署检查清单

### 开发环境准备
- [ ] 安装新增依赖包
- [ ] 配置测试API密钥
- [ ] 初始化新数据库表
- [ ] 创建密钥存储目录

### 生产环境部署
- [ ] 数据库迁移脚本
- [ ] 密钥加密机制验证
- [ ] 错误日志配置
- [ ] 用户文档更新

## 风险评估和缓解

| 风险项 | 概率 | 影响 | 缓解措施 |
|--------|------|------|----------|
| API服务不可用 | 中 | 高 | 提供模板回退 |
| 用户密钥泄露 | 低 | 高 | 本地加密存储 |
| 生成质量不佳 | 中 | 中 | 提供参数调整 |
| 成本过高 | 低 | 中 | 显示余额提醒 |

## 后续扩展计划

### Phase 5: 高级功能（可选）
- 批量生成多个版本供选择
- A/B测试不同风格效果
- 用户训练个性化风格
- 团队协作功能

### Phase 6: 商业功能（可选）
- 使用量统计分析
- 成本优化建议
- 专业模板商店
- API代理服务

这个方案确保了在完全保留现有功能的前提下，平滑地增加AI能力，给用户充分的选择权和控制权。