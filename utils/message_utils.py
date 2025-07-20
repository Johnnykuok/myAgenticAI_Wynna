"""
消息处理工具模块
提供统一的消息处理功能
"""
from typing import Dict, Any, List
from .timestamp_utils import add_timestamp_to_message


def create_user_message(content: str) -> Dict[str, Any]:
    """
    创建用户消息
    
    Args:
        content: 消息内容
        
    Returns:
        Dict[str, Any]: 用户消息字典
    """
    message = {
        "role": "user",
        "content": content
    }
    return add_timestamp_to_message(message)


def create_assistant_message(content: str) -> Dict[str, Any]:
    """
    创建助手消息
    
    Args:
        content: 消息内容
        
    Returns:
        Dict[str, Any]: 助手消息字典
    """
    message = {
        "role": "assistant",
        "content": content
    }
    return add_timestamp_to_message(message)


def create_system_message(content: str) -> Dict[str, Any]:
    """
    创建系统消息
    
    Args:
        content: 消息内容
        
    Returns:
        Dict[str, Any]: 系统消息字典
    """
    return {
        "role": "system",
        "content": content
    }


def create_tool_message(tool_call_id: str, name: str, content: str) -> Dict[str, Any]:
    """
    创建工具消息
    
    Args:
        tool_call_id: 工具调用ID
        name: 工具名称
        content: 工具返回内容
        
    Returns:
        Dict[str, Any]: 工具消息字典
    """
    message = {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "name": name,
        "content": content
    }
    return add_timestamp_to_message(message)


def merge_messages_preserve_timestamps(existing_messages: List[Dict[str, Any]], 
                                     new_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    合并消息，保护已有的时间戳不被覆盖
    
    Args:
        existing_messages: 已有消息列表
        new_messages: 新消息列表
        
    Returns:
        List[Dict[str, Any]]: 合并后的消息列表
    """
    if not existing_messages:
        return new_messages
    
    if not new_messages:
        return existing_messages
    
    # 创建一个已有消息的映射，用于查找已有的时间戳
    existing_map = {}
    for i, msg in enumerate(existing_messages):
        key = f"{msg.get('role', '')}-{msg.get('content', '')}"
        existing_map[key] = i
    
    # 处理新消息，保护已有的时间戳
    merged_messages = []
    for new_msg in new_messages:
        key = f"{new_msg.get('role', '')}-{new_msg.get('content', '')}"
        
        # 如果在已有消息中找到相同的消息，保留原有的时间戳
        if key in existing_map:
            existing_msg = existing_messages[existing_map[key]]
            if 'timestamp' in existing_msg:
                # 保留原有的时间戳
                merged_msg = dict(new_msg)
                merged_msg['timestamp'] = existing_msg['timestamp']
                merged_messages.append(merged_msg)
            else:
                # 如果原有消息没有时间戳，使用新消息的时间戳
                merged_messages.append(new_msg)
        else:
            # 如果是新消息，直接添加
            merged_messages.append(new_msg)
    
    return merged_messages