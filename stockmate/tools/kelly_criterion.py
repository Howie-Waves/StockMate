"""
凯利公式仓位管理工具
Kelly Criterion Position Sizing Tool

基于凯利公式计算最优仓位比例，实现科学的资金管理。
公式：f* = (bp - q) / b
其中：
- f* = 应投入的资金比例
- b = 赔率（盈亏比）
- p = 获胜概率
- q = 失败概率 (1-p)
"""

from typing import Dict, Any
import math


class KellyCalculator:
    """凯利公式计算器"""

    @staticmethod
    def calculate(
        win_probability: float,  # 获胜概率 (0-100)
        win_loss_ratio: float,   # 盈亏比（例如：预期赚3元亏1元，则 ratio=3）
        planned_capital: float = 100000,
        stop_loss_pct: float = 5.0,
        take_profit_pct: float = 15.0,
    ) -> Dict[str, Any]:
        """
        使用凯利公式计算最优仓位

        公式: f* = (bp - q) / b
        其中:
        - f* = 应投入的资金比例
        - b = 赔率（盈亏比）
        - p = 获胜概率
        - q = 失败概率 (1-p)

        Args:
            win_probability: 获胜概率百分比 (0-100)
            win_loss_ratio: 盈亏比，例如 2.5 表示预期盈利是亏损的 2.5 倍
            planned_capital: 计划投入的总资金
            stop_loss_pct: 止损百分比
            take_profit_pct: 止盈百分比

        Returns:
            包含计算结果的字典
        """
        # 转换概率为小数
        p = win_probability / 100.0
        q = 1 - p
        b = win_loss_ratio

        # 计算凯利公式
        # f* = (bp - q) / b
        kelly_fraction = (b * p - q) / b

        # 期望值计算
        expected_value = b * p - q

        # 判断是否为正期望值
        is_positive_ev = expected_value > 0

        # 计算建议金额
        if kelly_fraction > 0:
            recommended_amount = planned_capital * kelly_fraction
            half_kelly_amount = planned_capital * (kelly_fraction / 2)
        else:
            recommended_amount = 0
            half_kelly_amount = 0

        # 生成风险提示
        risk_warning = KellyCalculator._generate_risk_warning(
            kelly_fraction, is_positive_ev, win_probability
        )

        # 实际盈亏比（基于止盈止损）
        actual_win_loss_ratio = take_profit_pct / stop_loss_pct if stop_loss_pct > 0 else 0

        return {
            "win_probability": round(win_probability, 2),
            "win_loss_ratio": round(win_loss_ratio, 2),
            "planned_capital": round(planned_capital, 2),
            "stop_loss_pct": round(stop_loss_pct, 2),
            "take_profit_pct": round(take_profit_pct, 2),
            "kelly_fraction": max(0, round(kelly_fraction, 4)),
            "recommended_amount": round(recommended_amount, 2),
            "half_kelly_amount": round(half_kelly_amount, 2),
            "expected_value": round(expected_value, 4),
            "is_positive_ev": is_positive_ev,
            "risk_warning": risk_warning,
            "actual_win_loss_ratio": round(actual_win_loss_ratio, 2),
        }

    @staticmethod
    def _generate_risk_warning(
        kelly_fraction: float, is_positive_ev: bool, win_prob: float
    ) -> str:
        """生成风险提示"""
        if not is_positive_ev:
            return "⚠️ 负期望值：不建议交易，凯利公式建议空仓等待更好的机会。"

        if kelly_fraction > 0.5:
            return "⚠️ 高风险警告：凯利公式建议仓位过高，强烈建议使用半凯利或1/4凯利以降低风险。"

        if kelly_fraction > 0.25:
            return "⚠️ 风险提示：建议考虑使用半凯利公式（保守策略）以平滑资金曲线。"

        if win_prob < 55:
            return "⚠️ 胜率偏低：虽然期望值为正，但建议谨慎使用较小仓位。"

        return "✅ 风险可控：可以考虑使用凯利公式建议的仓位。"

    @staticmethod
    def calculate_from_backtest(
        backtest_win_rate: float,
        backtest_return: float,
        planned_capital: float,
        stop_loss_pct: float = 5.0,
        take_profit_pct: float = 15.0,
    ) -> Dict[str, Any]:
        """
        从回测结果计算凯利公式

        Args:
            backtest_win_rate: 回测胜率 (%)
            backtest_return: 回测收益率 (%)
            planned_capital: 计划投入资金
            stop_loss_pct: 止损比例
            take_profit_pct: 止盈比例

        Returns:
            凯利公式计算结果
        """
        # 使用止盈止损比例作为基础盈亏比
        base_win_loss_ratio = take_profit_pct / stop_loss_pct if stop_loss_pct > 0 else 2.0

        return KellyCalculator.calculate(
            win_probability=backtest_win_rate,
            win_loss_ratio=base_win_loss_ratio,
            planned_capital=planned_capital,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct,
        )


if __name__ == "__main__":
    # 测试凯利公式计算
    print("=== 测试凯利公式计算器 ===")

    # 测试用例 1：正期望值
    result1 = KellyCalculator.calculate(
        win_probability=68,
        win_loss_ratio=2.5,
        planned_capital=100000,
        stop_loss_pct=5.0,
        take_profit_pct=12.5,
    )
    print("\n测试 1 - 正期望值 (胜率68%, 盈亏比2.5):")
    print(f"  凯利比例: {result1['kelly_fraction']:.2%}")
    print(f"  建议金额: ¥{result1['recommended_amount']:,.0f}")
    print(f"  期望值: {result1['expected_value']:.4f}")
    print(f"  风险提示: {result1['risk_warning']}")

    # 测试用例 2：负期望值
    result2 = KellyCalculator.calculate(
        win_probability=40,
        win_loss_ratio=1.5,
        planned_capital=100000,
        stop_loss_pct=5.0,
        take_profit_pct=7.5,
    )
    print("\n测试 2 - 负期望值 (胜率40%, 盈亏比1.5):")
    print(f"  凯利比例: {result2['kelly_fraction']:.2%}")
    print(f"  期望值: {result2['expected_value']:.4f}")
    print(f"  风险提示: {result2['risk_warning']}")
