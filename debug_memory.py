#!/usr/bin/env python3
"""调试历史记忆功能"""

import sys
import os
import json
sys.path.append(os.path.dirname(__file__))

from main import load_conversation, limit_conversation_history

def debug_conversation(conversation_id):
    """调试特定对话的历史记忆"""
    
    print(f"调试对话ID: {conversation_id}")
    
    # 加载原始对话
    messages = load_conversation(conversation_id)
    print(f"\n原始对话消息数: {len(messages)}")
    for i, msg in enumerate(messages):
        content = msg.get('content', f"[{msg.get('name', 'tool')}]")
        print(f"  {i}: {msg['role']} - {content}")
    
    # 添加系统消息（如果没有）
    if not messages or messages[0].get('role') != 'system':
        system_msg = {"role": "system", "content":"你是由郭桓君同学开发的智能体。你的人设是一个讲话活泼可爱、情商高的小妹妹"}
        messages = [system_msg] + messages
        print(f"\n添加系统消息后: {len(messages)}")
    
    # 限制历史对话
    limited = limit_conversation_history(messages, max_rounds=3)
    print(f"\n限制后消息数: {len(limited)}")
    for i, msg in enumerate(limited):
        content = msg.get('content', f"[{msg.get('name', 'tool')}]")
        print(f"  {i}: {msg['role']} - {content}")
    
    # 模拟添加新的用户消息
    limited.append({"role": "user", "content": "新消息：测试记忆功能"})
    print(f"\n添加新用户消息后: {len(limited)}")
    for i, msg in enumerate(limited):
        content = msg.get('content', f"[{msg.get('name', 'tool')}]")
        print(f"  {i}: {msg['role']} - {content}")
    
    # 统计用户消息轮数
    user_messages = [msg for msg in limited if msg['role'] == 'user']
    print(f"\n用户消息轮数: {len(user_messages)}")
    
    return limited

if __name__ == "__main__":
    conversation_id = "f0d5600a-60e0-433a-85be-9b32da4af09d"
    debug_conversation(conversation_id)