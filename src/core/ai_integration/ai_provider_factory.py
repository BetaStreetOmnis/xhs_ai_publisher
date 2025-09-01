from typing import Optional, Dict, Any
from .kimi_adapter import KimiAdapter
from .qwen_adapter import QwenAdapter

class AIProviderFactory:
    """AI服务提供商工厂"""
    
    PROVIDERS = {
        'kimi': {
            'name': 'Kimi AI',
            'description': '月之暗面Kimi大模型',
            'adapter': KimiAdapter,
            'website': 'https://platform.moonshot.cn/'
        },
        'qwen': {
            'name': '通义千问',
            'description': '阿里云通义千问大模型',
            'adapter': QwenAdapter,
            'website': 'https://dashscope.aliyun.com/'
        }
    }
    
    @staticmethod
    def create_provider(provider_type: str, api_key: str) -> Optional[object]:
        """创建对应的AI服务实例"""
        if provider_type not in AIProviderFactory.PROVIDERS:
            raise ValueError(f"不支持的服务商: {provider_type}")
        
        adapter_class = AIProviderFactory.PROVIDERS[provider_type]['adapter']
        return adapter_class(api_key)
    
    @staticmethod
    def get_provider_info(provider_type: str) -> Optional[Dict[str, Any]]:
        """获取服务商信息"""
        return AIProviderFactory.PROVIDERS.get(provider_type)
    
    @staticmethod
    def list_providers() -> Dict[str, Dict[str, Any]]:
        """列出所有支持的服务商"""
        return AIProviderFactory.PROVIDERS
    
    @staticmethod
    def is_provider_supported(provider_type: str) -> bool:
        """检查是否支持指定服务商"""
        return provider_type in AIProviderFactory.PROVIDERS