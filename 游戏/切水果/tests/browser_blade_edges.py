"""Replay observed edge coordinates through the browser input and visible blade."""
import json
from pathlib import Path
import sys
from playwright.sync_api import sync_playwright

url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8772"
errors = []
failures = []
with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.add_init_script("""localStorage.setItem('fruit_flash_pref', JSON.stringify({input:'gesture',
      gesture:{sensitivity:1.4,sensitivityY:1.4,offsetX:0,offsetY:0}}));""")
    page.goto(url)
    page.wait_for_function("window.__game?.scene.isActive('MenuScene')")
    page.locator('#btn-start').click()
    page.wait_for_function("window.__game.scene.isActive('GameScene')")
    page.evaluate("""async () => {
      const {gestureClient:c}=await import('/js/net/client.js');
      c.stopped=true; c.ws.close(); window.edgeClient=c;
    }""")
    page.wait_for_function("!window.edgeClient.isConnected")
    page.evaluate("""() => {
      const c=window.edgeClient; c.connected=true;
      c._handle({type:'status',camera_ok:true,model_missing:false,initializing:false,fps:30});
      window.edgePoint={x:0.35,y:0.92,visible:true};
      window.edgeSeq=0;
      window.edgeTimer=setInterval(()=>c._handle({type:'gesture',active:true,stroke_id:1,
        revision:0,seq:++window.edgeSeq,...window.edgePoint}),30);
      const s=window.__game.scene.getScene('GameScene');
      s.spawner.clear(); s.spawner.nextInterval=999999;
    }""")

    def state():
        page.wait_for_timeout(120)
        return page.evaluate("""() => {
          const s=window.__game.scene.getScene('GameScene'); const g=s.handBlade.sprite;
          const cursor=document.querySelector('#hand-cursor'); const style=getComputedStyle(cursor);
          return {x:g.x,y:g.y,visible:g.visible,input:s.gestureInput.getPosition(),
            cursorPosition:style.position,cursorPointerEvents:style.pointerEvents};
        }""")

    first = state()
    page.evaluate("window.edgePoint={x:0.4,y:0.94,visible:true}")
    second = state()
    if not first['visible'] or not second['visible'] or second['y'] <= first['y']:
        failures.append('Visible hand motion near camera bottom did not move the blade down')
    if first['cursorPosition'] != 'fixed' or first['cursorPointerEvents'] != 'none':
        failures.append('Hand feedback must use viewport coordinates without intercepting input')
    corners = []
    for x, y in ((0, 0), (1, 0), (0, 1), (1, 1)):
        page.evaluate("point => window.edgePoint={...point,visible:true}", {"x": x, "y": y})
        result = state()
        corners.append(result)
        if not result['visible'] or not (20 <= result['x'] <= 1260 and 20 <= result['y'] <= 880):
            failures.append(f'Blade tip clipped at corner {x},{y}')
        if result['input'] != {"x": result['x'], "y": result['y']}:
            failures.append('Visible tip and collision position differ')
    page.evaluate("window.edgePoint={x:0.35,y:0.92,visible:true}")
    state()
    Path('artifacts').mkdir(exist_ok=True)
    page.screenshot(path='artifacts/blade-edges-desktop.png')
    page.set_viewport_size({"width": 390, "height": 844})
    mobile = state()
    if not mobile['visible'] or not (20 <= mobile['x'] <= 370 and 20 <= mobile['y'] <= 824):
        failures.append('Blade tip is not visible on mobile')
    page.screenshot(path='artifacts/blade-edges-mobile.png')
    page.evaluate("window.edgePoint={x:0,y:0,visible:false}")
    page.wait_for_function("!window.__game.scene.getScene('GameScene').handBlade.sprite.visible")
    page.wait_for_selector('#hand-tracking-notice:not(.hidden)')
    notice = page.locator('#hand-tracking-notice').evaluate("el=>getComputedStyle(el).position")
    if notice != 'fixed':
        failures.append('Missing-hand explanation is not positioned above the game')
    page.screenshot(path='artifacts/blade-missing-notice.png')
    page.evaluate('clearInterval(window.edgeTimer)')
    browser.close()
report = {"source": "observed coordinates replayed through browser; no camera",
          "passed": not failures and not errors, "bottom_motion": [first, second],
          "corners": corners, "mobile": mobile, "failures": failures, "page_errors": errors}
Path('artifacts/blade-edges-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
raise SystemExit(0 if report['passed'] else 1)
