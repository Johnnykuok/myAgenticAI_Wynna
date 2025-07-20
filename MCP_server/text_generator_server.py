import json
import os
import httpx
from datetime import datetime
from dotenv import load_dotenv
from mcp.server import FastMCP

# 加载环境变量
load_dotenv()

# 初始化 FastMCP 服务器
app = FastMCP('text-generator-server')

# 高德天气API配置
GAODE_API_KEY = os.getenv("GAODE_API_KEY")
WEATHER_URL = os.getenv("GAODE_WEATHER_URL", "https://restapi.amap.com/v3/weather/weatherInfo")

@app.tool()
async def get_weather(location: str) -> str:
    """
    获取指定城市的天气信息
    
    Args:
        location: 城市名称，如'北京'或'杭州'
    
    Returns:
        天气信息的JSON字符串
    """
    print(f"🌤️ 收到天气查询请求: {location}")
    params = {
        "key": GAODE_API_KEY,
        "city": location,
        "extensions": "base"
    }
    
    try:
        print(f"📡 调用高德天气API，查询城市: {location}")
        async with httpx.AsyncClient() as client:
            response = await client.get(WEATHER_URL, params=params)
            result = response.json()
            print(f"✅ 高德API响应成功，状态: {result.get('status')}")
            
            if result.get("status") == "1" and result.get("count") != "0":
                weather_data = result["lives"][0]
                print(f"🌤️ 天气查询成功: {weather_data['province']}{weather_data['city']} - {weather_data['weather']}")
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
                print(f"❌ 未找到城市天气信息: {location}")
                return json.dumps({
                    "status": "error", 
                    "message": "未找到该城市天气信息"
                }, ensure_ascii=False)
                
    except Exception as e:
        print(f"❌ 天气API请求失败: {str(e)}")
        return json.dumps({
            "status": "error", 
            "message": f"API请求失败: {str(e)}"
        }, ensure_ascii=False)

@app.tool()
async def get_current_time() -> str:
    """
    获取当前时间
    
    Returns:
        当前时间的JSON字符串
    """
    print("🕐 收到时间查询请求")
    try:
        current_time = datetime.now()
        print(f"✅ 时间查询成功: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        return json.dumps({
            "status": "success",
            "current_time": current_time.strftime("%Y-%m-%d %H:%M:%S"),
            "weekday": current_time.strftime("%A"),
            "date": current_time.strftime("%Y年%m月%d日"),
            "time": current_time.strftime("%H时%M分%S秒")
        }, ensure_ascii=False)
    except Exception as e:
        print(f"❌ 时间查询失败: {str(e)}")
        return json.dumps({
            "status": "error", 
            "message": f"获取时间失败: {str(e)}"
        }, ensure_ascii=False)

if __name__ == "__main__":
    app.run(transport='stdio')