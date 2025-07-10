import asyncio
import json
from typing import List, Dict, Any
from datetime import datetime
from config import get_openai_client, DOUBAO_MODEL
from tools import get_current_weather, get_current_time
import base64
import os
from openai import OpenAI
import requests

class SimpleTaskDispatcher:
    """简化版任务分配器，不依赖MCP协议"""
    
    def __init__(self):
        self.client = get_openai_client()
        self.task_cache = {}
        
        # 豆包文生图客户端
        self.image_client = OpenAI(
            base_url=os.getenv("DOUBAO_BASE_URL"),
            api_key=os.getenv("DOUBAO_API_KEY")
        )
        
        # 博查AI搜索API配置
        self.bocha_api_key = "sk-5635f459fa3c4e31b4a835678597649e"
        self.bocha_api_url = "https://api.bochaai.com/v1/ai-search"
    
    def classify_todo_item(self, todo_item: str) -> str:
        """使用豆包大模型分类TODO项"""
        try:
            response = self.client.chat.completions.create(
                model=DOUBAO_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": """你是一个任务分类专家。请判断给定的任务应该分配给哪种类型的Agent：

1. "photo" - 图片生成Agent：任务涉及生成、创建、绘制图片、图像、插图等视觉内容
2. "text" - 文字生成Agent：任务涉及文字处理、信息查询、天气查询、时间查询、文本分析等
3. "web_search" - 网页搜索Agent：任务涉及搜索网络信息、查找最新资讯、获取网页内容、搜索相关信息等

请只返回 "photo"、"text" 或 "web_search"，不要返回其他内容。"""
                    },
                    {
                        "role": "user",
                        "content": f"请为以下任务分类：{todo_item}"
                    }
                ],
                max_tokens=10,
                temperature=0.1
            )
            
            result = response.choices[0].message.content.strip().lower()
            if result in ["photo", "text", "web_search"]:
                return result
            else:
                return "text"
                
        except Exception as e:
            print(f"任务分类失败: {e}")
            return "text"
    
    def parse_todo_content(self, todo_content: str) -> List[str]:
        """解析TODO内容，提取各个任务项"""
        lines = todo_content.split('\n')
        todo_items = []
        
        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-') or line.startswith('*')):
                clean_line = line
                if line[0].isdigit():
                    clean_line = line.split('.', 1)[-1].strip()
                elif line.startswith('-') or line.startswith('*'):
                    clean_line = line[1:].strip()
                
                if clean_line:
                    todo_items.append(clean_line)
        
        return todo_items
    
    async def execute_photo_task(self, original_question: str, todo_content: str, task: str) -> Dict[str, Any]:
        """执行图片生成任务"""
        try:
            # 生成图片描述提示词和用户友好描述
            prompt_response = self.client.chat.completions.create(
                model=DOUBAO_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": f"""你是一个专业的图片生成专家。

用户的原始问题：{original_question}

完整的任务分解：
{todo_content}

你需要完成的具体任务：{task}

请以JSON格式输出：
{{
    "prompt": "详细的英文图片描述提示词，用于AI图片生成",
    "description": "简短的中文描述，向用户说明生成了什么图片"
}}

英文提示词要具体、生动，包含风格、色彩、构图等元素。
中文描述要简洁友好，不超过20个字。"""
                    },
                    {
                        "role": "user",
                        "content": f"为任务生成图片描述：{task}"
                    }
                ],
                max_tokens=300,
                temperature=0.7,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "image_generation",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "prompt": {
                                    "type": "string",
                                    "description": "英文图片生成提示词"
                                },
                                "description": {
                                    "type": "string",
                                    "description": "中文图片描述"
                                }
                            },
                            "required": ["prompt", "description"],
                            "additionalProperties": False
                        },
                        "strict": True
                    }
                }
            )
            
            try:
                result = json.loads(prompt_response.choices[0].message.content)
                prompt = result.get("prompt", task)
                description = result.get("description", "生成的图片")
            except:
                prompt = task
                description = "生成的图片"
                
            print(f"🎨 生成图片提示词: {prompt}")
            print(f"📝 用户描述: {description}")
            
            # 调用豆包文生图API
            response = self.image_client.images.generate(
                model="doubao-seedream-3-0-t2i-250415",
                prompt=prompt,
                size="2048x2048",
                response_format="b64_json"
            )
            
            # 获取Base64编码的图像数据
            b64_image_data = response.data[0].b64_json
            image_data = base64.b64decode(b64_image_data)
            
            # 确保生成的图片保存目录存在
            images_dir = "/Users/guohuanjun/Downloads/myagent_1/static/generated_images"
            os.makedirs(images_dir, exist_ok=True)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"generated_image_{timestamp}.png"
            filepath = os.path.join(images_dir, filename)
            
            # 保存图片
            with open(filepath, "wb") as f:
                f.write(image_data)
            
            return {
                "todo": task,
                "agent_type": "photo",
                "timestamp": datetime.now().isoformat(),
                "status": "success",
                "content": f"已成功生成图片：{description}",
                "tool_results": [{
                    "tool_name": "generate_image",
                    "args": {"prompt": prompt},
                    "result": json.dumps({
                        "status": "success",
                        "message": "图片生成成功",
                        "filepath": filepath,
                        "filename": filename,
                        "web_path": f"/static/generated_images/{filename}",
                        "prompt": prompt,
                        "description": description
                    }, ensure_ascii=False)
                }]
            }
            
        except Exception as e:
            print(f"图片生成任务失败: {e}")
            return {
                "todo": task,
                "agent_type": "photo",
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "content": f"图片生成失败: {str(e)}",
                "tool_results": []
            }
    
    async def execute_text_task(self, original_question: str, todo_content: str, task: str) -> Dict[str, Any]:
        """执行文字任务"""
        try:
            # 首先让AI判断是否需要调用工具
            tool_response = self.client.chat.completions.create(
                model=DOUBAO_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": f"""你是一个专业的任务执行助手。
                        
用户的原始问题：{original_question}

完整的任务分解：
{todo_content}

你需要完成的具体任务：{task}

请判断这个任务是否需要调用以下工具：
1. 天气查询 - 如果涉及查询某个城市的天气
2. 时间查询 - 如果涉及获取当前时间
3. 无需工具 - 如果可以直接回答

请以JSON格式回复：
{{"action": "weather", "location": "城市名"}} 
{{"action": "time"}}
{{"action": "direct", "response": "直接回答内容"}}"""
                    },
                    {
                        "role": "user",
                        "content": f"分析任务：{task}"
                    }
                ],
                max_tokens=200,
                temperature=0.1
            )
            
            tool_decision = tool_response.choices[0].message.content.strip()
            print(f"🔧 工具决策: {tool_decision}")
            
            try:
                decision = json.loads(tool_decision)
                action = decision.get("action", "direct")
                
                tool_results = []
                
                if action == "weather" and "location" in decision:
                    # 调用天气工具
                    weather_result = get_current_weather(decision["location"])
                    tool_results.append({
                        "tool_name": "get_weather",
                        "args": {"location": decision["location"]},
                        "result": weather_result
                    })
                elif action == "time":
                    # 调用时间工具
                    time_result = get_current_time()
                    tool_results.append({
                        "tool_name": "get_current_time",
                        "args": {},
                        "result": time_result
                    })
                
                # 生成最终回答
                if tool_results:
                    # 有工具调用结果，让AI基于结果生成回答
                    tool_info = "\n".join([f"工具{tr['tool_name']}返回：{tr['result']}" for tr in tool_results])
                    final_response = self.client.chat.completions.create(
                        model=DOUBAO_MODEL,
                        messages=[
                            {
                                "role": "system",
                                "content": f"基于工具调用结果，为用户任务生成完整回答。\n任务：{task}\n工具结果：\n{tool_info}"
                            },
                            {
                                "role": "user",
                                "content": "请生成友好完整的回答"
                            }
                        ],
                        max_tokens=300,
                        temperature=0.3
                    )
                    content = final_response.choices[0].message.content
                else:
                    # 直接回答
                    content = decision.get("response", f"已完成任务：{task}")
                
                return {
                    "todo": task,
                    "agent_type": "text",
                    "timestamp": datetime.now().isoformat(),
                    "status": "success",
                    "content": content,
                    "tool_results": tool_results
                }
                
            except json.JSONDecodeError:
                # 如果无法解析JSON，直接生成回答
                direct_response = self.client.chat.completions.create(
                    model=DOUBAO_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": f"请完成以下任务：{task}\n\n原始问题：{original_question}"
                        },
                        {
                            "role": "user",
                            "content": task
                        }
                    ],
                    max_tokens=300,
                    temperature=0.3
                )
                
                return {
                    "todo": task,
                    "agent_type": "text",
                    "timestamp": datetime.now().isoformat(),
                    "status": "success",
                    "content": direct_response.choices[0].message.content,
                    "tool_results": []
                }
                
        except Exception as e:
            print(f"文字任务执行失败: {e}")
            return {
                "todo": task,
                "agent_type": "text",
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "content": f"任务执行失败: {str(e)}",
                "tool_results": []
            }
    
    async def execute_web_search_task(self, original_question: str, todo_content: str, task: str) -> Dict[str, Any]:
        """执行网页搜索任务"""
        try:
            # 首先让AI提取搜索关键词
            search_response = self.client.chat.completions.create(
                model=DOUBAO_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": f"""你是一个搜索专家。
                        
用户的原始问题：{original_question}

完整的任务分解：
{todo_content}

你需要完成的具体任务：{task}

请分析这个任务，提取出最佳的搜索关键词，并以JSON格式返回：
{{"query": "搜索关键词", "description": "搜索目的的简短描述"}}

搜索关键词要具体、准确，能够找到相关信息。"""
                    },
                    {
                        "role": "user",
                        "content": f"为任务提取搜索关键词：{task}"
                    }
                ],
                max_tokens=200,
                temperature=0.3
            )
            
            try:
                search_info = json.loads(search_response.choices[0].message.content)
                query = search_info.get("query", task)
                description = search_info.get("description", "网页搜索")
            except:
                query = task
                description = "网页搜索"
            
            print(f"🔍 搜索关键词: {query}")
            print(f"📝 搜索目的: {description}")
            
            # 调用博查AI搜索API
            data = {
                "query": query,
                "freshness": "noLimit",
                "answer": False,
                "stream": False
            }
            
            response = requests.post(
                self.bocha_api_url,
                headers={"Authorization": f"Bearer {self.bocha_api_key}"},
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # 解析搜索结果
                parsed_results = []
                
                for message in result.get("messages", []):
                    if message.get("content_type") == "webpage":
                        content = json.loads(message.get("content", "{}"))
                        web_results = content.get("value", [])
                        
                        for item in web_results[:5]:  # 限制显示前5个结果
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
                
                # 生成用户友好的搜索结果摘要
                if parsed_results:
                    results_text = "\n".join([
                        f"• {result['title']}\n  {result['snippet']}\n  来源：{result['site_name']} ({result['url']})\n" 
                        for result in parsed_results[:3]
                    ])
                    
                    summary_response = self.client.chat.completions.create(
                        model=DOUBAO_MODEL,
                        messages=[
                            {
                                "role": "system",
                                "content": f"基于搜索结果，为用户任务生成简洁的总结。\n任务：{task}\n搜索结果：\n{results_text}"
                            },
                            {
                                "role": "user",
                                "content": "请生成友好完整的搜索结果总结"
                            }
                        ],
                        max_tokens=400,
                        temperature=0.3
                    )
                    content = summary_response.choices[0].message.content
                else:
                    content = f"搜索完成，但未找到相关结果。搜索关键词：{query}"
                
                return {
                    "todo": task,
                    "agent_type": "web_search",
                    "timestamp": datetime.now().isoformat(),
                    "status": "success",
                    "content": content,
                    "tool_results": [{
                        "tool_name": "web_search",
                        "args": {"query": query, "freshness": "noLimit", "max_results": 5},
                        "result": json.dumps({
                            "status": "success",
                            "query": query,
                            "total_results": len(parsed_results),
                            "results": parsed_results
                        }, ensure_ascii=False)
                    }]
                }
            else:
                return {
                    "todo": task,
                    "agent_type": "web_search",
                    "timestamp": datetime.now().isoformat(),
                    "status": "error",
                    "content": f"搜索失败：API返回状态码 {response.status_code}",
                    "tool_results": []
                }
                
        except Exception as e:
            print(f"网页搜索任务失败: {e}")
            return {
                "todo": task,
                "agent_type": "web_search",
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "content": f"网页搜索失败: {str(e)}",
                "tool_results": []
            }
    
    async def dispatch_and_execute_tasks(self, original_question: str, todo_content: str) -> str:
        """分配并执行所有任务"""
        # 解析TODO项
        todo_items = self.parse_todo_content(todo_content)
        print(f"📋 解析出 {len(todo_items)} 个任务项")
        
        if not todo_items:
            return "没有找到有效的任务项"
        
        # 分类任务
        classified_tasks = {}
        for todo_item in todo_items:
            agent_type = self.classify_todo_item(todo_item)
            if agent_type not in classified_tasks:
                classified_tasks[agent_type] = []
            classified_tasks[agent_type].append(todo_item)
            print(f"📝 任务 '{todo_item[:30]}...' 分配给 {agent_type} Agent")
        
        # 并行执行任务
        all_results = []
        
        # 执行所有任务
        async def execute_task(agent_type: str, task: str):
            if agent_type == "photo":
                return await self.execute_photo_task(original_question, todo_content, task)
            elif agent_type == "web_search":
                return await self.execute_web_search_task(original_question, todo_content, task)
            else:
                return await self.execute_text_task(original_question, todo_content, task)
        
        # 创建所有任务的协程
        tasks_coroutines = []
        for agent_type, tasks in classified_tasks.items():
            for task in tasks:
                tasks_coroutines.append(execute_task(agent_type, task))
        
        # 并行执行所有任务
        all_results = await asyncio.gather(*tasks_coroutines)
        
        # 缓存结果用于汇总
        cache_key = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.task_cache[cache_key] = {
            "original_question": original_question,
            "todo_content": todo_content,
            "results": all_results,
            "timestamp": datetime.now().isoformat()
        }
        
        return cache_key
    
    def get_task_results(self, cache_key: str) -> Dict[str, Any]:
        """从缓存获取任务结果"""
        return self.task_cache.get(cache_key)

# 全局简化任务分配器实例
_simple_dispatcher = None

async def get_simple_task_dispatcher():
    """获取简化任务分配器实例（单例模式）"""
    global _simple_dispatcher
    if _simple_dispatcher is None:
        _simple_dispatcher = SimpleTaskDispatcher()
    return _simple_dispatcher

def get_simple_task_results(cache_key: str) -> Dict[str, Any]:
    """从缓存获取任务结果"""
    global _simple_dispatcher
    if _simple_dispatcher:
        return _simple_dispatcher.get_task_results(cache_key)
    return None