# -*- coding: utf-8 -*-
import datetime
import re
from urllib.parse import urlparse, parse_qs
import logging
from scrapy.spiders import CrawlSpider
from scrapy.http import Request, HtmlResponse, FormRequest

# Python 3
import html

import json
import codecs

from pydash import strings

from reserve_america.items import ReservationItem, ParkItem, CampsiteItem, CampsiteDetailItem
from reserve_america.park_list import park_list

from reserve_america.spiders.payload.post import park_post_body, one_campsite_post_body, advance_search_form


class CampsiteSpider(CrawlSpider):
    name = 'campsite-ca'

    url = 'https://www.reservecalifornia.com/CaliforniaWebHome/Facilities/AdvanceSearch.aspx/GetGoogleMapPlaceData'
    campsite_url = 'https://www.reservecalifornia.com/CaliforniaWebHome/Facilities/UnitDetailPopup.aspx?facility_id=%s&unit_id=%s&arrival_date=%s 12:00:00 AM&is_available=%s'
    advance_search_url = 'https://www.reservecalifornia.com/CaliforniaWebHome/Facilities/AdvanceSearch.aspx'
    url_template = 'https://www.reserveamerica.com/campsiteCalendar.do?page=calendar&contractCode=%s&parkId=%d&calarvdate=%s&sitepage=true&startIdx=0'
    # url_template = 'https://www.reserveamerica.com/campsiteCalendar.do?contractCode=%s&parkId=%d'
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

    def __init__(self, *args, **kwargs):
        self.first_date = self.__offset_date(datetime.datetime.today(), 2)
        self.cookie_index = 0
        super(CampsiteSpider, self).__init__(*args, **kwargs)

    def __offset_date(self, date, offset):
        return date + datetime.timedelta(days=offset)

    def parse_park(self, response):
        # f = open('receives/park.json', 'w')
        # get park string
        park = codecs.decode(response.body, 'utf8')
        # convert json string to JSon
        park_dict = json.loads(park)

        facility_infos = park_dict['d']['ListJsonPlaceInfos'][0]['JsonFacilityInfos']

        yield FormRequest(url=self.advance_search_url, formdata=advance_search_form, callback=self.parse_advance_post)

        # get each campsite group
        # while len(facility_infos):
        #     facility = facility_infos.pop()
        #     one_campsite_post_body['FacilityId'] = facility['FacilityId']
        #     one_campsite_post_body['PlaceId'] = facility['PlaceId']
        #     # get campsites in each campsite group
        #     yield Request(url=self.url_campsite, method="POST", meta={'cookiejar': 1, 'FacilityId':facility['FacilityId'], 'PlaceId':facility['PlaceId']}, body=json.dumps(campsit_post_body),
        #                   headers={'Content-Type': 'application/json'},
        #                   callback=self.parse_campsite_list)

    def parse_advance_post(self, response):
        f = open('result_3.html', 'w')
        # f.write(str(response.body))
        f.write(codecs.decode(response.body, 'utf8'))
        f.close()
        pass

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

    def step_1(self, response):
        yield Request(url=self.url, method="POST", meta={'cookiejar': 1}, body=json.dumps(park_post_body),
                      headers={'Content-Type': 'application/json'},
                      callback=self.parse_park)

    def start_requests(self):
        yield Request(url='https://www.reservecalifornia.com/CaliforniaWebHome/Facilities/AdvanceSearch.aspx/GetGoogleMapPlaceData', meta={'cookiejar': 1}, callback=self.step_1)
