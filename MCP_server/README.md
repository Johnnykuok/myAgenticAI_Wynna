# MCP服务器

这个文件夹包含了基于MCP（Model Context Protocol）协议的服务器文件。

## 文件说明

- `photo_generator_server.py` - 图片生成Agent服务器
  - 负责处理图片生成任务
  - 使用豆包文生图API
  - 通过MCP协议提供图片生成工具

- `text_generator_server.py` - 文字处理Agent服务器  
  - 负责处理文字相关任务
  - 提供天气查询和时间查询工具
  - 通过MCP协议与主系统通信

## 使用方式

这些服务器文件被`task_dispatcher.py`调用，用于实现任务的分布式处理。

## 注意事项

- 这些文件需要安装MCP相关依赖包才能运行
- 目前系统使用`simple_task_dispatcher.py`作为简化版本，不依赖MCP协议
- MCP服务器文件保留作为未来扩展的参考实现