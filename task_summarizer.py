import json
from typing import Dict, Any, List
from config import get_openai_qwen_client, QWEN_MODEL
from utils.log_manager import log_info, log_success, log_error, log_task

class TaskSummarizer:
    """任务汇总与生成节点"""
    
    def __init__(self):
        self.client = get_openai_qwen_client()
    
    def format_results_for_display(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """整理任务结果数据，返回结构化数据供大模型处理"""
        log_task(f"开始整理 {len(results)} 个任务结果")
        structured_results = []
        
        for i, result in enumerate(results, 1):
            todo = result.get("todo", "")
            content = result.get("content", "")
            agent_type = result.get("agent_type", "")
            tool_results = result.get("tool_results", [])
            status = result.get("status", "")
            
            log_info(f"处理任务 {i}: {todo[:30]}... (Agent: {agent_type})")
            
            task_data = {
                "task_number": i,
                "todo": todo,
                "status": status,
                "agent_type": agent_type,
                "ai_content": content.strip() if content else "",
                "tool_results": []
            }
            
            if status == "error":
                log_error(f"任务 {i} 执行失败: {content}")
                task_data["error_message"] = content
                structured_results.append(task_data)
                continue
            
            # 处理工具结果
            for tool_result in tool_results:
                tool_name = tool_result.get("tool_name", "")
                result_content = tool_result.get("result", "")
                log_info(f"处理工具结果: {tool_name}")
                
                try:
                    result_json = json.loads(result_content)
                    
                    if tool_name == "generate_image" and result_json.get("status") == "success":
                        # 图片生成结果
                        web_path = result_json.get("web_path", "")
                        prompt = result_json.get("prompt", "")
                        filename = result_json.get("filename", "")
                        log_success(f"图片生成成功: {filename}")
                        
                        description = prompt if prompt else (filename if filename else "生成的图片")
                        
                        if web_path:
                            task_data["tool_results"].append({
                                "type": "image",
                                "tool_name": tool_name,
                                "path": web_path,
                                "description": description,
                                "filename": filename
                            })
                    elif tool_name in ["get_weather", "get_current_time"] and result_json.get("status") == "success":
                        # 文字工具结果
                        log_success(f"{tool_name} 工具调用成功")
                        task_data["tool_results"].append({
                            "type": "data",
                            "tool_name": tool_name,
                            "data": result_json
                        })
                    elif tool_name == "web_search" and result_json.get("status") == "success":
                        # 网页搜索结果
                        search_count = result_json.get("total_results", 0)
                        log_success(f"网页搜索成功，找到 {search_count} 个结果")
                        task_data["tool_results"].append({
                            "type": "web_search",
                            "tool_name": tool_name,
                            "data": result_json
                        })
                except Exception as e:
                    # 如果无法解析JSON，直接添加文本内容
                    task_data["tool_results"].append({
                        "type": "text",
                        "tool_name": tool_name,
                        "content": result_content
                    })
            
            structured_results.append(task_data)
        
        log_success(f"数据整理完成，共处理 {len(structured_results)} 个任务")
        return structured_results
    
    def summarize_all_results(self, original_question: str, todo_content: str, results: List[Dict[str, Any]]) -> str:
        """汇总所有子Agent的输出"""
        log_task("开始汇总所有任务结果")
        try:
            # 整理所有结果数据
            structured_results = self.format_results_for_display(results)
            
            # 提取TODO列表
            todo_list = []
            if "# TODO" in todo_content:
                lines = todo_content.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and (line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')) or line[0].isdigit()):
                        todo_list.append(line)
            
            # 构建结构化的输入数据
            task_data_for_model = []
            for i, task in enumerate(structured_results):
                task_info = {
                    "todo_number": task.get("task_number", i+1),
                    "todo_content": task.get("todo", ""),
                    "status": task.get("status", ""),
                    "ai_generated_content": task.get("ai_content", ""),
                    "tool_results": task.get("tool_results", []),
                    "error_message": task.get("error_message", "")
                }
                task_data_for_model.append(task_info)
            
            # 构建强化的系统提示词
            system_prompt = """你是一个专业的任务报告生成专家。你的任务是根据TODO列表和对应的执行结果，生成一份完整的报告。

**严格要求**：
1. **必须严格按照TODO顺序**：每个TODO项必须有一个对应的输出段落，不能遗漏、不能重复、不能改变顺序
2. **标题格式**：使用**一、**、**二、**、**三、**等中文数字标题，绝对不使用#标题
3. **图片保留**：必须保持![description](path)格式不变，原样输出
4. **内容组织**：每个段落包含：TODO项的标题 + 对应的执行结果 + 工具结果（如图片、数据等）
5. **不要重复**：不要重复同一个TODO项的内容，不要创造新的标题
6. **逻辑清晰**：确保内容连贯、有逻辑、可读性强

**输出格式示例**：
**一、[TODO1的具体内容]**
[对应的执行结果和工具输出]
![image](path) [如果有图片]

**二、[TODO2的具体内容]**
[对应的执行结果和工具输出]

请直接输出最终报告，不要添加其他说明。"""

            user_message = f"""用户的原始问题：{original_question}

任务分解列表：
{todo_content}

任务执行结果数据：
{json.dumps(task_data_for_model, ensure_ascii=False, indent=2)}

请严格按照TODO顺序生成报告，每个TODO项必须有对应的输出段落。"""
            
            log_info("调用Qwen-Plus-Latest模型进行结果汇总")
            response = self.client.chat.completions.create(
                model=QWEN_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=3000,
                temperature=0.2
            )
            
            summarized_content = response.choices[0].message.content.strip()
            log_success(f"汇总完成，生成内容长度: {len(summarized_content)} 字符")
            
            # 如果汇总失败，返回简单的备用格式
            if not summarized_content:
                log_error("汇总内容为空，返回备用格式")
                return self._generate_fallback_summary(structured_results)
            
            return summarized_content
            
        except Exception as e:
            log_error(f"汇总结果失败: {e}")
            # 如果汇总失败，返回备用格式
            return self._generate_fallback_summary(self.format_results_for_display(results))
    
    def _generate_fallback_summary(self, structured_results: List[Dict[str, Any]]) -> str:
        """生成备用汇总格式，确保按TODO顺序输出"""
        fallback_content = ""
        chinese_numbers = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]
        
        for i, task in enumerate(structured_results):
            todo = task.get("todo", "")
            status = task.get("status", "")
            ai_content = task.get("ai_content", "")
            tool_results = task.get("tool_results", [])
            error_message = task.get("error_message", "")
            
            # 使用中文数字标题
            number = chinese_numbers[i] if i < len(chinese_numbers) else str(i+1)
            fallback_content += f"\n**{number}、{todo}**\n\n"
            
            if status == "error":
                fallback_content += f"❌ {error_message}\n\n"
                continue
            
            # 添加AI生成的内容
            if ai_content:
                fallback_content += f"{ai_content}\n\n"
            
            # 处理工具结果
            for tool_result in tool_results:
                tool_type = tool_result.get("type", "")
                if tool_type == "image":
                    path = tool_result.get("path", "")
                    description = tool_result.get("description", "")
                    if path:
                        fallback_content += f"![{description}]({path})\n\n"
                elif tool_type in ["data", "web_search"]:
                    # 简单处理数据类型的工具结果
                    tool_name = tool_result.get("tool_name", "")
                    if "weather" in tool_name:
                        fallback_content += "**天气信息已获取**\n\n"
                    elif "time" in tool_name:
                        fallback_content += "**时间信息已获取**\n\n"
                    elif "search" in tool_name:
                        fallback_content += "**搜索结果已获取**\n\n"
                elif tool_type == "text":
                    content = tool_result.get("content", "")
                    if content:
                        fallback_content += f"{content}\n\n"
        
        return fallback_content
    
    def generate_final_response(self, cache_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成最终的响应数据"""
        log_task("开始生成最终响应数据")
        original_question = cache_data.get("original_question", "")
        todo_content = cache_data.get("todo_content", "")
        results = cache_data.get("results", [])
        
        # 汇总所有结果
        final_content = self.summarize_all_results(original_question, todo_content, results)
        
        # 统计执行结果
        total_tasks = len(results)
        successful_tasks = len([r for r in results if r.get("status") == "success"])
        failed_tasks = total_tasks - successful_tasks
        
        # 检查是否有图片生成
        has_images = any(
            any(tr.get("tool_name") == "generate_image" for tr in r.get("tool_results", []))
            for r in results
        )
        
        # 检查是否有网页搜索
        has_web_search = any(
            any(tr.get("tool_name") == "web_search" for tr in r.get("tool_results", []))
            for r in results
        )
        
        log_success(f"最终响应生成完成 - 总任务: {total_tasks}, 成功: {successful_tasks}, 失败: {failed_tasks}")
        
        return {
            "response": final_content,
            "mode": "taskPlanning",
            "status": "completed",
            "task_summary": {
                "total_tasks": total_tasks,
                "successful_tasks": successful_tasks,
                "failed_tasks": failed_tasks,
                "has_images": has_images,
                "has_web_search": has_web_search,
                "execution_time": cache_data.get("timestamp", "")
            },
            "detailed_results": results
        }