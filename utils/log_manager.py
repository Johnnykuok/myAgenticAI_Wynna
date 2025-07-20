"""
实时日志管理模块
捕获所有print输出并同步到前端
"""
import sys
import threading
import time
from datetime import datetime
from typing import List, Dict, Any
from queue import Queue, Empty
import json

class LogCapture:
    """日志捕获类，重定向print输出"""
    
    def __init__(self):
        self.logs = []
        self.log_queue = Queue()
        self.original_stdout = sys.stdout
        self.lock = threading.Lock()
        self.max_logs = 1000  # 最多保存1000条日志
        
    def write(self, text):
        """重写write方法，捕获print输出"""
        # 写入原始输出
        self.original_stdout.write(text)
        self.original_stdout.flush()
        
        # 过滤空行和换行符
        text = text.strip()
        if text:
            timestamp = datetime.now().isoformat()
            log_entry = {
                "timestamp": timestamp,
                "message": text,
                "level": "INFO"
            }
            
            with self.lock:
                # 添加到日志列表
                self.logs.append(log_entry)
                
                # 限制日志数量
                if len(self.logs) > self.max_logs:
                    self.logs.pop(0)
                
                # 添加到队列供实时获取
                self.log_queue.put(log_entry)
    
    def flush(self):
        """flush方法，保持兼容性"""
        self.original_stdout.flush()
    
    def get_recent_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取最近的日志"""
        with self.lock:
            return self.logs[-limit:] if len(self.logs) > limit else self.logs.copy()
    
    def get_new_logs(self, timeout: float = 1.0) -> List[Dict[str, Any]]:
        """获取新的日志（阻塞式）"""
        new_logs = []
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                log_entry = self.log_queue.get(timeout=0.1)
                new_logs.append(log_entry)
            except Empty:
                if new_logs:  # 如果已经有日志，立即返回
                    break
                continue
        
        return new_logs
    
    def clear_logs(self):
        """清空日志"""
        with self.lock:
            self.logs.clear()
            # 清空队列
            while not self.log_queue.empty():
                try:
                    self.log_queue.get_nowait()
                except Empty:
                    break

# 全局日志捕获实例
_log_capture = None

def init_log_capture():
    """初始化日志捕获"""
    global _log_capture
    if _log_capture is None:
        _log_capture = LogCapture()
        sys.stdout = _log_capture
        print("🚀 日志捕获系统已启动")
    return _log_capture

def get_log_capture():
    """获取日志捕获实例"""
    global _log_capture
    if _log_capture is None:
        return init_log_capture()
    return _log_capture

def restore_stdout():
    """恢复原始stdout"""
    global _log_capture
    if _log_capture is not None:
        sys.stdout = _log_capture.original_stdout
        print("📝 日志捕获系统已关闭")

def log_info(message: str):
    """记录信息日志"""
    print(f"ℹ️  {message}")

def log_success(message: str):
    """记录成功日志"""
    print(f"✅ {message}")

def log_warning(message: str):
    """记录警告日志"""
    print(f"⚠️  {message}")

def log_error(message: str):
    """记录错误日志"""
    print(f"❌ {message}")

def log_task(message: str):
    """记录任务日志"""
    print(f"📋 {message}")

def log_agent(message: str):
    """记录Agent日志"""
    print(f"🤖 {message}")