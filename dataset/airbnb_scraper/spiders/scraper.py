from asyncio import *
import re
import sys 
if sys.platform == 'win32':
    set_event_loop_policy(WindowsSelectorEventLoopPolicy())
from scrapy import *
from scrapy_playwright.page import PageMethod

class AirBNB(Spider):
  name = 'airbnb'
  
  async def start(self):
    yield Request(
      url = 'https://www.airbnb.com/s/United-States/homes',
      meta = {
        'playwright': True,
        'playwright_include_page': True,
        'playwright_page_methods': [
          PageMethod("wait_for_selector", "div[data-testid=card-container]"),
          PageMethod('evaluate', '''
                     async () => {
                      const selector = 'div[data-testid="card-container"]';
                      let previousCount = 0;
                      let sameCountTries = 0;
                      const maxTries = 5;  // stop if no new cards after 5 scrolls

                      while (sameCountTries < maxTries) {
                          // Scroll down by viewport height
                          window.scrollBy(0, window.innerHeight);
                          await new Promise(r => setTimeout(r, 2000)); // wait for potential load

                          const currentCount = document.querySelectorAll(selector).length;
                          if (currentCount > previousCount) {
                              previousCount = currentCount;
                              sameCountTries = 0;  // reset because we got new cards
                          } else {
                              sameCountTries++;
                          }
                      }

                      // Final scroll to bottom to trigger any last items
                      window.scrollTo(0, document.body.scrollHeight);
                      await new Promise(r => setTimeout(r, 2000));
                  }
        ''')
          
        ]
      }
    )
  
  async def close_popups(self, page):
    popup_selectors = [
        'button[aria-label="Close"]',
        'button:has-text("Got it")',
        'button:has-text("Accept")',
        'button:has-text("Dismiss")',
        'button:has-text("×")',       
        '[data-testid="modal-close"]',  
        'div[role="dialog"] button[aria-label="Close"]',
        'div[class*="modal"] button[aria-label="Close"]',
    ]
    for selector in popup_selectors:
        try:
            locator = page.locator(selector)
            if await locator.count() > 0 and await locator.first.is_visible():
                await locator.first.click(timeout=3000)
                await page.wait_for_timeout(500)
        except Exception:
            continue
  
  async def parse(self, response):
    page = response.meta['playwright_page']
    cards = response.css('div[data-testid="card-container"] a::attr(href)').getall()
    self.logger.info(f"Found {len(cards)} listing cards on search page")
    for i, rel_url in enumerate(cards, 1):
      self.logger.info(f"Yielding request #{i}")
      yield response.follow(rel_url, callback=self.parse_listing, meta={'playwright': True, 'playwright_include_page': True})
    await page.close()
    
  async def parse_listing(self, response):
    page = response.meta['playwright_page']
    try:
      
      await self.close_popups(page)
      
      misc = None
      price = None
      
      try:
        price_cont = page.locator('span[style*="--pricing-guest-price: none;"]')
        if await price_cont.count() == 0:
          price_cont = page.locator('button:has-text("₽"), button:has-text("$"), button:has-text("€")')
        price = await price_cont.first.text_content()
        match = re.search(r'([\d,]+)', price)
        if match:
          price = int(match.group(1).replace(',', ''))
      except Exception as price_parsing_error:
        self.logger.warning(f"Could not open description modal: {price_parsing_error}")
          
      image_urls = await page.eval_on_selector_all(
          'div[data-section-id="HERO_DEFAULT"] img',
          'elements => elements.map(img => img.src)'
      )
      location_h2 = await page.text_content('div[data-section-id="OVERVIEW_DEFAULT_V2"] h2[elementtiming="LCP-target"]')
      if not location_h2:
          location_h2 = await page.text_content('h2[elementtiming="LCP-target"]')
      try:
        view = page.locator('div[data-section-id="OVERVIEW_DEFAULT_V2"]')
        if view:
          ol = view.locator('ol')
          if await ol.count() > 0:
            items = await ol.locator('li').all_text_contents()
            if items:
              misc = ' · '.join(items)
            
      except Exception as ex:
        self.logger.warning(f"Could not open description modal: {ex}")
      
      desc = None
      try:
        desc_btn = page.locator('button[aria-label="Show more about this place"]')
        if await desc_btn.count() > 0:
          await desc_btn.scroll_into_view_if_needed()
          await desc_btn.first.click(force=True, timeout=20000)
          await page.wait_for_selector('div[data-section-id="DESCRIPTION_MODAL"]', state="visible", timeout=20000)
          desc = await page.text_content('div[data-section-id="DESCRIPTION_MODAL"]')
          await page.keyboard.press("Escape") 
          await page.wait_for_selector('div[data-section-id="DESCRIPTION_MODAL"]', state="hidden", timeout=20000)
        else:
          desc_btn = page.locator('button[aria-label="About this space"]')
          if await desc_btn.count() > 0:
            desc_btn.scroll_into_view_if_needed()
            await desc_btn.first.click(force=True, timeout=20000)
            await page.wait_for_selector('div[data-section-id="DESCRIPTION_MODAL"]', state="visible", timeout=20000)
            desc = await page.text_content('div[data-section-id="DESCRIPTION_MODAL"]')
            await page.keyboard.press("Escape") 
            await page.wait_for_selector('div[data-section-id="DESCRIPTION_MODAL"]', state="hidden", timeout=20000)
          else:
            visible_desc = page.locator('div[data-section-id="DESCRIPTION_DEFAULT"]')
            if await visible_desc.count() > 0:
              desc = await visible_desc.text_content()

      except Exception as description_parsing_error:
          self.logger.warning(f"Could not open description modal: {description_parsing_error}")
        
      amenities = []
      try:
        amenities_sec = page.locator('div[data-section-id="AMENITIES_DEFAULT"]')
        amenities_btn = amenities_sec.locator('button:has-text("amenities")')
        await amenities_btn.scroll_into_view_if_needed()
        await amenities_btn.first.click(force=True, timeout=20000)
        await page.wait_for_selector('div[aria-label="What this place offers"]', state="visible", timeout=20000)
        amenities = await page.eval_on_selector_all(
          'div[aria-label="What this place offers"] [id$="-row-title"]',
          'elements => elements.map(el => el.textContent.trim())'
        )
        await page.keyboard.press("Escape") 
        await page.wait_for_selector('div[aria-label="What this place offers"]', state="hidden", timeout=20000)
      except Exception as amenities_error:
        self.logger.warning(f"Could not extract amenities: {amenities_error}")
      
      yield {
        'url': response.url,
        'description': desc,
        'amenities': amenities,
        'imame_urls': image_urls,
        'location': location_h2,
        'Price': price,
        'Miscellaneous': misc,

        
      }
    finally:
      await page.close()