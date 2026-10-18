"""Bounded-resource soak: real wall time, plus fast repeated lifecycle checks."""
import json
from pathlib import Path
import sys
import time
from playwright.sync_api import sync_playwright

url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8767"
seconds = int(sys.argv[2]) if len(sys.argv) > 2 else 180
artifacts = Path(__file__).resolve().parents[1] / "artifacts"
artifacts.mkdir(exist_ok=True)
errors = []
samples = []
with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(url)
    page.wait_for_function("window.__game?.scene.isActive('MenuScene')")
    for _ in range(15):
        page.locator('#btn-start').click()
        page.wait_for_function("window.__game.scene.isActive('GameScene')")
        page.locator('#btn-live-menu').click()
        page.wait_for_function("window.__game.scene.isActive('MenuScene')")
    listeners = page.evaluate("""async () => {
      const {gestureClient:c} = await import('/js/net/client.js');
      return {messages:c._listeners.size, resize:window.__game.scale.listenerCount('resize'), textures:Object.keys(window.__game.textures.list).length};
    }""")
    assert listeners['messages'] == 1, listeners
    page.locator('[data-mode="demo"]').click()
    page.locator('#btn-start').click()
    page.wait_for_function("window.__game.scene.isActive('GameScene')")
    page.evaluate("""() => { const s=window.__game.scene.getScene('GameScene'); s.spawner.opts.spawnIntervalMin=90; s.spawner.opts.spawnIntervalMax=130; s.spawner.opts.bombRatio=0; }""")
    start = time.monotonic()
    while time.monotonic() - start < seconds:
        page.wait_for_timeout(min(15000, max(1, (seconds-(time.monotonic()-start))*1000)))
        sample = page.evaluate("""() => {
          const s=window.__game.scene.getScene('GameScene');
          return {pool:s.spawner.group.getLength(), active:s.spawner.group.countActive(true), bodies:s.physics.world.bodies.size,
            objects:s.children.length, timers:s.time._active.length + s.time._pendingInsertion.length, sliced:s.sliced, fps:window.__game.loop.actualFps,
            heap:performance.memory?.usedJSHeapSize||null, emitters:s._juiceEmitters?.size||0};
        }""")
        sample['wall_seconds'] = round(time.monotonic() - start, 1)
        samples.append(sample)
        assert sample['pool'] <= 48 and sample['objects'] < 150 and sample['timers'] < 10 and sample['emitters'] <= 6, sample
        assert not errors, errors
        print(json.dumps(sample), flush=True)
    assert samples[-1]['sliced'] > 50, samples[-1]
    page.locator('#btn-live-menu').click()
    page.wait_for_function("window.__game.scene.isActive('MenuScene')")
    final_listeners = page.evaluate("""async () => {const {gestureClient:c}=await import('/js/net/client.js'); return c._listeners.size;}""")
    assert final_listeners == 1
    report = {"wall_seconds": round(time.monotonic()-start, 1), "restart_cycles":15,
              "listeners_after_restarts":listeners, "samples":samples, "page_errors":errors}
    (artifacts/'soak-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    browser.close()
