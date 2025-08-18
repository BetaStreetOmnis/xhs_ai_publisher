# 清理之前的构建
rm -rf build dist
rm -rf temp_build

# 安装必要工具
# brew install create-dmg imagemagick

# 检查并安装 playwright
if ! pip show playwright > /dev/null 2>&1; then
    echo "正在安装 playwright..."
    pip install playwright
    playwright install
fi

# 创建圆角图标 (增加圆角半径，更接近 macOS 风格)
convert icon.png \
    -gravity south \
    -geometry +0-150 \
    \( +clone -alpha extract \
       -draw 'fill black polygon 0,0 0,22 22,0 fill white circle 22,22 22,0' \
       \( +clone -flip \) -compose Multiply -composite \
       \( +clone -flop \) -compose Multiply -composite \
    \) -alpha off -compose CopyOpacity -composite \
    \( -size 1024x1024 xc:none -draw 'roundrectangle 0,0 1024,1024 160,160' \) \
    -compose DstIn -composite \
    rounded_icon.png

# 创建iconset
mkdir MyIcon.iconset
sips -z 16 16     rounded_icon.png --out MyIcon.iconset/icon_16x16.png
sips -z 32 32     rounded_icon.png --out MyIcon.iconset/icon_16x16@2x.png
sips -z 32 32     rounded_icon.png --out MyIcon.iconset/icon_32x32.png
sips -z 64 64     rounded_icon.png --out MyIcon.iconset/icon_32x32@2x.png
sips -z 128 128   rounded_icon.png --out MyIcon.iconset/icon_128x128.png
sips -z 256 256   rounded_icon.png --out MyIcon.iconset/icon_128x128@2x.png
sips -z 256 256   rounded_icon.png --out MyIcon.iconset/icon_256x256.png
sips -z 512 512   rounded_icon.png --out MyIcon.iconset/icon_256x256@2x.png
sips -z 512 512   rounded_icon.png --out MyIcon.iconset/icon_512x512.png
sips -z 1024 1024 rounded_icon.png --out MyIcon.iconset/icon_512x512@2x.png

# 创建 icns 文件
iconutil -c icns MyIcon.iconset

# 获取 Python 证书路径
CERT_PATH=$(python3 -c "import certifi; print(certifi.where())")

# 打包命令
pyinstaller  \
    --workpath temp_build \
    --distpath dist \
    --clean \
    --onefile \
    --noconsole \
    --name "XhsAi" \
    --icon MyIcon.icns \
    --add-data "${CERT_PATH}:certifi" \
    --add-data "../src:src" \
    --paths ".." \
    --collect-submodules src \
    --hidden-import playwright \
    --hidden-import playwright.sync_api \
    --hidden-import playwright._impl._driver \
    --hidden-import playwright.async_api \
    ../main.py


# 手动复制 Playwright 浏览器依赖
mkdir -p dist/XhsAi.app/Contents/MacOS/ms-playwright
cp -r $HOME/Library/Caches/ms-playwright/* dist/XhsAi.app/Contents/MacOS/ms-playwright/

# 设置浏览器文件权限
chmod -R 777 dist/XhsAi.app/Contents/MacOS/ms-playwright

# 添加应用程序本身的执行权限
chmod +x dist/XhsAi.app/Contents/MacOS/XhsAi

# 打包完成后清理临时文件
rm -rf temp_build
rm -f rounded_icon.png

# 创建输出目录
mkdir -p output

# 创建 DMG
create-dmg \
    --volname "XhsAi" \
    --volicon "MyIcon.icns" \
    --window-pos 200 120 \
    --window-size 480 200 \
    --icon-size 128 \
    --icon "XhsAi" 120 40 \
    --hide-extension "XhsAi" \
    --app-drop-link 360 40 \
    --format UDBZ \
    "output/XhsAi.dmg" \
    "dist/"



sudo chmod -R 777 dist
sudo chmod -R 777 output

# 清理临时文件
rm -rf MyIcon.iconset
rm -rf dist