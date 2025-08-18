# 🍎 小红书AI发布助手 - Mac安装指南

## 快速开始

### 一键安装（推荐）

```bash
# 下载并运行Mac专用安装脚本
./install_mac.sh
```

### 一键启动

```bash
# 启动程序
./start_mac.sh
```

---

## 详细安装步骤

### 1. 系统要求

- **操作系统**: macOS 10.14+ 
- **Python版本**: 3.8+ (推荐3.11)
- **内存**: 最低4GB RAM
- **存储**: 至少2GB可用空间

### 2. 安装方式

#### 方式一：自动安装（推荐）

```bash
# 1. 进入项目目录
cd /path/to/xhs_ai_publisher

# 2. 运行Mac安装脚本
./install_mac.sh

# 3. 启动程序
./start_mac.sh
```

#### 方式二：手动安装

```bash
# 1. 安装Homebrew（如果没有）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. 安装Python
brew install python@3.11

# 3. 创建虚拟环境
python3 -m venv venv

# 4. 激活虚拟环境
source venv/bin/activate

# 5. 安装依赖
pip install -r requirements.txt

# 6. 初始化数据库（如果需要）
python init_db.py

# 7. 启动程序
python main.py
```

### 3. 脚本功能说明

#### `install_mac.sh` - 安装脚本
- 🔍 自动检测Python环境
- 🍺 自动安装Homebrew（如需要）
- 🐍 自动安装Python 3.11
- 🏗️ 创建虚拟环境
- 📦 安装项目依赖
- 🗄️ 初始化数据库
- 📝 创建启动脚本

#### `start_mac.sh` - 启动脚本
- 🔍 环境检测
- 🛠️ 依赖检查
- 🚀 智能启动
- ❌ 错误处理

---

## 常见问题

### Q: 安装过程中提示权限错误
**A**: 确保终端有足够权限，尝试使用 `sudo` 或在系统偏好设置中给予终端完全磁盘访问权限。

### Q: Python版本不兼容
**A**: 
```bash
# 卸载旧版本并重新安装
brew uninstall python@3.11
brew install python@3.11
```

### Q: 虚拟环境创建失败
**A**:
```bash
# 删除旧环境重新创建
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Q: 依赖安装失败
**A**:
```bash
# 升级pip并重新安装
pip install --upgrade pip
pip install -r requirements.txt --no-cache-dir
```

### Q: 程序无法启动
**A**:
1. 检查虚拟环境: `ls venv/bin/`
2. 重新运行安装脚本: `./install_mac.sh`
3. 查看错误日志获取详细信息

---

## 卸载程序

```bash
# 删除虚拟环境
rm -rf venv

# 删除生成的启动脚本
rm -f start_mac.sh

# 如不再需要Python（可选）
brew uninstall python@3.11
```

---

## 技术支持

- 📚 查看项目README
- 🐛 遇到问题请创建Issue
- 💬 加入讨论群获取帮助

---

*专为macOS优化 | 支持Apple Silicon & Intel芯片*