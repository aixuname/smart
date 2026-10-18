"""Visual artifacts and keyboard/layout checks against a --no-camera server."""
import json
from pathlib import Path
import sys

from playwright.sync_api import sync_playwright

url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8769"
artifacts = Path(__file__).resolve().parents[1] / "artifacts"
artifacts.mkdir(exist_ok=True)
errors = []
reports = []


def check_horizontal_layout(page, panel):
    result = page.locator(panel).evaluate("""el => {
      const r = el.getBoundingClientRect();
      return {left:r.left, right:r.right, viewport:innerWidth,
        scroll:el.scrollWidth, client:el.clientWidth};
    }""")
    assert result["left"] >= 0 and result["right"] <= result["viewport"] + 1, result
    assert result["scroll"] <= result["client"] + 1, result


with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    for width, height in [(1440, 960), (1280, 720), (768, 1024), (390, 844), (320, 740)]:
        page = browser.new_page(viewport={"width": width, "height": height}, reduced_motion="reduce")
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(url)
        page.wait_for_function("window.__game?.scene.isActive('MenuScene')")
        page.wait_for_function("document.querySelector('.hero-art img').naturalWidth > 0")
        ids = page.locator('[id]').evaluate_all("els => els.map(el=>el.id)")
        assert len(ids) == len(set(ids)), "Duplicate IDs in interface"
        check_horizontal_layout(page, '.home-panel')
        page.screenshot(path=str(artifacts / f'ui-home-{width}.png'), animations='disabled')

        # Enter on a mode card selects it; it must not also start the game.
        page.locator('[data-mode="timed"]').focus()
        page.keyboard.press('Enter')
        assert page.locator('[data-mode="timed"]').get_attribute('aria-pressed') == 'true'
        assert page.evaluate("window.__game.scene.isActive('MenuScene')")
        page.locator('#btn-input-config').click()
        page.wait_for_function("document.querySelector('#gesture-diagnostic').textContent.includes('禁用')")
        check_horizontal_layout(page, '.input-config-panel')
        assert page.locator('#menu-overlay').evaluate('el=>el.inert')
        page.screenshot(path=str(artifacts / f'ui-settings-{width}.png'), animations='disabled')

        # Focus cannot escape into the covered menu, in either direction.
        page.locator('#btn-input-close').focus()
        page.keyboard.press('Shift+Tab')
        assert page.locator('#btn-input-done').evaluate('el=>el===document.activeElement')
        page.keyboard.press('Tab')
        assert page.locator('#btn-input-close').evaluate('el=>el===document.activeElement')
        page.keyboard.press('Escape')
        assert page.locator('#input-config-overlay').is_hidden()
        assert page.locator('#btn-input-config').evaluate('el=>el===document.activeElement')

        page.locator('#btn-input-config').click()
        page.locator('.device-settings summary').click()
        page.locator('#gesture-camera').scroll_into_view_if_needed()
        check_horizontal_layout(page, '.input-config-panel')
        assert page.locator('#gesture-camera').is_visible()
        page.screenshot(path=str(artifacts / f'ui-settings-detail-{width}.png'), animations='disabled')
        page.locator('#btn-input-done').click()
        page.locator('#btn-rank').click()
        check_horizontal_layout(page, '.leaderboard-panel')
        page.screenshot(path=str(artifacts / f'ui-rank-{width}.png'), animations='disabled')
        page.keyboard.press('Escape')
        assert page.locator('#leaderboard-overlay').is_hidden()

        page.locator('#btn-start').click()
        page.wait_for_function("window.__game.scene.isActive('GameScene')")
        page.wait_for_timeout(150)
        # Keep status/actions clear of each other and score/state within the canvas.
        bounds = page.evaluate("""() => {
          const s = window.__game.scene.getScene('GameScene');
          return [s.hudScore, s.hudState, s.hudInput].map(t => {
            const b=t.getBounds(); return {left:b.left, right:b.right, width:innerWidth};
          });
        }""")
        assert all(b['left'] >= 0 and b['right'] <= b['width'] for b in bounds), bounds
        page.screenshot(path=str(artifacts / f'ui-game-{width}.png'), animations='disabled')
        page.locator('#btn-live-config').click()
        assert page.evaluate("window.__game.scene.isPaused('GameScene')")
        page.locator('#btn-input-close').click()
        assert page.evaluate("window.__game.scene.isActive('GameScene')")
        page.evaluate("window.__game.scene.getScene('GameScene')._gameOver()")
        page.wait_for_selector('#result-overlay:not(.hidden)')
        check_horizontal_layout(page, '.result-panel')
        page.screenshot(path=str(artifacts / f'ui-result-{width}.png'), animations='disabled')
        page.locator('#btn-menu').click()
        assert not errors, errors
        reports.append({"viewport": [width, height], "horizontal_overflow": False,
                        "keyboard_and_modal_return": "passed", "game_and_result": "passed"})
        page.close()
    browser.close()

report = {"viewports": reports, "page_errors": errors}
(artifacts / 'ui-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
