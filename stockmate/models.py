"""
StockMate 数据模型定义
使用 Pydantic 确保类型安全和数据验证
"""

from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional
from datetime import datetime


class StockAnalysisReport(BaseModel):
    """
    股票分析报告 - 最终输出标准结构

    所有 Agent 的决策必须收敛于此结构，确保系统输出的一致性和可验证性。
    """

    # 基本信息
    ticker: str = Field(..., description="股票代码，如 '600000' 或 '000001'")

    # 宏观/新闻情感分析
    sentiment_score: float = Field(
        ...,
        ge=0,
        le=100,
        description="市场情绪评分，0-100，越高越看涨",
    )

    # 技术面信号
    technical_signal: Literal["Buy", "Sell", "Hold"] = Field(
        ..., description="技术分析信号"
    )

    # 风控评估（拥有一票否决权）
    risk_assessment: Literal["Approved", "Rejected"] = Field(
        ..., description="风控评估，Rejected 将强制否决所有买入信号"
    )

    # 风险指标
    var_value: float = Field(..., ge=0, description="在险价值或波动率数值")

    # 最终决策
    final_decision: Literal["Buy", "Sell", "Wait"] = Field(
        ..., description="最终操作建议，综合考虑所有因素后的决策"
    )

    # 决策依据
    reasoning: str = Field(..., description="决策逻辑链摘要，必须包含数据来源引用")

    # 回测验证结果
    backtest_win_rate: Optional[float] = Field(
        None, description="历史策略胜率 (0-100)"
    )
    backtest_return: Optional[float] = Field(
        None, description="历史策略总收益率 (%)"
    )

    # 元数据
    analysis_timestamp: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        description="分析时间戳",
    )

    @field_validator("sentiment_score")
    @classmethod
    def validate_sentiment(cls, v: float) -> float:
        """验证情绪分数在合理范围内"""
        if not 0 <= v <= 100:
            raise ValueError("sentiment_score 必须在 0-100 之间")
        return round(v, 2)

    @field_validator("var_value")
    @classmethod
    def validate_var(cls, v: float) -> float:
        """验证风险指标为正数"""
        if v < 0:
            raise ValueError("var_value 必须为非负数")
        return round(v, 4)

    def model_dump_json(self, **kwargs) -> str:
        """输出格式化的 JSON 字符串"""
        return super().model_dump_json(indent=2, **kwargs)

    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "600000",
                "sentiment_score": 65.5,
                "technical_signal": "Buy",
                "risk_assessment": "Approved",
                "var_value": 0.0234,
                "final_decision": "Buy",
                "reasoning": "基于 RSI 低于 30 的超卖信号，配合正面新闻情绪，回测显示该策略历史胜率 68%。",
                "backtest_win_rate": 68.5,
                "backtest_return": 24.3,
                "analysis_timestamp": "2024-01-15 14:30:00",
            }
        }


class MarketData(BaseModel):
    """市场数据结构"""

    ticker: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    date: str

    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "600000",
                "open": 10.50,
                "high": 10.80,
                "low": 10.40,
                "close": 10.75,
                "volume": 125000000,
                "date": "2024-01-15",
            }
        }


class NewsItem(BaseModel):
    """新闻条目结构"""

    title: str
    content: str
    publish_time: str
    source: str = "未知来源"

    class Config:
        json_schema_extra = {
            "example": {
                "title": "某公司发布年度业绩预增公告",
                "content": "预计净利润同比增长50%...",
                "publish_time": "2024-01-15 09:30:00",
                "source": "东方财富网",
            }
        }


class BacktestResult(BaseModel):
    """回测结果结构"""

    strategy_type: str
    win_rate: float = Field(..., ge=0, le=100, description="胜率 (%)")
    total_return: float = Field(..., description="总收益率 (%)")
    sharpe_ratio: Optional[float] = Field(None, description="夏普比率")
    max_drawdown: Optional[float] = Field(None, description="最大回撤 (%)")
    total_trades: int = Field(..., ge=0, description="总交易次数")

    class Config:
        json_schema_extra = {
            "example": {
                "strategy_type": "RSI",
                "win_rate": 68.5,
                "total_return": 24.3,
                "sharpe_ratio": 1.25,
                "max_drawdown": -12.5,
                "total_trades": 45,
            }
        }
