from PIL import Image
import os

def create_ico():
    # 打开PNG图片
    img = Image.open('icon.png')
    
    # 创建不同尺寸的图标
    sizes = [(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)]
    icons = []
    
    for size in sizes:
        # 调整大小并保持质量
        resized = img.resize(size, Image.Resampling.LANCZOS)
        icons.append(resized)
    
    # 保存为ICO文件
    icons[0].save('icon.ico', format='ICO', sizes=[(icon.width, icon.height) for icon in icons])

if __name__ == '__main__':
    create_ico()