import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import os
from src.core.write_xiaohongshu import XiaohongshuPoster
import json
import requests
from PIL import Image, ImageTk
import io
import threading


# 加载提示窗口类
class LoadingWindow:
    def __init__(self, parent):
        self.top = tk.Toplevel(parent)
        self.top.title("")
        # 设置窗口大小和位置
        window_width = 300
        window_height = 150
        screen_width = parent.winfo_screenwidth()
        screen_height = parent.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.top.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # 设置窗口样式
        self.top.configure(bg='#f8f9fa')
        self.top.transient(parent)  # 设置为父窗口的临时窗口
        self.top.grab_set()  # 模态窗口
        self.top.resizable(False, False)  # 禁止调整大小
        
        # 创建加载动画
        self.loading_frame = ttk.Frame(self.top, style='Preview.TFrame')
        self.loading_frame.pack(expand=True, fill='both')
        
        # 加载提示文字
        self.loading_label = ttk.Label(
            self.loading_frame,
            text="✨ 正在生成内容...",
            font=('微软雅黑', 14, 'bold'),
            style='Preview.TLabel'
        )
        self.loading_label.pack(pady=(20, 10))
        
        # 进度条
        self.progress = ttk.Progressbar(
            self.loading_frame,
            mode='indeterminate',
            length=200
        )
        self.progress.pack(pady=10)
        self.progress.start(10)  # 开始进度条动画
        
        # 提示文字
        self.tip_label = ttk.Label(
            self.loading_frame,
            text="请稍候，正在为您生成精美内容",
            font=('微软雅黑', 12),
            style='Preview.TLabel'
        )
        self.tip_label.pack(pady=10)
        
    def destroy(self):
        self.top.destroy()

# 在LoadingWindow类后面添加新的提示窗口类
class TipWindow:
    def __init__(self, parent, message, duration=2000):  # duration单位为毫秒
        self.top = tk.Toplevel(parent)
        self.top.title("")
        
        # 设置窗口样式
        self.top.configure(bg='#2c3e50')
        self.top.overrideredirect(True)  # 移除窗口边框
        self.top.attributes('-alpha', 0.95)  # 设置透明度
        
        # 创建主框架
        main_frame = tk.Frame(self.top, bg='#2c3e50')
        main_frame.pack(fill='both', expand=True)
        
        # 创建图标和消息的容器
        content_frame = tk.Frame(main_frame, bg='#2c3e50')
        content_frame.pack(pady=12, padx=20)
        
        # 根据消息类型选择图标
        icon = "❌" if "❌" in message else "✅" if "✅" in message else "ℹ️"
        message = message.replace("❌", "").replace("✅", "").strip()
        
        # 创建图标标签
        icon_label = tk.Label(
            content_frame,
            text=icon,
            font=('微软雅黑', 16),
            fg='white',
            bg='#2c3e50'
        )
        icon_label.pack(side='left', padx=(0, 10))
        
        # 创建消息标签
        self.label = tk.Label(
            content_frame,
            text=message,
            font=('微软雅黑', 13),
            fg='white',
            bg='#2c3e50',
            justify='left'
        )
        self.label.pack(side='left')
        
        # 添加底部装饰条
        decoration = tk.Frame(self.top, height=3, bg='#3498db')
        decoration.pack(side='bottom', fill='x')
        
        # 获取父窗口位置和大小
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        
        # 计算提示窗口位置（居中偏上显示）
        self.top.update_idletasks()  # 更新窗口大小
        window_width = self.top.winfo_width()
        window_height = self.top.winfo_height()
        x = parent_x + (parent_width - window_width) // 2
        y = parent_y + parent_height // 4  # 显示在窗口上方1/4处
        
        # 设置窗口位置
        self.top.geometry(f"+{x}+{y}")
        
        # 添加淡入淡出效果
        self.fade_in()
        
        # 设置定时器关闭窗口
        self.top.after(duration, self.fade_out)
    
    def fade_in(self):
        alpha = 0.0
        while alpha < 0.95:
            alpha += 0.1
            self.top.attributes('-alpha', alpha)
            self.top.update()
            self.top.after(20)
    
    def fade_out(self):
        alpha = 0.95
        while alpha > 0:
            alpha -= 0.1
            self.top.attributes('-alpha', alpha)
            self.top.update()
            self.top.after(20)
        self.destroy()
    
    def destroy(self):
        self.top.destroy()

# 小红书发布助手ui
class XiaohongshuUI:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("✨ 小红书发文助手") 
        self.window.geometry("1400x800") # 调整窗口尺寸
        self.window.configure(bg='#f8f9fa')
        
        # 设置窗口居中显示
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x = (screen_width - 1400) // 2
        y = (screen_height - 800) // 2
        self.window.geometry(f"1400x800+{x}+{y}")
        
        # 创建占位图
        placeholder = Image.new('RGB', (300, 300), '#f8f9fa')
        self.placeholder_photo = ImageTk.PhotoImage(placeholder)
        
        # 设置主题样式
        style = ttk.Style()
        style.theme_use('clam')
        
        # 自定义样式
        style.configure('TLabelframe', background='#f8f9fa', borderwidth=1)
        style.configure('TLabelframe.Label', font=('微软雅黑', 14, 'bold'), foreground='#2c3e50', background='#f8f9fa')
        style.configure('TButton', 
                       font=('微软雅黑', 13, 'bold'),
                       padding=10,
                       background='#4a90e2',
                       foreground='white',
                       borderwidth=0)
        style.configure('TLabel', font=('微软雅黑', 13), foreground='#34495e', background='#f8f9fa')
        style.configure('TEntry', 
                       padding=10,
                       font=('微软雅黑', 13),
                       fieldbackground='#ffffff',
                       borderwidth=1)
        
        # 预览区域样式
        style.configure('Preview.TFrame', background='#f8f9fa')
        style.configure('Preview.TLabel', background='#f8f9fa')
        
        # 初始化变量
        self.phone_var = tk.StringVar()
        self.country_code_var = tk.StringVar(value="+86") # 新增国家区号变量
        self.input_text = tk.StringVar()
        self.title_var = tk.StringVar() 
        self.subtitle_var = tk.StringVar()
        self.header_var = tk.StringVar(value="大模型技术分享")
        self.author_var = tk.StringVar(value="贝塔街的万事屋")
        
        # 国家区号字典
        self.country_codes = {
            "中国": "+86",
            "中国香港": "+852", 
            "中国台湾": "+886",
            "中国澳门": "+853",
            "新加坡": "+65",
            "马来西亚": "+60",
            "日本": "+81",
            "韩国": "+82",
            "美国": "+1",
            "加拿大": "+1",
            "英国": "+44",
            "法国": "+33",
            "德国": "+49",
            "意大利": "+39",
            "西班牙": "+34",
            "葡萄牙": "+351",
            "俄罗斯": "+7",
            "澳大利亚": "+61",
            "新西兰": "+64",
            "印度": "+91",
            "泰国": "+66",
            "越南": "+84",
            "菲律宾": "+63",
            "印度尼西亚": "+62",
            "阿联酋": "+971",
            "沙特阿拉伯": "+966",
            "巴西": "+55",
            "墨西哥": "+52",
            "南非": "+27",
            "埃及": "+20"
        }
        
        # 设置主容器
        self.main_container = ttk.Frame(self.window, padding="25 15 25 15")
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        self.create_widgets()
        
        self.images = []
        self.image_list = []
        self.current_image_index = 0  # 添加当前图片索引的初始化
        
    def create_widgets(self):
        # 手机号输入
        phone_frame = ttk.LabelFrame(self.main_container, text="🔐 登录信息", padding=15)
        phone_frame.pack(fill="x", pady=(0,15))
        
        # 新增国家区号下拉框
        ttk.Label(phone_frame, text="🌏 国家区号:").pack(side="left")
        country_combobox = ttk.Combobox(phone_frame, textvariable=self.country_code_var, width=15)
        country_combobox['values'] = [f"{country}({code})" for country, code in self.country_codes.items()]
        country_combobox.set("中国(+86)")  # 设置默认值
        country_combobox.pack(side="left", padx=15)
        
        # 当选择改变时更新country_code_var
        def on_country_select(event):
            selected = country_combobox.get()
            country_code = selected.split('(')[1].replace(')', '')
            self.country_code_var.set(country_code)
        country_combobox.bind('<<ComboboxSelected>>', on_country_select)
        
        ttk.Label(phone_frame, text="📱 手机号:").pack(side="left")
        phone_entry = ttk.Entry(phone_frame, textvariable=self.phone_var, width=30)
        phone_entry.pack(side="left", padx=15)
        login_btn = ttk.Button(phone_frame, text="🚀 登录", command=self.login, style='TButton')
        login_btn.pack(side="left")
        
        # 操作按钮区域
        button_frame = ttk.Frame(self.main_container)
        button_frame.pack(fill="x", pady=(0,15))
        
        generate_btn = ttk.Button(button_frame, text="✨ 生成内容", command=self.generate_content, style='TButton')
        generate_btn.pack(side="left", padx=(0,15))
        
        preview_btn = ttk.Button(button_frame, text="🎯 预览发布", command=self.preview_post, style='TButton')
        preview_btn.pack(side="left")

        # 左右布局容器
        content_container = ttk.Frame(self.main_container)
        content_container.pack(fill=tk.BOTH, expand=True)
        
        # 左侧内容区域
        left_frame = ttk.Frame(content_container)
        left_frame.pack(side="left", fill=tk.BOTH, expand=True, padx=(0,15))
         
        # 输入区域
        input_frame = ttk.LabelFrame(left_frame, text="✏️ 内容输入", padding=15)
        input_frame.pack(fill="both", expand=True, pady=(0,15))
        
        self.input_text_widget = scrolledtext.ScrolledText(
            input_frame, 
            height=8,
            font=('微软雅黑', 14),
            wrap=tk.WORD,
            bg='#f8f9fa',
            fg='#2c3e50',
            padx=10,
            pady=10
        )
        self.input_text_widget.pack(fill="both", expand=True)
        
        # 标题编辑区
        title_frame = ttk.LabelFrame(left_frame, text="📝 标题编辑", padding=15)
        title_frame.pack(fill="x")
        
        # 使用Grid布局管理标题区域
        for i, (label_text, var) in enumerate([
            ("📌 标题:", self.title_var),
            ("📄 内容:", self.subtitle_var),
            ("🏷️ 眉头标题:", self.header_var),
            ("👤 作者:", self.author_var)
        ]):
            ttk.Label(title_frame, text=label_text).grid(row=i, column=0, sticky="w", pady=8)
            if label_text == "📄 内容:":
                entry = ttk.Entry(title_frame, textvariable=var, width=45)
            else:
                entry = ttk.Entry(title_frame, textvariable=var, width=35)
            entry.grid(row=i, column=1, padx=15, pady=8, sticky="ew")
        
        title_frame.grid_columnconfigure(1, weight=1)
        
        # 右侧图片预览区
        self.preview_frame = ttk.LabelFrame(content_container, text="🖼️ 图片预览", padding=15)
        self.preview_frame.pack(side="right", fill="both", expand=True)
        
        # 创建图片预览的容器
        self.preview_container = ttk.Frame(self.preview_frame, style='Preview.TFrame')
        self.preview_container.pack(fill="both", expand=True)
        
        # 创建图片显示区域
        self.image_frame = ttk.Frame(self.preview_container, style='Preview.TFrame')
        self.image_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 创建图片标签
        self.image_label = ttk.Label(self.image_frame, style='Preview.TLabel')
        self.image_label.pack(expand=True)
        
        # 显示占位图
        self.image_label.configure(image=self.placeholder_photo)
        self.image_label.image = self.placeholder_photo
        
        # 创建标题标签
        self.image_title_label = ttk.Label(self.image_frame, text="暂无图片", font=('微软雅黑', 13, 'bold'), style='Preview.TLabel')
        self.image_title_label.pack(pady=(8,0))
        
        # 创建按钮区域
        button_frame = ttk.Frame(self.preview_container, style='Preview.TFrame')
        button_frame.pack(fill="x", pady=(0,10))
        
        # 添加左右切换按钮
        self.prev_btn = ttk.Button(button_frame, text="◀️ 上一张", command=self.prev_image)
        self.prev_btn.pack(side="left", padx=5)
        
        self.next_btn = ttk.Button(button_frame, text="下一张 ▶️", command=self.next_image)
        self.next_btn.pack(side="right", padx=5)
        
        # 初始化时禁用按钮
        self.prev_btn.state(['disabled'])
        self.next_btn.state(['disabled'])

    def login(self):
        try:
            phone = self.phone_var.get()
            country_code = self.country_code_var.get()
            if not phone:
                messagebox.showerror("❌ 错误", "请输入手机号")
                return
                
            self.poster = XiaohongshuPoster()
            self.poster.login(phone, country_code=country_code)
            messagebox.showinfo("✅ 成功", "登录成功")
        except Exception as e:
            messagebox.showerror("❌ 错误", f"登录失败: {str(e)}")

    def generate_content(self):
        try:
            input_text = self.input_text_widget.get("1.0", tk.END).strip()
            if not input_text:
                messagebox.showerror("❌ 错误", "请输入内容")
                return
            
            # 显示加载窗口
            loading_window = LoadingWindow(self.window)
            
            # 创建线程执行生成内容的操作
            def generate():
                try:
                    workflow_id = "7431484143153070132"
                    parameters = {
                        "BOT_USER_INPUT": input_text,
                        "HEADER_TITLE": self.header_var.get(),
                        "AUTHOR": self.author_var.get()
                    }
                    
                    # 调用API
                    response = requests.post(
                        "http://8.137.103.115:8081/workflow/run",
                        json={
                            "workflow_id": workflow_id,
                            "parameters": parameters
                        }
                    )
                    print(response.content)
                    
                    if response.status_code != 200:
                        raise Exception("API调用失败")
                        
                    res = response.json()
                    
                    # 解析返回结果
                    print(res)
                    output_data = json.loads(res['data'])
                    title = json.loads(output_data['output'])['title']
                    
                    # 在主线程中更新UI
                    self.window.after(0, lambda: self.update_ui_after_generate(
                        title,
                        output_data['content'],
                        json.loads(res['data'])['image'],
                        json.loads(res['data'])['image_content'],
                        input_text
                    ))
                    
                except Exception as e:
                    import traceback
                    error_details = traceback.format_exc()
                    self.window.after(0, lambda: messagebox.showerror("❌ 错误", f"生成内容失败: {str(e)}\n{error_details}"))
                finally:
                    # 关闭加载窗口
                    self.window.after(0, loading_window.destroy)
            
            # 启动线程
            threading.Thread(target=generate, daemon=True).start()
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            messagebox.showerror("❌ 错误", f"生成内容失败: {str(e)}\n{error_details}")
            
    def update_ui_after_generate(self, title, content, cover_image_url, content_image_urls, input_text):
        """在主线程中更新UI"""
        # 更新标题和内容
        self.title_var.set(title)
        self.subtitle_var.set(content)
        
        # 清空之前的图片列表
        self.images = []
        self.image_list = []
        self.current_image_index = 0
        
        # 下载并显示图片
        self.download_and_show_image(cover_image_url, "封面图")
        for i, url in enumerate(content_image_urls):
            self.download_and_show_image(url, f"内容图{i+1}")
        
        # 显示第一张图片
        if self.image_list:
            self.show_current_image()
            
        # 显示生成的内容
        self.input_text_widget.delete("1.0", tk.END)
        self.input_text_widget.insert("1.0", input_text)

    def download_and_show_image(self, url, title):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                # 保存图片
                img_path = os.path.join(os.path.dirname(__file__), f'/static/images/{title}.jpg')
                with open(img_path, 'wb') as f:
                    f.write(response.content)
                self.images.append(img_path)
                
                # 显示图片预览
                image = Image.open(io.BytesIO(response.content))
                # 计算合适的图片大小，保持宽高比
                display_size = (300, 300)  # 目标显示大小
                image.thumbnail(display_size, Image.LANCZOS)
                photo = ImageTk.PhotoImage(image)
                
                # 保存图片和标题信息
                self.image_list.append({
                    'photo': photo,
                    'title': title
                })
                
        except Exception as e:
            print(f"下载图片失败: {str(e)}")

    def show_current_image(self):
        if not self.image_list:
            # 如果没有图片，显示占位图
            self.image_label.configure(image=self.placeholder_photo)
            self.image_label.image = self.placeholder_photo
            self.image_title_label.configure(text="暂无图片")
            self.update_button_states()
            return
            
        current_image = self.image_list[self.current_image_index]
        self.image_label.configure(image=current_image['photo'])
        self.image_label.image = current_image['photo']  # 保持引用
        self.image_title_label.configure(text=current_image['title'])
        self.update_button_states()
        print(f"当前图片索引: {self.current_image_index}, 总图片数: {len(self.image_list)}")  # 添加调试信息

    def update_button_states(self):
        if not self.image_list:
            self.prev_btn.state(['disabled'])
            self.next_btn.state(['disabled'])
            return
            
        # 当有图片时，按钮永远可用，因为是循环切换
        self.prev_btn.state(['!disabled'])
        self.next_btn.state(['!disabled'])

    def prev_image(self):
        if self.image_list:
            # 循环切换到上一张，如果是第一张则切换到最后一张
            self.current_image_index = (self.current_image_index - 1) % len(self.image_list)
            self.show_current_image()

    def next_image(self):
        if self.image_list:
            # 循环切换到下一张，如果是最后一张则切换到第一张
            self.current_image_index = (self.current_image_index + 1) % len(self.image_list)
            self.show_current_image()

    def preview_post(self):
        try:
            if not hasattr(self, 'poster'):
                # 显示自定义提示
                TipWindow(self.window, "❌ 请先登录")
                return
                
            title = self.title_var.get()
            content = self.subtitle_var.get()
                
            self.poster.post_article(title, content, self.images)
            # 显示成功提示
            TipWindow(self.window, "🎉 文章已准备好，请在浏览器中检查并发布")
            
        except Exception as e:
            # 显示错误提示
            TipWindow(self.window, f"❌ 预览发布失败: {str(e)}")

    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    app = XiaohongshuUI()
    app.run()