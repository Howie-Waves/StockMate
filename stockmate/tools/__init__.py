"""StockMate 工具模块"""

from stockmate.tools.stock_tools import (
    get_a_share_data,
    get_latest_news,
    run_backtest,
    get_stock_info,
    get_stock_news,
    backtest_strategy,
)

__all__ = [
    "get_a_share_data",
    "get_latest_news",
    "run_backtest",
    "get_stock_info",
    "get_stock_news",
    "backtest_strategy",
]
