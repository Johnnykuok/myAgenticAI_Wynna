"""
时间戳工具模块
提供统一的时间戳处理功能
"""
from datetime import datetime
from typing import Dict, Any, Optional


def get_current_timestamp() -> str:
    """
    获取当前时间的ISO格式字符串
    
    Returns:
        str: ISO格式的时间戳字符串
    """
    return datetime.now().isoformat()


def add_timestamp_to_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """
    为消息添加时间戳（如果没有的话）
    
    Args:
        message: 消息字典
        
    Returns:
        Dict[str, Any]: 添加时间戳后的消息字典
    """
    if 'timestamp' not in message and message.get('role') in ['user', 'assistant']:
        message['timestamp'] = get_current_timestamp()
    return message


def ensure_messages_have_timestamps(messages: list) -> list:
    """
    确保消息列表中的所有消息都有时间戳
    
    Args:
        messages: 消息列表
        
    Returns:
        list: 包含时间戳的消息列表
    """
    return [add_timestamp_to_message(msg) for msg in messages]


def format_timestamp_for_display(timestamp: Optional[str]) -> str:
    """
    格式化时间戳用于前端显示
    
    Args:
        timestamp: ISO格式的时间戳字符串
        
    Returns:
        str: 格式化的时间戳字符串，格式：YYYY年MM月DD日HH:mm:ss
    """
    if not timestamp:
        return ''
    
    try:
        dt = datetime.fromisoformat(timestamp)
        return dt.strftime('%Y年%m月%d日%H:%M:%S')
    except (ValueError, AttributeError):
        return timestamp