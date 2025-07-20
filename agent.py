import json
import uuid
import threading
import time
from datetime import datetime
from config import get_openai_client, DOUBAO_MODEL, SYSTEM_PROMPT, MAX_CONVERSATION_ROUNDS
from tools import tools, execute_tool_call
from conversation import (
    load_conversation, save_conversation, limit_conversation_history,
    generate_conversation_summary, conversation_summary_cache
)
from utils.timestamp_utils import get_current_timestamp
from utils.message_utils import create_user_message, create_assistant_message, create_tool_message, create_system_message

def run_agent(user_input, conversation_id=None, mode=None):
    """运行智能体对话"""
    client = get_openai_client()
    
    if conversation_id:
        messages = load_conversation(conversation_id)
        # 确保有系统消息
        if not messages or messages[0].get('role') != 'system':
            messages = [create_system_message(SYSTEM_PROMPT)] + messages
        # 限制历史对话为最多3轮
        messages = limit_conversation_history(messages, max_rounds=MAX_CONVERSATION_ROUNDS)
    else:
        conversation_id = str(uuid.uuid4())
        messages = [create_system_message(SYSTEM_PROMPT)]
    
    # 添加用户消息（自动添加时间戳）
    messages.append(create_user_message(user_input))
    
    # 检查是否是新对话的第一条用户消息
    user_messages = [msg for msg in messages if msg['role'] == 'user']
    is_new_conversation = len(user_messages) == 1
    
    # 如果是新对话，立即保存并启动总结生成
    if is_new_conversation:
        conversation_summary_cache[conversation_id] = "..."
        save_conversation(conversation_id, messages)
        
        # 启动异步生成总结
        first_user_message = user_input
        print(f"启动新对话总结生成: {conversation_id}")
        
        def generate_summary_for_new_conversation():
            try:
                time.sleep(0.5)
                summary = generate_conversation_summary(first_user_message)
                conversation_summary_cache[conversation_id] = summary
                save_conversation(conversation_id, messages, summary)
                print(f"新对话总结生成完成: {conversation_id} -> {summary}")
            except Exception as e:
                print(f"新对话总结生成失败: {e}")
                fallback = first_user_message[:8] if len(first_user_message) > 8 else first_user_message
                conversation_summary_cache[conversation_id] = fallback
        
        thread = threading.Thread(target=generate_summary_for_new_conversation)
        thread.daemon = True
        thread.start()
    
    # 限制最大循环次数，避免无限循环
    max_iterations = 10
    iteration_count = 0
    
    while iteration_count < max_iterations:
        iteration_count += 1
        try:
            # 调用模型获取响应
            response = client.chat.completions.create(
                model=DOUBAO_MODEL,
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )
        except Exception as e:
            save_conversation(conversation_id, messages)
            return {"response": f"抱歉，AI服务暂时不可用：{str(e)}", "conversation_id": conversation_id}
        
        message = response.choices[0].message
        # 将OpenAI message对象转换为字典格式，自动添加时间戳
        # 如果content为空且有工具调用，暂时不创建assistant消息
        if not message.content and message.tool_calls:
            # 只有工具调用没有内容时，先不添加assistant消息，等工具执行完再添加
            pass
        else:
            message_dict = create_assistant_message(message.content or "正在处理您的请求...")
        
        # 如果有工具调用，添加工具调用信息
        if hasattr(message, 'tool_calls') and message.tool_calls:
            # 如果content为空，创建带工具调用的assistant消息
            if not message.content:
                message_dict = create_assistant_message("")
            
            # 将tool_calls对象转换为可序列化的字典格式
            tool_calls_dict = []
            for tool_call in message.tool_calls:
                # 验证工具调用信息是否完整
                if tool_call.function.name and tool_call.function.name.strip():
                    tool_calls_dict.append({
                        "id": tool_call.id,
                        "type": tool_call.type,
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }
                    })
            
            if tool_calls_dict:  # 只有在有有效工具调用时才添加
                message_dict["tool_calls"] = tool_calls_dict
                messages.append(message_dict)
        elif message.content:  # 只有在有内容时才添加普通消息
            messages.append(message_dict)
        
        # 检查是否需要调用工具
        if message.tool_calls:
            for tool_call in message.tool_calls:
                # 验证工具调用信息是否完整
                if not tool_call.function.name or not tool_call.function.name.strip():
                    print(f"警告：跳过无效的工具调用，工具名为空: {tool_call.id}")
                    continue
                    
                try:
                    # 执行工具调用
                    tool_result = execute_tool_call(tool_call)
                    
                    # 添加工具响应到消息历史（自动添加时间戳）
                    messages.append(create_tool_message(
                        tool_call.id,
                        tool_call.function.name,
                        tool_result
                    ))
                except Exception as e:
                    # 工具调用失败时添加错误信息（自动添加时间戳）
                    messages.append(create_tool_message(
                        tool_call.id,
                        tool_call.function.name,
                        json.dumps({"status": "error", "message": f"工具调用失败: {str(e)}"})
                    ))
        else:
            # 没有工具调用时返回最终回复
            # 如果这是新对话的第一轮，生成AI总结
            user_messages = [msg for msg in messages if msg['role'] == 'user']
            if len(user_messages) == 1 and conversation_id not in conversation_summary_cache:
                first_user_message = user_messages[0]['content']
                print(f"为新对话生成总结: {conversation_id}")
                summary = generate_conversation_summary(first_user_message)
                conversation_summary_cache[conversation_id] = summary
                save_conversation(conversation_id, messages, summary, mode)
            else:
                save_conversation(conversation_id, messages, mode=mode)
            
            return {"response": message.content.strip(), "conversation_id": conversation_id, "mode": mode}
    
    # 如果超过最大迭代次数，返回错误信息
    save_conversation(conversation_id, messages)
    return {"response": "抱歉，处理您的请求时出现了问题，请稍后再试。", "conversation_id": conversation_id}