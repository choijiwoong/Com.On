from flask import Flask, render_template, request, jsonify
import json
import os

app = Flask(__name__, static_folder='static', template_folder='templates')

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/result.html")
def result():
    return render_template("result.html")

@app.route("/api/questions")
def api_questions():
    with open(os.path.join(app.static_folder, "questions.json"), encoding="utf-8") as f:
        return jsonify(json.load(f))

@app.route("/api/products")
def api_products():
    query = request.args.get("query", "")
    with open(os.path.join(app.static_folder, "products.json"), encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data.get(query, []))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

