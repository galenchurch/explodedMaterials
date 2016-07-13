from __future__ import print_function
import httplib2
import os

from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools
import json


class expld:
    def __init__(self, service, shtID):
        self.service = service
        self.shtID = shtID
        self.sheetProperties = self.getSheetProperties()
        self.tree = {}
        self.sheets = []
        self.templateCol = []
        self.getSheets()

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



    def TEST(self):
        print(self.sheets)
        print(self.getColList(self.sheets[0]))
        #self.fromOneMakeTree('PartNo')
        tree = self.nestedTree('PartNo', self.sheets[0])
        print(tree.keys())
        print(json.dumps(tree, indent=4))
        print(len(tree['201-0018']))

def nested_set(dic, keys, value):
    for key in keys[:-1]:
        dic = dic.setdefault(key, {})
    dic[keys[-1]] = value