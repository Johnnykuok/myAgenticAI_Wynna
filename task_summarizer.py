import json
from typing import Dict, Any, List
from config import get_openai_qwen_client, QWEN_MODEL
from utils.log_manager import log_info, log_success, log_error, log_task

class TaskSummarizer:
    """任务汇总与生成节点"""
    
    def __init__(self):
        self.client = get_openai_qwen_client()
    
    def format_results_for_display(self, results: List[Dict[str, Any]]) -> str:
        """格式化结果用于前端显示，支持图片和文字混合"""
        log_task(f"开始格式化 {len(results)} 个任务结果")
        formatted_content = ""
        
        for i, result in enumerate(results, 1):
            todo = result.get("todo", "")
            content = result.get("content", "")
            agent_type = result.get("agent_type", "")
            tool_results = result.get("tool_results", [])
            status = result.get("status", "")
            
            # 添加任务标题
            formatted_content += f"\n**{i}. {todo}**\n\n"
            log_info(f"处理任务 {i}: {todo[:30]}... (Agent: {agent_type})")
            
            if status == "error":
                log_error(f"任务 {i} 执行失败: {content}")
                formatted_content += f"❌ {content}\n\n"
                continue
            
            # 处理工具结果
            image_results = []
            text_results = []
            
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
                        
                        # 构建图片描述，优先使用prompt，如果没有就用文件名
                        description = prompt if prompt else (filename if filename else "生成的图片")
                        
                        if web_path:
                            image_results.append({
                                "path": web_path,
                                "description": description,
                                "filename": filename
                            })
                    elif tool_name in ["get_weather", "get_current_time"] and result_json.get("status") == "success":
                        # 文字工具结果
                        log_success(f"{tool_name} 工具调用成功")
                        text_results.append({
                            "tool": tool_name,
                            "data": result_json
                        })
                    elif tool_name == "web_search" and result_json.get("status") == "success":
                        # 网页搜索结果
                        search_count = result_json.get("total_results", 0)
                        log_success(f"网页搜索成功，找到 {search_count} 个结果")
                        text_results.append({
                            "tool": tool_name,
                            "data": result_json
                        })
                except Exception as e:
                    # 如果无法解析JSON，直接添加文本内容
                    # log_error(f"解析工具结果失败 {tool_name}: {str(e)}")
                    text_results.append({
                        "tool": tool_name,
                        "content": result_content
                    })
            
            # 添加图片结果
            for img_result in image_results:
                description = img_result['description']
                path = img_result['path']
                filename = img_result.get('filename', '')
                
                # 只添加markdown图片格式，不添加多余的文字描述
                formatted_content += f"![{description}]({path})\n\n"
            
            # 添加文字结果
            for text_result in text_results:
                if text_result.get("tool") == "get_weather" and "data" in text_result:
                    weather_data = text_result["data"]
                    formatted_content += f"**天气信息**\n"
                    formatted_content += f"地点：{weather_data.get('location', '')}\n"
                    formatted_content += f"天气：{weather_data.get('weather', '')}\n"
                    formatted_content += f"温度：{weather_data.get('temperature', '')}°C\n"
                    formatted_content += f"风向风力：{weather_data.get('wind', '')}\n"
                    formatted_content += f"湿度：{weather_data.get('humidity', '')}\n"
                    formatted_content += f"更新时间：{weather_data.get('report_time', '')}\n\n"
                elif text_result.get("tool") == "get_current_time" and "data" in text_result:
                    time_data = text_result["data"]
                    formatted_content += f"**当前时间**\n"
                    formatted_content += f"日期时间：{time_data.get('current_time', '')}\n"
                    formatted_content += f"星期：{time_data.get('weekday', '')}\n"
                    formatted_content += f"中文日期：{time_data.get('date', '')}\n"
                    formatted_content += f"中文时间：{time_data.get('time', '')}\n\n"
                elif text_result.get("tool") == "web_search" and "data" in text_result:
                    search_data = text_result["data"]
                    formatted_content += f"**搜索结果**\n"
                    formatted_content += f"搜索关键词：{search_data.get('query', '')}\n"
                    formatted_content += f"找到结果：{search_data.get('total_results', 0)} 个\n\n"
                    
                    # 显示搜索结果
                    results = search_data.get('results', [])
                    for idx, result in enumerate(results[:3], 1):  # 显示前3个结果
                        formatted_content += f"{idx}. **{result.get('title', '')}**\n"
                        formatted_content += f"{result.get('snippet', '')}\n"
                        formatted_content += f"来源：{result.get('site_name', '')} - [{result.get('url', '')}]({result.get('url', '')})\n\n"
                else:
                    formatted_content += f"**工具结果**\n"
                    formatted_content += f"{text_result.get('content', '')}\n\n"
            
            # 添加Agent生成的内容
            if content and content.strip():
                formatted_content += f"**AI生成内容**\n"
                formatted_content += f"{content}\n\n"
        
        log_success(f"格式化完成，生成内容长度: {len(formatted_content)} 字符")
        return formatted_content
    
    def summarize_all_results(self, original_question: str, todo_content: str, results: List[Dict[str, Any]]) -> str:
        """汇总所有子Agent的输出"""
        log_task("开始汇总所有任务结果")
        try:
            # 格式化所有结果
            formatted_results = self.format_results_for_display(results)
            
            # 构建汇总提示词
            system_prompt = f"""你是一个专业的报告生成与任务汇总专家。请将所有todo项的执行结果整合成一个完整、连贯的回答。

            要求：
            1. 理解所有子Agent的执行结果，并将它们整合成一个完整的、有逻辑的、阅读友好的回答
            2. **必须完整保留原始markdown图片格式**：![描述](路径)
            3. 确保内容连贯、逻辑清晰
            4. 如果有图片，必须保持原始的![alt](path)格式不变
            5. 为用户提供完整、友好的回复
            6. 重要：绝对不要使用#、##、###、####等任何markdown标题格式，只使用**粗体**来强调重点内容
            7. 对于每一个to-do项必须分段，使用**一、**、**二、**、**三、**等中文数字标题格式
            8. 保持良好的段落对齐，避免格式混乱
            9. **严格要求**：如果输入中包含![描述](路径)格式的图片，输出中必须原样保留，不能修改格式
            
            格式示例：
            **一、第一个任务标题**
            任务内容描述...
            ![图片描述](/static/generated_images/filename.png)
            
            **二、第二个任务标题**
            任务内容描述...
            
            请直接输出整合后的markdown内容，保持图片格式不变，不要添加额外的说明。"""

            user_message = f"""  
            用户的原始问题：
            {original_question}
            
            任务分解内容：
            {todo_content}
            
            所有子Agent的执行结果：
            {formatted_results}

            """
            
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
            
            # 如果汇总失败，返回格式化的原始结果
            if not summarized_content:
                log_error("汇总内容为空，返回格式化的原始结果")
                return formatted_results
            
            return summarized_content
            
        except Exception as e:
            log_error(f"汇总结果失败: {e}")
            # 如果汇总失败，返回格式化的原始结果
            return self.format_results_for_display(results)
    
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