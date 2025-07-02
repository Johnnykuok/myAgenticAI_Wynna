#!/usr/bin/env python3
"""测试历史记忆功能"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from main import limit_conversation_history

def test_limit_conversation_history():
    """测试对话历史限制功能"""
    
    # 测试用例1：超过3轮的对话
    test_messages = [
        {"role": "system", "content": "你是AI助手"},
        
        # 第1轮
        {"role": "user", "content": "第1轮：你好"},
        {"role": "assistant", "content": "第1轮：你好！我是AI助手"},
        
        # 第2轮
        {"role": "user", "content": "第2轮：今天天气怎么样？"},
        {"role": "assistant", "content": "第2轮：我可以帮你查询天气"},
        {"role": "tool", "tool_call_id": "call_123", "name": "get_weather", "content": "晴天"},
        {"role": "assistant", "content": "第2轮：今天是晴天"},
        
        # 第3轮
        {"role": "user", "content": "第3轮：现在几点了？"},
        {"role": "assistant", "content": "第3轮：我来查询时间"},
        {"role": "tool", "tool_call_id": "call_456", "name": "get_time", "content": "15:30"},
        {"role": "assistant", "content": "第3轮：现在是15:30"},
        
        # 第4轮（应该被丢弃）
        {"role": "user", "content": "第4轮：谢谢"},
        {"role": "assistant", "content": "第4轮：不客气"},
        
        # 第5轮（应该被丢弃）
        {"role": "user", "content": "第5轮：再见"},
        {"role": "assistant", "content": "第5轮：再见！"}
    ]
    
    print("原始消息数量:", len(test_messages))
    print("原始消息:")
    for i, msg in enumerate(test_messages):
        print(f"  {i}: {msg['role']} - {msg['content'][:30]}")
    
    # 限制为3轮
    limited = limit_conversation_history(test_messages, max_rounds=3)
    
    print(f"\n限制后消息数量: {len(limited)}")
    print("限制后的消息:")
    for i, msg in enumerate(limited):
        content = msg.get('content', f"[{msg.get('name', 'tool')}]")
        print(f"  {i}: {msg['role']} - {content[:30]}")
    
    # 验证结果
    user_messages = [msg for msg in limited if msg['role'] == 'user']
    print(f"\n用户消息轮数: {len(user_messages)}")
    for i, msg in enumerate(user_messages):
        print(f"  轮{i+1}: {msg['content']}")
    
    # 检查是否保留了系统消息
    system_messages = [msg for msg in limited if msg['role'] == 'system']
    print(f"\n系统消息数量: {len(system_messages)}")
    
    return len(user_messages) <= 3 and len(system_messages) > 0

if __name__ == "__main__":
    print("测试历史记忆功能...")
    success = test_limit_conversation_history()
    print(f"\n测试结果: {'成功' if success else '失败'}")