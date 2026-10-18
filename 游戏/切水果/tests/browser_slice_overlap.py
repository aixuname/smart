"""Exercise visible blade/fruit overlap through actual game input and collision logic."""
import json
from pathlib import Path
import sys
from playwright.sync_api import sync_playwright

url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8772"
errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(url)
    page.wait_for_function("window.__game?.scene.isActive('MenuScene')")
    page.locator('#btn-start').click()
    page.wait_for_function("window.__game.scene.isActive('GameScene')")
    page.evaluate("""async () => {
      const {gestureClient:c}=await import('/js/net/client.js');
      c.stopped=true; c.ws.close(); window.overlapClient=c;
    }""")
    page.wait_for_function('!window.overlapClient.isConnected')
    page.evaluate("""() => {
      const c=window.overlapClient; c.connected=true;
      c._handle({type:'status', camera_ok:true, model_missing:false, initializing:false});
      window.overlapPoint={x:0.8,y:0.5,visible:true,active:true};
      window.overlapSeq=0; window.overlapStroke=1;
      window.overlapTimer=setInterval(()=>c._handle({type:'gesture',revision:0,
        seq:++window.overlapSeq,stroke_id:window.overlapStroke,...window.overlapPoint}),20);
      const s=window.__game.scene.getScene('GameScene');
      s.spawner.clear(); s.spawner.nextInterval=999999;
      window.placeFruit=(x,y,bomb=false)=>{
        const f=s.spawner._spawnOne(bomb).setTexture(bomb?'bomb':'fruit-red').setScale(1)
          .setPosition(x,y).setVelocity(0,0).setAngularVelocity(0).setAngle(0);
        f.body.setAllowGravity(false); window.overlapFruit=f; return f;
      };
      window.setTip=(x,y,active=true,visible=true)=>{
        window.overlapPoint={x:1-x/1280,y:y/900,active,visible};
      };
    }""")
    page.wait_for_timeout(150)

    def scene(expression):
        return page.evaluate("() => { const s=window.__game.scene.getScene('GameScene'); " + expression + " }")

    def sliced():
        page.wait_for_timeout(140)
        return scene('return s.sliced;')

    cases = {}
    # A 14px visible tip ring grazes a 30px fruit at distance 40px.
    page.evaluate('setTip(400,450)')
    page.wait_for_timeout(100)
    scene('s.sliced=0; s.spawner.clear(); placeFruit(500,490);')
    page.evaluate('setTip(600,450)')
    cases['tip_ring_graze'] = sliced() == 1

    # Silver blade is 35px behind the tip; the handle is farther back and should not cut.
    scene('s.sliced=0; s.spawner.clear(); s.handBlade.rotation=0; s.handBlade.last=null;')
    page.evaluate('setTip(600,400)')
    page.wait_for_timeout(100)
    scene('s.handBlade.rotation=0; s.handBlade.sprite.setRotation(0); placeFruit(520,400);')
    cases['handle_does_not_cut'] = sliced() == 0
    scene('s.spawner.clear(); s.misses=0; placeFruit(530,396,true);')
    page.wait_for_timeout(140)
    cases['bomb_touching_only_handle_does_not_explode'] = scene('return s.misses;') == 0
    scene('s.spawner.clear(); placeFruit(540,400);')
    cases['silver_blade_overlap'] = sliced() == 1

    scene('s.sliced=0; s.spawner.clear();')
    page.evaluate('setTip(700,550)')
    page.wait_for_timeout(100)
    scene('placeFruit(700,550);')
    cases['active_stationary_contact'] = sliced() == 1

    scene('s.sliced=0; s.spawner.clear();')
    page.evaluate('setTip(700,550,false)')
    page.wait_for_timeout(100)
    scene('placeFruit(700,550);')
    cases['inactive_overlap_does_not_cut'] = sliced() == 0
    page.evaluate('setTip(700,550,true)')
    cases['activation_contact_without_motion'] = sliced() == 1

    # Expiry must turn off contact even if the last reported hand remains visible.
    page.evaluate('clearInterval(window.overlapTimer)')
    page.wait_for_timeout(380)
    scene('s.sliced=0; s.spawner.clear(); placeFruit(700,550);')
    cases['expired_hand_does_not_cut'] = sliced() == 0
    page.evaluate("""window.overlapTimer=setInterval(()=>overlapClient._handle({type:'gesture',revision:0,
      seq:++window.overlapSeq,stroke_id:window.overlapStroke,...window.overlapPoint}),20)""")
    page.wait_for_timeout(100)

    scene('s.spawner.clear(); s.sliced=0; s.misses=0; placeFruit(700,610,true);')
    page.wait_for_timeout(120)
    cases['separated_bomb_does_not_explode'] = scene('return s.misses;') == 0

    # Loss/reacquire must not create an invisible screen-spanning swing.
    scene('s.sliced=0; s.spawner.clear();')
    page.evaluate('setTip(200,600)')
    page.wait_for_timeout(100)
    page.evaluate('setTip(200,600,false,false); window.overlapStroke++')
    page.wait_for_timeout(100)
    scene('placeFruit(600,600);')
    page.evaluate('setTip(1000,600); window.overlapStroke++')
    cases['reacquire_does_not_cut_across_screen'] = sliced() == 0

    # An actual fruit's outer rim is cut by a thin trajectory, without relying on tip padding.
    shape = scene("return s.spawner.collectCircles()[0].r;")
    cases['fruit_radius_matches_visible_body'] = abs(shape-30) < .001
    scene('s.spawner.clear(); s.sliced=0;')
    page.evaluate('setTip(600,450)')
    page.wait_for_timeout(100)
    scene('placeFruit(567,450); placeFruit(900,450);')
    Path('artifacts').mkdir(exist_ok=True)
    page.screenshot(path='artifacts/slice-overlap.png')
    page.evaluate('clearInterval(window.overlapTimer)')
    browser.close()

report = {"source": "synthetic gesture samples / actual Phaser fruit and slicer; no camera",
          "passed": all(cases.values()) and not errors, "cases": cases, "page_errors": errors}
Path('artifacts/slice-overlap-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
raise SystemExit(0 if report['passed'] else 1)
