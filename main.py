import os
import json
import uuid
import asyncio
from functools import wraps
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS

# 导入自定义模块
from config import FLASK_DEBUG, FLASK_HOST, FLASK_PORT, CONVERSATIONS_DIR, ensure_conversations_dir
from agent import run_agent
from task_planning import judge_question_type, handle_task_planning, confirm_and_execute_tasks_new
from conversation import (
    get_all_conversations, load_conversation, save_conversation, 
    delete_conversation_from_cache
)

# 初始化Flask应用
app = Flask(__name__)
CORS(app)

# 确保对话目录存在
ensure_conversations_dir()

def async_route(f):
    """装饰器：让Flask支持async路由"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper

# Flask路由定义
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

@app.route('/static/generated_images/<path:filename>')
def generated_images(filename):
    return send_from_directory('static/generated_images', filename)

@app.route('/api/chat', methods=['POST'])
def chat():
    """聊天接口"""
    data = request.json
    user_input = data.get('message', '')
    conversation_id = data.get('conversation_id')
    
    if not user_input:
        return jsonify({'error': '消息不能为空'}), 400
    
    try:
        # 首先判断问题类型
        question_type = judge_question_type(user_input)
        
        if question_type == "taskPlanning":
            # 任务规划模式
            result = handle_task_planning(user_input, conversation_id)
        else:
            # chatBot模式
            result = run_agent(user_input, conversation_id, mode=question_type)
        
        # 添加模式信息到返回结果
        result['mode'] = question_type
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/confirm-tasks', methods=['POST'])
@async_route
async def confirm_tasks():
    """确认任务分解结果"""
    data = request.json
    conversation_id = data.get('conversation_id')
    confirmed_tasks = data.get('tasks', [])
    original_question = data.get('original_question', '')
    modified_todo_content = data.get('modified_todo_content')  # 获取用户修改后的todo内容
    
    if not conversation_id or not confirmed_tasks:
        return jsonify({'error': '参数不完整'}), 400
    
    try:
        result = await confirm_and_execute_tasks_new(conversation_id, confirmed_tasks, original_question, modified_todo_content)
        return jsonify(result)
    except Exception as e:
        print(f"确认任务执行错误: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'确认任务时出现错误: {str(e)}'}), 500

@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    """获取所有对话列表"""
    try:
        conversations = get_all_conversations()
        return jsonify(conversations)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations/refresh', methods=['GET'])
def refresh_conversations():
    """刷新对话列表，用于获取异步生成的总结"""
    try:
        conversations = get_all_conversations()
        return jsonify(conversations)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversation/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """获取特定对话"""
    try:
        # 加载完整的对话数据
        conversation_file = os.path.join(CONVERSATIONS_DIR, f"{conversation_id}.json")
        if os.path.exists(conversation_file):
            with open(conversation_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    # 新格式，包含messages和其他信息
                    return jsonify({
                        "messages": data.get("messages", []),
                        "mode": data.get("mode"),
                        "summary": data.get("summary")
                    })
                else:
                    # 旧格式，只有消息列表
                    return jsonify({
                        "messages": data,
                        "mode": None,
                        "summary": None
                    })
        else:
            return jsonify({
                "messages": [],
                "mode": None,
                "summary": None
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversation/new', methods=['POST'])
def new_conversation():
    """创建新对话"""
    try:
        conversation_id = str(uuid.uuid4())
        return jsonify({'conversation_id': conversation_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversation/save', methods=['POST'])
def save_conversation_endpoint():
    """保存对话"""
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
                "content": "你是由郭桓君同学开发的通用AI智能体。你的人设是一个讲话活泼可爱、情商高的小妹妹。你既可以与用户闲聊，也可以进行复杂任务的规划、分配、执行和汇总。"
            })
        
        # 为没有时间戳的消息添加时间戳
        current_time = datetime.now()
        for msg in messages:
            if msg.get('role') in ['user', 'assistant'] and 'timestamp' not in msg:
                msg['timestamp'] = current_time.isoformat()
        
        # 保存对话
        save_conversation(conversation_id, messages)
        
        return jsonify({'success': True, 'message': '对话保存成功'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversation/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    """删除对话"""
    try:
        conversation_file = os.path.join(CONVERSATIONS_DIR, f"{conversation_id}.json")
        
        if not os.path.exists(conversation_file):
            return jsonify({'error': '对话不存在'}), 404
        
        # 删除文件
        os.remove(conversation_file)
        
        # 从缓存中移除
        delete_conversation_from_cache(conversation_id)
        
        return jsonify({'success': True, 'message': '对话删除成功'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 运行Flask应用
if __name__ == "__main__":
    app.run(
        debug=FLASK_DEBUG,
        host=FLASK_HOST,
        port=FLASK_PORT
    )