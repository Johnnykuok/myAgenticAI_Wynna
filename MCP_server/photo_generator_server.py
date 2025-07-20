import json
import base64
import os
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from mcp.server import FastMCP

# 加载环境变量
load_dotenv()

# 初始化 FastMCP 服务器
app = FastMCP('photo-generator-server')

# 豆包文生图API配置
doubao_client = OpenAI(
    base_url=os.getenv("DOUBAO_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"),
    api_key=os.getenv("DOUBAO_API_KEY")
)

@app.tool()
async def generate_image(prompt: str) -> str:
    """
    使用豆包大模型生成图片
    
    Args:
        prompt: 图片生成的描述文本，详细描述想要生成的图片内容
    
    Returns:
        生成图片的本地保存路径的JSON字符串
    """
    print(f"🎨 收到图片生成请求: {prompt[:100]}...")
    try:
        # 调用豆包文生图API
        print("📡 调用豆包文生图API...")
        response = doubao_client.images.generate(
            model="doubao-seedream-3-0-t2i-250415",
            prompt=prompt,
            size="2048x2048",
            response_format="b64_json"
        )
        print("✅ 豆包API响应成功，开始处理图片数据")
        
        # 获取Base64编码的图像数据
        b64_image_data = response.data[0].b64_json
        print(f"📥 获取到Base64图片数据，大小: {len(b64_image_data)} 字符")
        
        # 解码Base64数据
        image_data = base64.b64decode(b64_image_data)
        print(f"🔄 解码完成，图片大小: {len(image_data)} 字节")
        
        # 确保生成的图片保存目录存在  
        images_dir = os.getenv("GENERATED_IMAGES_PATH", "static/generated_images")
        # 如果是相对路径，确保从项目根目录开始
        if not os.path.isabs(images_dir):
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            images_dir = os.path.join(project_root, images_dir)
        os.makedirs(images_dir, exist_ok=True)
        print(f"📁 图片保存目录: {images_dir}")
        
        # 生成文件名（使用时间戳避免重复）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"generated_image_{timestamp}.png"
        filepath = os.path.join(images_dir, filename)
        print(f"💾 准备保存图片: {filename}")
        
        # 保存图片
        with open(filepath, "wb") as f:
            f.write(image_data)
        print(f"✅ 图片保存成功: {filepath}")
        
        return json.dumps({
            "status": "success",
            "message": "图片生成成功",
            "filepath": filepath,
            "filename": filename,
            "web_path": f"/static/generated_images/{filename}",
            "prompt": prompt
        }, ensure_ascii=False)
        
    except Exception as e:
        print(f"❌ 图片生成失败: {str(e)}")
        return json.dumps({
            "status": "error", 
            "message": f"图片生成失败: {str(e)}"
        }, ensure_ascii=False)

if __name__ == "__main__":
    app.run(transport='stdio')