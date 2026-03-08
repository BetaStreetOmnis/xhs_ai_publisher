<div align="center">

<h1>🌟 小红书AI发布助手</h1>

![Python Version](https://img.shields.io/badge/Python-3.8%2B-3776AB?style=for-the-badge&logo=python&logoColor=white) ![License](https://img.shields.io/badge/License-Apache%202.0-4CAF50?style=for-the-badge&logo=apache&logoColor=white) ![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-0078D4?style=for-the-badge&logo=windows&logoColor=white) ![Version](https://img.shields.io/badge/Version-2.0.0-FF6B35?style=for-the-badge&logo=rocket&logoColor=white)

<br/>

![Status](https://img.shields.io/badge/Status-Active-28A745?style=flat-square) ![Stars](https://img.shields.io/badge/Stars-Welcome-FFD700?style=flat-square) ![Contributors](https://img.shields.io/badge/Contributors-Welcome-8A2BE2?style=flat-square)

<br/><br/>

### 🎨 智能内容创作 • 🤖 AI驱动 • 📱 一键发布

[🇨🇳 简体中文](./readme.md) | [🇺🇸 English](./readme_en.md)

<br/>

![软件界面](./images/ui.png)

</div>

---

## 🆕 1.6号更新

- 📊 **热点数据**：内置微博/百度/头条/B站等热榜，支持一键带回首页生成内容
- 🪧 **新增营销模板**：在「🖼️ 封面中心」可选 **营销海报🌟🌟🌟（本地生成 6 张图）/ 促销横幅 / 产品展示** 等
- 🖼️ **预览/下载体验升级**：首页支持一键打开「封面模板库」，并一键下载 **封面 + 多页内容图**
- 🎨 **UI 体验优化**：左侧编辑、右侧图片预览，生成流程更顺滑

## 📖 项目简介

> **小红书AI发布助手** 是一个功能强大的自动化内容创作与发布工具，专为小红书平台的内容创作者设计。

🎯 **核心价值**
- 🧠 **智能创作**: 基于先进AI技术自动生成高质量内容
- ⚡ **效率提升**: 一键操作节省90%发布时间
- 🎨 **专业品质**: 精美界面设计，用户体验极佳
- 🔧 **功能完整**: 从内容生成到发布全流程自动化

---

## ✨ 核心功能

<table>
<tr>
<td width="50%">

### 🤖 AI智能生成
- 🎯 **智能标题**: AI生成吸引人的标题
- 📝 **内容创作**: 基于主题自动生成文章
- 🔧 **自定义模型**: 支持配置 OpenAI 兼容/Claude/Ollama 等接口用于内容生成（未配置则回退到内置方案）
- 🧩 **文案模板**: 支持选择不同风格的提示词模板（`templates/prompts/*.json`），可自行扩展
- 📊 **热点采集**: 内置微博/百度/头条/B站等热榜，一键带回首页生成内容
- 🔗 **网页链接导入**: 粘贴网页链接导入标题/正文/图片（支持公众号/通用网页；效果视站点而定）
- 🖼️ **图片处理**: 智能匹配和处理图片
- 🖼️ **封面/内容图模板**: 支持在「🖼️ 封面中心」选择模板（含营销海报/促销横幅/产品展示等），生成时自动输出封面 + 多页内容图（可一键下载）
- 🏷️ **标签推荐**: 自动推荐热门标签

</td>
<td width="50%">

### 🚀 自动化发布
- 📱 **一键登录**: 支持手机号快速登录，支持国家区号选择；如遇风控可切换手动完成登录
- 🧩 **导入登录态**: 支持从系统 Chrome 导入小红书登录态（适用于短信/扫码风控后的登录复用）
- 📋 **内容预览**: 发布前完整预览效果
- ⏰ **定时发布（无人值守）**: 支持任务管理与到点自动发布（需保持程序运行且账号已登录）
- 💾 **状态保存**: 自动保存登录状态

</td>
</tr>
<tr>
<td width="50%">

### 👥 用户管理
- 🔄 **多账户/用户管理**: 支持新增/切换/删除用户；登录态与数据按用户隔离
- 🗂️ **本地数据**: 用户/环境/配置/日志均落地本地（`~/.xhs_system/`）

</td>
<td width="50%">

### 🛡️ 安全稳定
- 🔐 **数据加密**: 模型 API Key 默认本地加密存储（`~/.xhs_system/keys.enc`）
- 📝 **日志记录**: 完整的操作日志记录
- 🔄 **错误恢复**: 智能错误处理和恢复

</td>
</tr>
</table>

---

## 📁 项目架构

```
📦 xhs_ai_publisher/
├── 📂 assets/                       # 🧩 内置系统模板预览（可选）
├── 📂 templates/                    # 🧩 文案/封面模板（可自行扩展）
├── 🧰 install.sh                    # 📦 一键安装（macOS/Linux）
├── 🧰 install.bat                   # 📦 一键安装（Windows）
├── 📂 src/                          # 🔧 源代码目录
│   ├── 📂 core/                     # ⚡ 核心功能模块
│   │   ├── 📂 models/               # 🗄️ 数据模型
│   │   ├── 📂 services/             # 🔧 业务服务层
│   │   ├── 📂 pages/                # 🎨 界面页面
│   │   ├── 📂 processor/            # 🧩 内容/图片处理
│   │   ├── 📂 scheduler/            # ⏰ 定时任务（到点自动发布）
│   │   └── 📂 ai_integration/       # 🤖 AI适配（实验）
│   ├── 📂 web/                      # 🌐 Web接口
│   │   ├── 📂 templates/            # 📄 HTML模板
│   │   └── 📂 static/               # 🎨 静态资源
│   └── 📂 logger/                   # 📝 日志系统
├── 📂 images/                       # 🖼️ 文档/界面截图资源
├── 📂 docs/                         # 📚 文档
├── 📂 tests/                        # 🧪 测试目录
├── 📂 venv/                         # 🐍 本地虚拟环境（已在 .gitignore，不会上传 GitHub）
├── 🐍 main.py                       # 🚀 主程序入口
├── 🚀 启动程序.sh                   # ▶️ 启动脚本（macOS/Linux）
├── 🚀 启动程序.bat                  # ▶️ 启动脚本（Windows）
├── ⚙️ .env.example                  # 🔑 环境变量示例（不要提交真实 .env）
├── 📋 requirements.txt              # 📦 依赖包列表
└── 📖 readme.md                     # 📚 项目说明
```

---

## 🛠️ 快速开始

### 📋 系统要求

<div align="center">

| 组件 | 版本要求 | 说明 |
|:---:|:---:|:---:|
| 🐍 **Python** | `3.8+` | 推荐使用最新版本 |
| 🌐 **Chrome** | `最新版` | 用于浏览器自动化 |
| 💾 **内存** | `4GB+` | 推荐8GB以上 |
| 💿 **磁盘** | `2GB+` | 用于存储依赖和数据 |

</div>

> Windows 建议使用 **Python 3.11/3.12（64 位）**；Python 3.13 或 32 位 Python 常见会导致 **PyQt5 安装失败**。

### 🚀 安装方式

#### 🎯 一键安装（推荐）

| 操作系统 | 安装脚本 | 启动脚本 |
|:---:|:---:|:---:|
| macOS / Linux | `./install.sh` | `./启动程序.sh` |
| Windows | `install.bat` | `启动程序.bat` |

```bash
# macOS/Linux
chmod +x install.sh 启动程序.sh
./install.sh
./启动程序.sh
```

> `./启动程序.sh` 会优先使用 `venv/bin/python`；若虚拟环境解释器缺失、软链失效或环境损坏，会自动回退到系统 `python3` / `python`，不会写死机器路径。

```bat
:: Windows
install.bat
启动程序.bat
```

> 默认会检测 Playwright 浏览器并在缺失时自动安装；可用参数：
> - 强制安装：`./install.sh --with-browser` / `install.bat --with-browser`
> - 跳过浏览器：`./install.sh --skip-browser` / `install.bat --skip-browser`
> - Windows 双击 `启动程序.bat` / `install.bat` 失败时，现在会保留报错窗口，方便定位问题

#### 🧩 登录工具 + 服务模式（参考社区常见做法）

参考 `xiaohongshu-mcp`、`xhs-toolkit` 这类项目的思路，当前仓库也支持：
- **先在可视化环境完成一次登录，保存登录态**
- **再由 Web/API 服务或 Docker 无头复用该登录态执行发布**

本地获取登录态：

```bash
python scripts/xhs_login_cli.py --phone 13800138000 --country-code +86
```

说明：
- 该命令会打开浏览器并尽量复用/保存 `storage_state + cookies`
- 若命中验证码/扫码/滑块风控，可按提示在浏览器中手动完成
- 成功后，登录态默认保存在 `~/.xhs_system/`（或 `XHS_DATA_DIR` 指定目录）
- 当本地 `storage_state/cookies` 失效时，登录流程会自动尝试扫描系统 Chrome 的多个 Profile，识别可用的小红书登录态并导入；可用 `XHS_AUTO_IMPORT_SYSTEM_CHROME_STATE=false` 关闭
- 使用真实 Chrome 持久化 Profile 时，默认不再注入额外 stealth 指纹覆写；如确有需要可设置 `XHS_ENABLE_STEALTH_SCRIPT=true`
- 自动发布默认禁用 JS 强制点击/强制 input/change 兜底；仅手动确认模式或显式设置 `XHS_ENABLE_FORCE_DOM_ACTIONS=true` 时才启用
- 若系统 Chrome 正在运行，自动识别登录态会默认跳过，避免额外弹出多窗口；需要手动导入时再显式操作

#### 🐳 Docker 部署（推荐 Web/API 模式）

> 桌面版 `PyQt` 不适合直接做容器 GUI 部署；**容器里推荐运行 `FastAPI + Playwright` 服务模式**。

```bash
docker compose build
docker compose up -d
```

默认暴露：
- Web/API：`http://localhost:8000`
- 健康检查：`http://localhost:8000/healthz`
- 就绪检查：`http://localhost:8000/readyz`

服务优化说明：
- 现在 Web/Docker 模式默认采用 **懒加载浏览器运行时**
- 服务启动时只初始化基础管理器，不会立刻拉起 Playwright 浏览器
- 第一次调用登录/发布接口时，才按需初始化浏览器运行时
- 如需启动即预热浏览器，可设置 `XHS_WEB_EAGER_BROWSER=true`

容器部署建议流程：
1. 先在本机可视化环境执行一次 `python scripts/xhs_login_cli.py ...` 获取登录态
2. 将登录态目录挂载到容器的 `/data`（本仓库默认映射 `./docker-data:/data`）
3. 再以无头模式运行容器服务进行发布

注意：
- 默认 `docker-compose.yml` 中启用了 `XHS_HEADLESS=true`
- 如果当前登录态失效，无头模式不会弹验证码窗口，而会明确提示需要先在有界面环境重新登录
- `docker compose ps` 可直接看到健康状态；健康检查依赖 `/healthz`

#### 📥 手动安装（高级用户）

```bash
# 1️⃣ 创建虚拟环境
python -m venv venv

# 2️⃣ 激活虚拟环境（macOS/Linux）
source venv/bin/activate

# 3️⃣ 安装依赖
pip install -r requirements.txt

# 4️⃣ （可选）安装 Playwright Chromium
PLAYWRIGHT_BROWSERS_PATH="$HOME/.xhs_system/ms-playwright" python -m playwright install chromium

# 5️⃣ 启动程序（首次启动会自动初始化数据库）
./启动程序.sh
```

> `./启动程序.sh` 会自动检测可用 Python；如果本地 `venv/bin/python` 已损坏，也会回退到系统 Python 启动，并提示你后续可用 `./install.sh` 修复环境。

提示：
- 运行数据默认存放于 `~/.xhs_system/`（数据库、日志、浏览器缓存等）
- 也可通过 `XHS_DATA_DIR=/your/path` 改为自定义目录（Docker/服务模式推荐）

常见问题：
- Windows 安装失败（多为 PyQt5）：请用 Python 3.11/3.12（64 位），避免 Python 3.13 或 32 位 Python
- Linux 浏览器启动失败：可能缺少系统依赖，执行 `sudo python -m playwright install-deps chromium`（或对应发行版命令）
- `qt.qpa.fonts ... Microsoft YaHei`：Qt 的字体告警，可忽略；当前版本已改为自动选择系统可用字体
- 内容页个别符号显示“方框/叉号”：通常是系统字体不支持该字符（emoji/圈数字/信息符号等）；建议减少特殊符号，或更换/安装字体（程序也会做一部分字符清理/替换）

---

## 📱 使用指南

### 🎯 基础使用流程

<div align="center">

```mermaid
flowchart LR
    A[🚀 启动程序] --> B[📱 登录账户]
    B --> C[✍️ 输入主题]
    C --> D[🤖 AI生成内容]
    D --> E[👀 预览效果]
    E --> F[📤 一键发布]
    
    style A fill:#e1f5fe
    style B fill:#f3e5f5
    style C fill:#e8f5e8
    style D fill:#fff3e0
    style E fill:#fce4ec
    style F fill:#e0f2f1
```

</div>

### 📝 详细步骤

1. **🚀 启动程序**
   - 运行 `./启动程序.sh` 或 `python main.py`
   - 等待程序加载完成
	
2. **👥 用户管理（可选）**
   - 侧边栏「👥」支持新增/切换/删除用户
   - 登录态、浏览器环境、cookie/token 等数据按用户隔离

3. **🌐 浏览器环境（可选）**
   - 侧边栏「🌐」创建环境，并可设置“⭐ 默认环境”
   - 默认环境的代理/基础指纹会应用到发布会话（UA/viewport/locale/timezone/geolocation 等）

4. **📊 数据中心（可选）**
   - 侧边栏「📊」查看多平台热榜
   - 选中热点后点击「✍️ 用作首页主题」一键带回首页生成

5. **🖼️ 封面模板（可选）**
   - 侧边栏「🖼️」进入封面中心选择模板，并「✅ 应用到首页」
   - 也可在首页右侧预览区点击「🧩 封面模板」快速跳转

6. **📱 账户登录**
   - 选择国家区号并输入手机号码
   - 接收并输入验证码；如遇扫码/滑块风控，可取消输入后在浏览器中手动完成登录
   - 系统自动保存登录状态；若本地登录态失效，会自动尝试从系统 Chrome Profile 识别并导入可用登录态
   - 如需手动指定/强制导入：可点击「🧩 导入登录态」从系统 Chrome 导入（建议先完全退出 Chrome，避免 Profile 被占用）

7. **🔗 网页链接导入（可选）**
   - 首页「🔗 导入」粘贴网页链接
   - 点击「📥 导入」自动抓取标题/正文/图片并填充到草稿（效果视站点而定）

8. **✍️ 内容创作**
   - 在主题输入框输入创作主题
   - 点击"生成内容"按钮
   - AI自动生成标题和内容

9. **🖼️ 图片处理**
   - 系统自动匹配相关图片
   - 可手动上传自定义图片
   - 支持多图片批量处理

10. **👀 预览发布**
   - 点击"预览发布"查看效果
   - 确认内容无误后点击发布
   - 或点击「⏰ 定时发布」设置时间，到点自动发布（需保持程序运行且账号已登录）

---

## 🤖 自定义模型与模板

- 入口：侧边栏「⚙️ 后台配置」→「AI模型配置」
- API Key：保存时默认加密写入 `~/.xhs_system/keys.enc`（`settings.json` 不再明文保存）
- 文案模板：在「文案模板」下拉框选择；模板文件位于 `templates/prompts/`
- 系统图片模板：侧边栏「⚙️ 后台配置」→「模板库」可选择/导入（将外部模板导入到 `~/.xhs_system/system_templates`，便于跨平台使用）
- 封面模板：侧边栏「🖼️ 封面中心」选择并应用到首页；生成图片默认缓存于 `~/.xhs_system/generated_imgs/`，可在首页「📥 下载图片」导出

### ⚙️ 通过 `.env` 配置模型（可选，推荐 OpenAI-compatible）

> `.env` 已在 `.gitignore`，不会推送到 GitHub；请勿把真实 key 写进 `.env.example`。

```bash
cp .env.example .env
```

说明：
- 默认优先使用 UI「AI模型配置」里的设置；仅当 UI 未配置时才会使用 `.env` 作为兜底
- 如需强制使用 `.env`，将 `XHS_LLM_OVERRIDE=true`
- `XHS_LLM_BASE_URL` 可填 base_url（如 `.../v1`、`.../api/paas/v4`）或完整的 `.../chat/completions`（程序会自动补全）

以智谱 GLM-5 为例（OpenAI-compatible）：

```bash
XHS_LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
XHS_LLM_MODEL=glm-5
XHS_LLM_API_KEY=你的key

# 可选：强制使用环境变量（即使 UI 已配置）
XHS_LLM_OVERRIDE=true

# 可选：GLM-5 建议给大一点
XHS_LLM_TIMEOUT=120
XHS_LLM_MAX_TOKENS=3200
```

图片排版风格（可选）：

```bash
XHS_IMG_SHOW_TAGS=false
XHS_IMG_SHOW_CONTENT_CARD=false
XHS_IMG_BOXED_LIST_CARDS=false
```

## 🔧 高级配置

### 📁 数据与配置位置

- `~/.xhs_system/settings.json`：应用配置（手机号/标题/模型/模板等）
- `~/.xhs_system/keys.enc`：模型 API Key 加密存储
- `~/.xhs_system/xhs_data.db`：本地数据库（用户/浏览器环境等）
- `~/.xhs_system/generated_imgs/`：生成图片缓存
- `~/.xhs_system/ms-playwright/`：Playwright 浏览器缓存目录
- `~/.xhs_system/logs/`：运行日志
- `~/.xhs_system/hotspots_cache.json`：热点缓存
- `~/.xhs_system/schedule_tasks.json`：定时发布任务

---

## 📊 开发路线图

<div align="center">

### 🗓️ 开发计划

</div>

- [x] ✅ **基础功能**: 内容生成和发布
- [x] ✅ **用户管理**: 多账户/当前用户切换/数据隔离
- [x] ✅ **模板库**: 文案模板 + 系统图片模板导入 + 封面模板库
- [x] ✅ **数据中心**: 多平台热榜采集 + 一键带回首页生成
- [x] ✅ **定时发布**: 支持任务管理与到点自动发布（需保持程序运行）
- [ ] 🔄 **发布效果分析**: 数据统计/分析面板持续完善
- [ ] 🔄 **API接口**: 开放API接口

---

## 🤝 参与贡献

<div align="center">

**🎉 我们欢迎所有形式的贡献!**

<img src="https://img.shields.io/badge/🐛_Bug修复-欢迎-FF6B6B?style=for-the-badge" alt="Bug修复"/>
<img src="https://img.shields.io/badge/💡_功能建议-欢迎-4ECDC4?style=for-the-badge" alt="功能建议"/>
<img src="https://img.shields.io/badge/📝_文档完善-欢迎-45B7D1?style=for-the-badge" alt="文档完善"/>
<img src="https://img.shields.io/badge/💻_代码贡献-欢迎-96CEB4?style=for-the-badge" alt="代码贡献"/>

</div>

### 🛠️ 贡献指南

1. 🍴 Fork 项目
2. 🌿 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 💾 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 📤 推送到分支 (`git push origin feature/AmazingFeature`)
5. 🔄 创建 Pull Request

---

## 📞 联系我们

<div align="center">

### 💬 加入我们的社区

<table>
<tr>
<td align="center">
<img src="images/wechat_qr.jpg" width="150" height="150"/>
<br/>
<strong>🐱 微信群</strong>
<br/>
<em>扫码加入讨论</em>
</td>
<td align="center">
<img src="images/mp_qr.jpg" width="150" height="150"/>
<br/>
<strong>📱 公众号</strong>
<br/>
<em>获取最新动态</em>
</td>
</tr>
</table>

<br/>

<img src="https://img.shields.io/badge/📧_邮箱-联系我们-EA4335?style=for-the-badge&logo=gmail&logoColor=white" alt="邮箱"/>
<img src="https://img.shields.io/badge/💬_微信-在线咨询-07C160?style=for-the-badge&logo=wechat&logoColor=white" alt="微信"/>
<img src="https://img.shields.io/badge/🐛_问题反馈-GitHub-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub Issues"/>

</div>

---

## ⭐ Star 历史

[![Star History Chart](https://api.star-history.com/svg?repos=betastreetomnis/xhs_ai_publisher&type=Date)](https://star-history.com/#betastreetomnis/xhs_ai_publisher&Date)

---

## 📄 许可证

<div align="center">

本项目采用 **Apache 2.0** 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

<br/>

<img src="https://img.shields.io/badge/📜_许可证-Apache_2.0-4CAF50?style=for-the-badge&logo=apache&logoColor=white" alt="许可证"/>

<br/><br/>

---

<sub>🌟 为小红书内容创作者精心打造 | Built with ❤️ for Xiaohongshu content creators</sub>

<br/>

**⭐ 如果这个项目对您有帮助，请给我们一个星标!**

</div>
