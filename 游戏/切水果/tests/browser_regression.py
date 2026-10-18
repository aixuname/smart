"""UI regression checks for calibration, pause, pooling and unavailable storage."""
import json
from pathlib import Path
import sys
from playwright.sync_api import sync_playwright

url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8767"
errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.add_init_script("localStorage.setItem('fruit_flash_rank', '[null,{}, {\"name\":\"bad\",\"score\":\"<script>\"}]')")
    page.goto(url)
    page.wait_for_function("window.__game?.scene.isActive('MenuScene')")
    page.locator('#btn-start').click()
    page.wait_for_function("window.__game.scene.isActive('GameScene')")
    pool = page.evaluate("""() => {
      const s = window.__game.scene.getScene('GameScene');
      s.spawner.clear();
      const first = s.spawner._spawnOne(false);
      s.spawner.release(first);
      const reused = s.spawner._spawnOne(true);
      const result = {same: first === reused, active: reused.active, bomb: reused.getData('isBomb'), gravity: reused.body.allowGravity};
      for (let i=0; i<47; i++) s.spawner._spawnOne(false);
      result.capacity = s.spawner.group.getLength();
      result.overflow = s.spawner._spawnOne(false) === null;
      s.spawner.clear();
      s.spawner.nextInterval = 999999;
      s.combo.onSlice(s.elapsed); s.combo.onSlice(s.elapsed);
      return result;
    }""")
    assert pool == {"same": True, "active": True, "bomb": True, "gravity": True, "capacity": 48, "overflow": True}, pool
    page.locator('#btn-live-config').click()
    before = page.evaluate("window.__game.scene.getScene('GameScene').elapsed")
    page.wait_for_timeout(2100)
    page.locator('#btn-input-done').click()
    page.wait_for_timeout(100)
    state = page.evaluate("""() => { const s = window.__game.scene.getScene('GameScene'); return {elapsed:s.elapsed, combo:s.combo.count}; }""")
    assert state['combo'] == 2 and state['elapsed'] - before < 1000, state
    effect = page.evaluate("""async () => {
      const { Effects } = await import('/js/effects/Effects.js');
      const s = window.__game.scene.getScene('GameScene');
      const a = Effects.juiceBurst(s, 300, 300, 0xff4757);
      const b = Effects.juiceBurst(s, 300, 300, 0xff4757);
      const positions = [];
      a.forEachAlive(p => positions.push([p.x,p.y]));
      return {same:a===b, origin:[a.x,a.y], positions};
    }""")
    assert effect['same'] and effect['origin'] == [0, 0]
    assert effect['positions'] and all(abs(x-300)<1 and abs(y-300)<1 for x,y in effect['positions']), effect
    page.locator('#btn-live-config').click()
    page.evaluate("""async () => { const {gestureClient:c} = await import('/js/net/client.js'); c.stopped=true; c.ws.close(); }""")
    page.wait_for_timeout(150)
    page.locator('#btn-gesture-calibrate').click()
    page.evaluate("""async () => {
      const {gestureClient:c} = await import('/js/net/client.js'); c.connected=true;
      window.__calibrationFeed = setInterval(() => {
        const second = document.querySelector('#gesture-calibration-status').textContent.includes('右下角');
        c._handle({type:'gesture', x:second?0.2:0.8, y:second?0.8:0.2, visible:true, active:true, stroke_id:1});
      }, 50);
    }""")
    page.wait_for_function("document.querySelector('#gesture-calibration-status').textContent.includes('标定完成')", timeout=12000)
    page.evaluate("clearInterval(window.__calibrationFeed)")
    settings = page.evaluate("window.__game.registry.get('gestureOptions')")
    assert abs(settings['sensitivity'] - 1/0.6) < .001 and abs(settings['sensitivityY'] - 1/0.6) < .001, settings
    page.locator('#btn-gesture-preset-save').click()
    page.locator('#gesture-sensitivity').fill('2.25')
    page.locator('#gesture-sensitivity').dispatch_event('input')
    page.locator('#btn-gesture-preset-load').click()
    assert abs(page.evaluate("window.__game.registry.get('gestureOptions').sensitivity") - 1/0.6) < .001
    page.locator('#btn-gesture-calibrate').click()
    page.wait_for_function("document.querySelector('#gesture-calibration-status').textContent.includes('没有持续识别')", timeout=6500)
    assert abs(page.evaluate("window.__game.registry.get('gestureOptions').sensitivity") - 1/0.6) < .001
    page.locator('#btn-input-done').click()
    page.evaluate("Object.defineProperty(Storage.prototype, 'setItem', {value(){throw new Error('quota');}})")
    page.evaluate("window.__game.scene.getScene('GameScene')._gameOver()")
    page.wait_for_selector('#result-overlay:not(.hidden)')
    page.locator('#btn-save-rank').click()
    assert '本次会话' in page.locator('#btn-save-rank').inner_text()
    assert not errors, errors
    report = {"checks": ["invalid ranks", "bounded sprite pool", "reuse reset", "pause freezes combo", "particle origin", "emitter reuse", "two-corner calibration", "mapping preset", "missing hand calibration", "storage fallback"], "page_errors": errors}
    print(json.dumps(report))
    browser.close()
