# -*- coding: utf-8 -*-
"""
简单的凯利公式计算测试
不依赖外部库
"""


def kelly_calculate(win_probability, win_loss_ratio, planned_capital):
    """
    凯利公式计算

    f* = (bp - q) / b
    其中:
    - f* = 应投入的资金比例
    - b = 赔率（盈亏比）
    - p = 获胜概率
    - q = 失败概率 (1-p)
    """
    # 转换概率为小数
    p = win_probability / 100.0
    q = 1 - p
    b = win_loss_ratio

    # 计算凯利公式
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

    return {
        "kelly_fraction": max(0, round(kelly_fraction, 4)),
        "recommended_amount": round(recommended_amount, 2),
        "half_kelly_amount": round(half_kelly_amount, 2),
        "expected_value": round(expected_value, 4),
        "is_positive_ev": is_positive_ev,
    }


# 测试用例 1：正期望值 (胜率68%, 盈亏比2.5)
print("=" * 60)
print("Test 1 - Positive EV (Win Rate 68%, R/R Ratio 2.5)")
print("=" * 60)
result1 = kelly_calculate(68, 2.5, 100000)
print("Kelly Fraction: {:.2%}".format(result1['kelly_fraction']))
print("Recommended Amount: {:,.0f}".format(result1['recommended_amount']))
print("Half Kelly: {:,.0f}".format(result1['half_kelly_amount']))
print("Expected Value: {:.4f}".format(result1['expected_value']))
print("Positive EV: {}".format('Yes' if result1['is_positive_ev'] else 'No'))

# 测试用例 2：负期望值 (胜率35%, 盈亏比1.5)
print("\n" + "=" * 60)
print("Test 2 - Negative EV (Win Rate 35%, R/R Ratio 1.5)")
print("=" * 60)
result2 = kelly_calculate(35, 1.5, 100000)
print("Kelly Fraction: {:.2%}".format(result2['kelly_fraction']))
print("Recommended Amount: {:,.0f}".format(result2['recommended_amount']))
print("Expected Value: {:.4f}".format(result2['expected_value']))
print("Positive EV: {}".format('Yes' if result2['is_positive_ev'] else 'No'))
if not result2['is_positive_ev']:
    print("WARNING: Negative EV - System should veto this trade")

# 测试用例 3：盈亏比3.0 (止盈15%, 止损5%)
print("\n" + "=" * 60)
print("Test 3 - R/R Ratio 3.0 (TP 15%, SL 5%)")
print("=" * 60)
result3 = kelly_calculate(60, 3.0, 100000)
print("Kelly Fraction: {:.2%}".format(result3['kelly_fraction']))
print("Recommended Amount: {:,.0f}".format(result3['recommended_amount']))
print("Half Kelly: {:,.0f}".format(result3['half_kelly_amount']))
print("Expected Value: {:.4f}".format(result3['expected_value']))
print("Positive EV: {}".format('Yes' if result3['is_positive_ev'] else 'No'))

# 验证计算正确性
print("\n" + "=" * 60)
print("Verification")
print("=" * 60)
# 例如：p=0.68, b=2.5
# EV = 2.5 * 0.68 - 0.32 = 1.7 - 0.32 = 1.38
# f* = (2.5 * 0.68 - 0.32) / 2.5 = 1.38 / 2.5 = 0.552
p = 0.68
b = 2.5
q = 1 - p
ev_manual = b * p - q
kelly_manual = (b * p - q) / b
print("Manual - EV: {:.4f}, Kelly: {:.4f}".format(ev_manual, kelly_manual))
print("Program - EV: {:.4f}, Kelly: {:.4f}".format(result1['expected_value'], result1['kelly_fraction']))
is_correct = abs(ev_manual - result1['expected_value']) < 0.0001 and abs(kelly_manual - result1['kelly_fraction']) < 0.0001
print("Calculation Correct: {}".format(is_correct))
