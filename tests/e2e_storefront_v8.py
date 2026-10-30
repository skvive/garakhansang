"""Actual Chromium DOM tests for shopping-cart availability policy and catalog event refresh."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json
ROOT=Path(__file__).resolve().parents[1]
js=(ROOT/'storefront/assets/js/app.js').read_text('utf-8')
results=[]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
 for mode,width in [('desktop',1366),('mobile',390)]:
  page=browser.new_page(viewport={'width':width,'height':850})
  page.set_content('''<main><label>수량 <input id="qty" type="number" value="1" /></label><button data-add="bangeo-hoe">장바구니 담기</button><div id="cart-items"></div><span data-cart-count>0</span><span data-subtotal>0원</span></main>''')
  page.evaluate('window.GARAK_PRODUCTS=[{slug:"bangeo-hoe",price:55000,stock:0,status:"hidden",name:"대방어회",image:"product-bangeo-hoe"}]')
  page.add_script_tag(content=js)
  page.evaluate("window.dispatchEvent(new Event('DOMContentLoaded'))")
  button=page.locator('[data-add]');count=page.locator('[data-cart-count]')
  button.click();assert count.inner_text()=='0';results.append((mode,'hidden_denied',True))
  page.evaluate('window.GARAK_PRODUCTS[0].status="published"')
  button.click();assert count.inner_text()=='0';results.append((mode,'out_of_stock_denied',True))
  page.evaluate('window.GARAK_PRODUCTS[0].stock=2')
  page.locator('#qty').fill('2');button.click();assert count.inner_text()=='2';results.append((mode,'valid_2_units_added',True))
  page.locator('#qty').fill('1');button.click();assert count.inner_text()=='2';results.append((mode,'over_stock_denied',True))
  page.evaluate('window.GARAK_PRODUCTS[0].stock=0;document.dispatchEvent(new Event("garak:catalog-updated"))')
  assert '품절' in page.locator('#cart-items').inner_text()
  assert page.locator('[data-subtotal]').inner_text()=='0원'
  results.append((mode,'stock_change_in_cart_zero_total',True))
  page.screenshot(path=str(ROOT/'docs'/f'V8_cart_validation_{mode}.png'))
  page.close()
 browser.close()
(ROOT/'docs'/'QA_V8_CART.json').write_text(json.dumps({'tests':results,'total':len(results),'passed':True},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'tested':len(results),'passed':True,'scenarios':results},ensure_ascii=False))
