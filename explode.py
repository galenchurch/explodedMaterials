from __future__ import print_function
import httplib2
import os

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
            print(key)
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
        curr_level_bom = self.newBom(db, tree, top_bom)

        #db.bomDev.update_one({"_id": curr_level_bom}, {"part_id":part}})  need to add the part id for the current level part itself

        for key, value in tree.items():
            #try to insert recursive with children field 
            if("children" not in value):  
                #no children just insert part
                part = db.partsDev.insert_one(value).inserted_id
                print(db.bomDev.update_one({"_id": curr_level_bom}, {"$push": {"children":part}}))                    
            else:
                #field exists
                if(len(value["children"])>0):
                    part = db.partsDev.insert_one(value).inserted_id
                    print(db.bomDev.update_one({"_id": curr_level_bom}, {"$push": {"children":part}}))
                    child_bom = self.addPartsAndBom(db, value["children"], value[self.nester])
                    db.bomDev.update_one({"_id": child_bom}, {"$set":{"part_id":part}})
                else:
                    #zero children just insert part
                    part = db.partsDev.insert_one(value).inserted_id
                    print(db.bomDev.update_one({"_id": curr_level_bom}, {"$push": {"children":part}}))                    
        return curr_level_bom  

    def recurTree(self, db, curr_top):
        """recursivly add part information from boms to JSON"""
        
        current = db.bomDev.find_one({"_id":curr_top})
        if current:
            if "children" in current:
                if len(current["children"])>0:
                    print("recurTree current {} has children".format(current))
                    rec_data = {"name": current["name"], "children":[]}
                    for child in current["children"]:
                        rec_data["children"].append(self.recurTree(db, child))
                else:
                    part_data = db.partsDev.find_one({"_id":child})
                    try:
                        rec_data = {"name":part_data[self.nester]}
                    except KeyError:
                        print("no: {} in: {}".format(self.nester, child))
        else:
            part_data = db.partsDev.find_one({"_id":curr_top})
            try:
                rec_data = {"name":part_data[self.nester]}
            except KeyError:
                print("no: {} in: {}".format(self.nester, child))

        return rec_data


    def recurTreeOLD(self, db, curr_top):
        """recursivly add part information from boms to JSON"""
        
        current = db.bomDev.find_one({"_id":curr_top})
        try:
            print("recurTree: {}".format(current["_id"]))
            #cur_data = db.partsDev.find_one({"_id":current})
            rec_data = {"name": current["name"], "children":[]}

            try:
                if(len(current["children"])>0):
                    for child in current["children"]:
                        child_data = db.partsDev.find_one({"_id":child})
                        if(len(child_data["children"])>0):
                            rec_data = self.recurTree(db, child_data["_id"])
                        rec_data["children"].append(child_insert)

            except KeyError:
                print("key_error")

            return rec_data
        except TypeError:
            print("there was no {}".format(curr_top))
            return None

    def genJsonForD3(self, db, top_bom):
        data = {'name': top_bom, 'children': []}
        

        top = db.bomDev.find_one({"name":top_bom})
        if(top):
            print(top["_id"])
            data["children"] = self.recurTree(db, top["_id"])
            print(data)

            with open('templates/data.json', 'w') as outfile:
                json.dump(data, outfile, indent=4, sort_keys=True, separators=(',', ':'))
        else:
            print("Failed to find Top {}".format(top_bom))
            return None

    def describeBom(self, db, bom_id, attr):
        if type(attr) is dict:
            part = db.partsDev.insert_one(attr).inserted_id
            db.bomDev.update_one({"_id": bom_id}, {"$set":{"part_id":part}})
        return part





                



    def TEST(self, db):
        print(self.sheets)
        print(self.getColList(self.sheets[0]))
        #self.fromOneMakeTree('PartNo')
        tree = self.nestedTree('PartNo', self.sheets[0])
        print(tree.keys())
        print(json.dumps(tree, indent=4))
        print(len(tree['201-0018']))
        working_bom = self.addPartsAndBom(db, tree, self.sheets[0])
        print(db.partsDev.find())
        print(self.describeBom(db, working_bom, {"PartNo":self.sheets[0], "desctiption":"top_level"}))
        self.genJsonForD3(db, self.sheets[0])




def nested_set(dic, keys, value):
    for key in keys[:-1]:
        dic = dic.setdefault(key, {})
    dic[keys[-1]] = value