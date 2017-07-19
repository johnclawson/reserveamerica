# -*- coding: utf-8 -*-
import scrapy
import datetime
import json
from urllib.parse import urlparse, parse_qs


class BigBasinSpider(scrapy.Spider):
    name = 'big_basin'

    # CONST
    # JSON file store extract information for all parks
    PARKS = 'parks.json'
    # JSON file store extract information for all reservations
    RESERVATIONS = 'reservations.json'
    # All available status for a site, immutable dict
    STATUSES = {
        'a': 'a',
        'w': 'w',
        'r': 'r',
        'x': 'x'
    }
    # css selectors used to extract information from html page
    SELECTORS = {
        'siteItems': '#calendar tbody tr:not(.separator)',
        'siteInfo': 'td',
        'siteMarkTitle': 'a.sitemarker img::attr(title)',
        'siteListLabelHref': 'div.siteListLabel a::attr(href)',
        'siteListLabelText': 'div.siteListLabel a::text',
        'siteLoopText': 'div.loopName::text',
        'siteAvailableHref': 'a::attr(href)'
    }

    first_date = datetime.datetime.strptime('07/29/2017', "%m/%d/%Y").date()

    # start url is configurable
    start_urls = [
        'https://www.reserveamerica.com/campsiteCalendar.do'
        '?page=calendar'
        '&contractCode=CA'
        '&parkId=120009'
        '&calarvdate=07/29/2017'
        '&sitepage=true'
        '&startIdx=0'
    ]

    def __merge_list(self, source_list, target_list):
        """
        merge two list, and return merged list. make sure you pass list not other type
        :param source_list: list want to be merged from
        :param target_list: list want to be merged to
        :return: merged list
        """
        target_list = target_list+source_list
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

    def __parse_sites_pages(self, response):
        return self.__parse_sites_page(response)

    def __parse_site(self, tds, first_date):
        """
        parse a site reservation information
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
                url = td.css(self.SELECTORS['siteListLabelHref']).extract_first()
                queries = parse_qs(urlparse(url).query, keep_blank_values=True)
                site['id'] = queries['siteId'][0]
                site['parkId'] = queries['parkId'][0]
                site['contractCode'] = queries['contractCode'][0]
                site['title'] = td.css(self.SELECTORS['siteMarkTitle']).extract_first()
                site['name'] = td.css(self.SELECTORS['siteListLabelText']).extract_first()
                site['url'] = url
            # second item is site's loop
            elif index == 1:
                loop = td.css(self.SELECTORS['siteLoopText']).extract_first()
                site['loop'] = loop
            else:
            # reservation information
                date_str = self.__date_string(self.__offset_date(first_date, index - 2))
                url = td.css(self.SELECTORS['siteAvailableHref']).extract_first()
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

    def __parse_sites_page(self, response):
        """
        Parse Reserve America Page to a JSON data

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
        park = {}

        # traverse all sites in currently get page
        sites = response.css(self.SELECTORS['siteItems'])
        # each site is one tr
        for site in sites:
            site_info = site.css(self.SELECTORS['siteInfo'])
            site_data = self.__parse_site(site_info, self.first_date)

            self.__merge_dict(site_data,park)

        return park

    def parse(self, response):
        data = self.__parse_sites_pages(response)
        pass
