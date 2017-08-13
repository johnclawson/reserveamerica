# -*- coding: utf-8 -*-
import datetime
import re
try:
    # python 3.x
    from urllib.parse import urlparse, parse_qs
except Exception:
    # python 2.x
    from urlparse import urlparse, parse_qs
import logging
from scrapy.spiders import CrawlSpider
from scrapy.http import Request

from pydash import strings

from reserve_america.items import ParkItem, CampsiteItem, CampsiteDetailItem
from reserve_america.park_list import park_list

class CampsiteSpider(CrawlSpider):
    name = 'campsite'

    url_template = 'https://www.reserveamerica.com/campsiteCalendar.do?page=calendar&contractCode=%s&parkId=%d&calarvdate=%s&sitepage=true&startIdx=0'
    # url_template = 'https://www.reserveamerica.com/campsiteCalendar.do?contractCode=%s&parkId=%d'

    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.basicConfig(
        level=logging.WARNING,
        format=
        '%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
        datefmt='%a, %d %b %Y %H:%M:%S',
        filename='reservation.log',
        filemode='w')

    scrawl_parks = park_list

    def __init__(self, *args, **kwargs):
        self.first_date = self.__offset_date(datetime.datetime.today(), 2)
        self.cookie_index = 0
        super(CampsiteSpider, self).__init__(*args, **kwargs)

    def __offset_date(self, date, offset):
        return date + datetime.timedelta(days=offset)

    def get_data_from_url(self, url):
        queries = parse_qs(urlparse(url).query, keep_blank_values=True)
        return {
            "parkId": queries['parkId'][0],
            "contractCode": queries['contractCode'][0],
            "siteId": queries['siteId'][0]
        }

    def has_next_campsite_list(self, response):
        url = response.xpath('//div[@id="sitelistdiv"]/table/thead/tr/td/span[@class="pagenav"]/a[contains(@id, "Next")]/@href').extract_first()
        if url:
            url = 'https://www.reserveamerica.com'+url

    def parse_park(self, response):
        parkItem = ParkItem()
        # f = open('park.html', 'w')
        # f.write(response.body.decode("utf-8"))
        # f.close()
        parkItem['name'] = response.xpath('//div[@id="campname"]/h1/span[@id="cgroundName"]/text()').extract_first()
        parkItem['parkId'] = response.meta['parkId']
        parkItem['contractCode'] = response.meta['contractCode']
        parkItem['_id'] = '%s::%s' % (response.meta['parkId'], response.meta['contractCode'])
        parkItem['addressCountry'] = response.xpath('//div[@itemprop="address"]/meta[@itemprop="addressCountry"]/@content').extract_first()
        parkItem['addressStreet'] = response.xpath('//div[@itemprop="address"]/span[@itemprop="streetAddress"]/text()').extract_first()
        parkItem['addressLocality'] = response.xpath('//div[@itemprop="address"]/span[@itemprop="addressLocality"]/text()').extract_first()
        parkItem['addressRegion'] = response.xpath('//div[@itemprop="address"]/span[@itemprop="addressRegion"]/text()').extract_first()
        parkItem['postalCode'] = response.xpath('//div[@itemprop="address"]/span[@itemprop="postalCode"]/text()').extract_first()
        parkItem['telephone'] = response.xpath('//div/span[@itemprop="telephone"]/text()').extract_first()
        parkItem['services'] = response.xpath('//div[@id="servicesamenitiescontent"]/div/table[@id="contenttable"]/tbody/tr/td[@class="td2"]/ul/li/text()').extract()

        yield parkItem

        ## parse campsites
        campsite_url_list = response.xpath(
            '//table[@id="shoppingitems"]/tbody/tr/td/div[@class="siteListLabel"]/a/@href').extract()
        while len(campsite_url_list):
            url = campsite_url_list.pop()
            url = 'https://www.reserveamerica.com' + url
            yield Request(url=url, callback=self.parse_campsite, dont_filter=True,
                          meta={'cookiejar': self.cookie_index, 'parkId': response.meta['parkId'],
                                'contractCode': response.meta['contractCode']})
        next_page = self.has_next_campsite_list(response)
        if next_page:
            yield Request(url=url, callback=self.parse_campsite_page, dont_filter=True,
                          meta={'cookiejar': self.cookie_index, 'parkId': response.meta['parkId'],
                                'contractCode': response.meta['contractCode']})

    def parse_campsite_page(self, response):
        campsite_url_list = response.xpath(
            '//table[@id="shoppingitems"]/tbody/tr/td/div[@class="siteListLabel"]/a/@href').extract()
        while len(campsite_url_list):
            url = campsite_url_list.pop()
            url = 'https://www.reserveamerica.com' + url
            yield Request(url=url, callback=self.parse_campsite, dont_filter=True,
                          meta={'cookiejar': self.cookie_index, 'parkId': response.meta['parkId'],
                                'contractCode': response.meta['contractCode']})
        next_page = self.has_next_campsite_list(response)
        if next_page:
            yield Request(url=url, callback=self.parse_campsite_page, dont_filter=True,
                          meta={'cookiejar': self.cookie_index, 'parkId': response.meta['parkId'],
                                'contractCode': response.meta['contractCode']})
        else:
            logging.debug("No more campsites")
            yield None
            pass

    def parse_campsite(self, response):
        campsiteItem = CampsiteItem()
        data = self.get_data_from_url(response.url)
        campsiteItem['_id'] = '%s::%s::%s' % (data['parkId'], data['contractCode'], data['siteId'])
        campsiteItem['parkId'] = data['parkId']
        campsiteItem['contractCode'] = data['contractCode']
        campsiteItem['siteId'] = data['siteId']
        campsiteItem['nameArea'] = response.xpath('//div[@id="sitenamearea"]/div/span/text()').extract_first() + response.xpath('//div[@id="sitenamearea"]/div/text()').extract_first()
        campsiteItem['url'] = response.url
        campsiteItem['detail'] = self.parse_campsite_detail(response)
        yield campsiteItem

    def parse_campsite_detail(self, response):
        details = response.xpath('//div[@id="sitedetail"]/ul/li/text()').extract()
        campsiteDetailItem = {}
        while len(details):
            item = details.pop()
            item = re.search('^([^:]+):\s*(.+)', item)
            campsiteDetailItem[strings.snake_case(item.group(1))] = item.group(2)
        return campsiteDetailItem

    def start_requests(self):
        while len(self.scrawl_parks):
            park = self.scrawl_parks.pop()
            if park['url']:
                url = park['url']
            else:
                url = self.url_template % (park['contractCode'], park['parkId'], self.first_date.strftime('%m/%d/%Y'))
            # url = self.url_template % (park['contractCode'], park['parkId'], self.first_date.strftime('%m/%d/%Y'))
            # url = self.url_template % (park['contractCode'], park['parkId'])
            logging.debug("[start_requests] url: %s", url)
            yield Request(url=url, callback=self.parse_park, dont_filter=True,
                          meta={'cookiejar': self.cookie_index, 'parkId': park['parkId'], 'contractCode': park['contractCode']})

