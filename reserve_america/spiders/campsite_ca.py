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
from reserve_america.data_mapping import equal_campsite_detail_keys
from reserve_america.park_list import park_list

from reserve_america.spiders.payload.post import park_post_body, one_campsite_post_body, advance_search_form


class CampsiteSpider(CrawlSpider):
    name = 'campsite-ca'

    url = 'https://www.reservecalifornia.com/CaliforniaWebHome/Facilities/AdvanceSearch.aspx/GetGoogleMapPlaceData'
    campsite_url_template = 'https://www.reservecalifornia.com/CaliforniaWebHome/Facilities/UnitDetailPopup.aspx?facility_id=%s&unit_id=%s&arrival_date=%s 12:00:00 AM&is_available=%s'
    advance_search_url = 'https://www.reservecalifornia.com/CaliforniaWebHome/Facilities/AdvanceSearch.aspx'
    url_template = 'https://www.reserveamerica.com/campsiteCalendar.do?page=calendar&contractCode=%s&parkId=%d&calarvdate=%s&sitepage=true&startIdx=0'
    # url_template = 'https://www.reserveamerica.com/campsiteCalendar.do?contractCode=%s&parkId=%d'
    reserve_url_template = 'https://www.reservecalifornia.com/CaliforniaWebHome/Facilities/UnitDetailPopup.aspx?facility_id=%d&unit_id=%d&arrival_date=%s 12:00:00 AM&dis=%s 12:00:00 AM&is_available=true'

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

    def parse_park(self, response):
        # self.save_park_json(response)
        # get park string
        park = codecs.decode(response.body, 'utf8')
        # convert json string to JSon
        park_dict = json.loads(park)

        park_info = park_dict['d']['ListJsonPlaceInfos'][0]

        # parse park information
        park_item = ParkItem()
        park_item['name'] = park_info["Name"]
        park_item['parkId'] = park_info["PlaceId"]
        park_item['contractCode'] = "ca"
        park_item['_id'] = '%s::%s' % (park_item['parkId'], park_item['contractCode'])
        park_item['url'] = park_info["PlaceinfoUrl"]
        park_item['services'] = park_info["AllHightlights"].split(",")

        yield park_item

        facility_infos = park_info['JsonFacilityInfos']

        # yield FormRequest(url=self.advance_search_url, formdata=advance_search_form, callback=self.parse_advance_post)

        # get each campsite group
        while len(facility_infos):
            self.cookie_index = self.cookie_index + 1
            facility = facility_infos.pop()
            date_str = self.first_date.strftime('%m/%d/%Y')
            advance_search_form['ctl01$mainContent$hdnFacilityid'] = str(facility['FacilityId'])
            advance_search_form['ctl01$mainContent$hdnPlaceid'] = str(facility['PlaceId'])
            advance_search_form['ctl01$AdvanceMainSearch$hdnArrivalDate'] = date_str
            advance_search_form['ctl01$AdvanceMainSearch$txtArrivalDate'] = date_str
            advance_search_form['ctl01$mainContent$txtDateRange'] = date_str
            advance_search_form['ctl01$mainContent$TopMenuMainSearch$txtTopArrivalDate'] = date_str
            yield FormRequest(url=self.advance_search_url,
                              meta={'cookiejar': self.cookie_index,
                                    'cookieIndex': self.cookie_index,
                                    'FacilityId': facility['FacilityId'],
                                    'PlaceId': facility['PlaceId']},
                              formdata=advance_search_form,
                              callback=self.parse_campsite_list)
            # get campsites in each campsite group
            # yield Request(url=self.url_campsite, method="POST", meta={'cookiejar': 1, 'FacilityId':facility['FacilityId'], 'PlaceId':facility['PlaceId']}, body=json.dumps(campsit_post_body),
            #               headers={'Content-Type': 'application/json'},
            #               callback=self.parse_campsite_list)

    def save_campsite_list_html(self, response):
        url = ('receives/result_campsites_%d_%d.html' % (response.meta['PlaceId'], response.meta['FacilityId']))
        f = open(url, 'w')
        # f.write(str(response.body))
        f.write(codecs.decode(response.body, 'utf8'))
        f.close()

    def save_park_json(self, response):
        # get park string
        park = codecs.decode(response.body, 'utf8')
        # convert json string to JSon
        park_dict = json.loads(park)
        url = 'receives/result_park_%d.json' % park_dict['d']['ListJsonPlaceInfos'][0]['PlaceId']
        f = open(url, 'w')
        f.write(json.dumps(park_dict))
        f.close()

    def parse_campsite_list(self, response):
        # self.save_campsite_list_html(response)
        sites = response.xpath('//div[@id="divUnitGridlist"]/div/table/tr[@class="unitdata"]/td[2]/@onclick').extract()
        for link in sites:
            reservation_item = self.parse_campsite_from_url_link(link,
                                                                 response.meta['PlaceId'],
                                                                 response.meta['FacilityId'])
            is_available = False
            if reservation_item['status'] == 'a':
                is_available = True

            url = self.campsite_url_template % (reservation_item['facilityId'],
                                                reservation_item['siteId'],
                                                reservation_item['date'],
                                                is_available)
            yield Request(
                url=url,
                meta={'cookiejar': response.meta['cookieIndex'],
                      'cookieIndex': response.meta['cookieIndex'],
                      'FacilityId': response.meta['FacilityId'],
                      'PlaceId': response.meta['PlaceId'],
                      'SiteId': reservation_item['siteId']},
                callback=self.parse_campsite)

    def parse_campsite(self, response):
        campsite_item = CampsiteItem()
        campsite_item['_id'] = '%s::%s::%s::%s' % (response.meta['PlaceId'], response.meta['FacilityId'], 'ca', response.meta['SiteId'])
        campsite_item['parkId'] = response.meta['PlaceId']
        campsite_item['facilityId'] = response.meta['FacilityId']
        campsite_item['contractCode'] = 'ca'
        campsite_item['siteId'] = response.meta['SiteId']
        campsite_item['name'] = response.xpath('//div[@class="popup-heading"]/strong/text()').extract_first()
        campsite_item['url'] = ''
        campsite_item['detail'] = self.parse_campsite_detail(response)
        yield campsite_item

    def parse_campsite_detail(self, response):
        campsite_detail_item = CampsiteDetailItem()
        campsite_detail_item['unknown'] = {}
        campsite_detail_units = response.xpath('//div[@id="divMobileunit"]/p')
        # parse unit detail
        while len(campsite_detail_units):
            unit = campsite_detail_units.pop()
            key = unit.xpath('text()').extract_first()
            value = unit.xpath('b/text()').extract_first()
            key = strings.snake_case(key)
            if key in campsite_detail_item.fields:
                campsite_detail_item[key] = value
            elif key in equal_campsite_detail_keys:
                campsite_detail_item[equal_campsite_detail_keys[key]] = value
            else:
                campsite_detail_item['unknown'][key] = value

        # parse Amenities
        campsite_detail_amenities = response.xpath('//div[@id="pnlAmenities"]/ul/li')
        while len(campsite_detail_amenities):
            amenity = campsite_detail_amenities.pop()
            key = amenity.xpath('text()').extract_first()
            value = amenity.xpath('b/text()').extract_first()
            key = strings.snake_case(key)
            if key in campsite_detail_item.fields:
                campsite_detail_item[key] = value
            elif key in equal_campsite_detail_keys:
                campsite_detail_item[equal_campsite_detail_keys[key]] = value
            else:
                campsite_detail_item['unknown'][key] = value
        return campsite_detail_item

    def parse_campsite_from_url_link(self, link, park_id, facility_id):
        reservation_item = ReservationItem()
        link = html.unescape(link)
        reservation_item['siteId'] = re.search('unit_id=([^\'&,\s]+)', link).group(1)
        reservation_item['date'] = re.search('arrival_date=([^\'&,\s]+)', link).group(1)
        reservation_item['weekday'] = datetime.datetime.strptime(reservation_item['date'], "%m/%d/%Y").date().weekday()
        id = '%s::%s::%s::%s::%s' % (park_id, 'ca', facility_id, reservation_item['siteId'], reservation_item['date'])
        reservation_item['_id'] = id
        reservation_item['facilityId'] = facility_id
        reservation_item['parkId'] = park_id
        reservation_item['contractCode'] = 'CA'
        reservation_item['lastModified'] = datetime.datetime.now().isoformat()
        is_available = re.search('is_available=([^\'&,\s]+)', link).group(1)
        if is_available == 'false':
            reservation_item['status'] = self.__get_status('r')
        else:
            reservation_item['status'] = self.__get_status('a')

        return reservation_item

    def home_page(self, response):
        yield Request(url=self.url, method="POST", meta={'cookiejar': 1}, body=json.dumps(park_post_body),
                      headers={'Content-Type': 'application/json'},
                      callback=self.parse_park)

    def start_requests(self):
        yield Request(url='https://www.reservecalifornia.com/CaliforniaWebHome/Facilities/AdvanceSearch.aspx/GetGoogleMapPlaceData',
                      meta={'cookiejar': 1},
                      callback=self.home_page)
