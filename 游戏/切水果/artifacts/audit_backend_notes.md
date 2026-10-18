# 后端只读审查复核（2026-10-16）

复核使用本机源码、mock 摄像头/模型、临时设置文件及临时 `127.0.0.1` 端口；两次运行均经过正常提权审批且退出码为 0。未打开真实摄像头、下载模型、修改生产代码或 `backend/settings.json`，未重复主代理已通过的 81 项 core 检查。根/父目录未找到用户引用的 RTK.md。

执行证据：

```powershell
.venv/Scripts/python.exe -X utf8 artifacts/audit_backend_probe.py
.venv/Scripts/python.exe -X utf8 artifacts/audit_backend_followup.py
```

原探针逻辑与源码一致；其中 6.6 秒是 mock 时钟推进量，并非实机等待测量。预览探针在第 5 次 read 主动抛异常结束，证明失败分支不消费按键，未运行无限循环或开启 OpenCV 窗口。补充探针的 HTTP 500 traceback 是预期复现输出，不是测试失败。

## 1. P2：读帧抛异常时不会自动重开摄像头

- 位置：`backend/gesture_server.py:368` 调用 `cap.read()`，`:399-403` 将采集/推理异常统一作为“识别失败”，没有释放 capture；自动打开条件在 `:362`，要求 `self.cap is None`、切换设备或显式 retry。返回 `False` 的另一分支 `:371-381` 会释放设备，不能把两种故障混为一谈。
- 触发：设备曾正常读帧，之后 `read()` 连续抛异常。原探针成功 1 帧、异常 6 次，模拟跨过 6.6 秒；只打开 1 次，直到循环结束才释放 capture。异常持续时自动重连条件始终不满足。未实测具体摄像头驱动是否会这样失败。
- 当前影响：手势停止并报告识别失败，HTTP/鼠标流程仍可用；README.md:128 的“每隔约 3 秒重连”不覆盖此异常路径。补充探针证明显式 retry 会释放旧 capture、重新打开，随后成功读取并清除错误。此结论不适用于驱动一直阻塞不返回的情况。
- 用户排查：在设置中查看错误及 `/api/status` 的 `frame_age_ms` 是否持续增加；等待超过 3 秒仍无恢复时点击“重连摄像头 / 模型”。仍失败则停止服务后检查占用/连接并重启。修复建议是区分采集与推理异常，对采集异常释放设备并进入现有自动重连路径。

## 2. P2：WebSocket 握手缺少服务端 Origin 校验

- 位置：`backend/gesture_server.py:67-70` 只检查 POST；`:155-157` 在 GET `/ws` 上直接 `prepare()`。发送内容包括 `:171` 的完整 status/settings，以及 `:195-214` 的实时手势消息。
- 触发与证据：Python aiohttp 客户端带 `Origin: https://unrelated-origin.invalid` 成功握手，收到 status/settings 和合成的可见手势；同一 Origin 的 POST `/api/retry` 返回 403。因此服务端同源限制在 WS 上缺失。该字符串仅作请求头，没有访问此外部域名。
- 当前影响：正常游戏连接不受影响；能访问该本机端口的客户端可在任意 Origin 头下订阅状态和控制点。默认仅监听本机（`backend/main.py:85`），此探针没有证明任意浏览器网站都能访问，也未测浏览器混合内容、本地网络访问权限等限制。没有通过 WS 取得摄像头 JPEG 或完整 21 点骨架。
- 用户排查：运行原探针可重现服务端行为；如评估浏览器风险，应单独记录目标浏览器版本、页面来源和本地网络权限。修复建议是在 `ws.prepare()` 前校验 Origin，并明确无 Origin 的本机客户端策略。

## 3. P3：独立预览持续读帧失败后无法通过 Q / Esc 退出

- 位置：`backend/preview.py:149-152` 在 `ret=False` 时 sleep 后直接 continue；按键处理位于 `:185-187`，仅成功读帧时执行。
- 触发与证据：先成功 1 帧，再连续失败 3 帧，`waitKey` 仅调用 1 次；预先安排的 Esc 未被读取。清理 `:188-191` 在探针主动结束后正常调用。
- 当前影响：只影响 README.md:138 提到的独立骨架预览工具；设备断开/停止交付帧后，该工具持续重试且跳过键盘轮询。浏览器游戏的退出/暂停流程不经过该工具。
- 用户排查：预览停在旧画面且 Q / Esc 无效时，在启动它的终端按 Ctrl+C，再检查设备并重开。修复建议让失败分支也处理退出按键，并对持续失败显示错误或设置重开策略。

## 4. P3：超大 JSON 整数绕过正常校验错误处理

- 位置：`backend/gesture_tracking.py:40-42` 在范围判断前调用 `math.isfinite(value)`，超出浮点转换范围的 Python 整数抛 `OverflowError`；`backend/gesture_server.py:95-97` 和 `:31-36` 未捕获该异常。
- 触发与证据：`{"target_fps": 10**400}` 的等价 JSON 为 417 字节，小于请求上限 4096。POST 返回 500（预期应为校验 400），随后 `/api/status` 仍为 200、settings/revision 未变且未写文件。将相同内容写入临时设置文件后，`GestureServer(no_camera=True, ...)` 构造失败。
- 当前影响：页面正常取值及当前已保存设置不会生成这种数值；没有证据表明常规操作受影响。API 错误不会把非法值持久化，也不会使运行中的服务整体崩溃。只有手动编辑/外部工具写入这样的设置文件，才会在下次启动时阻断启动，甚至影响 `--no-camera`。
- 用户排查：若启动日志出现 `int too large to convert to float`，停止服务、备份设置文件并检查数值是否超出页面允许范围；可把 `target_fps` 改回 10–60 后重试。不要为复现改真实配置；使用补充探针的临时文件。修复建议先做整数范围比较，或把 OverflowError 统一转换为 ValueError。

## 可观测性优化（不是测得的性能退化）

- `frame_age_ms`（`backend/gesture_server.py:127`、`:369`、`:383`）是距最近一次成功 `cap.read()` 返回的时间，不包含传感器曝光/驱动缓存中帧已停留多久，不能据此宣称真实摄像头帧龄或端到端延迟。
- `fps`（`backend/gesture_server.py:395-397`）平滑的是各帧间隔的倒数；间隔波动时可高于“同一窗口帧数 / 总时长”的实际吞吐。评估吞吐宜同时统计固定窗口的完成帧数及时间，不能据当前显示值断言速度提升或退化。
- 引擎的 `recovery_attempts` / `recovery_successes` 在 `backend/mediapipe_engine.py:88-89`、`:116`、`:120` 累加，但 `status_msg()` 的 `metrics` 只来自独立 `PipelineMetrics`（`backend/gesture_server.py:137`），没有暴露这两个计数。现场难以判断同帧补检的频率和收益；建议加入观测值并说明重载模型会重置计数。
- `dispatch`（`backend/gesture_server.py:197`）计时止于发布器取走消息，不代表 WS 发送完成或浏览器渲染耗时；各阶段 P50/P95 也不应简单相加充当端到端分位数。
