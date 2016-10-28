from __future__ import print_function
import httplib2
import os, json

from bson.objectid import ObjectId
from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools
from JSONEncoder import JSONEncoder


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
        self.full={}
        self.fuller={}

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
        to_insert = {self.nester:bom_title, "children":[], "inserted_by": self.shtID}
        print("New Bom {} ".format(to_insert))
        bom_db_id = self.UpdateOrInsert(db, to_insert, col="bomDev")
        # bom_db_id = db.bomDev.insert_one({"name":bom_title, "children":[]}).inserted_id
        print(bom_db_id)
        return bom_db_id

    def addPartsAndBom(self, db, tree, top_bom):

        """bom consists of:
                basic top level info
                children: child(qty, ObjectId(part))"""

        #create a new BoM
        curr_level_bom = self.newBom(db, tree, top_bom)

        #for full tree creation on recurssive
        # current_full = {"id":curr_level_bom, "children":[]}

        for key, value in tree.items():
            #add sheet id
            to_insert = value
            to_insert["inserted_by"] = self.shtID

            #try to insert recursive with children field 
            if("children" not in to_insert):  
                #no children just insert part
                part_inserted_id = self.UpdateOrInsert(db, to_insert)

                #test, get and add part qty to part dict
                part_qty = self.getOrFail(to_insert, "QTY")
                if part_qty:
                    part = {"id": part_inserted_id, "qty":part_qty}
                else:
                    part = {"id": part_inserted_id}

                db.bomDev.update_one({"_id": curr_level_bom}, {"$push": {"children":part}})
                # current_full["children"].append(part) 
                # self.full[top_bom] = current_full               
            else:
                #children exist
                if(len(to_insert["children"])>0):
                    part_inserted_id = self.UpdateOrInsert(db, to_insert)

                    #test, get and add part qty to part dict
                    part_qty = self.getOrFail(to_insert, "QTY")
                    if part_qty:
                        part = {"id": part_inserted_id, "qty":part_qty}
                    else:
                        part = {"id": part_inserted_id}

                   

                    db.bomDev.update_one({"_id": curr_level_bom}, {"$push": {"children":part}})

                    child_bom = self.addPartsAndBom(db, to_insert["children"], to_insert[self.nester])
                    # current_full["children"].append(part) 
                    # nested_set(current_full,  [curr_level_bom, "children"], child_bom) 
                    print("making child nested_set.{}".format(curr_level_bom))


                    # print("new child bom{}".format(child_bom))
                    # print("new child bom part{}".format(part))

                    db.bomDev.update_one({"_id": child_bom}, {"$set":{"part":part}})
                    # self.full[top_bom] = current_full
                else:
                    #zero children just insert part
                   
                    part_inserted_id = self.UpdateOrInsert(db, to_insert)

                    db.bomDev.update_one({"_id": curr_level_bom}, {"$push": {"children":part}}) 
                    # self.full[top_bom] = current_full  

        # nested_set(self.full,  str(top_bom), current_full)
                
        return curr_level_bom  

    def sameExists(self, db, search, col="partsDev"):
        found = db[col].find_one({self.nester:search})
        if found:
            try:
                if found["inserted_by"] == self.shtID:
                    print("updating {}...".format(col))
                    return found["_id"]
                else:
                    print("new {}...".format(col))
                    return False
            except KeyError:
                print("newError {}...".format(col))
                return False

    def UpdateOrInsert(self, db, data, col="partsDev"):
        check = self.sameExists(db, data[self.nester], col)
        if check:
            db[col].update_one({"_id":check}, {"$set" :data})
            return check
        else:
            return db[col].insert_one(data).inserted_id

    def getOrFail(self, doc, key):
        try:
            return doc[key]
        except KeyError:
            return False
        except:
            return False

    def recurFullFill(self, db, curr_top):
        """recursivly add part information from boms to JSON"""

        #check for complete bom with current shtID

        sheetlocation = db.bomDev.find_one({"sheet":self.shtID})

        if not sheetlocation:
            print("No BoM with sheet_ID:{}").format(self.shtID)
            return False

        print("top = {}".format(curr_top))
        # curr_top = bson.objectid.ObjectId(curr_top)
        # print(curr_top)       
        print(type(curr_top))     

        current_bom = db.bomDev.find_one({"_id":curr_top})
        current_part = db.partsDev.find_one({"_id":curr_top})
        

        
        if current_bom:  #curr_top of ObjectID type is a bom document
            # print("bom: {}".format(current_bom))
            """get "name" information and build rec_data structure"""

            part_data = db.partsDev.find_one({"_id":current_bom["part"]["id"]})
            print(part_data)
            if part_data: #if there is part info use it
                rec_data = {"name":part_data[self.nester], "id":part_data["_id"], "children":[]}
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


    def recurTree(self, db, curr_top):
        """recursivly add part information from boms to JSON"""
        # print("top = {}".format(curr_top))
        # curr_top = bson.objectid.ObjectId(curr_top)
        # print(curr_top)       
        # print(type(curr_top))     

        current_bom = db.bomDev.find_one({"_id":curr_top})
        current_part = db.partsDev.find_one({"_id":curr_top})

        if current_bom:  #curr_top of ObjectID type is a bom document
            # print("bom: {}".format(current_bom))
            """get "name" information and build rec_data structure"""

            part_data = db.partsDev.find_one({"_id":current_bom["part"]["id"]})
            print(part_data)
            if part_data: #if there is part info use it
                rec_data = {"name":part_data[self.nester], "id":part_data["_id"], "children":[]}
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
                        print("out a level")
                    return rec_data
            else:
                return rec_data

        elif current_part: #curr_top of ObjectID type is a part document

            """attempt to find and associated BoM for the part"""
            # print("current part from attemp {}".format(current_part))
            bom_data = db.bomDev.find_one({"part.id":current_part["_id"]})
            # print("bom_data: {}".format(bom_data))
            if bom_data:
                 return self.recurTree(db, bom_data["_id"])
            else:
                return {"name": current_part[self.nester], "id":current_part["_id"]}

        else:
            return {"name":"unknown part/bom"}


    def genJsonForD3(self, db, top_bom):
        data = {self.nester: top_bom, 'children': []}
        

        top = db.bomDev.find_one({self.nester:top_bom})
        if(top):
            # print(top["_id"])
            data = self.recurTree(db, top["_id"])
            # print("data for wite: {}".format(data))

            with open('/var/www/static/data/data.json', 'w') as outfile:
                json.dump(json.loads(JSONEncoder().encode(data)), outfile, indent=4, sort_keys=True, separators=(',', ':'))
        else:
            print("Failed to find Top {}".format(top_bom))
            return None

    def updateFullTree(self, db, top_bom):
        top = db.bomDev.find_one({"name":top_bom})
        if(top):
            data = self.recurTree(db, top["_id"])
            print("data:{}".format(data))
            data["sheet_id"] = self.shtID
            exiting = db.fullBomDev.find_one_and_replace({"sheet_id":self.shtID}, data, upsert=True)



        

    def describeBom(self, db, bom_id, attr):
        if type(attr) is dict:
            part = self.UpdateOrInsert(db, attr)
            # part = db.partsDev.insert_one(attr).inserted_id
            db.bomDev.update_one({"_id": bom_id}, {"$set":{"part":{"id":part}}})
        return part

    def TEST(self, db):
        print(self.sheets)
        print(self.getColList(self.sheets[0]))
        #self.fromOneMakeTree('PartNo')
        tree = self.nestedTree('PartNo', self.sheets[0])
        # print("tree:{}/n".format(tree))
        # print(json.dumps(tree, indent=4))
        print(len(tree['201-0018']))
        working_bom = self.addPartsAndBom(db, tree, self.sheets[0])
        print(self.describeBom(db, working_bom, {self.nester: self.sheets[0], "desctiption":"top_level", "sheet":self.shtID, "inserted_by":self.shtID}))
        
        self.genJsonForD3(db, self.sheets[0])
        # print("full: {}".format(self.full))
        # self.updateFullTree(db, self.sheets[0])




def nested_set(dic, keys, value):
    for key in keys[:-1]:
        dic = dic.setdefault(key, {})
    dic[keys[-1]] = value