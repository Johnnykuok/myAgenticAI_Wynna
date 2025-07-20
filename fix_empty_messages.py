#!/usr/bin/env python3
"""
修复对话文件中的空白消息
"""

import os
import json
import glob
from typing import Dict, Any, List

def clean_empty_messages(conversation_file: str) -> bool:
    """清理对话文件中的空白消息"""
    try:
        with open(conversation_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, dict) or 'messages' not in data:
            print(f"跳过非标准格式文件: {conversation_file}")
            return False
        
        original_count = len(data['messages'])
        cleaned_messages = []
        
        for msg in data['messages']:
            # 跳过空白的assistant消息
            if (msg.get('role') == 'assistant' and 
                not msg.get('content', '').strip() and 
                not msg.get('tool_calls')):
                print(f"删除空白assistant消息: {msg.get('timestamp', 'unknown')}")
                continue
            
            # 跳过无效的工具调用
            if msg.get('role') == 'assistant' and msg.get('tool_calls'):
                valid_tool_calls = []
                for tool_call in msg['tool_calls']:
                    if (tool_call.get('function', {}).get('name', '').strip() and
                        tool_call.get('id', '').strip()):
                        valid_tool_calls.append(tool_call)
                
                if valid_tool_calls:
                    msg['tool_calls'] = valid_tool_calls
                    cleaned_messages.append(msg)
                elif msg.get('content', '').strip():
                    # 移除无效的tool_calls，保留有内容的消息
                    del msg['tool_calls']
                    cleaned_messages.append(msg)
                else:
                    print(f"删除无效工具调用消息: {msg.get('timestamp', 'unknown')}")
                    continue
            else:
                cleaned_messages.append(msg)
            
        # 清理无效的tool消息
        for i, msg in enumerate(cleaned_messages[:]):
            if (msg.get('role') == 'tool' and 
                not msg.get('name', '').strip()):
                print(f"删除无效tool消息: {msg.get('tool_call_id', 'unknown')}")
                cleaned_messages.remove(msg)
        
        # 如果有改动，保存清理后的文件
        if len(cleaned_messages) != original_count:
            data['messages'] = cleaned_messages
            
            # 备份原文件
            backup_file = conversation_file + '.backup'
            os.rename(conversation_file, backup_file)
            
            # 保存清理后的文件
            with open(conversation_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 清理完成: {conversation_file}")
            print(f"   原消息数: {original_count}, 清理后: {len(cleaned_messages)}")
            print(f"   备份文件: {backup_file}")
            return True
        else:
            print(f"✓ 无需清理: {conversation_file}")
            return False
            
    except Exception as e:
        print(f"❌ 处理失败: {conversation_file} - {e}")
        return False

def main():
    """主函数"""
    conversations_dir = "conversations"
    
    if not os.path.exists(conversations_dir):
        print(f"对话目录不存在: {conversations_dir}")
        return
    
    # 获取所有对话文件
    pattern = os.path.join(conversations_dir, "*.json")
    conversation_files = glob.glob(pattern)
    
    if not conversation_files:
        print("未找到对话文件")
        return
    
    print(f"发现 {len(conversation_files)} 个对话文件")
    
    cleaned_count = 0
    for conv_file in conversation_files:
        if clean_empty_messages(conv_file):
            cleaned_count += 1
    
    print(f"\n✅ 处理完成!")
    print(f"总文件数: {len(conversation_files)}")
    print(f"清理文件数: {cleaned_count}")
    print(f"无需清理: {len(conversation_files) - cleaned_count}")

if __name__ == "__main__":
    main()