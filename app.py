from flask import Flask, render_template, request, jsonify, make_response
import json
import logging
import os
from googlesearch import search
from datetime import datetime
import uuid

app = Flask(__name__, static_folder='static', template_folder='templates')

# 로깅 설정
logging.basicConfig(level=logging.INFO)
log = logging.getLogger('werkzeug')
log.setLevel(logging.INFO)  # ERROR CRITICAL WARNING INFO
	
@app.route("/")
def index():
    user_id = request.cookies.get("user_id")
    if not user_id:
        user_id = str(uuid.uuid4())  # 고유 사용자 ID 생성
        response = make_response(render_template("index.html"))
        response.set_cookie("user_id", user_id, max_age=60*60*24*30)  # 30일간 유지
        app.logger.info(f"[LOG] 신규 사용자 방문 | ID: {user_id}")
        return response
    else:
        app.logger.info(f"[LOG] 기존 사용자 방문 | ID: {user_id}")
        return render_template("index.html")
    return render_template("index.html")

@app.route("/search")
def result():
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    query = request.args.get("query", "쿼리 없음")

    # 쿠키 확인 및 사용자 ID 추출 (없으면 신규 생성)
    user_id = request.cookies.get("user_id")
    new_user = False
    if not user_id:
        user_id = str(uuid.uuid4())
        new_user = True

    # 로그 출력
    log_msg = f"{now} [LOG] 결과창 이동 | query = {query} | 사용자: {user_id}"
    app.logger.info(log_msg)

    # 결과 페이지 렌더링 및 쿠키 설정
    response = make_response(render_template("result.html"))
    if new_user:
        response.set_cookie("user_id", user_id, max_age=60 * 60 * 24 * 30)  # 30일

    return response

@app.route("/api/questions")
def api_questions():
    with open(os.path.join(app.static_folder, "questions.json"), encoding="utf-8") as f:
        return jsonify(json.load(f))

@app.route("/api/keep-alive")
def receive_ping():
    return "true"

@app.route("/api/products")
def api_products():
    query = request.args.get("query", "")
    with open(os.path.join(app.static_folder, "products.json"), encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data.get(query, []))
    
# ✅ 추가: 실시간 구글 쇼핑 검색 API(상세페이지)
@app.route("/api/google_search")
def api_google_search():
    user_query = request.args.get("query", "")
    if not user_query:
        return jsonify({"error": "검색어가 없습니다."}), 400

    full_query = (
        f"{user_query} site:coupang.com/vp/products/ "
        f"OR site:smartstore.naver.com "
        f"OR site:shopping.naver.com"
    )

    try:
        urls = search(full_query, lang="ko", stop=5)
        return jsonify({"results": list(urls)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
@app.route('/log/click', methods=['POST'])
def log_click():
    data = request.get_json()
    product_name = data.get('product_name', 'Unknown')
    query = data.get('product_query', 'Unknown')
    user_id = request.cookies.get("user_id", "익명")
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    log_msg = f"[LOG] 상세클릭 {now} | {product_name}  | {query} | 사용자: {user_id}"
    app.logger.info(log_msg)

    return '', 200
    
@app.errorhandler(404)
def page_not_found(e):
    user_id = request.cookies.get("user_id", "익명")
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    url = request.url  # 🔹 여기가 핵심
    log_msg = f"[LOG] ERROR 404 {now} | {url} | 사용자: {user_id}"
    app.logger.info(log_msg)

    return render_template("404.html"), 404



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

