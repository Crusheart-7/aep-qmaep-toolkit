#!/usr/bin/env python3
"""
aep_module_tool.py
--------------------
在 AEP 层面彻底删除一个效果模块（而不是把参数清零），并同步修正根结构的
模块计数与引用表。只处理 AEP 本身，不涉及任何编码/加密层。

## 背景

`aep_param_tool.py` 的 `set` 只改数值、不改结构，适合"保留节点关闭效果"
的场景。但如果目标就是让某个模块彻底从工程里消失（而不是数值归零），
必须同步做三件事：

1. 删除该模块覆盖的完整字节区间
2. 根结构的模块计数减一
3. 根引用表里，指向被删区间内部的引用要整条删掉；指向被删区间之后的
   引用要整体减去被删长度；指向被删区间之前的引用不用动

用真实样本（500-全景环绕.aep，删除 Delay 模块 0x328–0x460）验证过：
按这个规则算出来的新文件，和实际验证成功的目标文件逐字节相同。

## 已验证的根结构（仅这一个样本，不代表所有 AEP 都一样）

```
offset 0x20 (uint32): 模块数量
offset 0x24 起，每 4 字节一个 uint32：模块引用表，长度 = 模块数量
```

**其他 AEP 文件必须自己先确认这个假设是否成立**（用 `inspect-header` 子命令
看一下数量和引用表是否像样），本工具不会替你猜测别的文件的头部布局。

## 用法

    # 查看头部：模块数量 + 引用表，自己判断是否符合上面的假设
    python aep_module_tool.py inspect-header --in project.aep

    # 已经用 aep_param_tool.py list 之类的方法确定了要删除的模块的
    # 完整字节区间 [start, end) 之后，执行删除：
    python aep_module_tool.py delete-range --in project.aep --out project_no_delay.aep \
        --start 0x328 --end 0x460

    # 删除后可以顺手确认目标字符串消失、其它字符串还在
    python aep_module_tool.py check-strings --in project_no_delay.aep \
        --absent "Right Feedback,Left Feedback,Right Time,Left Time" \
        --present "16000 Hz,Center,Width"
"""

import argparse
import struct
from pathlib import Path


def inspect_header(data: bytes, count_off: int, refs_off: int) -> None:
    count = struct.unpack_from("<I", data, count_off)[0]
    print(f"offset 0x{count_off:x}: 模块数量(假设) = {count}")
    if count > 64:
        print("  数量看起来不太合理（>64），这个样本的头部布局假设可能不适用于当前文件。")
        return
    print(f"offset 0x{refs_off:x} 起的引用表（{count} 项）：")
    for i in range(count):
        off = refs_off + i * 4
        if off + 4 > len(data):
            print(f"  [{i}] offset 0x{off:x}: 超出文件范围")
            continue
        val = struct.unpack_from("<I", data, off)[0]
        flag = "（超出文件长度，可疑）" if val > len(data) else ""
        print(f"  [{i}] @0x{off:x} = 0x{val:x} ({val}){flag}")


def delete_range(data: bytes, start: int, end: int, count_off: int, refs_off: int) -> bytes:
    if not (0 <= start < end <= len(data)):
        raise SystemExit(f"非法区间 [0x{start:x}, 0x{end:x})，文件长度 0x{len(data):x}")

    count = struct.unpack_from("<I", data, count_off)[0]
    old_refs = [struct.unpack_from("<I", data, refs_off + i * 4)[0] for i in range(count)]

    deleted_len = end - start
    new_refs = []
    removed = 0
    for val in old_refs:
        if start <= val < end:
            removed += 1  # 指向被删区间内部：整条丢弃
            continue
        elif val >= end:
            new_refs.append(val - deleted_len)  # 指向被删区间之后：整体前移
        else:
            new_refs.append(val)  # 指向被删区间之前：不变

    if removed == 0:
        print("警告：引用表里没有任何一项落在 [start, end) 内部——"
              "可能 start/end 没有精确对应某个模块的引用目标，"
              "结果的模块计数/引用表可能是错的，建议先用 inspect-header 复核。")

    new_data = bytearray(data[:start] + data[end:])
    new_count = count - removed
    struct.pack_into("<I", new_data, count_off, new_count)
    for i, val in enumerate(new_refs):
        struct.pack_into("<I", new_data, refs_off + i * 4, val)
    # 表尾多出来的槽位（如果模块数变少）清零，避免残留旧值造成误读
    for i in range(len(new_refs), count):
        off = refs_off + i * 4
        if off + 4 <= len(new_data):
            struct.pack_into("<I", new_data, off, 0)

    return bytes(new_data)


def cmd_inspect(args: argparse.Namespace) -> None:
    data = args.inp.read_bytes()
    inspect_header(data, args.count_off, args.refs_off)


def cmd_delete(args: argparse.Namespace) -> None:
    data = args.inp.read_bytes()
    new_data = delete_range(data, args.start, args.end, args.count_off, args.refs_off)
    args.out.write_bytes(new_data)
    print(f"[delete-range] 原长度 {len(data)} -> 新长度 {len(new_data)}（删除 {args.end - args.start} 字节），已写入 {args.out}")


def cmd_check(args: argparse.Namespace) -> None:
    data = args.inp.read_bytes()
    ok = True
    for s in (args.absent.split(",") if args.absent else []):
        s = s.strip()
        if not s:
            continue
        present = s.encode("utf-8") in data
        print(f"  应当不存在: {s!r:20s} -> {'❌ 仍存在' if present else '✅ 已删除'}")
        ok = ok and not present
    for s in (args.present.split(",") if args.present else []):
        s = s.strip()
        if not s:
            continue
        present = s.encode("utf-8") in data
        print(f"  应当存在:   {s!r:20s} -> {'✅ 存在' if present else '❌ 缺失'}")
        ok = ok and present
    if not ok:
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_inspect = sub.add_parser("inspect-header", help="查看根结构的模块数量与引用表")
    p_inspect.add_argument("--in", dest="inp", required=True, type=Path)
    p_inspect.add_argument("--count-off", dest="count_off", type=lambda s: int(s, 0), default=0x20)
    p_inspect.add_argument("--refs-off", dest="refs_off", type=lambda s: int(s, 0), default=0x24)
    p_inspect.set_defaults(func=cmd_inspect)

    p_delete = sub.add_parser("delete-range", help="删除指定字节区间并修正模块计数/引用表")
    p_delete.add_argument("--in", dest="inp", required=True, type=Path)
    p_delete.add_argument("--out", dest="out", required=True, type=Path)
    p_delete.add_argument("--start", dest="start", type=lambda s: int(s, 0), required=True)
    p_delete.add_argument("--end", dest="end", type=lambda s: int(s, 0), required=True)
    p_delete.add_argument("--count-off", dest="count_off", type=lambda s: int(s, 0), default=0x20)
    p_delete.add_argument("--refs-off", dest="refs_off", type=lambda s: int(s, 0), default=0x24)
    p_delete.set_defaults(func=cmd_delete)

    p_check = sub.add_parser("check-strings", help="核对删除后哪些标签消失/保留")
    p_check.add_argument("--in", dest="inp", required=True, type=Path)
    p_check.add_argument("--absent", dest="absent", default="", help="逗号分隔，期望不再出现的字符串")
    p_check.add_argument("--present", dest="present", default="", help="逗号分隔，期望仍然存在的字符串")
    p_check.set_defaults(func=cmd_check)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
