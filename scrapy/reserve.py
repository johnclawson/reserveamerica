import scrapy

class BlogSpider(scrapy.Spider):
  name = 'blogspider'
  start_urls = ['https://www.reserveamerica.com/camping/big-basin-redwoods-sp/r/campgroundDetails.do?contractCode=CA&parkId=120009']

  def parse(self, response):
    for title in response.css('h2.entry-title'):
      yield {'title': title.css('a ::text').extract_first()}

    for next_page in response.css('div.prev-post > a'):
      yield response.follow(next_page, self.parse)
