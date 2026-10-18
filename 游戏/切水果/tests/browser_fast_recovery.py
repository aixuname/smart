"""Fast photo motion -> real model -> WebSocket -> visible blade and slicing.

The fixture server never opens a physical camera. This test does not inject hand
coordinates, replace inference, or save camera images.
"""
import json
import math
from pathlib import Path
import statistics
import sys

from playwright.sync_api import sync_playwright


url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8771"
errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        assert page.request.post(url + "/test/feed", data={"motion": "smooth", "blank": False}).ok
        page.goto(url)
        page.wait_for_function("window.__game?.scene.isActive('MenuScene')")
        page.evaluate("""async () => {
          const {gestureClient:c} = await import('/js/net/client.js');
          window.fastClient = c;
        }""")
        page.wait_for_function("window.fastClient.lastGesture.visible", timeout=20000)
        page.locator("#btn-start").click()
        page.wait_for_function("window.__game.scene.getScene('GameScene').handBlade.sprite.visible")
        page.evaluate("""() => {
          const s = window.__game.scene.getScene('GameScene');
          s.spawner.clear(); s.spawner.nextInterval = 999999;
          s.score = 0; s.sliced = 0;
          window.fastY = s.gestureInput.getPosition().y;
          window.fastSamples = [];
          window.fastSegments = [];
          window.recordFast = false;
          window.stopFastRecording = window.fastClient.onMessage(msg => {
            if (msg.type === 'gesture' && window.recordFast) {
              const {seq, x, y, visible, active, stroke_id} = msg;
              window.fastSamples.push({seq, x, y, visible, active, stroke_id,
                receivedAt: performance.now()});
            }
          });
          s.events.on('postupdate', () => {
            if (window.recordFast) window.fastSegments.push(...s.bladeManager.segments);
          });
        }""")
        # Place the target while no hand is present so only the subsequent fast
        # motion, rather than the preceding smooth sweep, can cut it.
        assert page.request.post(url + "/test/feed", data={"blank": True}).ok
        page.wait_for_function("!window.fastClient.lastGesture.visible")
        page.wait_for_function("!window.__game.scene.getScene('GameScene').handBlade.sprite.visible")
        page.evaluate("""() => {
          const s = window.__game.scene.getScene('GameScene');
          s.spawner._spawnOne(false).setTexture('fruit-red').setScale(1)
            .setPosition(s.scale.width / 2, window.fastY)
            .setVelocity(0,0).setAngularVelocity(0).body.setAllowGravity(false);
          s.sliced = 0; s.score = 0;
          window.recordFast = true;
        }""")
        assert page.request.post(url + "/test/feed", data={"motion": "fast", "blank": False}).ok
        page.wait_for_function("window.fastSamples.filter(m => m.visible).length >= 60", timeout=15000)
        page.wait_for_function("window.__game.scene.getScene('GameScene').sliced === 1", timeout=4000)
        motion = page.evaluate("""() => {
          window.recordFast = false;
          const s = window.__game.scene.getScene('GameScene');
          return {samples: window.fastSamples, segments: window.fastSegments,
                  sliced: s.sliced, score: s.score, targetY: window.fastY,
                  lastPosition: s.gestureInput.getPosition()};
        }""")
        samples = motion["samples"]
        # A few requests already in flight can precede the mode change; measure
        # steady fast motion from the first detected hand onwards.
        first_visible = next(i for i, sample in enumerate(samples) if sample["visible"])
        samples = samples[first_visible:]
        visible = [sample for sample in samples if sample["visible"]]
        ratio = len(visible) / len(samples)
        assert len(visible) >= 60 and ratio >= 0.9, {"samples": len(samples), "visible": len(visible)}
        assert max(sample["x"] for sample in visible) - min(sample["x"] for sample in visible) > 0.35
        crossing = [segment for segment in motion["segments"]
                    if min(segment["x1"], segment["x2"]) < 600
                    and max(segment["x1"], segment["x2"]) > 680]
        assert crossing, "fast model samples must generate a continuous path across the central fruit"
        assert motion["sliced"] == 1 and motion["score"] >= 10, motion
        intervals = sorted(right["receivedAt"] - left["receivedAt"]
                           for left, right in zip(samples, samples[1:]))
        status = page.request.get(url + "/api/status").json()

        # A true blank must disable both the displayed blade and stationary
        # cutting. Put a new fruit exactly at the last genuine blade position.
        assert page.request.post(url + "/test/feed", data={"blank": True}).ok
        page.wait_for_function("!window.fastClient.lastGesture.visible", timeout=1500)
        page.wait_for_function("""() => {
          const s = window.__game.scene.getScene('GameScene');
          return !s.handBlade.sprite.visible && !s.gestureInput.isActive();
        }""", timeout=1000)
        page.evaluate("""pos => {
          const s = window.__game.scene.getScene('GameScene');
          s.spawner.clear(); s.sliced = 0; s.score = 0;
          s.spawner._spawnOne(false).setPosition(pos.x,pos.y)
            .setVelocity(0,0).body.setAllowGravity(false);
        }""", motion["lastPosition"])
        page.wait_for_timeout(300)
        assert page.evaluate("window.__game.scene.getScene('GameScene').sliced") == 0
        page.evaluate("window.__game.scene.getScene('GameScene').spawner.clear()")
        assert page.request.post(url + "/test/feed", data={"blank": False}).ok
        page.wait_for_function("""() => {
          const s = window.__game.scene.getScene('GameScene');
          return s.handBlade.sprite.visible && s.gestureInput.isActive();
        }""", timeout=10000)
        assert not errors, errors
        report = {"source": "fast project hand photo / real MediaPipe / actual WebSocket",
                  "motion": "x=40/430 every three frames, y=100, 640x480",
                  "samples": len(samples), "visible_samples": len(visible),
                  "visible_ratio": round(ratio, 4), "central_crossing_segments": len(crossing),
                  "ws_interval_p50_ms": round(statistics.median(intervals), 2),
                  "ws_interval_p95_ms": round(intervals[math.ceil(len(intervals) * 0.95) - 1], 2),
                  "service_fps": status["fps"], "pipeline_metrics": status["metrics"],
                  "cut_score": motion["score"], "blank_stops_blade_and_contact": True,
                  "reacquire": True, "page_errors": errors}
        Path("artifacts").mkdir(exist_ok=True)
        Path("artifacts/fast-recovery-browser-report.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report))
    finally:
        page.request.post(url + "/test/feed", data={"motion": "smooth", "blank": False})
        browser.close()
