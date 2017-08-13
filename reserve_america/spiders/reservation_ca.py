# -*- coding: utf-8 -*-
import datetime
import re
# python 3.x
from urllib.parse import urlparse, parse_qs
# Python 3
import html

import logging
from scrapy.spiders import CrawlSpider
from scrapy.http import Request, HtmlResponse

import json
import codecs

from pydash import strings

from reserve_america.items import ReservationItem

from reserve_america.park_list import park_list

from reserve_america.spiders.payload.post import park_post_body, campsit_post_body

class CampsiteSpider(CrawlSpider):
    name = 'campsite-ca'

    url = 'https://www.reservecalifornia.com/CaliforniaWebHome/Facilities/AdvanceSearch.aspx/GetGoogleMapPlaceData'
    url_campsite = 'https://www.reservecalifornia.com/CaliforniaWebHome/Facilities/AdvanceSearch.aspx/GetUnitGridDataHtmlString'
    reserve_url_template = 'https://www.reservecalifornia.com/CaliforniaWebHome/Facilities/UnitDetailPopup.aspx?facility_id=%d&unit_id=%d&arrival_date=%s 12:00:00 AM&dis=%s 12:00:00 AM&is_available=true&isunitnotavailable=0'

    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.basicConfig(
        level=logging.WARNING,
        format=
        '%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
        datefmt='%a, %d %b %Y %H:%M:%S',
        filename='reservation.log',
        filemode='w')

    scrawl_parks = park_list

    STATUSES = {
        'a': 'a',
        'w': 'w',
        'r': 'r',
        'x': 'x'
    }

    def __init__(self, *args, **kwargs):
        self.first_date = self.__offset_date(datetime.datetime.today(), 2)
        self.cookie_index = 0
        super(CampsiteSpider, self).__init__(*args, **kwargs)

    def __get_status(self, status):
        try:
            return self.STATUSES[status.lower()]
        except:
            # default return reserve
            return self.STATUSES['r']

    def __offset_date(self, date, offset):
        return date + datetime.timedelta(days=offset)

    def get_data_from_url(self, url):
        queries = parse_qs(urlparse(url).query, keep_blank_values=True)
        return {
            "parkId": queries['parkId'][0],
            "contractCode": queries['contractCode'][0],
            "siteId": queries['siteId'][0]
        }

    def parse_park(self, response):
        # f = open('receives/park.json', 'w')
        # get park string
        park = codecs.decode(response.body, 'utf8')
        # convert json string to JSon
        park_dict = json.loads(park)

        facility_infos = park_dict['d']['ListJsonPlaceInfos'][0]['JsonFacilityInfos']

        # get each campsite group
        while len(facility_infos):
            facility = facility_infos.pop()
            campsit_post_body['FacilityId'] = facility['FacilityId']
            campsit_post_body['PlaceId'] = facility['PlaceId']
            # get campsites in each campsite group
            yield Request(url=self.url_campsite, method="POST", meta={'cookiejar': 1, 'FacilityId':facility['FacilityId'], 'PlaceId':facility['PlaceId']}, body=json.dumps(campsit_post_body),
                          headers={'Content-Type': 'application/json'},
                          callback=self.parse_campsite_list)
        # f.write(json.dumps(park_dict))
        # f.close()

    def parse_campsite_list(self, response):
        html_url = ('receives/%d_%d.html' % (response.meta['PlaceId'], response.meta['FacilityId']))
        # f = open(html_url, 'w')
        campsite_page = codecs.decode(response.body, 'utf8')
        campsite_page_dict = json.loads(campsite_page)
        htmlBody = campsite_page_dict['d']
        html = HtmlResponse(url= html_url, encoding='utf-8', body=htmlBody)

        sites = html.xpath('//table/tr[@class="unitdata"]')
        all_reservations = []
        for site in sites:
            reservationLinks = site.xpath('//td/@onclick').extract()
            reservations = self.parse_campsite(reservationLinks, response.meta['PlaceId'], response.meta['FacilityId'])
            all_reservations = all_reservations + reservations

        while len(all_reservations):
            yield all_reservations.pop()

        # f.write(htmlBody)
        # f.close()

    def parse_campsite(self, reservationLinks, park_id, facility_id):
        reservations = []
        index = 0
        while index < len(reservationLinks):
            reservationItem = ReservationItem()
            link = reservationLinks[index]
            # if HTMLParser:
            #     # For python 2.x
            #     link = HTMLParser().unescape(link)
            # else:
            #     # For python 3.x
            link = html.unescape(link)
            reservationItem['siteId'] = re.search('unit_id=([^\'&,\s]+)', link).group(1)
            reservationItem['date'] = re.search('arrival_date=([^\'&,\s]+)', link).group(1)
            reservationItem['weekday'] = datetime.datetime.strptime(reservationItem['date'], "%m/%d/%Y").date().weekday()
            id = '%s::%s::%s::%s::%s' % (park_id, 'ca', facility_id, reservationItem['siteId'], reservationItem['date'])
            reservationItem['_id'] = id
            reservationItem['facilityId'] = facility_id
            reservationItem['parkId'] = park_id
            reservationItem['contractCode'] = 'CA'
            reservationItem['lastModified'] = datetime.datetime.now().isoformat()
            is_available = re.search('is_available=([^\'&,\s]+)', link).group(1)
            if is_available == 'false':
                reservationItem['status'] = self.__get_status('r')
            else:
                reservationItem['status'] = self.__get_status('a')
                # reservationItem['url'] =
            reservations.append(reservationItem)
            index = index + 1
        return reservations

    def step1(self, response):
        yield Request(url=self.url, method="POST", meta={'cookiejar': 1}, body=json.dumps(park_post_body), headers={'Content-Type': 'application/json'},
                          callback=self.parse_park)

    def start_requests(self):
        yield Request(url='https://www.reservecalifornia.com/CaliforniaWebHome/Facilities/AdvanceSearch.aspx/GetGoogleMapPlaceData', meta={'cookiejar': 1}, callback=self.step1)


