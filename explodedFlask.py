from flask import Flask
from flask import *
from fragmentation import frag

app = Flask(__name__)

@app.route("/")
def d3_circ():
    return render_template("d3.html")

@app.route("/tree")
def d3_tree():
    return render_template("d3-tree.html")

@app.route("/data.json")
def data():
    return render_template(json.loads("data.json"))

@app.route('/query/<col>/<obj_id>')
def api_article(col, obj_id):
    queryFrag = frag()
    return queryFrag.getDataFromDB(col, obj_id)

if __name__ == "__main__":
    app.run()