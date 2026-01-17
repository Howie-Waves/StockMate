"""
StockMate - 智能股票分析 Agent 系统
基于 smolagents 框架的多智能体协作系统
"""

__version__ = "0.1.0"
__author__ = "StockMate Team"

from stockmate.models import StockAnalysisReport, MarketData, NewsItem, BacktestResult
from stockmate.tools.stock_tools import (
    get_a_share_data,
    get_latest_news,
    run_backtest,
)

__all__ = [
    "StockAnalysisReport",
    "MarketData",
    "NewsItem",
    "BacktestResult",
    "get_a_share_data",
    "get_latest_news",
    "run_backtest",
]
