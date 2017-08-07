# -*- coding: utf-8 -*-
import datetime
try:
    # python 3.x
    from urllib.parse import urlparse, parse_qs
except Exception:
    # python 2.x
    from urlparse import urlparse, parse_qs
import logging
from scrapy.spiders import CrawlSpider
from scrapy.http import Request

from reserve_america.items import ParkItem, CampsiteItem

class CampsiteSpider(CrawlSpider):
    name = 'campsite'

    url_template = 'https://www.reserveamerica.com/campsiteCalendar.do?page=calendar&contractCode=%s&parkId=%d&calarvdate=%s&sitepage=true&startIdx=0'

    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.basicConfig(
        level=logging.WARNING,
        format=
        '%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
        datefmt='%a, %d %b %Y %H:%M:%S',
        filename='reservation.log',
        filemode='w')

    scrawl_parks = [
        {
            "contractCode": "CA",
            "parkId": 120009
        }
    ]

    def __init__(self, *args, **kwargs):
        self.first_date = self.__offset_date(datetime.datetime.today(), 2)
        self.cookie_index = 0
        super(CampsiteSpider, self).__init__(*args, **kwargs)

    def __offset_date(self, date, offset):
        return date + datetime.timedelta(days=offset)

    def parse_park(self, response):
        parkItem = ParkItem()
        parkItem['name'] = response.xpath('div[@id="campname"]/span[@id="cgroundName"]').extract_first()
        parkItem['parkId'] = response.meta['parkId']
        parkItem['contractCode'] = response.meta['contractCode']
        parkItem['_id'] = '%s::%s' % (response.meta['parkId'], response.meta['contractCode'])
        parkItem['addressCountry'] = response.xpath('div[@itemprop="address"]/meta[@itemprop="addressCountry"]/@content').extract_first()
        parkItem['addressStreet'] = response.xpath('div[@itemprop="address"]/span[@itemprop="streetAddress"]/text()').extract_first()
        parkItem['addressLocality'] = response.xpath('div[@itemprop="address"]/span[@itemprop="addressLocality"]/text()').extract_first()
        parkItem['addressRegion'] = response.xpath('div[@itemprop="address"]/span[@itemprop="addressRegion"]/text()').extract_first()
        parkItem['postalCode'] = response.xpath('div[@itemprop="address"]/span[@itemprop="postalCode"]/text()').extract_first()
        parkItem['telephone'] = response.xpath('div[@itemprop="address"]/span[@itemprop="telephone"]/text()').extract_first()
        parkItem['services'] = response.xpath('//div[@id="servicesamenitiescontent"]/table[@id="contenttable/"]/td[@class="td2"]/ul/li/text()').extract()

        yield parkItem

        ## parse campsites

    def start_requests(self):
        while len(self.scrawl_parks):
            park = self.scrawl_parks.pop()
            url = self.url_template % (park['contractCode'], park['parkId'], self.first_date.strftime('%m/%d/%Y'))
            logging.debug("[start_requests] url: %s", url)
            yield Request(url=url, callback=self.parse_park, dont_filter=True,
                          meta={'cookiejar': self.cookie_index, 'parkId': park['parkId'], 'contractCode': park['contractCode']})

