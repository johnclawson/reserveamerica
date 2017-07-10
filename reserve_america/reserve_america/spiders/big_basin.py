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

    start_urls = [
        'https://www.reserveamerica.com/campsiteCalendar.do?page=calendar&contractCode=CA&parkId=120009&calarvdate=07/29/2017&sitepage=true&startIdx=0'
    ]

    def __get_status(self, stas):
        try:
            return self.STATUSES[stas.lower()]
        except:
            # default return reserve
            return self.STATUSES['r']

    def __offset_date(self, date, offset):
        return date + datetime.timedelta(days=offset)

    def __date_string(self, date):
        return date.strftime('%m/%d/%Y')

    def __parse_site_reservations(self, tds, first_date):
        """
        parse a site reservation information
        :param tds: td selector list
        :param first_date: first date of this list
        :return:
        {
            id: '26702',
            parkId: '120009',
            contractCode: 'CA',
            loop: '',
            url: '/camping/Big_Basin_Redwoods_Sp/r/campsiteDetails.do?siteId=26702&contractCode=CA&parkId=120009',
            name: '104B',
            title: '104B , TENT ONLY SITE',
            reservations: {
                '07/29/2017': {
                    id: '26702',
                    parkId: '120009',
                    contractCode: 'CA',
                    status: 'r'
                },
                '07/30/2017': {
                    id: '26702',
                    parkId: '120009',
                    contractCode: 'CA',
                    status: 'a',
                    url: '/camping/Big_Basin_Redwoods_Sp/r/campsiteDetails.do?siteId=26702&contractCode=CA&parkId=120009&offset=0&arvdate=7/30/2017'
                },
                '07/31/2017': {
                    id: '26702',
                    parkId: '120009',
                    contractCode: 'CA',
                    status: 'w'
                },
                '08/01/2017': {
                    id: '26702',
                    parkId: '120009',
                    contractCode: 'CA',
                    status: 'x'
                },
                ...
            }
        }
        """
        site_reservations = {
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
                site_reservations['id'] = queries['siteId'][0]
                site_reservations['parkId'] = queries['parkId'][0]
                site_reservations['contractCode'] = queries['contractCode'][0]
                site_reservations['title'] = td.css(self.SELECTORS['siteMarkTitle']).extract_first()
                site_reservations['name'] = td.css(self.SELECTORS['siteListLabelText']).extract_first()
                site_reservations['url'] = url
            # second item is site's loop
            elif index == 1:
                loop = td.css(self.SELECTORS['siteLoopText']).extract_first()
                site_reservations['loop'] = loop
            else:
                date_str = self.__date_string(self.__offset_date(first_date, index - 2))
                url = td.css(self.SELECTORS['siteAvailableHref']).extract_first()
                if url:
                    # this date is available for book
                    site_reservations['reservations'][date_str] = {
                        'id': site_reservations['id'],
                        'parkId': site_reservations['parkId'],
                        'contractCode': site_reservations['contractCode'],
                        'status': self.__get_status('a'),
                        'url': url
                    }

                else:
                    status = td.css('::text').extract_first()
                    site_reservations['reservations'][date_str] = {
                        'id': site_reservations['id'],
                        'parkId': site_reservations['parkId'],
                        'contractCode': site_reservations['contractCode'],
                        'status': self.__get_status(status)
                    }

        return site_reservations

    def __parse_reserve_america(self, response):
        """
        Parse Reserve America Page to a JSON data

        :param response:
        :return:
        """

        """
        parks information data
        
        {
            '120009':{
                'name': '',
                'sites':{
                    '26702':{
                        # park information
                    }
                }
            }
        }
        """
        parks = {}

        """
        reservation information data
        {
            '120009':{
                '07/29/2017': {
                    'a': {
                       '26702': {
                            id: '26702',
                            parkId: '120009',
                            contractCode: 'CA',
                            status: 'a',
                            url: '/camping/Big_Basin_Redwoods_Sp/r/campsiteDetails.do?siteId=26702&contractCode=CA&parkId=120009&offset=0&arvdate=7/30/2017'
                        }
                    }
                }
                    
            }
        }
        """
        reservations = {}

        # traverse all sites in currently get page
        sites = response.css(self.SELECTORS['siteItems'])
        # each site is one tr
        for site in sites:
            site_info = site.css(self.SELECTORS['siteInfo'])
            site_data = self.__parse_site_reservations(site_info, self.first_date)

            # store reservations
            site_reservations = site_data['reservations']
            for key, reservation in site_reservations.items():
                park_id = reservation['parkId']
                site_id = reservation['id']
                status = reservation['status']
                if park_id not in reservations:
                    reservations[park_id] = {}
                if key not in reservations[park_id]:
                    reservations[park_id][key] = {}
                if status not in reservations[park_id][key]:
                    reservations[park_id][key][status] = {}
                if site_id not in reservations[park_id][key][status]:
                    reservations[park_id][key][status][site_id] = {}
                reservations[park_id][key][status][site_id] = reservation

            if site_data['parkId'] not in parks:
                parks[site_data['parkId']] = {
                    'sites': {
                    }
                }
            if site_data['id'] not in parks[site_data['parkId']]['sites']:
                del site_data['reservations']
                parks[site_data['parkId']]['sites'][site_data['id']] = site_data

        return {
            'parks': parks,
            'reservations': reservations
        }

    def parse(self, response):
        data = self.__parse_reserve_america(response)
        pass
