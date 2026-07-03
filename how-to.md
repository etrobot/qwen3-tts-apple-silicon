# 克隆音色 TTS API 使用说明

## 启动服务

```bash
uv run python clone_api_server.py
```

服务启动后访问：http://localhost:6111/docs 查看API文档

## API 接口

### 1. 生成语音（带时间戳）

**POST** `/tts`

返回 JSON 格式，包含音频 base64 和词级时间戳。

```bash
curl -X POST "http://localhost:6111/tts" \
  -H "Content-Type: application/json" \
  -d '{"text": "你好世界", "return_timestamps": true}'
```

**响应示例：**
```json
{
  "audio_base64": "UklGRiQAAABXQVZFZm10IBAAAAABAAEA...",
  "sample_rate": 24000,
  "duration": 2.88,
  "timestamps": [
    {"text": "你", "start_time": 0.0, "end_time": 1.68},
    {"text": "好", "start_time": 1.68, "end_time": 1.84},
    {"text": "世", "start_time": 1.84, "end_time": 2.08},
    {"text": "界", "start_time": 2.08, "end_time": 2.32}
  ]
}
```

**参数说明：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| text | string | 是 | 要合成的文本 |
| return_timestamps | boolean | 否 | 是否返回时间戳，默认 true |

### 2. 生成语音文件（兼容旧接口）

**POST** `/tts/file`

返回 WAV 音频文件。

```bash
curl -X POST "http://localhost:6111/tts/file" \
  -H "Content-Type: application/json" \
  -d '{"text": "你好世界"}' \
  --output output.wav
```

## Python 调用示例

```python
import requests
import base64

# 调用 API
response = requests.post(
    "http://localhost:6111/tts",
    json={"text": "你好世界", "return_timestamps": True}
)
data = response.json()

# 保存音频
audio_bytes = base64.b64decode(data["audio_base64"])
with open("output.wav", "wb") as f:
    f.write(audio_bytes)

# 打印时间戳
print(f"时长: {data['duration']}秒")
for ts in data["timestamps"]:
    print(f"[{ts['start_time']:.2f}s - {ts['end_time']:.2f}s] {ts['text']}")
```

## JavaScript 调用示例

```javascript
// 调用 API
const response = await fetch("http://localhost:6111/tts", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ text: "你好世界", return_timestamps: true })
});

const data = await response.json();

// 播放音频
const audio = new Audio(`data:audio/wav;base64,${data.audio_base64}`);
audio.play();

// 显示时间戳
console.log(`时长: ${data.duration}秒`);
data.timestamps.forEach(ts => {
  console.log(`[${ts.start_time.toFixed(2)}s - ${ts.end_time.toFixed(2)}s] ${ts.text}`);
});
```

## 支持的语言

ForcedAligner 支持以下语言的时间戳对齐：

- Chinese（中文）
- Cantonese（粤语）
- English（英语）
- German（德语）
- Spanish（西班牙语）
- French（法语）
- Italian（意大利语）
- Portuguese（葡萄牙语）
- Russian（俄语）
- Korean（韩语）
- Japanese（日语）

## 注意事项

1. 首次调用会加载 ForcedAligner 模型，需要几秒钟
2. 生成的音频采样率为 24000Hz
3. 时间戳精度约 ±0.02 秒