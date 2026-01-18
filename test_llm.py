"""
测试 LLM 服务是否正常工作
"""

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 测试配置
print("=== LLM 服务配置检查 ===")
print(f"OPENAI_API_KEY: {'已配置' if os.getenv('OPENAI_API_KEY') else '未配置'}")
print(f"OPENAI_BASE_URL: {os.getenv('OPENAI_BASE_URL', '未配置')}")
print(f"MODEL_NAME: {os.getenv('MODEL_NAME', '未配置')}")
print()

# 测试导入
try:
    from stockmate.tools.llm_service import (
        get_llm_client,
        generate_llm_explanation,
        generate_market_trend_description
    )
    print("✓ LLM 服务模块导入成功")
except ImportError as e:
    print(f"✗ LLM 服务模块导入失败: {e}")
    exit(1)

# 测试客户端创建
print("\n=== 测试 LLM 客户端创建 ===")
client = get_llm_client()
if client:
    print(f"✓ LLM 客户端创建成功: {type(client)}")
else:
    print("✗ LLM 客户端创建失败")
    exit(1)

# 测试简单的 API 调用
print("\n=== 测试 LLM API 调用 ===")
test_prompt = "请用一句话介绍什么是股票投资。"
print(f"测试提示词: {test_prompt}")

try:
    response = generate_llm_explanation(test_prompt, max_tokens=100, cache_key="test_prompt")
    print(f"✓ LLM 响应成功")
    print(f"响应内容: {response}")
except Exception as e:
    print(f"✗ LLM 调用失败: {e}")
    exit(1)

# 测试股票分析功能
print("\n=== 测试股票分析功能 ===")
try:
    trend_desc = generate_market_trend_description(
        symbol="600000",
        current_price=10.50,
        change_pct=2.35
    )
    print(f"✓ 趋势描述生成成功")
    print(f"趋势描述: {trend_desc}")
except Exception as e:
    print(f"✗ 趋势描述生成失败: {e}")

print("\n=== 所有测试完成 ===")
