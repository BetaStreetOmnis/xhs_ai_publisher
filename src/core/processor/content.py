import json
import traceback
import time
from PyQt5.QtCore import QThread, pyqtSignal
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

# 导入备用生成器
from .content_backup import BackupContentGenerator


"""历史版本，基于coze生成图片 - 增强版错误处理 + 故障转移"""

class ContentGeneratorThread(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, input_text, header_title, author, generate_btn):
        super().__init__()
        self.input_text = input_text
        self.header_title = header_title
        self.author = author
        self.generate_btn = generate_btn
        self.max_retries = 2  # 减少重试次数，更快切换到备用方案
        self.retry_delay = 2  # 减少重试间隔
        self.use_backup = False

    def run(self):
        """主运行方法，包含重试逻辑和故障转移"""
        retry_count = 0
        
        # 首先尝试主API
        while retry_count < self.max_retries:
            try:
                print(f"🚀 开始第 {retry_count + 1} 次尝试生成内容...")
                self._generate_content()
                return  # 成功则退出
            except Exception as e:
                retry_count += 1
                error_msg = str(e)
                
                if retry_count < self.max_retries:
                    print(f"⚠️ 第 {retry_count} 次尝试失败: {error_msg}")
                    print(f"🔄 {self.retry_delay} 秒后进行第 {retry_count + 1} 次重试...")
                    
                    # 更新按钮状态显示重试信息
                    self.generate_btn.setText(f"⏳ 重试中({retry_count + 1}/{self.max_retries})...")
                    
                    time.sleep(self.retry_delay)
                else:
                    print(f"❌ 主API所有 {self.max_retries} 次尝试都失败了")
                    print("🔄 切换到备用内容生成器...")
                    break
        
        # 如果主API失败，使用备用生成器
        try:
            self._use_backup_generator()
        except Exception as e:
            error_msg = f"主API和备用生成器都失败了: {str(e)}"
            print(f"❌ {error_msg}")
            self.error.emit(error_msg)
            # 恢复按钮状态
            self.generate_btn.setText("✨ 生成内容")
            self.generate_btn.setEnabled(True)

    def _use_backup_generator(self):
        """使用备用生成器"""
        print("🔄 启动备用内容生成器...")
        
        # 创建备用生成器实例
        backup_generator = BackupContentGenerator(
            self.input_text,
            self.header_title,
            self.author,
            self.generate_btn
        )
        
        # 连接信号
        backup_generator.finished.connect(self._handle_backup_result)
        backup_generator.error.connect(self._handle_backup_error)
        
        # 运行备用生成器（同步运行）
        backup_generator.run()

    def _handle_backup_result(self, result):
        """处理备用生成器的结果"""
        print("✅ 备用内容生成成功，发送结果...")
        self.finished.emit(result)

    def _handle_backup_error(self, error_msg):
        """处理备用生成器的错误"""
        print(f"❌ 备用生成器也失败了: {error_msg}")
        self.error.emit(error_msg)

    def _generate_content(self):
        """实际的内容生成逻辑（主API）"""
        try:
            # 更新按钮状态
            self.generate_btn.setText("⏳ 生成中...")
            self.generate_btn.setEnabled(False)

            # 打印详细的输入信息
            print("=" * 60)
            print("🚀 开始生成内容...")
            print(f"📝 输入内容: {self.input_text[:100]}{'...' if len(self.input_text) > 100 else ''}")
            print(f"🏷️ 眉头标题: {self.header_title}")
            print(f"👤 作者: {self.author}")
            print("=" * 60)

            workflow_id = "7431484143153070132"
            parameters = {
                "BOT_USER_INPUT": self.input_text,
                "HEADER_TITLE": self.header_title,
                "AUTHOR": self.author
            }

            api_url = "http://8.137.103.115:8081/workflow/run"
            print(f"🌐 API地址: {api_url}")
            print(f"📦 工作流ID: {workflow_id}")
            print(f"📋 请求参数: {parameters}")

            # 发送API请求
            print("📡 发送API请求...")
            try:
                response = requests.post(
                    api_url,
                    json={
                        "workflow_id": workflow_id,
                        "parameters": parameters
                    },
                    timeout=30,  # 减少超时时间，更快故障转移
                    headers={
                        'Content-Type': 'application/json',
                        'User-Agent': 'XhsAiPublisher/1.0',
                        'Accept': 'application/json'
                    }
                )
                
                print(f"✅ API请求发送成功")
                print(f"📊 响应状态码: {response.status_code}")
                print(f"📄 响应头信息: {dict(response.headers)}")
                
            except ConnectionError as e:
                error_msg = f"网络连接失败: {str(e)}"
                print(f"❌ {error_msg}")
                raise Exception(error_msg)
            except Timeout as e:
                error_msg = f"API请求超时（30秒）: {str(e)}"
                print(f"❌ {error_msg}")
                raise Exception(error_msg)
            except RequestException as e:
                error_msg = f"API请求异常: {str(e)}"
                print(f"❌ {error_msg}")
                raise Exception(error_msg)

            # 检查HTTP状态码
            if response.status_code != 200:
                error_detail = ""
                try:
                    error_detail = response.text[:200]
                    print(f"❌ API错误响应: {error_detail}")
                except:
                    error_detail = "无法获取错误详情"
                
                error_msg = f"API调用失败，状态码: {response.status_code}"
                if response.status_code == 400:
                    error_msg += " - 请求参数错误或API格式已更改"
                elif response.status_code == 404:
                    error_msg += " - API接口不存在"
                elif response.status_code == 500:
                    error_msg += " - 服务器内部错误"
                elif response.status_code == 502:
                    error_msg += " - 网关错误，服务不可用"
                elif response.status_code == 403:
                    error_msg += " - 访问被拒绝"
                
                raise Exception(error_msg)

            # 解析响应数据
            try:
                response_text = response.text
                print(f"📝 API原始响应长度: {len(response_text)} 字符")
                print(f"📝 API响应前500字符: {response_text[:500]}")
                
                res = response.json()
                print(f"✅ JSON解析成功")
                print(f"📊 响应数据键: {list(res.keys())}")
                
            except json.JSONDecodeError as e:
                error_msg = f"API响应JSON解析失败: {str(e)}"
                print(f"❌ {error_msg}")
                raise Exception(error_msg)

            # 验证响应数据结构
            if 'data' not in res:
                error_msg = f"API响应格式错误，缺少'data'字段"
                print(f"❌ {error_msg}")
                raise Exception(error_msg)
            
            try:
                output_data = json.loads(res['data'])
                print(f"✅ 输出数据解析成功")
                print(f"📊 输出数据键: {list(output_data.keys())}")
                
            except json.JSONDecodeError as e:
                error_msg = f"输出数据JSON解析失败: {str(e)}"
                print(f"❌ {error_msg}")
                raise Exception(error_msg)
            
            # 验证必需字段
            required_fields = ['output', 'content']
            missing_fields = []
            for field in required_fields:
                if field not in output_data:
                    missing_fields.append(field)
            
            if missing_fields:
                error_msg = f"输出数据缺少必需字段: {missing_fields}"
                print(f"❌ {error_msg}")
                raise Exception(error_msg)
            
            # 解析标题数据
            try:
                title_data = json.loads(output_data['output'])
                print(f"✅ 标题数据解析成功")
                
                if 'title' not in title_data:
                    error_msg = f"标题数据格式错误，缺少'title'字段"
                    print(f"❌ {error_msg}")
                    raise Exception(error_msg)
                
                title = title_data['title']
                
            except json.JSONDecodeError as e:
                error_msg = f"标题数据JSON解析失败: {str(e)}"
                print(f"❌ {error_msg}")
                raise Exception(error_msg)
            
            # 检查图片相关字段
            try:
                full_data = json.loads(res['data'])
                image_fields = ['image', 'image_content']
                for field in image_fields:
                    if field not in full_data:
                        print(f"⚠️ 警告: 缺少图片字段 '{field}'，将使用空值")
                
                cover_image = full_data.get('image', '')
                content_images = full_data.get('image_content', [])
                
            except Exception as e:
                print(f"⚠️ 图片数据处理警告: {str(e)}")
                cover_image = ''
                content_images = []

            # 构建结果
            result = {
                'title': title,
                'content': output_data['content'],
                'cover_image': cover_image,
                'content_images': content_images,
                'input_text': self.input_text
            }
            
            # 打印成功信息
            print("🎉 内容生成成功!")
            print(f"📌 标题: {title}")
            print(f"📄 内容长度: {len(result['content'])} 字符")
            print(f"📄 内容预览: {result['content'][:100]}...")
            print(f"🖼️ 封面图片: {'有' if cover_image else '无'}")
            print(f"📸 内容图片数量: {len(content_images) if isinstance(content_images, list) else 0}")
            print("=" * 60)

            self.finished.emit(result)
                
        except Exception as e:
            error_msg = str(e)
            print(f"❌ 主API生成内容失败: {error_msg}")
            print(f"🔍 详细错误信息:")
            print(traceback.format_exc())
            print("=" * 60)
            raise e
        finally:
            # 只有在不使用备用生成器时才恢复按钮状态
            if not self.use_backup:
                if hasattr(self, 'generate_btn'):
                    self.generate_btn.setText("✨ 生成内容")
                    self.generate_btn.setEnabled(True)