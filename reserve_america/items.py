# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

from scrapy import Item, Field

class ReservationItem(Item):
    """
    Reservation
    """
    _id = Field() # override MongoDB generate ID
    facilityId = Field()  # Facilicy id, this is used in https://www.reservecalifornia.com
    siteId = Field()  # campsite id
    parkId = Field()  # park id
    contractCode = Field()  # park contract code
    date = Field() # reservation date string
    weekday = Field() # reservation week day 0 - 6
    status = Field() # status value, oneOf ['r', 'a', 'w', 'x']
    url = Field() # if it is available, the book url
    lastModified = Field() #

class CampsiteDetailItem(Item):
    site_type = Field() # Site Type
    site_reserve_type = Field() # Site Reserve Type
    site_access = Field()
    accessible = Field()
    checkin_time = Field() # Checkin Time
    checkout_time = Field() # Checkout Time
    type_of_use = Field() # Checkout Time
    min_num_of_people = Field() #
    max_num_of_people = Field()
    pets_allowed = Field()
    max_num_of_vehicles = Field()
    driveway_surface = Field()
    driveway_entry = Field()
    driveway_length = Field()
    tent_pad = Field()
    bbq = Field()
    food_locker = Field()
    grills_fire_ring = Field()
    max_vehicle_length = Field()
    shade = Field()
    capacity_size_rating = Field()
    campfire_allowed = Field()
    fire_pit = Field()
    picnic_table = Field()
    hike_in_distance_to_site = Field()
    site_rating = Field()
    double_driveway = Field()
    site_length = Field()
    lantern_pole = Field()


class CampsiteItem(Item):
    """
    Campsite
    """
    _id = Field()  # override MongoDB generate ID
    siteId = Field() # campsite id
    parkId = Field() # park id
    contractCode = Field() # park contract code
    url = Field() # campsite detail information
    nameArea = Field() # campsite name
    detail = Field() # CampsiteDetailItem

class ParkItem(Item):
    """
    Park
    """
    _id = Field()  # override MongoDB generate ID
    parkId = Field() # park id
    contractCode = Field()  # park contract code
    name = Field() # park name
    services = Field() # services and amenities that this park provide
    addressCountry = Field() # park address
    addressStreet= Field() # park address
    addressLocality= Field() # park address
    addressRegion= Field() # park address
    postalCode= Field() # park address
    telephone= Field() # park address
