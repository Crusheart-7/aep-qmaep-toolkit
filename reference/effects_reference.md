# 效果器参数参考

## 参数在 AEP 里的存储方式（已用真实文件验证）

每个可调参数在 AEP 文件里紧挨着存成：

```
[float32 数值 4字节][uint32 标签长度 4字节][UTF-8 标签文本]
```

`scripts/aep_param_tool.py list` 就是靠扫描这个模式自动列出参数的，不需要
针对每个预设手写偏移量。

## EQ
十段：16000 / 8000 / 4000 / 2000 / 1000 / 500 / 250 / 125 / 63 / 31 Hz，
每段一个增益（float，单位近似 dB）。

## Stereo Enhancement
- `Center`：声像中心位置
- `Width`：立体声宽度（>100 表示比原始声场更宽）

## Delay
- `Right Time` / `Left Time`：对应文档里的 "Right Delay" / "Left Delay"（毫秒）
- `Right Feedback` / `Left Feedback`

作用：制造 Haas Effect（哈斯效应），让声音脱离头部、增强空间定位——但对
入耳式耳机用户，过强的单侧延迟容易造成不自然的空间偏移。

## 案例：500-全景环绕.aep 的真实参数（用 `aep_param_tool.py list` 实测得到）

| 参数 | 数值 |
|---|---|
| 16000 Hz | 2.0 |
| 8000 Hz | 2.0 |
| 4000 Hz | 1.0 |
| 2000 Hz | 1.0 |
| 1000 Hz | 1.0 |
| 500 Hz | 0.0 |
| 250 Hz | 0.0 |
| 125 Hz | 1.0 |
| 63 Hz | 1.0 |
| 31 Hz | 0.0 |
| Right Feedback | 0.0 |
| Left Feedback | 0.0 |
| **Right Time** | **26.12245 ms** |
| Left Time | 0.0 |
| Center | 100.0 |
| Width | 130.0 |

解读：高频段（16k/8k Hz）小幅提升明亮度；中低频（500/250 Hz）直接归零削弱
低频力量，跟文档描述的"提升明亮度、轻微削弱低频力量"一致；Width=130 说明
立体声场比原始宽度扩展了 30%；Right Time=26.12245ms + Left Time=0 是典型的
单侧延迟做法，制造 Haas Effect 让声音向右后方偏移。

去 Delay 优化版：把 `Right Time` 改成 0（用
`aep_param_tool.py set --label "Right Time" --value 0`），其余参数不动。
效果对比：
- 保留：音色、清晰度、声场（EQ 和 Stereo Enhancement 部分完全不受影响）
- 去除：延迟造成的定位偏移
- 更适合入耳式耳机

字节级验证：这个改动只会翻转文件里 4 个字节（那个 float32），已用
`cmp -l` 核对过。
