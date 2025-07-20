import json
import uuid
from datetime import datetime
from config import get_openai_client, DOUBAO_MODEL, SYSTEM_PROMPT
from conversation import save_conversation, load_conversation
from task_dispatcher import get_task_dispatcher, get_task_results
from task_summarizer import TaskSummarizer
from utils.timestamp_utils import get_current_timestamp
from utils.message_utils import create_user_message, create_assistant_message, create_system_message

def judge_question_type(user_message):
    """判断用户问题类型：chatbot模式 vs 任务规划模式"""
    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model=DOUBAO_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": """
                你是一个问题类型判断专家。请判断用户的问题属于以下哪种类型：
                1. chatBot模式：简单且常规的聊天类问题，如"现在几点了"、"杭州天气如何"、"你叫什么名字"、"你好"、"帮我写个故事"、"解释一下人工智能"等日常对话或简单咨询。
                2. taskPlanning模式：复杂的任务规划类问题，需要多步骤完成，如"为我制定8月份去杭州的旅游攻略"、"为我调研快手2024年的财报"、"帮我分析市场趋势并制定商业计划"等。
                
                请以JSON格式输出判断结果，格式如下：
                {
                    "type": "chatBot",
                    "confidence": 0.95,
                    "reason": "这是一个简单的日常咨询问题"
                }
                
                或者：
                {
                    "type": "taskPlanning", 
                    "confidence": 0.88,
                    "reason": "这是一个需要多步骤完成的复杂任务"
                }
                
                其中type只能是"chatBot"或"taskPlanning"，confidence为0-1之间的置信度，reason为判断理由。"""
                },
                {
                    "role": "user", 
                    "content": user_message
                }
            ],
            max_tokens=150,
            temperature=0.1,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "question_type_judgment",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["chatBot", "taskPlanning"],
                                "description": "问题类型，只能是chatBot或taskPlanning"
                            },
                            "confidence": {
                                "type": "number",
                                "description": "判断的置信度，范围0-1"
                            },
                            "reason": {
                                "type": "string",
                                "description": "判断理由"
                            }
                        },
                        "required": ["type", "confidence", "reason"],
                        "additionalProperties": False
                    },
                    "strict": True
                }
            }
        )
        
        result = json.loads(response.choices[0].message.content)
        question_type = result.get("type", "chatBot")
        confidence = result.get("confidence", 0.5)
        reason = result.get("reason", "")
        
        # 记录判断结果
        print(f"问题类型判断: {question_type}, 置信度: {confidence}, 理由: {reason}")
        
        return question_type
            
    except Exception as e:
        print(f"判断问题类型失败: {e}")
        # 失败时默认为chatBot模式
        return "chatBot"

def decompose_task(user_message):
    """任务拆解函数"""
    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model=DOUBAO_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": """
                    你是一个复杂任务的拆解专家，你会把用户的问题拆解为小的步骤。

                    请以JSON格式输出拆解结果，格式如下：
                    {
                        "tasks": [
                            "步骤一的具体描述",
                            "步骤二的具体描述",
                            "步骤三的具体描述"
                        ],
                        "markdown": "# TODO\n\n1. 步骤一的具体描述\n2. 步骤二的具体描述\n3. 步骤三的具体描述"
                    }
                    
                    其中tasks为拆解后的任务列表，markdown为to_do.md格式的内容。"""
                },
                {
                    "role": "user", 
                    "content": user_message
                }
            ],
            max_tokens=500,
            temperature=0.3,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "task_decomposition",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "tasks": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "description": "具体的任务步骤描述"
                                },
                                "description": "拆解后的任务步骤列表"
                            },
                            "markdown": {
                                "type": "string",
                                "description": "TODO格式的markdown内容"
                            }
                        },
                        "required": ["tasks", "markdown"],
                        "additionalProperties": False
                    },
                    "strict": True
                }
            }
        )
        
        result = json.loads(response.choices[0].message.content)
        tasks = result.get("tasks", [])
        markdown = result.get("markdown", "")
        
        # 记录拆解结果
        print(f"任务拆解成功，共{len(tasks)}个步骤")
        
        # 返回markdown格式，保持与原有代码兼容
        return markdown
        
    except Exception as e:
        print(f"任务拆解失败: {e}")
        return f"任务拆解失败：{str(e)}"


def handle_task_planning(user_input, conversation_id=None):
    """处理任务规划模式"""
    if conversation_id is None:
        conversation_id = str(uuid.uuid4())
    
    # 任务拆解
    decomposed_tasks = decompose_task(user_input)
    
    # 保存初始对话（使用工具函数创建消息）
    messages = [
        create_system_message(SYSTEM_PROMPT),
        create_user_message(user_input),
        create_assistant_message(f"我来帮你分析这个任务～这是一个比较复杂的问题，我把它拆解成了以下几个步骤：\n\n{decomposed_tasks}\n\n请确认这些步骤是否合适，或者你可以编辑后提交。确认后我会逐步为你完成每个任务哦！")
    ]
    
    save_conversation(conversation_id, messages, mode="taskPlanning")
    
    return {
        "response": f"我来帮你分析这个任务～这是一个比较复杂的问题，我把它拆解成了以下几个步骤：\n\n{decomposed_tasks}\n\n请确认这些步骤是否合适，或者你可以编辑后提交。确认后我会逐步为你完成每个任务哦！",
        "conversation_id": conversation_id,
        "mode": "taskPlanning",
        "decomposed_tasks": decomposed_tasks,
        "original_question": user_input,
        "status": "waiting_confirmation"
    }

async def confirm_and_execute_tasks_new(conversation_id, confirmed_tasks, original_question, modified_todo_content=None):
    """使用新的任务分配器确认并执行任务"""
    try:
        # 重构任务为markdown格式
        todo_content = "# TODO\n\n"
        for i, task in enumerate(confirmed_tasks, 1):
            todo_content += f"{i}. {task}\n"
        
        print(f"📋 开始执行 {len(confirmed_tasks)} 个任务")
        
        # 获取任务分配器并执行任务
        dispatcher = await get_task_dispatcher()
        cache_key = await dispatcher.dispatch_and_execute_tasks(original_question, todo_content)
        
        print(f"✅ 所有任务执行完成，缓存键: {cache_key}")
        
        # 获取执行结果
        cache_data = get_task_results(cache_key)
        if not cache_data:
            raise Exception("无法获取任务执行结果")
        
        # 使用任务汇总器生成最终响应
        summarizer = TaskSummarizer()
        final_response = summarizer.generate_final_response(cache_data)
        
        # 更新对话记录（使用工具函数创建消息）
        messages = load_conversation(conversation_id)
        
        # 直接使用用户修改后的todo内容，不添加前缀
        if modified_todo_content:
            user_confirmation_content = modified_todo_content
        else:
            # 如果没有修改后的内容，重构为markdown格式
            user_confirmation_content = "# TODO\n\n"
            for i, task in enumerate(confirmed_tasks, 1):
                user_confirmation_content += f"{i}. {task}\n"
        
        messages.append(create_user_message(user_confirmation_content))
        messages.append(create_assistant_message(final_response["response"]))
        save_conversation(conversation_id, messages)
        
        # 添加对话ID到响应
        final_response["conversation_id"] = conversation_id
        
        return final_response
        
    except Exception as e:
        print(f"执行任务失败: {e}")
        return {
            "response": f"执行任务时出现错误：{str(e)}",
            "conversation_id": conversation_id,
            "mode": "taskPlanning",
            "status": "error"
        }

