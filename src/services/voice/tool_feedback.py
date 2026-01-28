"""Tool Feedback for Voice Agent.

在工具调用时生成语音反馈。

Validates: Requirements 10.1, 10.2, 10.3, 10.4
"""

from enum import Enum


class FeedbackVerbosity(str, Enum):
    """反馈详细程度"""
    MINIMAL = "minimal"
    NORMAL = "normal"
    VERBOSE = "verbose"


class ToolFeedbackGenerator:
    """工具反馈生成器"""

    # 工具名称映射
    TOOL_NAMES = {
        "search": "搜索",
        "web_search": "网络搜索",
        "calculator": "计算器",
        "code_interpreter": "代码执行",
        "file_read": "读取文件",
        "file_write": "写入文件",
    }

    def __init__(self, verbosity: FeedbackVerbosity = FeedbackVerbosity.NORMAL):
        self.verbosity = verbosity

    def get_tool_display_name(self, tool_name: str) -> str:
        """获取工具显示名称"""
        return self.TOOL_NAMES.get(tool_name, tool_name)

    def generate_start_feedback(self, tool_name: str) -> str | None:
        """生成工具开始执行的反馈"""
        if self.verbosity == FeedbackVerbosity.MINIMAL:
            return None
        
        display_name = self.get_tool_display_name(tool_name)
        
        if self.verbosity == FeedbackVerbosity.VERBOSE:
            return f"正在使用{display_name}工具，请稍候"
        return f"正在{display_name}"

    def generate_complete_feedback(self, tool_name: str, success: bool) -> str | None:
        """生成工具完成的反馈"""
        if self.verbosity == FeedbackVerbosity.MINIMAL:
            return None
        
        display_name = self.get_tool_display_name(tool_name)
        
        if not success:
            return f"{display_name}失败了"
        
        if self.verbosity == FeedbackVerbosity.VERBOSE:
            return f"{display_name}已完成"
        return None  # NORMAL 模式下成功不播报

    def generate_result_summary(self, tool_name: str, result: str) -> str:
        """生成结果摘要"""
        # 截断过长的结果
        max_len = 200 if self.verbosity == FeedbackVerbosity.VERBOSE else 100
        if len(result) > max_len:
            result = result[:max_len] + "..."
        return result

    def set_verbosity(self, verbosity: FeedbackVerbosity):
        """设置详细程度"""
        self.verbosity = verbosity
