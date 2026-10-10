# QMAEP 密钥机制与来源记录规范

本文件只记录**机制**和**记录格式**，不包含任何具体密钥数值——这是有意的，
理由见 SKILL.md 里"关于 QMAEP 编码"一节（付费音效/全局密钥的顾虑）。

## 已确认的机制（用本机真实样本验证过）

```
cipher[i] = plain[i] XOR key[i % 128]     # AEP  -> QMAEP
plain[i]  = cipher[i] XOR key[i % 128]    # QMAEP -> AEP
```

- key 长度：128 字节，循环使用
- 可逆：同一个 key、同一个函数即可用于两个方向
- 已验证：用一份第三方提供的 128 字节表，对真实的
  `500-全景环绕.aep` / `.qmaep` 做了逐字节比对，encode 结果和官方文件完全
  一致——**机制是真的**，具体数值本身不在这个文件里，需要的话你自己留着，
  调用 `aep_qmaep_codec.py encode/decode --key <hex>` 时手动传。

## 密钥来源记录模板（防止重蹈"引用编造"的覆辙）

上一版第三方文档里有一条看起来很正式的"开源项目佐证"，实际搜不到对应仓库，
大概率是生成文档的某个环节编出来的。往后每次拿到一个新密钥/新发现，建议
按下面这张表把来源记清楚，只填你能独立核实的部分，核实不了的字段留空，
不要用编的内容填满：

```yaml
key_id:              # 给这次发现起个短名字，比如 "qmaep_v1_128b"
length: 128 bytes
source_type:          # 本地样本比对 / 他人提供 / 公开资料 / 格式记录 等，如实填
source_description:   # 具体怎么来的，一两句话
source_url:           # 只有真的能打开、能验证的链接才填；打不开/搜不到就留空
discovered_date:
method:               # 比如"已知明文密文对逐字节XOR + 周期检测"
verification:         # 具体怎么验证的（哪个文件、比对结果）
notes:                # 任何需要提醒后来者的坑，比如"未确认是否所有版本/所有预设通用"
```

### 示例：这次机制验证的记录（不含密钥数值）

```yaml
key_id: qmaep_128b_mechanism
length: 128 bytes
source_type: 第三方提供文档 + 本地样本交叉验证
source_description: 第三方文档给出具体128字节数值，本地用已有的
  500-全景环绕.aep/.qmaep 做了逐字节XOR验证，encode结果与官方qmaep完全一致
source_url:            # 文档里引用的"开源项目"搜不到，此项留空，不采信
discovered_date: 2026-09-13
method: 已知明文密文对逐字节XOR + 周期检测（verify-xor 工具，周期128，匹配率100%）
verification: aep_qmaep_codec.py encode(aep, key) == 真实 qmaep（字节级diff通过）
notes: 未确认这个128字节表是否对银河音效全部预设/全部版本通用，只在这一个
  样本上验证过；机制记在这里，具体数值不写入本技能包
```

## 参数编辑时的一条通用注意事项

`aep_param_tool.py` / `aep_module_tool.py` 只改动它们能明确识别、并且你
主动确认过的字节（数值、模块边界）。**不要顺手改动它们没有识别出来的字节**
——AEP 里除了参数值和标签，大概率还有校验/索引类的字段（参考
`aep_module_tool.py` 里那个模块计数/引用表），贸然改动容易让文件整体读取
失败，而且不一定能从报错里看出是哪里出的问题。
