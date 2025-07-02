#!/usr/bin/env python3
"""调试缓存状态"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

# 打印缓存状态
from main import conversation_summary_cache

print("当前缓存状态:")
print(f"缓存数量: {len(conversation_summary_cache)}")
for conversation_id, summary in conversation_summary_cache.items():
    print(f"  {conversation_id[:8]}: {summary}")

if len(conversation_summary_cache) == 0:
    print("缓存为空！这可能是问题所在。")