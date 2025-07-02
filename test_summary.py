#!/usr/bin/env python3
"""测试AI总结功能"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from main import generate_conversation_summary

def test_summary_generation():
    """测试AI总结生成功能"""
    
    test_messages = [
        "请帮我写一个Python的爬虫程序来获取股票价格数据",
        "今天北京的天气怎么样？",
        "现在几点了？",
        "我想学习机器学习算法",
        "帮我制定一个健身计划"
    ]
    
    print("测试AI总结生成功能...")
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n测试{i}:")
        print(f"原始消息: {message}")
        
        try:
            summary = generate_conversation_summary(message)
            print(f"AI总结: {summary} (长度: {len(summary)})")
        except Exception as e:
            print(f"生成失败: {e}")

if __name__ == "__main__":
    test_summary_generation()