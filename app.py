from flask import Flask, render_template, request, send_from_directory
import os

app = Flask(__name__, static_folder='static', template_folder='templates')


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/result.html")
def result():
    # 쿼리 문자열을 그대로 넘김
    query = request.args.get("query", "")
    return render_template("result.html", query=query)


# 정적 파일 처리 (CSS, JS, 이미지 등)
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(app.static_folder, filename)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render용 포트
    app.run(host="0.0.0.0", port=port)

