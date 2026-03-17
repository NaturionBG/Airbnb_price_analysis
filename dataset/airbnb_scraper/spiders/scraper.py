from scrapy import *
from scrapy_playwright.page import PageMethod
from asyncio import *
import re


class AirBNB(Spider):
  name = 'airbnb'
  
  def start_request(self):
    yield Request(
      url = 'https://www.airbnb.com/s/United-States/homesj',
      meta = dict(
        playwright = True,
        playwright_include_page = True,
        playwright_page_methods = [
          PageMethod("wait_for_selector", "div[data-testid=card-container]"),
          PageMethod('evaluate', '"window.scrollBy(0, document.body.scrollHeight)"')
          
        ]
      )
    )
  
  async def parse(self, response):
    page = response.meta['playwright_page']
    cards = response.css('div[data-testid="card-container"] a::attr(href)').getall()
    for rel_url in cards:
      yield response.follow(rel_url, callback=self.parse_listing)
    await page.close()
    
  async def parse_card(self, response):
    page = response.meta['playwright_page']
    image_urls = response.css('div[data-section-id="HERO_DEFAULT"] img::attr(src)').getall()
    location_h2 = response.css('div[data-section-id="OVERVIEW_DEFAULT_V2"] h2[elementtiming="LCP-target"]::text').get()
    desc = None
    try:
      await page.click('button[aria-label="Show more about this place"]', timeout=5000)
      await page.wait_for_selector('div[data-section-id="DESCRIPTION_MODAL"]', state="visible", timeout=5000)
      desc = await page.text_content('div[data-section-id="DESCRIPTION_MODAL"]')
      close_btn = await page.query_selector('button[aria-label="Close"]')
      if close_btn:
        await close_btn.click()
    except Exception as description_parsing_error:
        self.logger.warning(f"Could not open description modal: {description_parsing_error}")
      
    amenities = []
    try:
      amenities_sec = page.locator('div[data-section-id="AMENITIES_DEFAULT"]')
      await amenities_sec.locator('button', has_text = re.compile(r'Show all \d+ amenities')).click()
      await page.wait_for_selector('div[aria-lable="What this place offers"]', state="visible", timeout=5000)
      amenities = await page.eval_on_selector_all(
        'div[aria-label="What this place offers"] [id$="-row-title"]',
        'elements => elements.map(el => el.textContent.trim())'
      )
      close_btn = await page.query_selector('div[aria-label="What this place offers"] button[aria-label="Close"]')
      if close_btn:
        await close_btn.click()
        await page.wait_for_selector('div[role="dialog"][aria-label="What this place offers"]', state="hidden", timeout=5000)
    except Exception as amenities_error:
      self.logger.warning(f"Could not extract amenities: {amenities_error}")
    
    yield {
      'url': response.url,
      'description': desc,
      'amenities': amenities,
      'imame_urls': image_urls,
      'location': location_h2
    }