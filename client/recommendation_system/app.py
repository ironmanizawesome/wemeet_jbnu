from flask import Flask, render_template, request
from utils.parser import load_crop_data, recommend_crops

app = Flask(__name__)

# 데이터 로드
CROP_FILE = "data/작물들.txt"
crops = load_crop_data(CROP_FILE)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/recommend", methods=["POST"])
def recommend():
    season = request.form.get("season")
    level = request.form.get("level")
    sunlight = request.form.get("sunlight")

    results = recommend_crops(crops, season, level, sunlight)

    return render_template("result.html", results=results, season=season, level=level, sunlight=sunlight)

if __name__ == "__main__":
    app.run(debug=True)
