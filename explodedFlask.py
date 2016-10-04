from flask import Flask
from flask import *
app = Flask(__name__)

@app.route("/")
def d3_test():
    return render_template("d3.html")

@app.route("/flare.json")
def flare():
    return render_template("flare.json")

if __name__ == "__main__":
    app.run()