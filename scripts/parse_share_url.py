#!/usr/bin/env python3
"""
parse_share_url.py
-------------------
把一个 QQ音乐"银河音效"分享 URL（或直接一段 soundParam）还原成 AEP 文件。
是 make_share_qrcode.py 的逆过程。

用法：
    python parse_share_url.py --url "https://y.qq.com/...&soundParam=...." --out restored.aep
    python parse_share_url.py --sound-param '{"aepEdit":{...}}' --out restored.aep
"""

import argparse
import base64
import gzip
import json
import urllib.parse
from pathlib import Path


def extract_sound_param(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(parsed.query)
    if "soundParam" not in qs:
        raise SystemExit("URL 中没有找到 soundParam 查询参数")
    return qs["soundParam"][0]


def sound_param_to_aep(sound_param_json: str) -> bytes:
    payload = json.loads(sound_param_json)
    param_b64 = payload["aepEdit"]["param"]
    gzipped = base64.b64decode(param_b64)
    return gzip.decompress(gzipped)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--url", help="完整分享 URL")
    src.add_argument("--sound-param", help="直接传 soundParam 的 JSON 字符串")
    parser.add_argument("--out", required=True, type=Path, help="还原出的 AEP 输出路径")
    args = parser.parse_args()

    sound_param_json = args.sound_param if args.sound_param else extract_sound_param(args.url)
    aep_bytes = sound_param_to_aep(sound_param_json)
    args.out.write_bytes(aep_bytes)
    print(f"[restore] -> {args.out} ({len(aep_bytes)} bytes)")


if __name__ == "__main__":
    main()
