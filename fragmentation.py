import json, os, warnings, sys

sys.path.append( "/var/www/docify" )
from pymongo import MongoClient
from pprint import pprint
from bson.objectid import ObjectId
from JSONEncoder import JSONEncoder
from docify import *

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
            return self.db.bomDev.find_one({"_id":ObjectId(obj_id)})
        elif col == "part":
            return self.db.partsDev.find_one({"_id":ObjectId(obj_id)})
        else:
            return {"error":"no such collection"}

    def getJSONfromDB(self, col, obj_id):
        return JSONEncoder().encode(self.getDataFromDB(col, obj_id))

    def returnDocifyDisplay(self, col, obj_id):
        data = self.getDataFromDB(col, obj_id)
        document = Document(data)
        print(document.elements)
        print("before_ret")
        ret_disp = ""
        for el in document.elements:
            ret_disp = "{}{}".format(ret_disp, el.displayView())
        return ret_disp

        