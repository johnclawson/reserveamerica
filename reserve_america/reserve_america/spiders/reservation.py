# -*- coding: utf-8 -*-
import datetime
import json
from urllib.parse import urlparse, parse_qs
import logging

from scrapy.spiders import CrawlSpider
from scrapy.http import Request


class BigBasinSpider(CrawlSpider):
    name = 'reservation'

    url_template = 'https://www.reserveamerica.com/campsiteCalendar.do?page=calendar&contractCode=%s&parkId=%d&calarvdate=%s&sitepage=true&startIdx=0'

    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.basicConfig(
        level=logging.WARNING,
        format=
        '%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
        datefmt='%a, %d %b %Y %H:%M:%S',
        filename='scrapy.log',
        filemode='w')

    scrawl_parks = [
        {
            "contractCode": "CA",
            "parkId": 120009
        }
    ]

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

    def __init__(self, start_url='', *args, **kwargs):
        self.park = {}
        self.first_date = self.__offset_date(datetime.datetime.today(), 2)
        self.cookie_index = 0
        super(BigBasinSpider, self).__init__(*args, **kwargs)

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
        self.parse_campsite_list(response)

        next_2_weeks_url = self.has_next_2_weeks(response)
        next_campsite_list_url = self.has_next_campsite_list(response)

        if next_campsite_list_url:
            logging.warning("+++++++++++++[parse_next_campsite_list] next_campsite_list_url: %s", next_campsite_list_url)
            calarvdate = self.get_calarvdate_from_url(next_campsite_list_url)
            yield Request(url=next_campsite_list_url, callback=self.parse_next_campsite_list, dont_filter=True, meta={'cookiejar': self.cookie_index, 'index':self.cookie_index, 'first_date':calarvdate})
        else:
            yield None

        if next_2_weeks_url:
            logging.warning("=============[parse_2_weeks] next_2_weeks_url: %s", next_2_weeks_url)
            self.cookie_index = self.cookie_index + 1
            calarvdate = self.get_calarvdate_from_url(next_2_weeks_url)
            yield Request(url=next_2_weeks_url, callback=self.parse_2_weeks, dont_filter=True, meta={'cookiejar': self.cookie_index, 'first_date':calarvdate})
        else:
            logging.warning("*************[parse_2_weeks] no more next week")
            yield None

    def parse_next_campsite_list(self, response):
        self.parse_campsite_list(response)
        next_campsite_list_url = self.has_next_campsite_list(response)

        if next_campsite_list_url:
            logging.warning("+++++++++++++[parse_next_campsite_list] next_campsite_list_url: %s", next_campsite_list_url)
            calarvdate = self.get_calarvdate_from_url(next_campsite_list_url)
            yield Request(url=next_campsite_list_url, callback=self.parse_next_campsite_list, dont_filter=True, meta={'cookiejar': response.meta['index'], 'index': response.meta['index'], 'first_date':calarvdate})
        else:
            logging.warning("?????????????[parse_next_campsite_list] no more campsite list")
            yield None

    def parse_campsite(self, tds, first_date):
        """
        parse a campsite reservation information
        :param tds: td selector list
        :param first_date: first date of this list
        :return:
        {
            '120009': {
                '26702': {
                    id: '26702',
                    parkId: '120009',
                    contractCode: 'CA',
                    loop: '',
                    url: '/camping/Big_Basin_Redwoods_Sp/r/campsiteDetails.do?siteId=26702&contractCode=CA&parkId=120009',
                    name: '104B',
                    title: '104B , TENT ONLY SITE',
                    reservations: {
                        '07/29/2017': {
                            status: 'r'
                        },
                        '07/30/2017': {
                            status: 'a',
                            url: '/camping/Big_Basin_Redwoods_Sp/r/campsiteDetails.do?siteId=26702&contractCode=CA&parkId=120009&offset=0&arvdate=7/30/2017'
                        },
                        '07/31/2017': {
                            status: 'w'
                        },
                        '08/01/2017': {
                            status: 'x'
                        },
                        ...
                    }
                }
            }
        }
        """
        park = {}
        site = {
            'id': None,
            'parkId': None,
            'contractCode': None,
            'loop': None,
            'url': None,
            'name': None,
            'title': None,
            'reservations': {}
        }
        for index, td in enumerate(tds):
            # first item is site's information
            if index == 0:
                url = td.css(self.SELECTORS['site_list_label_href']).extract_first()
                queries = parse_qs(urlparse(url).query, keep_blank_values=True)
                site['id'] = queries['siteId'][0]
                site['parkId'] = queries['parkId'][0]
                site['contractCode'] = queries['contractCode'][0]
                site['title'] = td.css(self.SELECTORS['site_mark_title']).extract_first()
                site['name'] = td.css(self.SELECTORS['site_list_label_text']).extract_first()
                site['url'] = url
            # second item is site's loop
            elif index == 1:
                loop = td.css(self.SELECTORS['site_loop_text']).extract_first()
                site['loop'] = loop
            else:
                # reservation information
                date_str = self.__date_string(self.__offset_date(first_date, index - 2), '')
                url = td.css(self.SELECTORS['site_available_href']).extract_first()
                if url:
                    # this date is available for book
                    site['reservations'][date_str] = {
                        'status': self.__get_status('a'),
                        'url': url
                    }

                else:
                    status = td.css('::text').extract_first()
                    site['reservations'][date_str] = {
                        'status': self.__get_status(status)
                    }
        park[site['parkId']] = {}
        park[site['parkId']][site['id']] = site
        return park

    def parse_campsite_list(self, response):
        """
        Parse current campsite list one by one and generate reservation data

        :param response:
        :return:
        """

        """
        park information data
        {
            '120009':{
               '26702': {
                    id: '26702',
                    parkId: '120009',
                    contractCode: 'CA',
                    loop: '',
                    url: '/camping/Big_Basin_Redwoods_Sp/r/campsiteDetails.do?siteId=26702&contractCode=CA&parkId=120009',
                    name: '104B',
                    title: '104B , TENT ONLY SITE',
                    reservations: {
                        '07/29/2017': {
                            status: 'r'
                        },
                        '07/30/2017': {
                            status: 'a',
                            url: '/camping/Big_Basin_Redwoods_Sp/r/campsiteDetails.do?siteId=26702&contractCode=CA&parkId=120009&offset=0&arvdate=7/30/2017'
                        },
                        '07/31/2017': {
                            status: 'w'
                        },
                        '08/01/2017': {
                            status: 'x'
                        },
                        ...
                    }
                }
            }
        }
        """

        # traverse all sites in currently get page
        sites = response.css(self.SELECTORS['site_items'])
        # each site is one tr
        for site in sites:
            site_info = site.css(self.SELECTORS['site_info'])
            site_data = self.parse_campsite(site_info, datetime.datetime.strptime(response.meta['first_date'][0], "%m/%d/%Y").date())

            self.__merge_dict(site_data, self.park)

    def start_requests(self):
        while len(self.scrawl_parks):
            park = self.scrawl_parks.pop()
            park_url = self.url_template % (park['contractCode'], park['parkId'], self.first_date.strftime('%m/%d/%Y'))
            logging.warning("=============[parse_2_weeks] next_2_weeks_url: %s", park_url)
            calarvdate = self.get_calarvdate_from_url(park_url)
            yield Request(url=park_url, callback=self.parse_2_weeks, dont_filter=True, meta={'cookiejar': self.cookie_index, 'first_date':calarvdate})
