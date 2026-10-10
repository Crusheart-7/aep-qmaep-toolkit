---
name: aep-qmaep-toolkit
description: Process user-owned AEP, QMAEP, AEPK, and QQ Music 银河音效 projects, including validated custom-effect share QR codes. Use for parameter inspection, conversion, packaging, or QR share troubleshooting; not for official preset download or account credentials.
---

# AEP / QMAEP / AEPK Codex Skill

## Purpose

用于处理 QQ音乐银河音效工程相关文件：

- AEP 参数解析与编辑
- QMAEP 与 AEP 转换
- AEPK 打包/解包
- soundParam 分享链接解析与生成
- 音效模块分析

本技能面向用户自有工程文件分析、修改和格式研究。

## Tools

scripts/aep_param_tool.py
- 查看和修改 AEP 参数

scripts/aep_module_tool.py
- 分析、删除效果模块

scripts/aep_qmaep_codec.py
- QMAEP/AEP 编解码
- AEPK 打包解包

scripts/parse_share_url.py
- soundParam URL解析

scripts/make_share_qrcode.py
- 生成分享二维码

生成或排查 QQ音乐自定义音效二维码时，读取：

```
docs/share_qrcode_protocol.md
```

## Format Flow

```
AEP
 |
 | 128 byte XOR
 v
QMAEP

AEP
 |
 | gzip
 v
Base64
 |
 v
soundParam
 |
 v
QQ音乐分享URL

AEP
 |
 | ZIP package
 v
AEPK
```

## QMAEP Key

算法：

- Key 长度：128 bytes
- XOR 周期：key[i % 128]
- 加密：cipher[i] = plain[i] XOR key[i % 128]
- 解密：plain[i] = cipher[i] XOR key[i % 128]

内置验证密钥：

```
C34AD6CA9067F752D8A166629F5B0900
C35E95239F13117ED8923FBC90BB740E
C347743D90AA3F51D8F411849FDE951D
C3C609D59FFA66F9D8F0F7A090A1D6F3
C3F3D6A190A0F7F0D8F966FA9FD509C6
C31D95DE9F8411F4D8513FAA903D7447
C30E74BB90BC3F92D87E11139F23955E
C300095B9F6266A1D852F76790CAD64A
```

使用方式：

```
codec.py decode --key <hex>
codec.py encode --key <hex>
```

## AEP Editing Rules

优先修改：

- float32 参数值
- 已识别效果模块
- 标签对应参数

避免修改：

- 未知结构字段
- 校验区域
- 未解析索引

## SoundParam Protocol

流程：

```
AEP
 -> gzip
 -> Base64
 -> soundParam
 -> URL
 -> QR Code
```

常见字段：

- soundType
- soundDes
- soundParam
- ADTAG
- channelId

## QQ音乐自定义音效二维码（已用可载入样本验证）

自定义工程不能复用官方推荐音效的普通 `soundType` 链接。分享链接首字段必须是
字面量 `(params)soundType=1024`，并带有 `soundId=20000`、`soundDes=自定义音效`；
`soundParam` 是直接 URL 编码的 JSON，不需要再对整个 JSON 额外 Base64。

`make_share_qrcode.py` 已按该布局提供默认值。二维码可扫描但客户端不能载入时，
优先按照 `docs/share_qrcode_protocol.md` 对照链接字段与解压后的 AEP 字节，
不要先怀疑 QMAEP XOR 或自行修改音效参数。

## Agent Instructions

处理任务时：

1. 先判断输入文件类型。
2. 优先保留原文件，输出新文件。
3. 修改前记录结构信息。
4. 修改后进行 round-trip 验证。
5. 对未知格式不要猜测，使用工具分析。
6. 读取本机 QQ音乐 UIN 前，确认用户明确授权；只使用 QQ音乐配置中的账号字段，
   不输出 UIN 或任何 Cookie / 登录令牌。具体位置、验证和回退规则见
   `docs/share_qrcode_protocol.md`。

## References

参考资料记录位于：

```
docs/
reference/
```
