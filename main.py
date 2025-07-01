import requests
import json
from openai import OpenAI
from datetime import datetime

# 初始化OpenAI客户端
client = OpenAI(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    api_key="583ca88d-ba68-401d-ae86-f5b6d87ef08f"
)

# 高德天气API配置
GAODE_API_KEY = "c8c31e524a0aaa6297ce0cf4a684059e"
WEATHER_URL = "https://restapi.amap.com/v3/weather/weatherInfo"

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
            "description": "当且仅当用户需要获取当前时间时，获取本地当前时间",
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

def run_agent(user_input):
    """运行智能体对话"""
    messages = [{"role": "system", "content":"你是由郭桓君同学开发的智能体。你的人设是一个讲话活泼可爱、情商高的小妹妹"},
                {"role": "user", "content": user_input}]
    
    while True:
        # 调用模型获取响应
        response = client.chat.completions.create(
            model="doubao-seed-1-6-flash-250615",  # 使用火山引擎指定模型
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        
        message = response.choices[0].message
        messages.append(message)
        
        # 检查是否需要调用工具
        if message.tool_calls:
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
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
        else:
            # 没有工具调用时返回最终回复
            return message.content.strip()
    
    return "抱歉，处理您的请求时出现问题"

# 示例使用
if __name__ == "__main__":
    while True:
        user_input = input("\n用户: ")
        if user_input.lower() in ["退出", "exit", "quit"]:
            break
            
        response = run_agent(user_input)
        print(f"助手: {response}")
