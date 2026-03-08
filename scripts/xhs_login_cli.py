#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.core.write_xiaohongshu import XiaohongshuPoster


async def _main() -> int:
    parser = argparse.ArgumentParser(description="小红书登录态获取工具（参考 xiaohongshu-mcp/xhs-toolkit 的登录工具思路）")
    parser.add_argument("--phone", required=True, help="手机号")
    parser.add_argument("--country-code", default="+86", help="国家区号，默认 +86")
    parser.add_argument("--user-id", type=int, default=None, help="可选：绑定到指定本地用户ID的数据目录")
    args = parser.parse_args()

    poster = XiaohongshuPoster(user_id=args.user_id)
    try:
        await poster.initialize()
        await poster.login(args.phone, args.country_code)
        logged_in = await poster._is_creator_logged_in()
        if logged_in:
            print("✅ 登录态已保存，可用于后续无头/服务模式发布")
            return 0
        print("❌ 未检测到有效登录态")
        return 1
    finally:
        await poster.cleanup()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
