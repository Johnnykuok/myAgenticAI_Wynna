import os
from dotenv import load_dotenv
from openai import OpenAI

# 加载环境变量
load_dotenv()

# 豆包模型配置
DOUBAO_BASE_URL = os.getenv("DOUBAO_BASE_URL")
DOUBAO_API_KEY = os.getenv("DOUBAO_API_KEY")
DOUBAO_MODEL = os.getenv("DOUBAO_MODEL")

# Qwen模型配置
QWEN_BASE_URL = os.getenv("QWEN_BASE_URL")
QWEN_API_KEY = os.getenv("QWEN_API_KEY")
QWEN_MODEL = os.getenv("QWEN_MODEL")

# DeepSeek模型配置
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL")

# 高德天气API配置
GAODE_API_KEY = os.getenv("GAODE_API_KEY")
GAODE_WEATHER_URL = os.getenv("GAODE_WEATHER_URL", "https://restapi.amap.com/v3/weather/weatherInfo")

# 博查AI搜索API配置
BOCHA_API_KEY = os.getenv("BOCHA_API_KEY")
BOCHA_API_URL = os.getenv("BOCHA_API_URL", "https://api.bochaai.com/v1/ai-search")

# 生成图片保存路径
GENERATED_IMAGES_PATH = os.getenv("GENERATED_IMAGES_PATH", "static/generated_images")

# Flask应用配置
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", 8070))

# 对话历史配置
CONVERSATIONS_DIR = "conversations"
MAX_CONVERSATION_ROUNDS = 3

# 系统提示词
SYSTEM_PROMPT = "你是由郭桓君同学开发的通用AI智能体，你的名字是Wynna。你的人设是一个讲话活泼可爱、情商高的小妹妹。你既可以与用户闲聊，也可以进行复杂任务的规划、分配、执行和汇总。你会最大程度的理解用户需求，并尽量满足用户的需求。"

# 初始化OpenAI客户端
def get_openai_doubao_client():
    """获取OpenAI客户端实例（豆包）"""
    return OpenAI(
        base_url=DOUBAO_BASE_URL,
        api_key=DOUBAO_API_KEY
    )

def get_openai_qwen_client():
    """获取OpenAI客户端实例（Qwen）"""
    return OpenAI(
        base_url=QWEN_BASE_URL,
        api_key=QWEN_API_KEY
    )

def get_openai_deepseek_client():
    """获取OpenAI客户端实例（DeepSeek）"""
    return OpenAI(
        base_url=DEEPSEEK_BASE_URL,
        api_key=DEEPSEEK_API_KEY
    )


def get_openai_client():
    """获取OpenAI客户端实例（默认豆包）"""
    return get_openai_doubao_client()

# 确保对话目录存在
def ensure_conversations_dir():
    """确保对话历史目录存在"""
    if not os.path.exists(CONVERSATIONS_DIR):
        os.makedirs(CONVERSATIONS_DIR)