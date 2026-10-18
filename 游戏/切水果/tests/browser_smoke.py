"""Run against a --no-camera test server; requires playwright for development only."""
import json
from pathlib import Path
import sys
from playwright.sync_api import sync_playwright

url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765"
artifacts = Path(__file__).resolve().parents[1] / "artifacts"
artifacts.mkdir(exist_ok=True)
errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(url)
    page.wait_for_function("window.__game?.scene.isActive('MenuScene')")
    page.locator("#btn-input-config").click()
    page.wait_for_function("document.querySelector('#gesture-diagnostic').textContent.includes('禁用')")
    page.wait_for_timeout(500)
    page.screenshot(path=str(artifacts / "gesture-settings.png"), full_page=True)
    assert page.locator("#gesture-activation").input_value() in ("always", "index", "pinch")
    assert page.locator('#gesture-point option[value="-1"]').count() == 1
    page.locator('#btn-input-done').click()
    page.locator('[data-mode="timed"]').click()
    page.locator('#btn-start').click()
    page.wait_for_function("window.__game.scene.isActive('GameScene')")
    assert page.evaluate("!window.__game.scene.isActive('MenuScene')")
    page.locator('#btn-live-config').click()
    assert page.evaluate("window.__game.scene.isPaused('GameScene')")
    before = page.evaluate("window.__game.scene.getScene('GameScene').elapsed")
    page.wait_for_timeout(400)
    assert page.evaluate("window.__game.scene.getScene('GameScene').elapsed") == before
    page.locator('[data-input="mouse"]').click()
    page.locator('#btn-input-done').click()
    assert page.evaluate("window.__game.scene.getScene('GameScene').gestureInput === null")
    page.mouse.move(400, 400)
    page.mouse.move(700, 400, steps=5)
    page.locator('#btn-live-config').click()
    page.locator('[data-input="gesture"]').click()
    page.locator('#btn-input-done').click()
    assert page.evaluate("!!window.__game.scene.getScene('GameScene').gestureInput")
    # Feed protocol messages through the actual singleton and collision chain.
    page.evaluate("""async () => {
      const {gestureClient: c} = await import('/js/net/client.js');
      c.stopped = true;
      c.ws.close();
    }""")
    page.wait_for_timeout(150)
    page.evaluate("""async () => {
      const {gestureClient: c} = await import('/js/net/client.js');
      c.connected = true;
      const s = window.__game.scene.getScene('GameScene');
      s.spawner.group.clear(true, true);
      s.spawner.nextInterval = 999999;
      s.gestureInput.setOptions({mirrorX: false, sensitivity: 1});
      s.spawner._spawnOne(false).setPosition(640, 450).setVelocity(0, 0).body.setAllowGravity(false);
      c._handle({type:'gesture', x:0.1, y:0.5, visible:true, active:true, stroke_id:1, revision:0});
    }""")
    page.wait_for_timeout(80)
    assert page.evaluate("window.__game.scene.getScene('GameScene').handBlade.sprite.visible")
    assert page.evaluate("Math.abs(window.__game.scene.getScene('GameScene').handBlade.sprite.x - 128) < 0.01")
    page.evaluate("""async () => {
      const {gestureClient: c} = await import('/js/net/client.js');
      c._handle({type:'gesture', x:0.9, y:0.5, visible:true, active:true, stroke_id:1, revision:0});
    }""")
    page.wait_for_function("window.__game.scene.getScene('GameScene').sliced === 1")
    page.screenshot(path=str(artifacts / 'hand-follow-blade.png'))
    page.evaluate("window.__game.scene.getScene('GameScene')._gameOver()")
    page.wait_for_selector('#result-overlay:not(.hidden)')
    page.locator('#nickname-input').fill('测试玩家')
    page.locator('#btn-save-rank').click()
    assert page.locator('#btn-save-rank').is_disabled()
    assert page.locator('.rank-tab.active').evaluate_all("tabs => tabs.length > 0 && tabs.every(tab => tab.dataset.rmode === 'timed')")
    page.locator('#btn-retry').click()
    page.wait_for_function("window.__game.scene.isActive('GameScene')")
    assert not page.evaluate("window.__game.scene.isActive('ResultScene')")
    page.locator('#btn-live-menu').click()
    page.wait_for_function("window.__game.scene.isActive('MenuScene')")
    page.locator('[data-mode="demo"]').click()
    page.locator('#btn-start').click()
    page.wait_for_function("window.__game.scene.getScene('GameScene').sliced > 0", timeout=15000)
    page.screenshot(path=str(artifacts / 'demo-game.png'))
    page.locator('#btn-live-menu').click()
    page.set_viewport_size({"width": 390, "height": 844})
    page.locator('#btn-input-config').click()
    page.wait_for_timeout(500)
    page.screenshot(path=str(artifacts / 'gesture-settings-mobile.png'))
    assert page.locator('.input-config-panel').evaluate('(el) => el.scrollWidth <= el.clientWidth + 1')
    page.locator('#btn-input-done').click()
    assert not errors, errors
    print(json.dumps({"browser": "Edge", "page_errors": errors, "checks": ["menu", "settings", "pause", "live input switch", "gesture to score", "result", "rank", "retry", "demo", "mobile layout"]}))
    browser.close()
