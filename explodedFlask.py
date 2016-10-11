from flask import Flask
from flask import *
app = Flask(__name__)

@app.route("/")
def d3_circ():
    return render_template("d3.html")

@app.route("/tree")
def d3_tree():
    return render_template("d3-tree.html")

@app.route("/data.json")
def data():
    return render_template("data.json")

if __name__ == "__main__":
    app.run()