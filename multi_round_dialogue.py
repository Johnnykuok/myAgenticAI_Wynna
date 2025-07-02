# 这是一个多轮对话的官方示例代码
import os
from volcenginesdkarkruntime import Ark
# 从环境变量中获取您的API KEY，配置方法见：https://www.volcengine.com/docs/82379/1399008
client = Ark(api_key=os.environ.get("ARK_API_KEY"))
client = Ark(
    api_key=os.environ.get("ARK_API_KEY"),
)

completion = client.chat.completions.create(
    # 替换 <MODEL> 为模型的Model ID , 查询Model ID：https://www.volcengine.com/docs/82379/1330310
    model="<MODEL>",
    messages=[
            {
                "content": "你是豆包，是由字节跳动开发的 AI 人工智能助手。",
                "role": "system",
            },
            {"content": "花椰菜是什么？", "role": "user"},
            {
                "content": "花椰菜又称菜花、花菜，是一种常见的蔬菜。",
                "role": "assistant",
            },
            {"content": "再详细点。", "role": "user"},
        ],
)
print(completion.choices[0].message.content)