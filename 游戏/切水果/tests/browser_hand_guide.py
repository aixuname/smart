"""Verify hand-to-blade correspondence using the moving photo / real-model server."""
import json
from pathlib import Path
import sys
from playwright.sync_api import sync_playwright

url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8771"
errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.add_init_script("""window.previewRequests=0; window.previewFrames=[];
      const originalFetch=window.fetch;
      window.fetch=async (...args)=>{
        if(args[0]==='/api/preview.jpg') window.previewRequests++;
        const response=await originalFetch(...args);
        if(args[0]==='/api/preview.jpg' && response.ok)
          window.previewFrames.push(JSON.parse(response.headers.get('X-Preview-Gesture')));
        return response;
      };""")
    page.goto(url)
    page.wait_for_function("window.__game?.scene.isActive('MenuScene')")
    assert page.locator('#hand-guide').is_hidden()
    assert page.evaluate('window.previewRequests') == 0
    page.locator('#btn-start').click()
    page.wait_for_function("window.__game.scene.isActive('GameScene')")
    page.evaluate("""() => {
      const s=window.__game.scene.getScene('GameScene');
      s.spawner.clear(); s.spawner.nextInterval=999999;
    }""")
    page.wait_for_selector('#hand-guide-connection:not(.hidden)', timeout=20000)
    page.wait_for_function("document.querySelector('#hand-guide-preview').naturalWidth > 0")

    def mapping_state():
        return page.evaluate("""() => {
          const frame=document.querySelector('#hand-guide-frame').getBoundingClientRect();
          const marker=document.querySelector('#hand-guide-marker');
          const line=document.querySelector('#hand-guide-connection line');
          const hand={x:parseFloat(marker.style.left)/frame.width,y:parseFloat(marker.style.top)/frame.height};
          const s=window.__game.scene.getScene('GameScene');
          const mirror=s.registry.get('gestureOptions').mirrorX;
          const matched=window.previewFrames.some(g=>g && Math.abs((mirror?1-g.x:g.x)-hand.x)<.0001 && Math.abs(g.y-hand.y)<.0001);
          return {matched,mirror,hand,blade:{x:s.handBlade.sprite.x,y:s.handBlade.sprite.y},
            connection:{x:Number(line.getAttribute('x2')),y:Number(line.getAttribute('y2'))},
            imageTransform:getComputedStyle(document.querySelector('#hand-guide-preview')).transform,
            pointerEvents:getComputedStyle(document.querySelector('#hand-guide-connection')).pointerEvents};
        }""")

    desktop = mapping_state()
    assert desktop['matched'] and desktop['mirror'], desktop
    assert desktop['pointerEvents'] == 'none'
    # Phaser and DOM have separate animation callbacks; allow one render frame of movement.
    assert abs(desktop['connection']['x'] - desktop['blade']['x']) < 35, desktop
    assert abs(desktop['connection']['y'] - desktop['blade']['y']) < 10, desktop
    assert desktop['imageTransform'].startswith('matrix(-1'), desktop
    assert page.locator('#guide-tip').is_hidden(), 'Old prompt must not cover the hand map'
    Path('artifacts').mkdir(exist_ok=True)
    page.screenshot(path='artifacts/hand-guide-desktop.png')
    page.locator('#hand-guide-line-toggle').uncheck()
    page.wait_for_selector('#hand-guide-connection.hidden', state='attached')
    assert page.locator('#hand-guide-preview').is_visible()
    page.locator('#hand-guide-line-toggle').check()
    page.wait_for_selector('#hand-guide-connection:not(.hidden)')

    # Collapsing must stop network traffic and release the last image.
    page.locator('#btn-hand-guide-toggle').click()
    page.wait_for_timeout(200)
    requests = page.evaluate('window.previewRequests')
    page.wait_for_timeout(550)
    assert page.evaluate('window.previewRequests') == requests
    assert page.locator('#hand-guide-preview').get_attribute('src') is None
    assert page.locator('#btn-hand-guide-toggle').get_attribute('aria-expanded') == 'false'
    page.locator('#btn-hand-guide-toggle').click()
    page.wait_for_selector('#hand-guide-connection:not(.hidden)')

    # A background tab can freeze rAF: the visibility event must synchronously stop polling.
    page.evaluate("""() => {
      Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});
      document.dispatchEvent(new Event('visibilitychange'));
    }""")
    assert page.locator('#hand-guide-preview').get_attribute('src') is None
    requests = page.evaluate('window.previewRequests')
    page.wait_for_timeout(450)
    assert page.evaluate('window.previewRequests') == requests
    page.evaluate("""() => {
      delete document.hidden; document.dispatchEvent(new Event('visibilitychange'));
    }""")
    page.locator('#btn-input-done').click()
    page.wait_for_selector('#hand-guide-connection:not(.hidden)')

    # Pausing hides this preview while settings uses its own preview.
    page.locator('#btn-live-config').click()
    page.wait_for_selector('#hand-guide.hidden', state='attached')
    assert page.locator('#hand-guide-preview').get_attribute('src') is None
    page.locator('#input-mirror').uncheck()
    page.locator('#btn-input-done').click()
    page.wait_for_selector('#hand-guide-connection:not(.hidden)')
    direct = mapping_state()
    assert direct['matched'] and not direct['mirror'] and direct['imageTransform'] == 'none', direct
    assert '左右反向' in page.locator('#hand-guide-direction').inner_text()

    # Calibrated range must remain meaningful in a mirrored preview, too.
    page.locator('#btn-live-config').click()
    page.locator('#input-mirror').check()
    page.locator('#gesture-sensitivity').fill('2')
    page.locator('#gesture-sensitivity').dispatch_event('input')
    page.locator('#btn-input-done').click()
    page.wait_for_selector('#hand-guide-connection:not(.hidden)')
    assert page.locator('#hand-guide-area').evaluate('el=>el.style.width') == '50%'
    calibrated = mapping_state()
    assert calibrated['matched'], calibrated

    page.set_viewport_size({"width": 390, "height": 844})
    page.wait_for_timeout(300)
    bounds = page.locator('#hand-guide').bounding_box()
    assert bounds['y'] >= 112 and bounds['x'] >= 0 and bounds['x']+bounds['width'] <= 390, bounds
    assert bounds['y']+bounds['height'] < page.locator('#status-bar').bounding_box()['y'], bounds
    assert page.locator('#hand-guide').evaluate('el=>el.scrollWidth<=el.clientWidth+1')
    page.screenshot(path='artifacts/hand-guide-mobile.png')
    page.set_viewport_size({"width": 844, "height": 390})
    page.wait_for_timeout(300)
    landscape = page.locator('#hand-guide').bounding_box()
    assert landscape['y']+landscape['height'] < page.locator('#status-bar').bounding_box()['y'], landscape
    frame = page.locator('#hand-guide-frame').bounding_box()
    assert abs(frame['width']/frame['height']-4/3) < .01, frame
    page.screenshot(path='artifacts/hand-guide-landscape.png')

    page.request.post(url+'/test/feed', data={"blank": True})
    page.wait_for_selector('#hand-guide-connection.hidden', state='attached', timeout=4000)
    page.wait_for_selector('#hand-guide-marker.hidden', state='attached', timeout=4000)
    page.request.post(url+'/test/feed', data={"blank": False})
    page.wait_for_selector('#hand-guide-connection:not(.hidden)', timeout=12000)

    page.locator('#btn-live-config').click()
    page.locator('.input-big-opt[data-input="mouse"]').click()
    page.locator('#btn-input-done').click()
    page.wait_for_timeout(200)
    assert page.locator('#hand-guide').is_hidden()
    requests = page.evaluate('window.previewRequests')
    page.wait_for_timeout(500)
    assert page.evaluate('window.previewRequests') == requests
    page.locator('#btn-live-menu').click()
    assert page.locator('#hand-guide').is_hidden()
    assert not errors, errors
    report = {"source": "moving photo / real MediaPipe / actual WS and JPEG",
              "passed": True, "desktop": desktop, "mirror_off": direct, "calibrated": calibrated,
              "mobile_bounds": bounds, "landscape_bounds": landscape,
              "collapse_pause_mouse_menu_background": "passed",
              "loss_and_reacquire": "passed", "page_errors": errors}
    Path('artifacts/hand-guide-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report))
    browser.close()
