import json
import os
import httpx
from datetime import datetime
from mcp.server import FastMCP

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
    params = {
        "key": GAODE_API_KEY,
        "city": location,
        "extensions": "base"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(WEATHER_URL, params=params)
            result = response.json()
            
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
                return json.dumps({
                    "status": "error", 
                    "message": "未找到该城市天气信息"
                }, ensure_ascii=False)
                
    except Exception as e:
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
        return json.dumps({
            "status": "error", 
            "message": f"获取时间失败: {str(e)}"
        }, ensure_ascii=False)

if __name__ == "__main__":
    app.run(transport='stdio')