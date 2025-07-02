import requests
import json
import os
import uuid
import threading
from openai import OpenAI
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS

# 初始化OpenAI客户端
client = OpenAI(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    api_key="583ca88d-ba68-401d-ae86-f5b6d87ef08f"
)

# 高德天气API配置
GAODE_API_KEY = "c8c31e524a0aaa6297ce0cf4a684059e"
WEATHER_URL = "https://restapi.amap.com/v3/weather/weatherInfo"

# 初始化Flask应用
app = Flask(__name__)
CORS(app)

# 存储对话历史的目录
CONVERSATIONS_DIR = "conversations"
if not os.path.exists(CONVERSATIONS_DIR):
    os.makedirs(CONVERSATIONS_DIR)

# 定义天气查询工具
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "当且仅当用户需要获取天气信息时，获取指定城市的实时天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "城市名称或行政区划代码，如'北京'或'110101'"
                    }
                },
                "required": ["location"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "当且仅当用户需要获取当前时间时，或者问题与当前时间相关时，获取本地当前时间",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

def get_current_weather(location):
    """调用高德地图API查询天气"""
    params = {
        "key": GAODE_API_KEY,
        "city": location,
        "extensions": "base"
    }
    try:
        response = requests.get(WEATHER_URL, params=params)
        result = response.json()
        
        # 处理API响应
        if result.get("status") == "1" and result.get("count") != "0":
            weather_data = result["lives"][0]
            return json.dumps({
                "status": "success",
                "location": f"{weather_data['province']}{weather_data['city']}",
                "weather": weather_data["weather"],
                "temperature": weather_data["temperature"],
                "wind": f"{weather_data['winddirection']}风{weather_data['windpower']}级",
                "humidity": f"{weather_data['humidity']}%",
                "report_time": weather_data["reporttime"]
            }, ensure_ascii=False)
        else:
            return json.dumps({"status": "error", "message": "未找到该城市天气信息"})
            
    except Exception as e:
        return json.dumps({"status": "error", "message": f"API请求失败: {str(e)}"})

def get_current_time():
    """获取当前本地时间"""
    try:
        current_time = datetime.now()
        return json.dumps({
            "status": "success",
            "current_time": current_time.strftime("%Y-%m-%d %H:%M:%S"),
            "weekday": current_time.strftime("%A"),
            "date": current_time.strftime("%Y年%m月%d日"),
            "time": current_time.strftime("%H时%M分%S秒")
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": f"获取时间失败: {str(e)}"})

def save_conversation(conversation_id, messages, summary=None):
    """保存对话历史到文件"""
    conversation_file = os.path.join(CONVERSATIONS_DIR, f"{conversation_id}.json")
    
    # 如果有总结，将其添加到数据中
    data = {
        "messages": messages
    }
    if summary:
        data["summary"] = summary
    elif conversation_id in conversation_summary_cache:
        data["summary"] = conversation_summary_cache[conversation_id]
    
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

# 对话总结缓存
conversation_summary_cache = {}

def generate_conversation_summary(user_message):
    """同步生成对话总结"""
    try:
        response = client.chat.completions.create(
            model="doubao-seed-1-6-flash-250615",
            messages=[
                {
                    "role": "system",
                    "content": "为我总结用户输入的内容的summary，summary是一个简短的总结，生成不超过10字的总结，只返回summary，不要输出任何其他内容："
                },
                {
                    "role": "user", 
                    "content": user_message[:100]  # 限制输入长度
                }
            ],
            max_tokens=15,
            temperature=0.1
        )
        
        summary = response.choices[0].message.content.strip()
        # 清理可能的引号或标点
        summary = summary.strip('"\'""''。！？，：')
        # 确保不超过10个字符
        if len(summary) > 10:
            summary = summary[:10]
        
        # 如果生成的内容为空，使用回退方案
        if not summary:
            summary = user_message[:5] if len(user_message) > 5 else user_message
            
        return summary
        
    except Exception as e:
        print(f"生成对话总结失败: {e}")
        # 失败时回退到原来的逻辑
        return user_message[:5] if len(user_message) > 5 else user_message

def get_conversation_summary(conversation_id, first_user_message):
    """获取对话总结"""
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
    
    # 对于旧对话，暂时使用前5个字符，避免频繁调用API
    fallback = first_user_message[:5] if len(first_user_message) > 5 else first_user_message
    conversation_summary_cache[conversation_id] = fallback
    return fallback

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
                        
                        # 使用新的获取总结函数
                        title = get_conversation_summary(conversation_id, first_user_message)
                        
                        conversations.append({
                            'id': conversation_id,
                            'title': title,
                            'last_message_time': os.path.getmtime(os.path.join(CONVERSATIONS_DIR, filename))
                        })
                except Exception as e:
                    print(f"处理对话文件 {conversation_id} 时出错: {e}")
                    continue
    return sorted(conversations, key=lambda x: x['last_message_time'], reverse=True)

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

def run_agent(user_input, conversation_id=None):
    """运行智能体对话"""
    if conversation_id:
        messages = load_conversation(conversation_id)
        # 确保有系统消息
        if not messages or messages[0].get('role') != 'system':
            system_msg = {"role": "system", "content":"你是由郭桓君同学开发的智能体。你的人设是一个讲话活泼可爱、情商高的小妹妹"}
            messages = [system_msg] + messages
        # 限制历史对话为最多3轮
        messages = limit_conversation_history(messages, max_rounds=3)
    else:
        conversation_id = str(uuid.uuid4())
        messages = [{"role": "system", "content":"你是由郭桓君同学开发的智能体。你的人设是一个讲话活泼可爱、情商高的小妹妹"}]
    
    messages.append({"role": "user", "content": user_input})
    
    # 限制最大循环次数，避免无限循环
    max_iterations = 10
    iteration_count = 0
    
    while iteration_count < max_iterations:
        iteration_count += 1
        try:
            # 调用模型获取响应
            response = client.chat.completions.create(
                model="doubao-seed-1-6-flash-250615",  # 使用火山引擎指定模型
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )
        except Exception as e:
            save_conversation(conversation_id, messages)
            return {"response": f"抱歉，AI服务暂时不可用：{str(e)}", "conversation_id": conversation_id}
        
        message = response.choices[0].message
        # 将OpenAI message对象转换为字典格式
        message_dict = {
            "role": message.role,
            "content": message.content
        }
        
        # 如果有工具调用，添加工具调用信息
        if hasattr(message, 'tool_calls') and message.tool_calls:
            # 将tool_calls对象转换为可序列化的字典格式
            tool_calls_dict = []
            for tool_call in message.tool_calls:
                tool_calls_dict.append({
                    "id": tool_call.id,
                    "type": tool_call.type,
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }
                })
            message_dict["tool_calls"] = tool_calls_dict
            
        messages.append(message_dict)
        
        # 检查是否需要调用工具
        if message.tool_calls:
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                try:
                    if function_name == "get_current_weather":
                        # 解析参数并调用天气查询
                        args = json.loads(tool_call.function.arguments)
                        weather_info = get_current_weather(args["location"])
                        
                        # 添加工具响应到消息历史
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": function_name,
                            "content": weather_info
                        })
                    elif function_name == "get_current_time":
                        # 调用时间查询
                        time_info = get_current_time()
                        
                        # 添加工具响应到消息历史
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": function_name,
                            "content": time_info
                        })
                except Exception as e:
                    # 工具调用失败时添加错误信息
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": json.dumps({"status": "error", "message": f"工具调用失败: {str(e)}"})
                    })
        else:
            # 没有工具调用时返回最终回复
            # 如果这是新对话的第一轮，生成AI总结
            user_messages = [msg for msg in messages if msg['role'] == 'user']
            if len(user_messages) == 1 and conversation_id not in conversation_summary_cache:
                first_user_message = user_messages[0]['content']
                print(f"为新对话生成总结: {conversation_id}")
                summary = generate_conversation_summary(first_user_message)
                conversation_summary_cache[conversation_id] = summary
                # 保存对话文件，包含总结
                save_conversation(conversation_id, messages, summary)
            else:
                # 保存对话文件
                save_conversation(conversation_id, messages)
            
            return {"response": message.content.strip(), "conversation_id": conversation_id}
    
    # 如果超过最大迭代次数，返回错误信息
    save_conversation(conversation_id, messages)
    return {"response": "抱歉，处理您的请求时出现了问题，请稍后再试。", "conversation_id": conversation_id}

# Flask API路由
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_input = data.get('message', '')
    conversation_id = data.get('conversation_id')
    
    if not user_input:
        return jsonify({'error': '消息不能为空'}), 400
    
    try:
        result = run_agent(user_input, conversation_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    try:
        conversations = get_all_conversations()
        return jsonify(conversations)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversation/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    try:
        messages = load_conversation(conversation_id)
        return jsonify(messages)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversation/new', methods=['POST'])
def new_conversation():
    try:
        conversation_id = str(uuid.uuid4())
        return jsonify({'conversation_id': conversation_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversation/save', methods=['POST'])
def save_conversation_endpoint():
    try:
        data = request.json
        conversation_id = data.get('conversation_id')
        messages = data.get('messages', [])
        
        if not conversation_id:
            return jsonify({'error': '对话ID不能为空'}), 400
        
        # 添加系统消息到消息开头（如果不存在）
        if not messages or messages[0].get('role') != 'system':
            messages.insert(0, {
                "role": "system", 
                "content": "你是由郭桓君同学开发的智能体。你的人设是一个讲话活泼可爱、情商高的小妹妹"
            })
        
        # 保存对话
        save_conversation(conversation_id, messages)
        
        return jsonify({'success': True, 'message': '对话保存成功'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 运行Flask应用
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8070)
