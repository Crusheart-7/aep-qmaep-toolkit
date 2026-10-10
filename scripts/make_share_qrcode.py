#!/usr/bin/env python3
"""
make_share_qrcode.py
---------------------
把一个 AEP 工程文件打包成 QQ音乐"银河音效"分享二维码。

流程（按技术文档 §6-7）：
    AEP --gzip--> Base64 --塞入 soundParam JSON--> 拼分享URL --> 生成二维码 PNG

用法：
    python make_share_qrcode.py --aep project.aep --name "我的音效" --uin 123456 \
        --out-url share_url.txt --out-png share_qrcode.png

注意：
- 已用一份可正常载入的 QQ音乐自定义音效二维码逐项验证：soundParam 是直接
  URL-encode 的 JSON；首字段必须是字面量 `(params)soundType=1024`，并包含
  soundId=20000 与 soundDes=自定义音效。
- 需要 `qrcode` 库生成 PNG（`pip install qrcode[pil] --break-system-packages`）。
  没装的话脚本仍会输出分享 URL 和 soundParam，只是跳过 PNG 生成。
"""

import argparse
import base64
import gzip
import json
import sys
import urllib.parse
from pathlib import Path

SHARE_BASE_URL = "https://y.qq.com/m/client/supersound/dist/index.html"


def build_sound_param(aep_bytes: bytes, name: str, uin: str) -> str:
    gzipped = gzip.compress(aep_bytes)
    param_b64 = base64.b64encode(gzipped).decode("ascii")
    payload = {"aepEdit": {"name": name, "param": param_b64, "uin": uin}}
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def build_share_url(
    name: str,
    sound_param_json: str,
    sound_type: str,
    sound_id: str,
    description: str,
) -> str:
    """构造与 QQ音乐已验证的自定义音效分享链接相同的参数布局。"""
    # `Music.deserializeParam` 以字面量 `(params)` 前缀识别分享参数。
    # 不能将这个首字段改成普通的 `soundType`。
    first = "(params)soundType=" + urllib.parse.quote(sound_type, safe="")
    query = [
        ("soundId", sound_id),
        ("soundName", name),
        ("soundDes", description),
        ("ADTAG", "erweimashare"),
        ("channelId", "10036163"),
        ("openinqqmusic", "1"),
        ("soundParam", sound_param_json),
    ]
    return SHARE_BASE_URL + "?" + first + "&" + urllib.parse.urlencode(
        query, quote_via=urllib.parse.quote
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--aep", required=True, type=Path, help="输入 AEP 文件路径")
    parser.add_argument("--name", required=True, help="音效名称（soundName / aepEdit.name）")
    parser.add_argument("--uin", required=True, help="QQ音乐用户ID（uin）")
    parser.add_argument(
        "--sound-type",
        default="1024",
        help="QQ音乐音效类型；自定义银河音效应使用 1024（默认）。",
    )
    parser.add_argument(
        "--sound-id",
        default="20000",
        help="自定义音效分享 ID；已验证样本使用 20000（默认）。",
    )
    parser.add_argument(
        "--description",
        default="自定义音效",
        help="分享页显示的音效描述。",
    )
    parser.add_argument("--out-url", type=Path, default=Path("share_url.txt"))
    parser.add_argument("--out-png", type=Path, default=Path("share_qrcode.png"))
    args = parser.parse_args()

    aep_bytes = args.aep.read_bytes()
    sound_param_json = build_sound_param(aep_bytes, args.name, args.uin)
    url = build_share_url(
        args.name,
        sound_param_json,
        args.sound_type,
        args.sound_id,
        args.description,
    )

    args.out_url.write_text(url, encoding="utf-8")
    print(f"[url] 已写入 {args.out_url}")
    print(url)

    try:
        import qrcode

        img = qrcode.make(url)
        img.save(args.out_png)
        print(f"[png] 已写入 {args.out_png}")
    except ImportError:
        print(
            "[png] 未安装 qrcode 库，跳过 PNG 生成。"
            "可运行: pip install qrcode[pil] --break-system-packages",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
