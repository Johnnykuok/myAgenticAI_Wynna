import json
import os
import requests
from dotenv import load_dotenv
from mcp.server import FastMCP

# 加载环境变量
load_dotenv()

app = FastMCP('web-search-server')

BOCHA_API_KEY = os.getenv("BOCHA_API_KEY")
BOCHA_API_URL = os.getenv("BOCHA_API_URL", "https://api.bochaai.com/v1/ai-search")

@app.tool()
async def web_search(query: str, freshness: str = "noLimit", max_results: int = 10) -> str:
    """
    使用博查AI搜索引擎进行网络搜索
    
    Args:
        query: 搜索查询关键词
        freshness: 搜索结果的时效性限制，可选值：noLimit, pastDay, pastWeek, pastMonth, pastYear
        max_results: 返回的最大结果数量，默认10个，最大50个
    
    Returns:
        搜索结果的JSON字符串，包含snippet和summary字段
    """
    print(f"🔍 收到网页搜索请求: {query} (时效性: {freshness}, 最大结果: {max_results})")
    try:
        data = {
            "query": query,
            "freshness": freshness,
            "answer": False,
            "stream": False
        }
        
        print(f"📡 调用博查AI搜索API...")
        response = requests.post(
            BOCHA_API_URL,
            headers={"Authorization": f"Bearer {BOCHA_API_KEY}"},
            json=data,
            timeout=30
        )
        
        print(f"✅ 博查AI API响应，状态码: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            
            parsed_results = []
            
            for message in result.get("messages", []):
                if message.get("content_type") == "webpage":
                    content = json.loads(message.get("content", "{}"))
                    web_results = content.get("value", [])
                    
                    for item in web_results[:max_results]:
                        search_result = {
                            "id": item.get("id", ""),
                            "title": item.get("name", ""),
                            "url": item.get("url", ""),
                            "snippet": item.get("snippet", ""),
                            "summary": item.get("summary", ""),
                            "site_name": item.get("siteName", ""),
                            "date_published": item.get("datePublished")
                        }
                        parsed_results.append(search_result)
            
            print(f"🔍 搜索完成，找到 {len(parsed_results)} 个结果")
            return json.dumps({
                "status": "success",
                "query": query,
                "total_results": len(parsed_results),
                "results": parsed_results
            }, ensure_ascii=False)
            
        else:
            print(f"❌ 搜索请求失败，状态码: {response.status_code}")
            return json.dumps({
                "status": "error",
                "message": f"搜索请求失败，状态码: {response.status_code}",
                "details": response.text
            }, ensure_ascii=False)
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求异常: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"网络请求异常: {str(e)}"
        }, ensure_ascii=False)
    except Exception as e:
        print(f"❌ 搜索过程中发生异常: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"搜索过程中发生异常: {str(e)}"
        }, ensure_ascii=False)

if __name__ == "__main__":
    app.run(transport='stdio')