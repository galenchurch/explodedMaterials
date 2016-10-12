from __future__ import print_function
import httplib2
import os

from bson.objectid import ObjectId
from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools
import json


class expld:
    def __init__(self, service, shtID, nester="PartNo"):
        self.service = service
        self.shtID = shtID
        self.sheetProperties = self.getSheetProperties()
        self.tree = {}
        self.sheets = []
        self.templateCol = []
        self.getSheets()
        self.nester = nester

    def getSheetProperties(self):
        result =  self.service.spreadsheets().get(spreadsheetId=self.shtID, fields='sheets(properties)').execute()
        return result.get('sheets', [])

    def getSheets(self):
        for sht in self.sheetProperties:
            self.sheets.append(sht['properties']['title'])

    def getSheetValues(self, rangeName):
        result = self.service.spreadsheets().values().get(spreadsheetId=self.shtID, range=rangeName).execute()
        return result.get('values', [])

    def getColList(self, template_sheet):
        rangeName = ('%s!1:1' % template_sheet)
        firstRow = self.getSheetValues(rangeName)
        self.templateCol = firstRow[0]
        return self.templateCol

    def confirmTreeIdent(self, tree_identifier):
        template_row = self.templateCol
        if tree_identifier in template_row:
            for i in range(len(template_row)):
                if tree_identifier == template_row[i]:
                    return i
            return -1
        else:
            return -1


    def makeTree(self, tree_identifier):
        temp_dict = {}
        nester = self.confirmTreeIdent(tree_identifier)
        if nester >= 0:
            for sheet_title in self.sheets:
                rangeName = ('%s' % sheet_title)
                current = self.getSheetValues(rangeName)
                if current[0] == self.templateCol:
                    for row in current[1:]:
                        for col,x in self.templateCol:
                            temp_dict[col] = row[x]
        else:
            print('cannot make tree from that identifier')


    def nestedTree(self, tree_identifier, current_bom):
        current_dict = {}
        nester = self.confirmTreeIdent(tree_identifier)
        if nester >= 0:
            rangeName = ('%s' % current_bom)
            current_list = self.getSheetValues(rangeName)

            for item, row in enumerate(current_list[1:]):
                if row[0] == "####":
                    #row to ignore should have '####' in the first col
                    return current_dict
                else:
                    for index, name in enumerate(current_list[0]):
                        try:
                            nested_set(current_dict, [row[nester], name], row[index])
                        except IndexError:
                            nested_set(current_dict, [row[nester], name], '')
                    if row[nester] in self.sheets and row[nester] != current_bom:
                        nested_set(current_dict, [row[nester], "children"], self.nestedTree(tree_identifier, row[nester]))
        else:
            print("nester no good")
            return ''
        return current_dict

    def addParts(self, db, tree):
        for key, value in tree.items():
            # print(key)
            try:
                #try to insert recursive with children field
                print(len(value["children"]))
                part = db.partsDev.insert_one(value).inserted_id
                self.addParts(db, value["children"])
            except:
                #no children just insert part
                print("no child")
                part = db.partsDev.insert_one(value).inserted_id

    def newBom(self, db, tree, bom_title):
        bom_db_id = db.bomDev.insert_one({"name":bom_title, "children":[]}).inserted_id
        print(bom_db_id)
        return bom_db_id

    def addPartsAndBom(self, db, tree, top_bom):
        """bom consists of:
                basic top level info
                children: child(qty, ObjectId(part))"""

        #create a new BoM
        curr_level_bom = self.newBom(db, tree, top_bom)

        for key, value in tree.items():
            #try to insert recursive with children field 
            if("children" not in value):  
                #no children just insert part
                
                part_inserted_id = db.partsDev.insert_one(value).inserted_id

                #test, get and add part qty to part dict
                part_qty = self.getOrFail(value, "QTY")
                if part_qty:
                    part = {"id": part_inserted_id, "qty":part_qty}
                else:
                    part = {"id": part_inserted_id}

                db.bomDev.update_one({"_id": curr_level_bom}, {"$push": {"children":part}})                 
            else:
                #children exist
                if(len(value["children"])>0):
                    part_inserted_id = db.partsDev.insert_one(value).inserted_id

                    #test, get and add part qty to part dict
                    part_qty = self.getOrFail(value, "QTY")
                    if part_qty:
                        part = {"id": part_inserted_id, "qty":part_qty}
                    else:
                        part = {"id": part_inserted_id}


                    db.bomDev.update_one({"_id": curr_level_bom}, {"$push": {"children":part}})

                    child_bom = self.addPartsAndBom(db, value["children"], value[self.nester])
                    print("new child bom{}".format(child_bom))
                    print("new child bom part{}".format(part))

                    db.bomDev.update_one({"_id": child_bom}, {"$set":{"part":part}})
                else:
                    #zero children just insert part
                    part = db.partsDev.insert_one(value).inserted_id
                    db.bomDev.update_one({"_id": curr_level_bom}, {"$push": {"children":part}})              
        return curr_level_bom  

    def getOrFail(self, doc, key):
        try:
            return doc[key]
        except KeyError:
            return False
        except:
            return False


    def recurTree(self, db, curr_top):
        """recursivly add part information from boms to JSON"""
        print("top = {}".format(curr_top))
        # curr_top = bson.objectid.ObjectId(curr_top)
        # print(curr_top)       
        print(type(curr_top))     

        current_bom = db.bomDev.find_one({"_id":curr_top})
        current_part = db.partsDev.find_one({"_id":curr_top})
        

        
        if current_bom:  #curr_top of ObjectID type is a bom document
            print("bom: {}".format(current_bom))
            """get "name" information and build rec_data structure"""

            part_data = db.partsDev.find_one({"_id":current_bom["part"]["id"]})
            print(part_data)
            if part_data: #if there is part info use it
                rec_data = {"name":part_data[self.nester], "children":[]}
            else: #else use bom.name
                rec_data = {"name":current_bom["name"], "children":[]}

            if "children" in current_bom:
                if len(current_bom["children"]) > 0:  #bom.children exists and has items
                    print("in bom in children")
                    for child in current_bom["children"]: #recursivly search though children (they will be parts or boms)
                        print(child)
                        to_append = {"qty": self.getOrFail(child, "qty")}
                        to_append.update(self.recurTree(db, child["id"]))
                        rec_data["children"].append(to_append)
                        # print(to_append)
                        # print(rec_data)
                    return rec_data
            else:
                return rec_data

        elif current_part: #curr_top of ObjectID type is a part document

            """attempt to find and associated BoM for the part"""
            print("current part from attemp {}".format(current_part))
            bom_data = db.bomDev.find_one({"part.id":current_part["_id"]})
            print("bom_data: {}".format(bom_data))
            if bom_data:
                 return self.recurTree(db, bom_data["_id"])
            else:
                return {"name": current_part[self.nester]}

        else:
            return {"name":"unknown part/bom"}


    def genJsonForD3(self, db, top_bom):
        data = {'name': top_bom, 'children': []}
        

        top = db.bomDev.find_one({"name":top_bom})
        if(top):
            print(top["_id"])
            data = self.recurTree(db, top["_id"])
            print("data for wite: {}".format(data))

            with open('templates/data.json', 'w') as outfile:
                json.dump(data, outfile, indent=4, sort_keys=True, separators=(',', ':'))
        else:
            print("Failed to find Top {}".format(top_bom))
            return None

    def genJsonForD3OLD(self, db, top_bom):
        data = {'name': top_bom, 'children': []}
        

        top = db.bomDev.find_one({"name":top_bom})
        if(top):
            print(top["_id"])
            data["children"] = self.recurTree(db, top["_id"])
            

            with open('templates/data.json', 'a+') as outfile:
                print(json.dump(data, outfile, indent=4, sort_keys=True, separators=(',', ':')))
        else:
            print("Failed to find Top {}".format(top_bom))
            return None

    def describeBom(self, db, bom_id, attr):
        if type(attr) is dict:
            part = db.partsDev.insert_one(attr).inserted_id
            db.bomDev.update_one({"_id": bom_id}, {"$set":{"part":{"id":part}}})
        return part





                



    def TEST(self, db):
        print(self.sheets)
        print(self.getColList(self.sheets[0]))
        #self.fromOneMakeTree('PartNo')
        tree = self.nestedTree('PartNo', self.sheets[0])
        # print(tree.keys())
        # print(json.dumps(tree, indent=4))
        print(len(tree['201-0018']))
        working_bom = self.addPartsAndBom(db, tree, self.sheets[0])
        print(self.describeBom(db, working_bom, {"PartNo":self.sheets[0], "desctiption":"top_level"}))
        self.genJsonForD3(db, self.sheets[0])




def nested_set(dic, keys, value):
    for key in keys[:-1]:
        dic = dic.setdefault(key, {})
    dic[keys[-1]] = value