# -*- coding: utf-8 -*-
import datetime
import re
import logging
from scrapy.spiders import CrawlSpider
from scrapy.http import Request, FormRequest, HtmlResponse
# Python 3
import html
import shutil
import os
import json
import codecs
from pydash import strings

from reserve_america.items import ReservationItem, ParkItem, CampsiteItem, CampsiteDetailItem
from reserve_america.data_mapping import equal_campsite_detail_keys
from reserve_america.park_list import ca_park_list
from reserve_america.utils import unique_url
from reserve_america.spiders.payload.post import park_post_body, campsites_reservations_post_body, post_body_park_info_by_name, advance_search_form, web_home, set_night_by_place_id_and_facility_id_on_unit_grid


class CampsiteSpider(CrawlSpider):
    name = 'reserve_california'

    # step 1: load default page. Create session Id. GET
    url_default = 'https://www.reservecalifornia.com/CaliforniaWebHome/Default.aspx'
    # step 2: use park name to get park information. POST
    url_get_park_info_by_name = 'https://www.reservecalifornia.com/CaliforniaWebHome/Facilities/AdvanceSearch.aspx/GetCityPlacename'
    # step 3: simulate click Go button
    url_webhome = 'https://www.reservecalifornia.com/CaliforniaWebHome/'
    # step 4: click reserve button for this park, first set night by placeId and facilityId
    url_set_by_place_id_facility_id = 'https://www.reservecalifornia.com/CaliforniaWebHome/Facilities/AdvanceSearch.aspx/SetNightByPlaceIdAndFacilityIdOnUnitGrid'
    # step 5: click reserve button for this park, second set
    url_get_google_map_place_data = 'https://www.reservecalifornia.com/CaliforniaWebHome/Facilities/AdvanceSearch.aspx/GetGoogleMapPlaceData'
    # step 6: get campsite information by click facility.
    url_advance_search = 'https://www.reservecalifornia.com/CaliforniaWebHome/Facilities/AdvanceSearch.aspx'
    # step 7: get campsite information
    url_template_campsite = 'https://www.reservecalifornia.com/CaliforniaWebHome/Facilities/UnitDetailPopup.aspx?facility_id=%s&unit_id=%s&arrival_date=%s 12:00:00 AM&is_available=%s'

    url_campsites_reservations = 'https://www.reservecalifornia.com/CaliforniaWebHome/Facilities/AdvanceSearch.aspx/GetUnitGridDataHtmlString'

    # logging.getLogger("requests").setLevel(logging.WARNING)
    # logging.basicConfig(
    #     level=logging.WARNING,
    #     format=
    #     '%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
    #     datefmt='%a, %d %b %Y %H:%M:%S',
    #     filename='reserve_california.log',
    #     filemode='w')

    scrawl_parks = ca_park_list

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
        except Exception:
            # default return reserve
            return self.STATUSES['r']

    def __offset_date(self, date, offset):
        return date + datetime.timedelta(days=offset)

    def get_env(self, key):
        try:
            return os.environ[key]
        except Exception:
            return None

    def parse_park(self, response):
        self.save_park_json(response)
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

        # get each campsite group
        while len(facility_infos):
            facility = facility_infos.pop()

            body = set_night_by_place_id_and_facility_id_on_unit_grid.copy()
            body['placeId'] = facility['PlaceId']
            body['facilityId'] = facility['FacilityId']
            self.cookie_index = self.cookie_index + 1
            # step 4: click reserve button, first set night by place id and facility id
            yield Request(url=unique_url(self.url_set_by_place_id_facility_id),
                          method="POST",
                          body=json.dumps(body),
                          meta={'cookiejar': self.cookie_index,
                                'FacilityId': facility['FacilityId'],
                                'PlaceId': facility['PlaceId']},
                          dont_filter=True,
                          headers={'Content-Type': 'application/json; charset=UTF-8'},
                          callback=self.after_set_park_facility
                          )

            campsite_list_body = campsites_reservations_post_body.copy()
            campsite_list_body['FacilityId'] = facility['FacilityId']
            campsite_list_body['PlaceId'] = facility['PlaceId']
            # step 7: get campsites reservations in each campsite group
            # yield Request(url=unique_url(self.url_campsites_reservations),
            yield Request(url=unique_url(self.url_campsites_reservations),
                          method="POST",
                          meta={'cookiejar': response.meta['cookiejar'],
                                'FacilityId': facility['FacilityId'],
                                'PlaceId': facility['PlaceId']},
                          body=json.dumps(campsite_list_body),
                          dont_filter=True,
                          headers={'Content-Type': 'application/json'},
                          callback=self.parse_campsites_reservations)

    def after_set_park_facility(self, response):
        # step 6: get campsites by click facility
        date_str = self.first_date.strftime('%m/%d/%Y')
        form_data = advance_search_form.copy()
        form_data['ctl01$mainContent$hdnFacilityid'] = str(response.meta['FacilityId'])
        form_data['ctl01$mainContent$hdnPlaceid'] = str(response.meta['PlaceId'])
        form_data['ctl01$mainContent$txtDateRange'] = date_str
        yield FormRequest(url=unique_url(self.url_advance_search),
                          meta={'cookiejar': response.meta['cookiejar'],
                                'FacilityId': response.meta['FacilityId'],
                                'PlaceId': response.meta['PlaceId']},
                          formdata=form_data,
                          callback=self.parse_campsite_list)

    def parse_campsites_reservations(self, response):
        html_url = ('receives/result_rs_%s_%s.html' % (str(response.meta['PlaceId']), str(response.meta['FacilityId'])))
        campsite_page = codecs.decode(response.body, 'utf8')
        campsite_page_dict = json.loads(campsite_page)
        html_body = campsite_page_dict['d']
        html = HtmlResponse(url= html_url, encoding='utf-8', body=html_body)
        sites = html.xpath('//table/tr[@class="unitdata"]')
        if len(sites):
            self.save_reservations_html(html, str(response.meta['PlaceId']), str(response.meta['FacilityId']))
        all_reservations = []
        for site in sites:
            reservation_links = site.xpath('//td/@onclick').extract()
            reservations = self.parse_a_campsite_reservations(reservation_links, response.meta['PlaceId'], response.meta['FacilityId'])
            all_reservations = all_reservations + reservations

        while len(all_reservations):
            yield all_reservations.pop()

    def parse_a_campsite_reservations(self, reservation_links, park_id, facility_id):
        reservations = []
        index = 0
        while index < len(reservation_links):
            reservation_item = ReservationItem()
            link = reservation_links[index]
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
                # reservation_item['url'] =
            reservations.append(reservation_item)
            index = index + 1
        return reservations

    def save_reservations_html(self, response, place_id, facility_id):
        if not self.get_env("DEBUG"):
            return
        url = ('receives/result_reservations_%s_%s.html' % (place_id, facility_id))
        f = open(url, 'w')
        f.write(codecs.decode(response.body, 'utf8'))
        f.close()

    def save_campsite_list_html(self, response):
        if not self.get_env("DEBUG"):
            return
        url = ('receives/result_campsites_%s_%s.html' % (str(response.meta['PlaceId']), str(response.meta['FacilityId'])))
        f = open(url, 'w')
        # f.write(str(response.body))
        f.write(codecs.decode(response.body, 'utf8'))
        f.close()

    def save_park_json(self, response):
        if not self.get_env("DEBUG"):
            return
        # get park string
        park = codecs.decode(response.body, 'utf8')
        # convert json string to JSon
        park_dict = json.loads(park)
        url = 'receives/result_park_%s.json' % str(park_dict['d']['ListJsonPlaceInfos'][0]['PlaceId'])
        f = open(url, 'w')
        f.write(json.dumps(park_dict))
        f.close()

    def parse_campsite_list(self, response):
        self.save_campsite_list_html(response)
        sites = response.xpath('//div[@id="divUnitGridlist"]/div/table/tr[@class="unitdata"]/td[2]/@onclick').extract()
        for link in sites:
            reservation_item = self.parse_campsite_from_url_link(link,
                                                                 response.meta['PlaceId'],
                                                                 response.meta['FacilityId'])
            is_available = False
            if reservation_item['status'] == 'a':
                is_available = True

            url = self.url_template_campsite % (reservation_item['facilityId'],
                                                reservation_item['siteId'],
                                                reservation_item['date'],
                                                is_available)
            # step 7: get each campsite information
            yield Request(
                url=unique_url(url),
                meta={'cookiejar': response.meta['cookiejar'],
                      'FacilityId': response.meta['FacilityId'],
                      'PlaceId': response.meta['PlaceId'],
                      'SiteId': reservation_item['siteId']},
                dont_filter=True,
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
        park = response.meta['park']
        body = park_post_body.copy()
        body['googlePlaceSearchParameters']['Latitude'] = str(park['Latitude'])
        body['googlePlaceSearchParameters']['Longitude'] = str(park['Longitude'])
        body['googlePlaceSearchParameters']['MapboxPlaceid'] = str(park['CityParkId'])
        # step 5: click reserve button, get google map place data
        yield Request(url=unique_url(self.url_get_google_map_place_data),
                      method="POST",
                      meta={'cookiejar': response.meta['cookiejar']},
                      body=json.dumps(body),
                      headers={'Content-Type': 'application/json; charset=UTF-8'},
                      dont_filter=True,
                      callback=self.parse_park)

    def set_select_park(self, response):
        body = codecs.decode(response.body, 'utf8')
        parks = json.loads(body)
        park = parks['d'][0]
        body = web_home.copy()
        date_str = self.first_date.strftime('%m/%d/%Y')
        body['ctl00$ctl00$mainContent$txtArrivalDate'] = date_str
        body['ctl00$ctl00$mainContent$hdnMasterPlaceId'] = str(park['CityParkId'])
        # step 3: set select park
        yield FormRequest(url=unique_url(self.url_webhome),
                          meta={'cookiejar': response.meta['cookiejar'],
                            'park':park},
                          method="POST",
                          formdata=body,
                          dont_filter=True,
                          callback=self.home_page)

    def index_page(self,response):
        body = post_body_park_info_by_name.copy()
        body['name'] = response.meta['parkName']
        # step 2: use park name get park information
        yield Request(url=unique_url(self.url_get_park_info_by_name),
                      meta={'cookiejar': response.meta['cookiejar']},
                      method="POST",
                      body=json.dumps(body),
                      headers={'Content-Type': 'application/json; charset=UTF-8'},
                      dont_filter=True,
                      callback=self.set_select_park)

    def start_requests(self):
        if self.get_env("DEBUG"):
            receives_dir = './receives'
            if os.path.exists(receives_dir):
                shutil.rmtree(receives_dir)
            os.makedirs(receives_dir)

        while len(self.scrawl_parks):
            park = self.scrawl_parks.pop()
            # step 1: Go to reserve california home page
            yield Request(url=unique_url(self.url_default),
                          meta={
                              'cookiejar': self.cookie_index,
                              'parkName': park['name']
                          },
                          dont_filter=True,
                          callback=self.index_page)
            self.cookie_index = self.cookie_index + 1

