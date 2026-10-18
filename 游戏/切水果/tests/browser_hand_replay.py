"""Exercise actual model results received over WebSocket, without injecting gestures."""
import json
from pathlib import Path
import sys
from playwright.sync_api import sync_playwright

url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8771"
errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(url)
    page.wait_for_function("window.__game?.scene.isActive('MenuScene')")
    page.evaluate("""async () => {
      const {gestureClient:c} = await import('/js/net/client.js');
      window.replayClient = c;
    }""")
    page.wait_for_function("window.replayClient.lastGesture.visible", timeout=20000)
    menu_cursor = page.locator('#hand-cursor').count()
    page.locator('#btn-input-config').click()
    page.wait_for_function("document.querySelector('#gesture-detection').value === '0.35'")
    for threshold in ('0.5', '0.35'):
        page.locator('#gesture-detection').select_option(threshold)
        page.locator('#btn-gesture-apply').click()
        page.wait_for_function("""async (threshold) => {
          const s = await (await fetch('/api/status')).json();
          return s.settings.min_detection_confidence === Number(threshold)
            && s.applied_revision === s.revision && !s.initializing && !s.error;
        }""", arg=threshold)
        page.wait_for_function("window.replayClient.lastGesture.visible")
    # Reopening must read the value persisted by the actual settings endpoint.
    page.locator('#btn-input-done').click()
    page.locator('#btn-input-config').click()
    page.wait_for_function("document.querySelector('#gesture-detection').value === '0.35'")
    seq_before_retry = page.evaluate('window.replayClient.lastGesture.seq')
    page.locator('#btn-gesture-retry').click()
    page.wait_for_function("""seq => window.replayClient.lastGesture.visible
      && window.replayClient.lastGesture.seq > seq + 5""", arg=seq_before_retry)
    page.wait_for_function("document.querySelector('#gesture-preview').naturalWidth > 0")
    Path('artifacts').mkdir(exist_ok=True)
    page.screenshot(path='artifacts/recognition-settings.png')
    page.set_viewport_size({'width': 390, 'height': 844})
    assert page.locator('.input-config-panel').evaluate('(el) => el.scrollWidth <= el.clientWidth + 1')
    page.locator('#gesture-detection').scroll_into_view_if_needed()
    page.screenshot(path='artifacts/recognition-settings-mobile.png')
    page.set_viewport_size({'width': 1280, 'height': 900})
    page.locator('#btn-input-done').click()
    page.locator('#btn-start').click()
    page.wait_for_function("window.__game.scene.getScene('GameScene').handBlade.sprite.visible", timeout=10000)
    positions = []
    for _ in range(30):
        page.wait_for_timeout(100)
        positions.append(page.evaluate("""() => {
          const s=window.__game.scene.getScene('GameScene');
          return {visible:s.handBlade.sprite.visible,x:s.handBlade.sprite.x,
            inputX:s.gestureInput.getPosition()?.x,seq:window.replayClient.lastGesture.seq};
        }"""))
    visible = [v for v in positions if v['visible'] and v.get('inputX') is not None]
    assert len(visible) >= 10, positions
    span = max(v['x'] for v in visible) - min(v['x'] for v in visible)
    assert span > 150, positions
    page.evaluate("""async () => {
      const {mapGesture}=await import('/js/input/gestureMapping.js');
      const s=window.__game.scene.getScene('GameScene');
      s.spawner.clear(); s.spawner.nextInterval=999999;
      const y=mapGesture(window.replayClient.lastGesture,s.registry.get('gestureOptions')).y*s.scale.height;
      s.spawner._spawnOne(false).setPosition(s.scale.width/2,y).setVelocity(0,0).body.setAllowGravity(false);
      s.sliced=0; s.score=0;
    }""")
    page.wait_for_function("window.__game.scene.getScene('GameScene').sliced===1", timeout=12000)
    score = page.evaluate("window.__game.scene.getScene('GameScene').score")
    assert score >= 10
    page.request.post(url+'/test/feed', data={"blank": True})
    page.wait_for_function("!window.__game.scene.getScene('GameScene').handBlade.sprite.visible", timeout=4000)
    page.request.post(url+'/test/feed', data={"blank": False})
    page.wait_for_function("window.__game.scene.getScene('GameScene').handBlade.sprite.visible", timeout=10000)
    assert not errors, errors
    report = {"source":"moving hand photo / real MediaPipe / actual WebSocket", "menu_cursor_present":bool(menu_cursor),
              "visible_samples":len(visible),"horizontal_travel_pixels":round(span),"cut_score":score,
              "loss_and_reacquire":"passed", "sensitivity_save_reload_and_retry":"passed",
              "page_errors":errors}
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/hand-replay-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
    browser.close()
