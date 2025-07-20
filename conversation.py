import json
import os
import threading
from datetime import datetime
from config import CONVERSATIONS_DIR, get_openai_client, DOUBAO_MODEL
from utils.message_utils import merge_messages_preserve_timestamps
from utils.timestamp_utils import get_current_timestamp

# 对话总结缓存
conversation_summary_cache = {}

def save_conversation(conversation_id, messages, summary=None, mode=None):
    """保存对话历史到文件。保护已有的时间戳不被覆盖"""
    conversation_file = os.path.join(CONVERSATIONS_DIR, f"{conversation_id}.json")
    
    # 加载现有数据（如果存在）
    existing_data = {}
    existing_messages = []
    if os.path.exists(conversation_file):
        try:
            with open(conversation_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                if isinstance(existing_data, dict) and "messages" in existing_data:
                    existing_messages = existing_data["messages"]
                elif isinstance(existing_data, list):
                    existing_messages = existing_data
        except:
            pass
    
    # 合并消息，保护已有的时间戳
    merged_messages = merge_messages_preserve_timestamps(existing_messages, messages)
    
    # 构建新数据
    data = {
        "messages": merged_messages
    }
    
    # 保留或更新总结
    if summary:
        data["summary"] = summary
    elif conversation_id in conversation_summary_cache:
        data["summary"] = conversation_summary_cache[conversation_id]
    elif "summary" in existing_data:
        data["summary"] = existing_data["summary"]
    
    # 保留或更新模式信息
    if mode:
        data["mode"] = mode
    elif "mode" in existing_data:
        data["mode"] = existing_data["mode"]
    
    with open(conversation_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_conversation(conversation_id):
    """从文件加载对话历史"""
    conversation_file = os.path.join(CONVERSATIONS_DIR, f"{conversation_id}.json")
    if os.path.exists(conversation_file):
        try:
            with open(conversation_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # 兼容旧格式（直接是消息列表）和新格式（包含messages和summary）
                if isinstance(data, list):
                    return data  # 旧格式
                elif isinstance(data, dict) and "messages" in data:
                    # 新格式，同时加载总结到缓存
                    if "summary" in data and conversation_id not in conversation_summary_cache:
                        conversation_summary_cache[conversation_id] = data["summary"]
                    return data["messages"]
                else:
                    return []
        except json.JSONDecodeError as e:
            print(f"JSON解析错误 {conversation_id}: {e}")
            return []
    return []

def generate_conversation_summary(user_message):
    """同步生成对话总结"""
    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model=DOUBAO_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": """为用户消息生成一个简短的总结，用于对话历史显示。

请以JSON格式输出，格式如下：
{
    "summary": "简短总结"
}

要求：
1. summary不超过16个中文字符
2. 要准确概括用户消息的核心内容
3. 避免使用标点符号和引号"""
                },
                {
                    "role": "user", 
                    "content": user_message[:200]
                }
            ],
            max_tokens=20,
            temperature=0.1,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "conversation_summary",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "summary": {
                                "type": "string",
                                "description": "对话的简短总结，不超过16个中文字符"
                            }
                        },
                        "required": ["summary"],
                        "additionalProperties": False
                    },
                    "strict": True
                }
            }
        )
        
        result = json.loads(response.choices[0].message.content)
        summary = result.get("summary", "").strip()
        
        # 清理可能的引号或标点
        summary = summary.strip('"\'""''。！？，：')
        
        # 确保不超过16个中文字符
        if len(summary) > 16:
            summary = summary[:16]
        
        # 如果生成的内容为空，使用回退方案
        if not summary:
            clean_message = user_message.strip()
            if len(clean_message) > 8:
                summary = clean_message[:8]
            else:
                summary = clean_message if clean_message else "新对话"
        
        print(f"生成对话总结成功: '{summary}'")
        return summary
        
    except Exception as e:
        print(f"生成对话总结失败: {e}")
        # 失败时回退到原来的逻辑
        clean_message = user_message.strip()
        if len(clean_message) > 8:
            return clean_message[:8]
        else:
            return clean_message if clean_message else "新对话"

def get_conversation_summary(conversation_id, first_user_message):
    """获取对话总结（统一入口）"""
    # 检查缓存
    if conversation_id in conversation_summary_cache:
        return conversation_summary_cache[conversation_id]
    
    # 尝试从文件中加载总结
    conversation_file = os.path.join(CONVERSATIONS_DIR, f"{conversation_id}.json")
    if os.path.exists(conversation_file):
        try:
            with open(conversation_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict) and "summary" in data:
                    conversation_summary_cache[conversation_id] = data["summary"]
                    return data["summary"]
        except:
            pass
    
    # 对于没有总结的对话，返回加载中状态，并启动异步生成
    conversation_summary_cache[conversation_id] = "..."
    
    # 异步生成总结
    def generate_summary_async():
        try:
            summary = generate_conversation_summary(first_user_message)
            conversation_summary_cache[conversation_id] = summary
            # 更新文件中的总结
            if os.path.exists(conversation_file):
                try:
                    with open(conversation_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    if isinstance(data, dict):
                        data["summary"] = summary
                    else:
                        data = {"messages": data, "summary": summary}
                    with open(conversation_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                except:
                    pass
        except Exception as e:
            print(f"异步生成总结失败: {e}")
            # 失败时使用回退方案
            fallback = first_user_message[:8] if len(first_user_message) > 8 else first_user_message
            conversation_summary_cache[conversation_id] = fallback
    
    # 启动后台线程生成总结
    thread = threading.Thread(target=generate_summary_async)
    thread.daemon = True
    thread.start()
    
    return "..."

def get_all_conversations():
    """获取所有对话列表"""
    conversations = []
    if os.path.exists(CONVERSATIONS_DIR):
        for filename in os.listdir(CONVERSATIONS_DIR):
            if filename.endswith('.json'):
                conversation_id = filename.replace('.json', '')
                try:
                    messages = load_conversation(conversation_id)
                    if messages:
                        # 查找第一个用户消息
                        first_user_message = next((msg['content'] for msg in messages if msg['role'] == 'user'), "新对话")
                        
                        # 查找第一个用户消息的时间戳
                        first_user_msg_obj = next((msg for msg in messages if msg['role'] == 'user'), None)
                        if first_user_msg_obj and 'timestamp' in first_user_msg_obj:
                            conversation_time = first_user_msg_obj['timestamp']
                        else:
                            # 为没有时间戳的旧对话添加固定的创建时间
                            file_path = os.path.join(CONVERSATIONS_DIR, filename)
                            file_mtime = os.path.getmtime(file_path)
                            conversation_time = datetime.fromtimestamp(file_mtime).isoformat()
                            
                            # 将时间戳保存到对话文件中
                            try:
                                if first_user_msg_obj:
                                    first_user_msg_obj['timestamp'] = conversation_time
                                    # 为所有没有时间戳的消息添加时间戳
                                    for msg in messages:
                                        if msg.get('role') in ['user', 'assistant'] and 'timestamp' not in msg:
                                            msg['timestamp'] = conversation_time
                                    save_conversation(conversation_id, messages)
                                    print(f"为旧对话 {conversation_id} 添加了时间戳: {conversation_time}")
                            except Exception as e:
                                print(f"保存时间戳失败: {e}")
                        
                        # 获取总结
                        title = get_conversation_summary(conversation_id, first_user_message)
                        
                        conversations.append({
                            'id': conversation_id,
                            'title': title,
                            'conversation_time': conversation_time
                        })
                except Exception as e:
                    print(f"处理对话文件 {conversation_id} 时出错: {e}")
                    continue
    return sorted(conversations, key=lambda x: x['conversation_time'], reverse=True)

def limit_conversation_history(messages, max_rounds=3):
    """限制对话历史为最多指定轮数"""
    if not messages:
        return messages
    
    # 找到系统消息
    system_messages = [msg for msg in messages if msg['role'] == 'system']
    # 找到非系统消息
    non_system_messages = [msg for msg in messages if msg['role'] != 'system']
    
    # 按用户消息分组来确定轮数
    rounds = []
    current_round = []
    
    for msg in non_system_messages:
        if msg['role'] == 'user':
            # 开始新的一轮
            if current_round:
                rounds.append(current_round)
            current_round = [msg]
        else:
            # 添加到当前轮
            current_round.append(msg)
    
    # 添加最后一轮（如果存在）
    if current_round:
        rounds.append(current_round)
    
    # 只保留最近的max_rounds轮对话
    recent_rounds = rounds[-max_rounds:] if len(rounds) > max_rounds else rounds
    
    # 重建消息列表：系统消息 + 限制后的对话历史
    limited_messages = system_messages[:]
    for round_messages in recent_rounds:
        limited_messages.extend(round_messages)
    
    return limited_messages


def delete_conversation_from_cache(conversation_id):
    """从缓存中删除对话"""
    if conversation_id in conversation_summary_cache:
        del conversation_summary_cache[conversation_id]