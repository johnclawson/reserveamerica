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
    campsiteId = Field()  # campsite id
    parkId = Field()  # park id
    contractCode = Field()  # park contract code
    date = Field() # reservation date string
    status = Field() # status value, oneOf ['r', 'a', 'w', 'x']
    url = Field() # if it is available, the book url
    lastModified = Field() #

class CampsiteItem(Item):
    """
    Campsite
    """
    _id = Field()  # override MongoDB generate ID
    campsiteId = Field() # campsite id
    parkId = Field() # park id
    contractCode = Field() # park contract code
    loop = Field() # campsite loop information
    url = Field() # campsite detail information
    name = Field() # campsite name
    title = Field() # campsite title

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
