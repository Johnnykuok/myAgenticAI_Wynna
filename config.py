import os
from dotenv import load_dotenv
from openai import OpenAI

# 加载环境变量
load_dotenv()

# 豆包模型配置
DOUBAO_BASE_URL = os.getenv("DOUBAO_BASE_URL")
DOUBAO_API_KEY = os.getenv("DOUBAO_API_KEY")
DOUBAO_MODEL = os.getenv("DOUBAO_MODEL")

# 高德天气API配置
GAODE_API_KEY = os.getenv("GAODE_API_KEY")
GAODE_WEATHER_URL = os.getenv("GAODE_WEATHER_URL")

# Flask应用配置
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", 8070))

# 对话历史配置
CONVERSATIONS_DIR = "conversations"
MAX_CONVERSATION_ROUNDS = 3

# 系统提示词
SYSTEM_PROMPT = "你是由郭桓君同学开发的智能体。你的人设是一个讲话活泼可爱、情商高的小妹妹"

# 初始化OpenAI客户端
def get_openai_client():
    """获取OpenAI客户端实例"""
    return OpenAI(
        base_url=DOUBAO_BASE_URL,
        api_key=DOUBAO_API_KEY
    )

# 确保对话目录存在
def ensure_conversations_dir():
    """确保对话历史目录存在"""
    if not os.path.exists(CONVERSATIONS_DIR):
        os.makedirs(CONVERSATIONS_DIR)