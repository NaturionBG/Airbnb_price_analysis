from scrapy import *
from scrapy_playwright.page import PageMethod
from asyncio import *
import re


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
          PageMethod('evaluate', 'window.scrollBy(0, document.body.scrollHeight)')
          
        ]
      }
    )
  
  async def parse(self, response):
    page = response.meta['playwright_page']
    cards = response.css('div[data-testid="card-container"] a::attr(href)').getall()
    for rel_url in cards:
      yield response.follow(rel_url, callback=self.parse_listing, meta={'playwright': True, 'playwright_include_page': True})
    await page.close()
    
  async def parse_listing(self, response):
    page = response.meta['playwright_page']
    
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
    location_h2 = location_h2 = await page.text_content('div[data-section-id="OVERVIEW_DEFAULT_V2"] h2[elementtiming="LCP-target"]')
    if not location_h2:
        location_h2 = await page.text_content('h2[elementtiming="LCP-target"]')
        
    desc = None
    try:
      desc_btn = page.locator('button[aria-label="Show more about this place"]')
      if await desc_btn.count() > 0:
        await desc_btn.first.click(force=True, timeout=5000)
        await page.wait_for_selector('div[data-section-id="DESCRIPTION_MODAL"]', state="visible", timeout=5000)
        desc = await page.text_content('div[data-section-id="DESCRIPTION_MODAL"]')
        await page.keyboard.press("Escape") 
        await page.wait_for_selector('div[data-section-id="DESCRIPTION_MODAL"]', state="hidden", timeout=5000)
      else:
        visible_desc = page.locator('div[data-section-id="DESCRIPTION_DEFAULT"]')
        if await visible_desc.count() > 0:
            desc = await visible_desc.text_content()
    except Exception as description_parsing_error:
        self.logger.warning(f"Could not open description modal: {description_parsing_error}")
      
    amenities = []
    try:
      amenities_sec = page.locator('div[data-section-id="AMENITIES_DEFAULT"]')
      await amenities_sec.locator('button', has_text = re.compile(r'Show all \d+ amenities')).click(force=True, timeout=10000)
      await page.wait_for_selector('div[aria-label="What this place offers"]', state="visible", timeout=5000)
      amenities = await page.eval_on_selector_all(
        'div[aria-label="What this place offers"] [id$="-row-title"]',
        'elements => elements.map(el => el.textContent.trim())'
      )
      await page.keyboard.press("Escape") 
      await page.wait_for_selector('div[aria-label="What this place offers"]', state="hidden", timeout=5000)
    except Exception as amenities_error:
      self.logger.warning(f"Could not extract amenities: {amenities_error}")
    
    yield {
      'url': response.url,
      'description': desc,
      'amenities': amenities,
      'imame_urls': image_urls,
      'location': location_h2,
      'Price': price
    }