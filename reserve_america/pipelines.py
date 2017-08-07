# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
import pymongo
import os
from reserve_america.items import ReservationItem, CampsiteItem, ParkItem

class MongoDBPipleline(object):

    def __init__(self):
        mongo_url = 'mongodb://localhost:27017/reserveamercia'
        mongo_user = ''
        mongo_password = ''
        mongo_host = 'locahost'
        mongo_port = '27017'
        mongo_db = 'reserveamercia'

        # Environment value overwrite default value
        if self.get_env('MONGO_USER'):
            mongo_user = self.get_env('MONGO_USER')
        if self.get_env('MONGO_PASSWORD'):
            mongo_password = self.get_env('MONGO_PASSWORD')
        if self.get_env('MONGO_HOST'):
            mongo_host = self.get_env('MONGO_HOST')
        if self.get_env('MONGO_PORT'):
            mongo_port = self.get_env('MONGO_PORT')
        if self.get_env('MONGO_DB'):
            mongo_db = self.get_env('MONGO_DB')

        if mongo_user:
            mongo_url = 'mongodb://%s:%s@%s:%s/%s' % (mongo_user, mongo_password, mongo_host, mongo_port, mongo_db)

        client = pymongo.MongoClient(mongo_url)
        db = client.get_default_database()
        self.Parks = db["Parks"]
        self.Campsites = db["Campsites"]
        self.Reservations = db["Reservations"]

    def get_env(self, key):
        try:
            return os.environ[key]
        except Exception:
            return ''

    def process_item(self, item, spider):
        if isinstance(item, ReservationItem):
            try:
                self.Reservations.update({"_id": item['_id']}, dict(item), upsert=True)
            except Exception:
                pass
        elif isinstance(item, CampsiteItem):
            try:
                self.Campsites.update({"_id": item['_id']}, dict(item), upsert=True)
            except Exception:
                pass
        elif isinstance(item, ParkItem):
            try:
                self.Parks.update({"_id": item['_id']}, dict(item), upsert=True)
            except Exception:
                pass
        else:
            pass
        return item
