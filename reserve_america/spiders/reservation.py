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

from reserve_america.items import ReservationItem
from reserve_america.park_list import park_list

class ReservationSpider(CrawlSpider):
    name = 'reservation'

    url_template = 'https://www.reserveamerica.com/campsiteCalendar.do?page=calendar&contractCode=%s&parkId=%d&calarvdate=%s&sitepage=true&startIdx=0'

    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.basicConfig(
        level=logging.WARNING,
        format=
        '%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
        datefmt='%a, %d %b %Y %H:%M:%S',
        filename='reservation.log',
        filemode='w')

    scrawl_parks = park_list

    # All available status for a site, immutable dict
    STATUSES = {
        'a': 'a',
        'w': 'w',
        'r': 'r',
        'x': 'x'
    }
    # css selectors used to extract information from html page
    SELECTORS = {
        'site_items': '#calendar tbody tr:not(.separator)',
        'site_info': 'td',
        'site_mark_title': 'a.sitemarker img::attr(title)',
        'site_list_label_href': 'div.siteListLabel a::attr(href)',
        'site_list_label_text': 'div.siteListLabel a::text',
        'site_loop_text': 'div.loopName::text',
        'site_available_href': 'a::attr(href)',
        'next_campsite_list': '#calendar thead tr td span.pagenav',
        'next_2_weeks': '#calendar thead tr td.week2'
    }

    def __init__(self, *args, **kwargs):
        self.first_date = self.__offset_date(datetime.datetime.today(), 2)
        self.cookie_index = 0
        # self.times = 3
        super(ReservationSpider, self).__init__(*args, **kwargs)

    def __merge_list(self, source_list, target_list):
        """
        merge two list, and return merged list. make sure you pass list not other type
        :param source_list: list want to be merged from
        :param target_list: list want to be merged to
        :return: merged list
        """
        target_list = target_list + source_list
        return target_list

    def __merge_dict(self, source_dict, target_dict):
        """
        merge two dict, and return merged dict. Make sure you pass dict not other type
        :param source_dict: dict want to be merged from
        :param target_dict: dict want to be merged to
        :return: merged dict
        """
        source_items = source_dict.items()
        for (key, value) in source_items:
            # target dict also have this key
            if key in target_dict:
                # for this key, value type is same
                if type(value) == type(target_dict[key]):
                    # if type is dict, continue to call __merge_dict
                    if isinstance(value, dict):
                        target_dict[key] = self.__merge_dict(value, target_dict[key])
                    # if type is list, call __merge_list
                    elif isinstance(value, list):
                        target_dict[key] = self.__merge_list(value, target_dict[key])
                    # for other type, use source to overwrite target
                    else:
                        target_dict[key] = value
                # for this key, value type is difference. then use source to overwrite target
                else:
                    target_dict[key] = value
            # target dict don't have this key, then add key value from source
            else:
                target_dict[key] = value
        return target_dict

    def __get_status(self, stas):
        try:
            return self.STATUSES[stas.lower()]
        except:
            # default return reserve
            return self.STATUSES['r']

    def __offset_date(self, date, offset):
        return date + datetime.timedelta(days=offset)

    def __date_string(self, date, date_format):
        """
        return a date string with format, default format is '%m/%d/%Y'
        :param date: date want to be transfer
        :param date_format: data format want to use, default is '%m/%d/%Y'
        :return:
        """
        if not date_format:
            date_format = '%m/%d/%Y'
        return date.strftime(date_format)

    def get_calarvdate_from_url(self, url):
        queries = parse_qs(urlparse(url).query, keep_blank_values=True)
        return queries['calarvdate']

    def has_next_campsite_list(self, response):
        """
        Whether still has more campsite list
        :param response:
        :return: url
        """
        url = response.xpath('//table[@id=\'calendar\']/thead/tr/td/span/a[contains(@id, "Next")]/@href').extract_first()
        if url:
            url = 'https://www.reserveamerica.com'+url

        return url

    def has_next_2_weeks(self, response):
        url = response.xpath('//table[@id=\'calendar\']/thead/tr/td/a[contains(@id, "nextWeek")]/@href').extract_first()
        if url:
            url = 'https://www.reserveamerica.com'+url+'&startIdx=0'
        return url

    def parse_2_weeks(self, response):
        """
        Parse current two weeks's campsite list. It will parse all campsite list page by page
        :param response:
        :return:
        """
        reservationItems = self.parse_campsite_list(response)

        while len(reservationItems):
            yield reservationItems.pop()

        next_2_weeks_url = self.has_next_2_weeks(response)
        next_campsite_list_url = self.has_next_campsite_list(response)

        if next_campsite_list_url:
            logging.debug("+++++++++++++[parse_next_campsite_list] next_campsite_list_url: %s", next_campsite_list_url)
            calarvdate = self.get_calarvdate_from_url(next_campsite_list_url)
            yield Request(url=next_campsite_list_url, callback=self.parse_next_campsite_list, dont_filter=True, meta={'cookiejar': self.cookie_index, 'index':self.cookie_index, 'first_date':calarvdate})
        else:
            yield None

        # if next_2_weeks_url and self.times:
        if next_2_weeks_url:
            logging.debug("=============[parse_2_weeks] next_2_weeks_url: %s", next_2_weeks_url)
            self.cookie_index = self.cookie_index + 1
            calarvdate = self.get_calarvdate_from_url(next_2_weeks_url)
            # self.times = self.times -1
            yield Request(url=next_2_weeks_url, callback=self.parse_2_weeks, dont_filter=True, meta={'cookiejar': self.cookie_index, 'first_date':calarvdate})
        else:
            logging.debug("*************[parse_2_weeks] no more next week")
            yield None

    def parse_next_campsite_list(self, response):
        reservationItems = self.parse_campsite_list(response)

        while len(reservationItems):
            yield reservationItems.pop()

        next_campsite_list_url = self.has_next_campsite_list(response)

        if next_campsite_list_url:
            logging.debug("+++++++++++++[parse_next_campsite_list] next_campsite_list_url: %s", next_campsite_list_url)
            calarvdate = self.get_calarvdate_from_url(next_campsite_list_url)
            yield Request(url=next_campsite_list_url, callback=self.parse_next_campsite_list, dont_filter=True, meta={'cookiejar': response.meta['index'], 'index': response.meta['index'], 'first_date':calarvdate})
        else:
            logging.debug("?????????????[parse_next_campsite_list] no more campsite list")
            yield None

    def parse_campsite(self, tds, first_date):
        """
        parse a campsite reservation information
        :param tds: td selector list
        :param first_date: first date of this list
        :return:

        """
        campsiteId = ''
        parkId = ''
        contractCode = ''
        reservations = []
        for index, td in enumerate(tds):
            # first item is site's information
            if index == 0:
                url = td.css(self.SELECTORS['site_list_label_href']).extract_first()
                queries = parse_qs(urlparse(url).query, keep_blank_values=True)
                campsiteId = queries['siteId'][0]
                parkId = queries['parkId'][0]
                contractCode = queries['contractCode'][0]
            # second item is site's loop
            elif index == 1:
                loop = td.css(self.SELECTORS['site_loop_text']).extract_first()

        index = 2
        while index < len(tds):
            reservationItem = ReservationItem()
            reservationItem['campsiteId'] = campsiteId
            reservationItem['parkId'] = parkId
            reservationItem['contractCode'] = contractCode
            td = tds[index]
            # reservation information
            date_str = self.__date_string(self.__offset_date(first_date, index - 2), '')
            url = td.css(self.SELECTORS['site_available_href']).extract_first()
            reservationItem['date'] = date_str
            if url:
                # this date is available for book
                reservationItem['status'] = self.__get_status('a')
                reservationItem['url'] = url
            else:
                status = td.css('::text').extract_first()
                reservationItem['status'] = self.__get_status(status)
            id = '%s::%s::%s::%s' % (parkId, contractCode, campsiteId, date_str)
            reservationItem['_id'] = id
            reservationItem['lastModified'] = datetime.datetime.now().isoformat()
            reservations.append(reservationItem)
            index = index + 1

        return reservations

    def parse_campsite_list(self, response):
        """
        Parse current campsite list one by one and generate reservation data

        :param response:
        :return:
        """

        # traverse all sites in currently get page
        sites = response.css(self.SELECTORS['site_items'])
        # each site is one tr
        all_reservations = []
        for site in sites:
            site_info = site.css(self.SELECTORS['site_info'])
            reservations = self.parse_campsite(site_info, datetime.datetime.strptime(response.meta['first_date'][0], "%m/%d/%Y").date())
            all_reservations = all_reservations+reservations

        # logging.debug("!!!!!!!!!!!all_reservations: %s", all_reservations)
        return all_reservations

    def start_requests(self):
        while len(self.scrawl_parks):
            park = self.scrawl_parks.pop()
            park_url = self.url_template % (park['contractCode'], park['parkId'], self.first_date.strftime('%m/%d/%Y'))
            logging.debug("=============[parse_2_weeks] next_2_weeks_url: %s", park_url)
            calarvdate = self.get_calarvdate_from_url(park_url)
            yield Request(url=park_url, callback=self.parse_2_weeks, dont_filter=True, meta={'cookiejar': self.cookie_index, 'first_date':calarvdate})
