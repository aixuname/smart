"""Select each anchor through the UI, using a photo / real model / real WS.

No physical camera is opened and no hand coordinates are injected. The fixture's
test-only oracle exposes actual model landmarks, paired with their WS sequence.
"""
import json
import math
from pathlib import Path
import sys

from playwright.sync_api import sync_playwright


url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8771"
errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.on("pageerror", lambda error: errors.append(str(error)))
    original_settings = page.request.get(url + "/api/settings").json()
    try:
        assert page.request.post(url + "/test/feed", data={"motion": "static", "blank": False}).ok
        assert page.request.post(url + "/api/settings", data={"blade_point_index": -1, "activation": "always"}).ok
        page.goto(url)
        page.wait_for_function("window.__game?.scene.isActive('MenuScene')")
        page.evaluate("""async () => {
          const {gestureClient:c} = await import('/js/net/client.js');
          window.pointClient = c;
          window.pointMessages = [];
          c.onMessage(msg => {
            if (msg.type === 'gesture') window.pointMessages.push({...msg});
          });
        }""")
        page.wait_for_function("window.pointClient.lastGesture.visible", timeout=20000)
        page.locator("#btn-start").click()
        page.wait_for_function("window.__game.scene.getScene('GameScene').handBlade.sprite.visible")
        page.evaluate("""() => {
          const s=window.__game.scene.getScene('GameScene');
          s.spawner.clear(); s.spawner.nextInterval=999999;
          window.pointSegments=[];
          s.events.on('postupdate', () => window.pointSegments.push(...s.bladeManager.segments));
        }""")

        def matched_model_sample():
            for _ in range(6):
                oracle = page.request.post(url + "/test/gesture", data={}).json()
                if not oracle or not oracle["visible"]:
                    page.wait_for_timeout(100)
                    continue
                page.wait_for_function("seq => window.pointClient.lastGesture.seq >= seq", arg=oracle["seq"])
                message = page.evaluate("seq => window.pointMessages.find(m => m.seq === seq)", oracle["seq"])
                if message:
                    return oracle, message
            raise AssertionError("No matching real WS sequence for the model-landmark oracle")

        results = []
        previous_point = -1
        # Return to index at the end so refresh proves a non-default persisted.
        for point, name, guide_name in [(8, "食指指尖", "食指指尖"),
                                        (12, "中指指尖", "中指指尖"),
                                        (-1, "手掌中心", "手掌"),
                                        (8, "食指指尖", "食指指尖")]:
            before = page.evaluate("({...window.pointClient.lastGesture})")
            page.locator("#btn-live-config").click()
            page.wait_for_function("value => document.querySelector('#gesture-point').value === String(value)",
                                   arg=previous_point)
            page.evaluate("window.pointSegments=[]")
            # Select and immediately finish, deliberately never clicking Apply.
            with page.expect_response(lambda response: response.url.endswith("/api/settings")
                                      and response.request.method == "POST", timeout=6000) as saving:
                page.locator("#gesture-point").select_option(str(point))
                page.locator("#btn-input-done").click()
            response = saving.value
            assert response.ok, response.text()
            saved = response.json()
            assert saved["settings"]["blade_point_index"] == point, saved
            revision = saved["revision"]
            page.wait_for_function("""rev => {
              const c=window.pointClient;
              return c.lastGesture.visible && c.lastGesture.revision === rev &&
                c.status.appliedRevision >= rev;
            }""", arg=revision)
            page.wait_for_function("window.__game.scene.getScene('GameScene').handBlade.sprite.visible")
            page.wait_for_timeout(500)
            oracle, message = matched_model_sample()
            assert message["revision"] == revision, message
            assert message["stroke_id"] != before["stroke_id"], "Changing anchors must start a new stroke"
            points = oracle["landmarks"]
            expected = ([sum(points[i][axis] for i in (0, 5, 9, 13, 17)) / 5 for axis in (0, 1)]
                        if point == -1 else points[point][:2])
            actual = [message["x"], message["y"]]
            error = math.dist(actual, expected)
            assert error < 0.015, {"point": point, "expected": expected, "actual": actual, "error": error}
            assert math.dist(actual, [oracle["x"], oracle["y"]]) < 1e-8
            rendered = page.evaluate("""() => {
              const s=window.__game.scene.getScene('GameScene');
              const p=s.gestureInput.getPosition();
              return {position:p, blade:{x:s.handBlade.sprite.x,y:s.handBlade.sprite.y},
                maxSegment:Math.max(0,...window.pointSegments.map(
                  v=>Math.hypot(v.x2-v.x1,v.y2-v.y1)))};
            }""")
            assert math.dist(list(rendered["position"].values()), list(rendered["blade"].values())) < 5, rendered
            assert rendered["maxSegment"] < 25, "Changing anchor drew an artificial cutting segment: " + str(rendered)
            page.wait_for_function("name => document.querySelector('#hand-guide').textContent.includes(name)",
                                   arg=guide_name)
            assert page.request.get(url + "/api/settings").json()["blade_point_index"] == point
            # Reopen before reloading: both the selection and explicit applied
            # label must describe the actual service setting.
            page.locator("#btn-live-config").click()
            page.wait_for_function("value => document.querySelector('#gesture-point').value === String(value)", arg=point)
            page.wait_for_function("name => document.querySelector('#gesture-point-status')?.textContent.includes('当前追踪：' + name)",
                                   arg=name)
            page.locator("#btn-input-done").click()
            results.append({"point": point, "name": name, "revision": revision,
                            "seq": message["seq"], "expected": expected, "actual": actual,
                            "model_anchor_error": round(error, 6), "max_switch_segment_px": round(rendered["maxSegment"], 3)})
            previous_point = point

        # The same photo produces distinct anchors; merely persisting different
        # setting numbers while still tracking the palm cannot satisfy this.
        for left, right in ((0, 1), (0, 2), (1, 2)):
            assert math.dist(results[left]["actual"], results[right]["actual"]) > 0.02, results
        page.reload()
        page.wait_for_function("window.__game?.scene.isActive('MenuScene')")
        page.locator("#btn-input-config").click()
        page.wait_for_function("document.querySelector('#gesture-point').value === '8'")
        page.wait_for_function("document.querySelector('#gesture-point-status')?.textContent.includes('当前追踪：食指指尖')")
        assert not errors, errors
        report = {"source": "static project hand photo / real MediaPipe / actual WebSocket",
                  "motion": "x=230,y=100,640x480", "apply_button_clicked": False,
                  "anchors": results, "reopen_and_refresh_persistence": True,
                  "no_artificial_switch_segments": True, "page_errors": errors}
        Path("artifacts").mkdir(exist_ok=True)
        Path("artifacts/tracking-point-browser-report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
    finally:
        page.request.post(url + "/api/settings", data=original_settings)
        page.request.post(url + "/test/feed", data={"motion": "smooth", "blank": False})
        browser.close()
