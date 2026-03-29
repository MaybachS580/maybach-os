"""
Maybach-OS: 个人 AI 商业智能体框架
"""

__version__ = "0.1.0"
__author__ = "Maybach"
__license__ = "MIT"

from .core.agent import MaybachAgent
from .notify.notifier import Notifier

__all__ = ["MaybachAgent", "Notifier"]
