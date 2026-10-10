#!/usr/bin/env python3
"""
aep_param_tool.py
------------------
直接在 AEP 文件里定位并修改效果器参数，不依赖 QMAEP/AEPK 的任何编码层。

背景：用真实样本（500-全景环绕.aep）逐字节比对验证过，AEP 里每一个可调参数
都是这样紧挨着存的：

    [float32 数值][uint32 标签长度][UTF-8 标签文本]

例如 `Right Time` 前面 8 字节就是它的数值 26.12245（对应文档里"500-全景环绕"
案例的 Right Delay）。这个规律在文件里 18 处标签上全部验证通过，因此本工具
用它做通用扫描，不需要针对某一个预设写死偏移量。

用法：
    # 列出某个 AEP 里所有可识别的 (偏移, 数值, 标签) 三元组
    python aep_param_tool.py list --in project.aep

    # 把 "Right Time" 对应的数值改成 0，另存为新文件（按文档 §5.2 建议，
    # 只归零参数、不删节点）
    python aep_param_tool.py set --in project.aep --out project_no_delay.aep \
        --label "Right Time" --value 0

    # 标签重名/想精确定位时，直接按 float 值所在偏移改
    python aep_param_tool.py set --in project.aep --out project_edited.aep \
        --offset 0x40c --value 0
"""

import argparse
import re
import struct
import sys
from pathlib import Path

LABEL_RE = re.compile(r'^([\x20-\x7e]+|[\u4e00-\u9fff]+)+$')


def scan_params(data: bytes, min_len: int = 3, max_len: int = 128):
    """扫描 [float32][uint32 len][utf8 text] 模式，返回 (float_offset, value, label_offset, text) 列表。"""
    results = []
    i = 0
    n = len(data)
    while i + 8 <= n:
        length = struct.unpack_from("<I", data, i + 4)[0]
        if min_len <= length <= max_len and i + 8 + length <= n:
            chunk = data[i + 8 : i + 8 + length]
            try:
                text = chunk.decode("utf-8")
            except UnicodeDecodeError:
                text = None
            if text is not None and LABEL_RE.match(text):
                val = struct.unpack_from("<f", data, i)[0]
                if val == val and abs(val) < 1e7:  # 排除 NaN / 明显不合理的数值
                    results.append((i, val, i + 8, text))
        i += 1
    return results


def cmd_list(args: argparse.Namespace) -> None:
    data = args.inp.read_bytes()
    params = scan_params(data, args.min_len, args.max_len)
    if not params:
        print("没有找到匹配 [float32][len][utf8] 模式的参数——这个文件的内部结构可能和"
              "500-全景环绕.aep 不完全一样，可以尝试放宽 --min-len/--max-len，或用十六进制"
              "工具手动比对。", file=sys.stderr)
        return
    for off, val, str_off, text in params:
        print(f"float@0x{off:04x} = {val:<14.5f}  label@0x{str_off:04x} = {text!r}")


def cmd_set(args: argparse.Namespace) -> None:
    data = bytearray(args.inp.read_bytes())

    if args.offset is not None:
        target_off = args.offset
    else:
        if not args.label:
            raise SystemExit("必须提供 --label 或 --offset 其中之一")
        params = scan_params(bytes(data), args.min_len, args.max_len)
        matches = [(off, val) for off, val, _, text in params if text == args.label]
        if not matches:
            raise SystemExit(f"没有找到标签为 {args.label!r} 的参数，先用 `list` 子命令确认标签名/偏移。")
        if len(matches) > 1:
            offs = ", ".join(hex(o) for o, _ in matches)
            raise SystemExit(
                f"标签 {args.label!r} 出现了 {len(matches)} 次（偏移: {offs}），"
                "存在歧义，请改用 --offset 精确指定其中一个。"
            )
        target_off, old_val = matches[0]

    old_val = struct.unpack_from("<f", data, target_off)[0]
    struct.pack_into("<f", data, target_off, args.value)

    args.out.write_bytes(bytes(data))
    label_desc = args.label if args.label else f"offset 0x{target_off:04x}"
    print(f"[set] {label_desc}: {old_val} -> {args.value}  已写入 {args.out}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="列出 AEP 里所有可识别的参数")
    p_list.add_argument("--in", dest="inp", required=True, type=Path)
    p_list.add_argument("--min-len", dest="min_len", type=int, default=3)
    p_list.add_argument("--max-len", dest="max_len", type=int, default=128)
    p_list.set_defaults(func=cmd_list)

    p_set = sub.add_parser("set", help="修改某个参数的数值，另存为新文件")
    p_set.add_argument("--in", dest="inp", required=True, type=Path)
    p_set.add_argument("--out", dest="out", required=True, type=Path)
    p_set.add_argument("--label", dest="label", help="按标签文本定位，如 'Right Time'")
    p_set.add_argument("--offset", dest="offset", type=lambda s: int(s, 0), help="按浮点数值的字节偏移精确定位（支持 0x 前缀）")
    p_set.add_argument("--value", dest="value", type=float, required=True)
    p_set.add_argument("--min-len", dest="min_len", type=int, default=3)
    p_set.add_argument("--max-len", dest="max_len", type=int, default=128)
    p_set.set_defaults(func=cmd_set)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
