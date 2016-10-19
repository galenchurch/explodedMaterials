# explodedMaterials

##general

A visualization parser to interface data originating in the form of a google sheet to storage in a database (mongodb) to properly formated JSON documents for use with d3.org visualizations

##specifics

###GoogleDocs

In the specific case as implemented the google doc is to contain a Bill of Materials (BoM).  Each sheet must be properly named and contain a "nester" (expld.nester) field so that nested tree visualization may be implemented.

### mongodb

Mongo stores data from the google sheet in two forms.  

1. It creates bom document for each assembly (loosely defined as a sheet, but more throetically defined as any "part" with child parts)

2. It creates a part document for each part (including assembles) with all other ancilarry information provided

the bom document references the part documents using their inderted_id of type bson.ObjectId

###visualization hosting (Flask)

the visualization requires JSON data in the nested tree format, so the function expld.genJsonForD3() and its conterpart expld.recurTree() recursicly loop through the "top level BoM" to pull all information from bom documents and part documents in the database into the file data.json
