from asyncio import *
import re
import sys 
import json
from scrapy import *
from scrapy_playwright.page import PageMethod

class AirBNB(Spider):
  name = 'airbnb'
  
  async def start(self):
        with open('urls.json', 'r') as f:
            data = json.load(f)
        for item in data:
            url = item['url']
            yield Request(
                url=url,
                callback=self.parse_listing,
                meta={
                    'playwright': True,
                    'playwright_include_page': True,
                    'playwright_page_timeout': 35000,
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
  
  
    
  async def parse_listing(self, response):
    page = response.meta['playwright_page']
  
    try:
      to_yield = await wait_for(self.extract(page, response), timeout=90)
      self.logger.info(f"Yielding item for {response.url}")
      yield to_yield
    except TimeoutError:
      self.logger.error('LISTING LOAD TIMEOUT OCCURED')
    except Exception as ex:
      self.logger.error(f'LISTING LOADING UNEXPECTED ERROR {ex}')
    try:
      await page.close()
    except Exception:
      self.logger.warning(f"Failed to close page for {response.url}")


  async def extract(self, page, response):
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
          await desc_btn.first.click(force=True, timeout=30000)
          await page.wait_for_selector('div[data-section-id="DESCRIPTION_MODAL"], div[data-plugin-in-point-id="DESCRIPTION_MODAL"]', state="visible", timeout=30000)
          desc = await page.text_content('div[data-section-id="DESCRIPTION_MODAL"], div[data-plugin-in-point-id="DESCRIPTION_MODAL"]', timeout=30000)
          await page.keyboard.press("Escape") 
          await page.wait_for_selector('div[data-section-id="DESCRIPTION_MODAL"], div[data-plugin-in-point-id="DESCRIPTION_MODAL"]', state="hidden", timeout=30000)
        else:
          desc_btn = page.locator('button[aria-label="About this space"]')
          if await desc_btn.count() > 0:
            await desc_btn.scroll_into_view_if_needed()
            await desc_btn.first.click(force=True, timeout=30000)
            await page.wait_for_selector('div[data-section-id="DESCRIPTION_MODAL"], div[data-plugin-in-point-id="DESCRIPTION_MODAL"]', state="visible", timeout=30000)
            desc = await page.text_content('div[data-section-id="DESCRIPTION_MODAL"], div[data-plugin-in-point-id="DESCRIPTION_MODAL"]', timeout=30000)
            await page.keyboard.press("Escape") 
            await page.wait_for_selector('div[data-section-id="DESCRIPTION_MODAL"], div[data-plugin-in-point-id="DESCRIPTION_MODAL"]', state="hidden", timeout=30000)
          else:
            visible_desc = page.locator('div[data-section-id="DESCRIPTION_DEFAULT"], div[data-plugin-in-point-id="DESCRIPTION_DEFAULT"]')
            if await visible_desc.count() > 0:
              desc = await visible_desc.first.text_content(timeout=30000)

      except Exception as description_parsing_error:
          self.logger.warning(f"Could not open description modal: {description_parsing_error}")
        
      return {
        'url': response.url,
        'description': desc,
        'imame_urls': image_urls,
        'location': location_h2,
        'Price': price,
        'Miscellaneous': misc,  
      }

# l1 = 'https://www.airbnb.com/s/United-States/homes'
l = [
  'https://www.airbnb.com/s/New-York--United-States/homes',
  'https://www.airbnb.com/s/Los-Angeles--California--United-States/homes',
  'https://www.airbnb.com/s/Denver--Colorado--United-States/homes',
  'https://www.airbnb.com/s/San-Francisco--California--United-States/homes',
  'https://www.airbnb.com/s/Seattle--Washington--United-States/homes',
  
] 
class AllListings(Spider):
  name = 'links'
  
  async def start(self):
    for link in l:
      yield Request(
        url = link,
        meta = {
          'playwright': True,
          'playwright_include_page': True,
          'playwright_page_timeout': 35000,

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
    max_pages = 15
    current_page = 1
    all_urls = set()
    while current_page <= max_pages:
        await self.close_popups(page)
        await page.wait_for_selector('div[data-testid="card-container"]', timeout=10000)
        cards = await page.eval_on_selector_all(
            'div[data-testid="card-container"] a[href^="/rooms/"]',
            'elements => elements.map(a => a.href)'
        )
        all_urls.update(cards)
        self.logger.info(f"Page {current_page}: collected {len(cards)} URLs (total {len(all_urls)})")
        
        next_btn = page.locator('a[aria-label="Next"]')
        if await next_btn.count() == 0:
            self.logger.info("No more pages loaded. Stopping Iterations.")
            break
        
        is_disabled = await next_btn.first.get_attribute('aria-disabled')
        if is_disabled == 'true':
            self.logger.info('Last Page Reached. Stopping page Iteration.')
            break
        
        await next_btn.scroll_into_view_if_needed()
        await next_btn.click(force=True, timeout=30000)
        current_page += 1
        await page.wait_for_selector('div[data-testid="card-container"]', timeout=10000)
        await page.wait_for_timeout(10000)
    
    await page.close()
    
    for url in all_urls:
            yield {'url': url}
  