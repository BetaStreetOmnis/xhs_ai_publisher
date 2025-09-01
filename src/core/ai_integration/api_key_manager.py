import os
import json
from typing import Dict, Optional
from cryptography.fernet import Fernet
import base64

class APIKeyManager:
    """用户API密钥管理器 - 本地加密存储"""
    
    def __init__(self):
        self.keys_dir = os.path.expanduser('~/.xhs_system')
        self.keys_file = os.path.join(self.keys_dir, 'keys.enc')
        self._ensure_keys_dir()
        self._init_encryption()
    
    def _ensure_keys_dir(self):
        """确保密钥目录存在"""
        if not os.path.exists(self.keys_dir):
            os.makedirs(self.keys_dir, mode=0o700)
    
    def _init_encryption(self):
        """初始化加密"""
        key_file = os.path.join(self.keys_dir, '.encryption_key')
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            os.chmod(key_file, 0o600)
        
        self.cipher = Fernet(key)
    
    def add_key(self, provider: str, key_name: str, api_key: str) -> bool:
        """添加API密钥"""
        try:
            keys = self._load_keys()
            if provider not in keys:
                keys[provider] = {}
            
            encrypted_key = self.cipher.encrypt(api_key.encode()).decode()
            keys[provider][key_name] = encrypted_key
            
            self._save_keys(keys)
            return True
        except Exception as e:
            print(f"添加密钥失败: {e}")
            return False
    
    def get_key(self, provider: str, key_name: str) -> Optional[str]:
        """获取指定密钥"""
        try:
            keys = self._load_keys()
            if provider in keys and key_name in keys[provider]:
                encrypted_key = keys[provider][key_name]
                return self.cipher.decrypt(encrypted_key.encode()).decode()
            return None
        except Exception as e:
            print(f"获取密钥失败: {e}")
            return None
    
    def list_keys(self) -> Dict[str, list]:
        """列出所有密钥（不显示实际密钥）"""
        try:
            keys = self._load_keys()
            result = {}
            for provider, key_dict in keys.items():
                result[provider] = list(key_dict.keys())
            return result
        except Exception:
            return {}
    
    def remove_key(self, provider: str, key_name: str) -> bool:
        """删除指定密钥"""
        try:
            keys = self._load_keys()
            if provider in keys and key_name in keys[provider]:
                del keys[provider][key_name]
                self._save_keys(keys)
                return True
            return False
        except Exception as e:
            print(f"删除密钥失败: {e}")
            return False
    
    def _load_keys(self) -> Dict:
        """加载密钥"""
        if not os.path.exists(self.keys_file):
            return {}
        
        try:
            with open(self.keys_file, 'r') as f:
                content = f.read()
                if content:
                    return json.loads(content)
                return {}
        except Exception:
            return {}
    
    def _save_keys(self, keys: Dict) -> None:
        """保存密钥"""
        try:
            with open(self.keys_file, 'w') as f:
                json.dump(keys, f, indent=2)
            os.chmod(self.keys_file, 0o600)
        except Exception as e:
            print(f"保存密钥失败: {e}")

# 全局单例
api_key_manager = APIKeyManager()