# Frontend audit: game rules, input and core

Date: 2026-10-16. Read-only production-code review. No camera, network connection, browser or service was started by this probe. `RTK.md` was unavailable in the root (the parent audit also checked ancestors). No Git repository was available for a clean/dirty comparison. Only the `audit_frontend_probe.*` and this report were written by this audit worker.

## Reproduction

```powershell
node artifacts/audit_frontend_probe.mjs
```

This executes actual `GameScene.update`, `GameScene._checkMisses`, `FruitSpawner.update`, `FruitSpawner._recycleOffscreen`, `FruitSpawner.release`, `GestureClient`, `GestureBladeInput`, `BladeManager` and `Slicer` methods. Rendering/audio/socket transport use inert stubs. Ballistic scenarios integrate the documented initial velocity and gravity at 60 Hz; they are a code-level simulation, not a full Phaser/browser measurement. Assertions passed; structured evidence is in `artifacts/audit_frontend_probe.json`.

Initial hypotheses, ranked before the probe:

| Rank | Hypothesis | Test | Result |
|---|---|---|---|
| 1 | Offscreen recycling prevents the timed-mode miss handler from charging missed fruit | Run actual scene update with bottom/side exit and a normal-bottom control | Confirmed |
| 2 | Current spawn ranges allow side-exit bypass during normal portrait gameplay | 60 Hz trajectory using allowed spawn values | Confirmed in code-level simulation |
| 3 | Receive-time freshness treats old transport-delayed frames as current input | Inject two ordered packets with a source timestamp five seconds old | Confirmed acceptance; occurrence frequency in the real local transport is not established |

## Finding F1 — P2, confirmed: missed-fruit penalty is bypassed by side recycling

**Locations:** `frontend/js/core/FruitSpawner.js:97-100` (horizontal/vertical recycling), `frontend/js/scenes/GameScene.js:157-160` (recycle-before-miss order), `frontend/js/scenes/GameScene.js:253-268` (only active fruit, downward crossing at h+30). Intended rule: `README.md:73`, missed fruit costs five points in timed mode.

**Trigger and effect:** An unsliced fruit leaves a portrait viewport horizontally, crosses x < -160 or x > width+160, and is recycled before reaching the bottom miss line. `release` sets `sliced=true` and disables the body, so `_checkMisses` skips it. The timed score does not lose five points. Different viewport shapes therefore change the scoring rule.

**Evidence:** Starting from score 20, a normal downward fruit at h+40 ends with score 15; a side-exiting fruit at x=481 in a 320px-wide viewport ends with score 20. With a 320×844 viewport, actual allowed spawn values x=230, vx=180 and vy=-sqrt(2×1400×844×0.82) reach x=482, y≈291.45 at 1.4 seconds and recycle without a penalty. No dropped frame is needed. The corresponding 1280×900 scenario receives the expected penalty. A diagnostic 63-trajectory grid bypasses the penalty in 10 cases at 320×844 and eight at 390×844; these edge-value counts are **not estimates of gameplay frequency**.

**Related bottom case:** If a frame first observes a descending fruit beyond h+120, the same order also bypasses the penalty. The probe confirms this state (score remains 20 at h+121), but does not establish that ordinary low rendering FPS in the bundled Phaser configuration necessarily reaches it. The concrete recycling threshold is **h+120**, not h+180. Resize or sufficiently large observed body displacement can also create this state.

**How to investigate:** Run the probe above; inspect `recycleOrdering.portrait60Hz`, `normal60Hz`, and `diagnosticGrid`. For a later browser check, use timed mode in a 320/390px portrait viewport, obtain a positive score, and watch fruit exiting the side. A breakpoint on `_recycleOffscreen` should show active unsliced non-bomb fruit being released while the score stays unchanged.

**Fix direction:** Make missed-fruit scoring and retirement one explicit operation/reason before disabling the sprite, or otherwise ensure all unsliced fruit leaving play use the timed miss rule. Merely moving the current `_checkMisses` above `spawner.update` addresses the overshot-bottom state but **does not address side exits**, because that method only checks y > h+30. Preserve no-penalty behavior for bombs, endless mode and fruit already sliced.

## Finding F2 — P2 conditional robustness issue: delayed packets can reactivate stale cutting

**Locations:** `frontend/js/net/GestureClient.js:65-69` (accept packet and overwrite receive time); `frontend/js/input/GestureBladeInput.js:22-32` (accept sequence and refresh input); `frontend/js/input/GestureBladeInput.js:49-50` (300ms receive-age check); `frontend/js/input/SampleBuffer.js:20` and `:28-31` (buffer age is also based on receipt). Source timestamps are generated at `backend/gesture_server.py:290` with `time.time()`.

**Trigger and effect:** A gesture packet generated more than 300ms ago is delivered late while the WebSocket remains connected, for example after transport/event-queue backlog. Its old `ts` is not checked. A pair of consecutively sequenced stale positions is treated as a fresh active stroke and can cut fruit along its old path.

**Evidence:** Injecting two consecutive samples whose `ts` was approximately 5,004ms old produces an active blade, one segment from x≈100 to x=900, and a collision with a fruit at (500,300). Receive age is under 1ms, so the normal receive timeout and `SampleBuffer` expiry do not reject it.

**Limits / do not overclaim:** This proves missing source-age validation, not frequent stale replay on a healthy localhost setup. The backend already has a latest-only mailbox (`gesture_server.py:158`) and a send timeout (`:164`), reducing application-level backlog. TCP/WebSocket events can still be buffered after that mailbox, but no live backlog measurement was performed. WebSocket ordering also means the synthetic finding should not be presented as normal out-of-order network delivery. The backend timestamp is generated after inference, so validating it would not by itself measure camera capture age.

**How to investigate:** Run the probe and inspect `staleDelivery`. During a later explicitly authorized browser/service session, log `Date.now()/1000 - msg.ts` at receipt together with sequence numbers and active state during a long main-thread task or a throttled connection. Local same-machine timestamps are comparable; a remote backend needs clock-offset handling before enforcing a wall-clock threshold.

**Fix direction:** Establish source-age / connection-session validity before `_handle` notifies subscribers; drop stale packets and reset any previous stroke. Keep receive timeout as the independent stop rule when no new traffic arrives. Use monotonic stream/session checks as appropriate; do not simply compare unsynchronized clocks for remote clients.

## Additional scope

Reviewed `GameScene`, `FruitSpawner`, `BladeManager`, `Slicer`, `CutGeometry`, `ComboSystem`, `Storage`, `MouseBladeInput`, `GestureBladeInput`, `DemoBladeInput`, `SampleBuffer`, mapping/calibration, and relevant effects/lifecycle calls. No additional high-confidence high-value defect was established within this scope. `GestureSettings`, main-page orchestration and browser baselines remain with the parent audit, to avoid duplicate work.
