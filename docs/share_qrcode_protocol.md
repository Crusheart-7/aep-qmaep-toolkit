# QQ音乐自定义音效分享二维码

本说明记录的是已用“可扫码、可载入”的自定义音效二维码与其对应 `.qmaep`
文件逐项验证的结果。它只适用于用户自有工程的分享二维码，不适用于官方预设
下载、会员资源或账号凭据处理。

## 已验证的链接布局

对自定义音效，分享 URL 使用 QQ 音乐的分享页：

```text
https://y.qq.com/m/client/supersound/dist/index.html?
  (params)soundType=1024
  &soundId=20000
  &soundName=<名称>
  &soundDes=自定义音效
  &ADTAG=erweimashare
  &channelId=10036163
  &openinqqmusic=1
  &soundParam=<URL 编码的 JSON>
```

关键点：

- `(params)soundType` 的括号和前缀是首个查询字段名的一部分，必须原样保留；
  不要改成普通 `soundType`，也不要把整个字段名再 URL 编码。
- `soundId=20000` 和 `soundDes=自定义音效` 是已验证样本带有的自定义音效字段。
- `soundName` 与 `aepEdit.name` 使用工程内的音效名称；若文件名与工程名不同，
  以工程名为准。
- 查询参数顺序应保持上述顺序，首字段置于最前，以便客户端的参数反序列化器
  识别私有前缀。

## `soundParam` 载荷

`soundParam` 解码后是直接的紧凑 JSON：

```json
{"aepEdit":{"name":"<名称>","param":"<Base64>","uin":"<QQ音乐 UIN>"}}
```

其中 `param` 的流程为：

```text
AEP bytes -> gzip -> Base64
```

整个 JSON 直接作为 `soundParam` 的 URL 编码值；不要把 JSON 再 Base64 一次。
对照样本中，`param` 解压后的 AEP 与同名 `.qmaep` 用已验证的 128-byte XOR key
解码后的 AEP 完全相同。因此“二维码能识别、但音效不能载入”时，优先检查 URL
布局和字段，而不是重编码 QMAEP。

## 本机 UIN 检测（需用户明确授权）

只有在用户明确允许读取本机 QQ音乐配置、且需要生成可导入分享二维码时，才查找
UIN。常见 Windows 路径为：

```text
%APPDATA%\Tencent\QQMusic\QQMusicServiceConfig.ini
```

读取规则：

1. 只提取独立的 `Uin=<数字>` 配置项，并在内存中传给二维码脚本。
2. 不在聊天、日志、文件名或 URL 文本输出完整 UIN；不得读取、展示或复制 Cookie、
   密码、会话票据或其他登录令牌。
3. `qmcomdata.ini` 中的 `uin=0` 表示未取得可用账号值；缓存、数据库、WebView 和
   任意长数字不应被猜测为 UIN。
4. 找不到有效值时，停下并请用户提供其 QQ音乐 UIN；不要用 `0`、空字符串或其他
   文件中的 ID 替代。

某些登录方式会产生较长的 QQ音乐 UIN；不要按 QQ 号位数自行拒绝，应该以该服务
配置项及可用参考二维码中的 `aepEdit.uin` 一致性为准。

## 验证与排错

生成后至少做以下检查：

1. 用二维码解码器读回 PNG，确认首个键严格为 `(params)soundType`，且值为 `1024`。
2. 确认 `soundId=20000`、`soundDes=自定义音效`、`soundName`、`aepEdit.name` 与预期
   一致，且 `aepEdit.uin` 已填入授权取得的值。
3. 从 `soundParam.aepEdit.param` Base64 解码并 gzip 解压，逐字节比较是否与输入 AEP
   相同。
4. 如有用户提供的成功二维码，先解码其 URL，再逐项比较字段名、字段顺序和载荷
   字节；将其作为协议依据，不要凭外观或“二维码可扫描”判断成功。

如果二维码被 QQ音乐识别但仍无法载入，保留原始文件，报告已经对比过的字段，并
请求一个可载入样本或客户端报错信息；不要擅自修改未知 AEP 字段。
