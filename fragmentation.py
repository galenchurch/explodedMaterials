import json, os, warnings
from pymongo import MongoClient
from pprint import pprint
from bson.objectid import ObjectId
from JSONEncoder import JSONEncoder

class frag:
    def __init__(self, db_uri_file="/var/www/expld/db_uri.json"):
        self.db = self.openDb(db_uri_file)

    def openDb(self, db_uri_file):
        """read db_uri_file and return mongo db client"""

        with open(db_uri_file, 'r') as data_file_db:
            db_data = json.loads(data_file_db.read())

        mbdClient = MongoClient(db_data["db_uri"])
        return mbdClient.expld

    def getDataFromDB(self, col, obj_id):
        if col == "bom":
            return JSONEncoder().encode(self.db.bomDev.find_one({"_id":ObjectId(obj_id)}))
        elif col == "part":
            return JSONEncoder().encode(self.db.partsDev.find_one({"_id":ObjectId(obj_id)}))
        else:
            return {"error":"no such collection"}
        