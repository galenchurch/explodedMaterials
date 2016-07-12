from __future__ import print_function
import httplib2
import os

from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools


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

    def fromOneMakeTree(self, tree_identifier):
        temp_dict = {}
        if tree_identifier in self.templateCol:
                for sheet_title in self.sheets:
                    rangeName = ('%s' % sheet_title)
                    current = self.getSheetValues(rangeName)
                    if current[0] == self.templateCol:
                        for row in current:
                            for col,x in self.templateCol:
                                temp_dict[col] = row[x]
                                
                    print(current)
        else:
            print('cannot make tree from that identifier')



    def TEST(self):
        print(self.sheets)
        print(self.getColList(self.sheets[0]))
        self.fromOneMakeTree('PartNo2')
