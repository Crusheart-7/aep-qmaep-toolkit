#!/usr/bin/env python3
"""
aep_qmaep_codec.py
------------------
AEPK 打包/解包（已用真实样本验证），QMAEP 编码假设检验工具，以及通用的
（key 由你提供、本脚本不内置）循环 XOR encode/decode。

## AEPK（已验证，可放心用）

用 500-全景环绕.aepk 实测确认：AEPK 就是一个普通 ZIP，内部固定两个文件：

    AudioEffectPackage/AudioEffect.qmaep   <- QMAEP 编码后的数据，原样存放
    AudioEffectPackage/FileList.txt        <- 内容就是一行 "AudioEffect.qmaep"

pack-aepk / unpack-aepk 就是照这个结构做的，round-trip 已经过字节级比对。

## QMAEP 编码（算法已确认，密钥有意不内置）

v1 版本一开始判断"简单循环 XOR"不成立，原因是当时只检测了 1~64 字节的
周期——后来才发现真实周期是 128 字节，检测范围不够长，属于诊断工具自己的
bug（现在 `verify-xor` 默认测到 200 字节了）。用真实的
500-全景环绕.aep / .qmaep 重新验证：**存在一个 128 字节、逐字节循环使用的
XOR 表，能把 AEP 精确转换成 QMAEP，反过来也一样精确还原**——这一步已经
在本机对真实样本做过逐字节比对，encode 结果和官方 .qmaep 文件完全一致。

也就是说，算法本身（"128 字节固定表、循环 XOR、可逆"）现在是确认成立的。
**但这个具体的 128 字节数值本身，本脚本不会写进来。** 原因很直接：
QQ音乐的银河音效里，至少一部分预设（比如车载定制音效、臻品全景声等）是绑定
会员/超级会员才能使用的付费功能。如果这确实是全局固定密钥（不是按文件区分），
将具体数值写入一个可被多台设备复用的工具包，可能会超出用户自有工程文件的
处理范围，因此本工具不内置该数值。`encode`/`decode` 子命令保持通用（按你传入
的 `--key` 做循环 XOR），需要时由用户自行、显式地传入。

好消息是：分享二维码那条链路（`make_share_qrcode.py`）你已经用真机验证过
是直接在 AEP 上做 gzip+Base64，完全不需要经过 QMAEP 编码。也就是说，
**日常"改参数 → 分享"的工作流根本不需要解决 QMAEP 编码问题**：
用 `aep_param_tool.py` / `aep_module_tool.py` 改完 AEP，直接拿改好的 AEP
生成分享链接/二维码即可。只有"直接替换 QQ音乐本地缓存的 .qmaep 文件"这种
场景才需要 encode/decode。

用法：
    python aep_qmaep_codec.py pack-aepk   --qmaep-in file.qmaep --out file.aepk
    python aep_qmaep_codec.py unpack-aepk --in file.aepk --out-dir extracted/
    python aep_qmaep_codec.py verify-xor  --aep file.aep --qmaep file.qmaep [--max-key-len 200]
    python aep_qmaep_codec.py encode --in file.aep   --out file.qmaep --key <hex>
    python aep_qmaep_codec.py decode --in file.qmaep --out file.aep   --key <hex>
"""

import argparse
import zipfile
from pathlib import Path


def _resolve_key(key_arg: str) -> bytes:
    if key_arg is None:
        raise SystemExit("缺少 --key：本脚本不内置任何密钥，需要你自行提供。")
    try:
        if all(c in "0123456789abcdefABCDEF" for c in key_arg) and len(key_arg) % 2 == 0:
            return bytes.fromhex(key_arg)
    except ValueError:
        pass
    return key_arg.encode("utf-8")


def xor_transform(data: bytes, key: bytes) -> bytes:
    if not key:
        raise ValueError("key 不能为空")
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))

AEPK_INNER_DIR = "AudioEffectPackage"
AEPK_INNER_QMAEP_NAME = "AudioEffect.qmaep"
AEPK_INNER_FILELIST_NAME = "FileList.txt"


def pack_aepk(qmaep_path: Path, out_path: Path) -> None:
    qmaep_data = qmaep_path.read_bytes()
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{AEPK_INNER_DIR}/{AEPK_INNER_QMAEP_NAME}", qmaep_data)
        z.writestr(f"{AEPK_INNER_DIR}/{AEPK_INNER_FILELIST_NAME}", AEPK_INNER_QMAEP_NAME + "\n")
    print(f"[pack-aepk] {qmaep_path} -> {out_path}")


def unpack_aepk(aepk_path: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(aepk_path) as z:
        names = z.namelist()
        z.extractall(out_dir)
    print(f"[unpack-aepk] {aepk_path} -> {out_dir}  ({len(names)} 个文件)")
    for n in names:
        print(f"    {n}")


def verify_xor_hypothesis(aep_path: Path, qmaep_path: Path, max_key_len: int) -> None:
    """诊断工具：检验"简单循环XOR"假设是否成立，不产出可复用的密钥/密钥流。"""
    aep = aep_path.read_bytes()
    qmaep = qmaep_path.read_bytes()
    if len(aep) != len(qmaep):
        print(f"长度不一致：aep={len(aep)} bytes, qmaep={len(qmaep)} bytes —— "
              "两者可能不是同一份工程的一对一对应文件。")
        return
    xor = bytes(a ^ b for a, b in zip(aep, qmaep))
    best_len, best_ratio = None, 0.0
    for klen in range(1, min(max_key_len, len(xor) - 1) + 1):
        total = len(xor) - klen
        if total <= 0:
            break
        matches = sum(1 for i in range(total) if xor[i] == xor[i + klen])
        ratio = matches / total
        if ratio > best_ratio:
            best_len, best_ratio = klen, ratio
    print(f"最佳周期候选：key_len={best_len}，字节重复匹配率={best_ratio:.1%}")
    if best_ratio > 0.9:
        print("=> 匹配率很高，这一对文件符合『简单循环 XOR』假设，可以按 key_len 继续分析。")
    else:
        print("=> 匹配率不足以支持『简单循环 XOR』假设（阈值 90%）。"
              "说明 QMAEP 的真实编码比文档里的示意伪代码更复杂，"
              "本工具到这里为止，不再往下猜测具体算法。")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_pack = sub.add_parser("pack-aepk", help="QMAEP -> AEPK（已按真实样本结构验证）")
    p_pack.add_argument("--qmaep-in", dest="inp", required=True, type=Path)
    p_pack.add_argument("--out", dest="out", required=True, type=Path)
    p_pack.set_defaults(func=lambda a: pack_aepk(a.inp, a.out))

    p_unpack = sub.add_parser("unpack-aepk", help="AEPK -> 解压出内部文件")
    p_unpack.add_argument("--in", dest="inp", required=True, type=Path)
    p_unpack.add_argument("--out-dir", dest="out_dir", required=True, type=Path)
    p_unpack.set_defaults(func=lambda a: unpack_aepk(a.inp, a.out_dir))

    p_verify = sub.add_parser("verify-xor", help="检验 AEP/QMAEP 是否符合简单循环XOR假设（诊断用，不产出密钥）")
    p_verify.add_argument("--aep", dest="aep", required=True, type=Path)
    p_verify.add_argument("--qmaep", dest="qmaep", required=True, type=Path)
    p_verify.add_argument("--max-key-len", dest="max_key_len", type=int, default=200)
    p_verify.set_defaults(func=lambda a: verify_xor_hypothesis(a.aep, a.qmaep, a.max_key_len))

    p_enc = sub.add_parser("encode", help="AEP -> QMAEP（通用循环XOR，key 由你提供，本脚本不内置）")
    p_enc.add_argument("--in", dest="inp", required=True, type=Path)
    p_enc.add_argument("--out", dest="out", required=True, type=Path)
    p_enc.add_argument("--key", dest="key", required=True)
    p_enc.set_defaults(func=lambda a: a.out.write_bytes(xor_transform(a.inp.read_bytes(), _resolve_key(a.key))) or print(f"[encode] {a.inp} -> {a.out}"))

    p_dec = sub.add_parser("decode", help="QMAEP -> AEP（通用循环XOR，key 由你提供，本脚本不内置）")
    p_dec.add_argument("--in", dest="inp", required=True, type=Path)
    p_dec.add_argument("--out", dest="out", required=True, type=Path)
    p_dec.add_argument("--key", dest="key", required=True)
    p_dec.set_defaults(func=lambda a: a.out.write_bytes(xor_transform(a.inp.read_bytes(), _resolve_key(a.key))) or print(f"[decode] {a.inp} -> {a.out}"))

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
