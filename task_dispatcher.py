import asyncio
import json
from typing import List, Dict, Any, Optional
from contextlib import AsyncExitStack
from datetime import datetime

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from config import get_openai_client, DOUBAO_MODEL

class MCPAgentClient:
    """MCP协议的Agent客户端"""
    
    def __init__(self, server_script: str):
        self.server_script = server_script
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.client = get_openai_client()
    
    async def connect(self):
        """连接到MCP服务器"""
        server_params = StdioServerParameters(
            command='python',
            args=[self.server_script],
            env=None
        )
        
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        stdio, write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(stdio, write)
        )
        
        await self.session.initialize()
        print(f"✅ 已连接到MCP服务器: {self.server_script}")
    
    async def process_task(self, original_question: str, todo_content: str, single_todo: str) -> Dict[str, Any]:
        """处理单个任务"""
        if not self.session:
            raise Exception("MCP会话未初始化")
        
        # 构建提示词
        system_prompt = f"""你是一个专业的任务执行Agent。
        
用户的原始问题：{original_question}

完整的任务分解：
{todo_content}

你需要完成的具体任务：{single_todo}

请根据你拥有的工具来完成这个任务。如果需要调用工具，请直接调用。如果不需要工具，请直接给出答案。
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请完成任务：{single_todo}"}
        ]
        
        # 获取所有MCP服务器工具列表信息
        response = await self.session.list_tools()
        
        # 生成function call的描述信息
        available_tools = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
        } for tool in response.tools]
        
        # 请求大模型
        response = self.client.chat.completions.create(
            model=DOUBAO_MODEL,
            messages=messages,
            tools=available_tools,
            tool_choice="auto"
        )
        
        # 处理返回的内容
        content = response.choices[0]
        result_data = {
            "todo": single_todo,
            "agent_type": "photo" if "photo_generator" in self.server_script else "text",
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "content": "",
            "tool_results": []
        }
        
        if content.finish_reason == "tool_calls":
            # 处理工具调用
            tool_calls_for_message = []
            tool_results = []
            
            for tool_call in content.message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                
                # 执行工具
                tool_result = await self.session.call_tool(tool_name, tool_args)
                print(f"🔧 Agent调用工具: {tool_name}，参数: {tool_args}")
                
                # 收集工具调用信息
                tool_calls_for_message.append({
                    "id": tool_call.id,
                    "type": tool_call.type,
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }
                })
                
                # 收集工具结果
                tool_results.append({
                    "role": "tool",
                    "content": tool_result.content[0].text,
                    "tool_call_id": tool_call.id,
                })
                
                # 保存工具结果到结果数据
                result_data["tool_results"].append({
                    "tool_name": tool_name,
                    "args": tool_args,
                    "result": tool_result.content[0].text
                })
            
            # 将大模型返回的调用工具数据存入messages中
            messages.append({
                "role": "assistant",
                "content": content.message.content,
                "tool_calls": tool_calls_for_message
            })
            
            # 将所有工具结果存入messages中
            messages.extend(tool_results)
            
            # 将上面的结果再返回给大模型用于生成最终的结果
            final_response = self.client.chat.completions.create(
                model=DOUBAO_MODEL,
                messages=messages,
            )
            result_data["content"] = final_response.choices[0].message.content
        else:
            result_data["content"] = content.message.content
        
        return result_data
    
    async def cleanup(self):
        """清理资源"""
        await self.exit_stack.aclose()

class TaskDispatcher:
    """任务分配与执行节点"""
    
    def __init__(self):
        self.agents = {
            "photo": MCPAgentClient("photo_generator_server.py"),
            "text": MCPAgentClient("text_generator_server.py")
        }
        self.client = get_openai_client()
        self.task_cache = {}  # 用于存储子Agent的输出
    
    async def initialize_agents(self):
        """初始化所有Agent连接"""
        for agent_type, agent in self.agents.items():
            await agent.connect()
        print("✅ 所有Agent初始化完成")
    
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

请只返回 "photo" 或 "text"，不要返回其他内容。"""
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
            if result in ["photo", "text"]:
                return result
            else:
                # 默认分配给text agent
                return "text"
                
        except Exception as e:
            print(f"任务分类失败: {e}")
            return "text"  # 默认分配给text agent
    
    def parse_todo_content(self, todo_content: str) -> List[str]:
        """解析TODO内容，提取各个任务项"""
        lines = todo_content.split('\n')
        todo_items = []
        
        for line in lines:
            line = line.strip()
            # 匹配以数字开头的任务项
            if line and (line[0].isdigit() or line.startswith('-') or line.startswith('*')):
                # 清理编号和标记
                clean_line = line
                if line[0].isdigit():
                    clean_line = line.split('.', 1)[-1].strip()
                elif line.startswith('-') or line.startswith('*'):
                    clean_line = line[1:].strip()
                
                if clean_line:
                    todo_items.append(clean_line)
        
        return todo_items
    
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
        
        # 使用asyncio.gather来并行执行不同类型的任务
        async def execute_agent_tasks(agent_type: str, tasks: List[str]):
            agent = self.agents[agent_type]
            results = []
            
            # 为同一类型的任务创建并发任务
            async def execute_single_task(task):
                try:
                    return await agent.process_task(original_question, todo_content, task)
                except Exception as e:
                    print(f"❌ 任务执行失败: {task[:30]}... - {e}")
                    return {
                        "todo": task,
                        "agent_type": agent_type,
                        "timestamp": datetime.now().isoformat(),
                        "status": "error",
                        "content": f"任务执行失败: {str(e)}",
                        "tool_results": []
                    }
            
            # 并行执行同类型的所有任务
            tasks_coroutines = [execute_single_task(task) for task in tasks]
            results = await asyncio.gather(*tasks_coroutines)
            return results
        
        # 为每种Agent类型创建执行协程
        agent_coroutines = []
        for agent_type, tasks in classified_tasks.items():
            agent_coroutines.append(execute_agent_tasks(agent_type, tasks))
        
        # 并行执行所有Agent类型的任务
        agent_results = await asyncio.gather(*agent_coroutines)
        
        # 合并所有结果
        for results in agent_results:
            all_results.extend(results)
        
        # 缓存结果用于汇总
        cache_key = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.task_cache[cache_key] = {
            "original_question": original_question,
            "todo_content": todo_content,
            "results": all_results,
            "timestamp": datetime.now().isoformat()
        }
        
        return cache_key
    
    async def cleanup(self):
        """清理所有Agent连接"""
        for agent in self.agents.values():
            await agent.cleanup()
        print("🧹 所有Agent连接已清理")

# 全局任务分配器实例
_task_dispatcher = None

async def get_task_dispatcher():
    """获取任务分配器实例（单例模式）"""
    global _task_dispatcher
    if _task_dispatcher is None:
        _task_dispatcher = TaskDispatcher()
        await _task_dispatcher.initialize_agents()
    return _task_dispatcher

def get_task_results(cache_key: str) -> Dict[str, Any]:
    """从缓存获取任务结果"""
    global _task_dispatcher
    if _task_dispatcher and cache_key in _task_dispatcher.task_cache:
        return _task_dispatcher.task_cache[cache_key]
    return None