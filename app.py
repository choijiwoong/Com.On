# =======================
# 📦 필수 모듈 임포트
# =======================
from flask import Flask, render_template, request, jsonify, make_response, send_file
import json
import logging
import os
from googlesearch import search
from datetime import datetime
import uuid
from openai import OpenAI
from dotenv import load_dotenv
import requests

# =======================
# 🚀 앱 초기화 및 설정
# =======================
app = Flask(__name__, static_folder='static', template_folder='templates')

# 🔧 로깅 설정
logging.basicConfig(level=logging.INFO)    
log = logging.getLogger('werkzeug')
log.setLevel(logging.INFO)

# =======================
# 🔐 환경 변수 및 API 키 로드
# =======================
if os.path.exists(".env"):
    load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
naver_api_client_id = os.getenv("NAVER_API_CLIENT_ID")
naver_api_client_secret = os.getenv("NAVER_API_CLIENT_SECRET")
slack_api_key=os.getenv("SLACK_API_TOKEN")

if not api_key:
    raise EnvironmentError("❌ OPENAI_API_KEY가 설정되지 않았습니다!")
client = OpenAI(api_key=api_key)


# 슬랙 알림 설정
def send_slack_alert(message):
    payload = {"text": message}
    requests.post(slack_api_key, json=payload)

# =======================
# 🏠 루트 페이지 (index)
# =======================
@app.route("/")
def index():
    user_id = request.cookies.get("user_id")
    if not user_id:
        user_id = str(uuid.uuid4())  # 고유 사용자 ID 생성
        response = make_response(render_template("index.html"))
        response.set_cookie("user_id", user_id, max_age=60*60*24*30)  # 30일 유지
        app.logger.info(f"[LOG] 신규 사용자 방문 | ID: {user_id}")
        return response
    else:
        app.logger.info(f"[LOG] 기존 사용자 방문 | ID: {user_id}")
        return render_template("index.html")

# =======================
# 🔍 검색 결과 페이지
# =======================
@app.route("/search")
def result():
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    query = request.args.get("query", "쿼리 없음")

    # 쿠키 확인 및 사용자 ID 생성
    user_id = request.cookies.get("user_id")
    new_user = False
    if not user_id:
        user_id = str(uuid.uuid4())
        new_user = True

    app.logger.info(f"{now} [LOG] 결과창 이동 | query = {query} | 사용자: {user_id}")
    send_slack_alert(f"/search {query}")
    response = make_response(render_template("result.html"))
    if new_user:
        response.set_cookie("user_id", user_id, max_age=60 * 60 * 24 * 30)
    return response

# =======================
# 📄 질문 리스트 API
# =======================
@app.route("/api/questions")
def api_questions():
    with open(os.path.join(app.static_folder, "data-json/questions.json"), encoding="utf-8") as f:
        return jsonify(json.load(f))

# =======================
# 🔐 서버 Keep-Alive
# =======================
@app.route("/api/keep-alive")
def receive_ping():
    return "true"

# =======================
# 🛍️ 상품 추천 API
# =======================
@app.route("/api/products")
def api_products():
    query = request.args.get("query", "")
    with open(os.path.join(app.static_folder, "data-json/products.json"), encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data.get(query, []))

# =======================
# 🖱️ 클릭 로깅
# =======================
@app.route('/log/click', methods=['POST'])
def log_click():
    data = request.get_json()
    product_name = data.get('product_name', 'Unknown')
    query = data.get('product_query', 'Unknown')
    user_id = request.cookies.get("user_id", "익명")
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    app.logger.info(f"[LOG] 상세클릭 {now} | {product_name}  | {query} | 사용자: {user_id}")
    return '', 200

# =======================
# ❌ 404 에러 핸들러
# =======================
@app.errorhandler(404)
def page_not_found(e):
    user_id = request.cookies.get("user_id", "익명")
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    app.logger.info(f"[LOG] ERROR 404 {now} | {request.url} | 사용자: {user_id}")
    return render_template("404.html"), 404

# =======================
# 🤖 GPT 응답 핸들링
# =======================
@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '데이터가 없습니다.'}), 400

        user_id = request.cookies.get("user_id")
        message = data.get('message', '')
        current_query = data.get('current_query', '')
        conversation_history = data.get('conversation_history', [])

        if not message:
            return jsonify({'error': '메시지가 비어있습니다.'}), 400

        # ✅ 시스템 메시지 구성
        system_content = f"""
            당신은 제품 추천 시스템의 핵심 응답 생성자입니다.  
            ❗당신이 생성하는 응답이 시스템 전체 작동에 영향을 주며, 규칙을 지키지 않으면 사용자에게 오류 메시지가 표시됩니다.  

            따라서 반드시 아래 형식과 지침을 지켜주세요.
            - 응답은 반드시 다음 JSON 형식만 사용해야 합니다.
            - 자연어 문장만 단독으로 응답하면 시스템 오류로 간주됩니다.
            - 필드는 모두 포함해야 하며, 값이 없을 경우 "없음"으로 명시하세요.
            - 절대로 설명이나 주석, 추가 문장은 포함하지 마세요.
            - 결과 메시지는 모두 response안에 담으면 됩니다!

            JSON 응답 형식:
            {{
                "should_search": false,
                "response": "",
                "is_final": false,
                "final_keywords": "",
                "conversation_summary": ""
            }}

            🧩 응답 작성 기준:
            - "response"에는 다음 질문 또는 안내 문장을 간결하게 작성합니다.
            - "conversation_summary"에는 지금까지 확인된 요구사항을 간단히 요약합니다.
            - "final_keywords"는 is_final이 true일 때만 작성하며, 검색에 바로 사용할 수 있도록 구성합니다.

            🔐 is_final 조건:
            - 다음 항목들이 모두 수집되면 is_final을 true로 설정하세요:
            - 가격대
            - 용도
            - 브랜드 선호도
            - 추가로 필요한 기능

            📌 current_query 사용 지침:
            - 사용자의 초기 요청은 다음과 같습니다:
            "{current_query}"
            - 이는 사용자의 최종 검색 목적을 나타냅니다.
            - final_keywords를 생성할 때 반드시 current_query를 참고하여 제품명(예: 이어폰, 모니터 등)을 포함하세요.
            - current_query는 누락된 제품 종류를 보완하는 데 사용됩니다.

            🚫 자연어 출력만 하는 잘못된 예시 (절대 이렇게 응답하지 마세요):
            특정 브랜드에 대한 선호도가 있으신가요?

            ✅ 올바른 형태 (예시 목적, 복사하지 마세요):
            {{
                "should_search": false,
                "response": "특정 브랜드에 대한 선호도가 있으신가요?",
                "is_final": false,
                "final_keywords": "",
                "conversation_summary": "가격대 - 3만원대, 용도 - 운동용"
            }}
            """
        
        # ✅ 대화 메시지 구성
        messages = [{"role": "system", "content": system_content}]
        for msg in conversation_history:
            messages.append(msg)
        messages.append({"role": "user", "content": message})

        # ✅ GPT 호출
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.1,
            max_tokens=300,
            timeout=10
        )

        bot_response = response.choices[0].message.content

        # ✅ JSON 응답 검사 및 fallback 처리
        if not bot_response.startswith("{"):
            summary = " / ".join([msg["content"] for msg in conversation_history if msg["role"] == "user"][-3:]) or "요구사항 요약 실패"
            app.logger.warning(f"[WARNING] GPT 응답이 JSON 아님. fallback 적용.")
            logging.info(f'[LOG] 채팅 사용자: {user_id} | 입력: "{message}" → 응답: "{bot_response}"')
            return jsonify({
                "should_search": False,
                "response": bot_response,
                "is_final": False,
                "final_keywords": "",
                "conversation_summary": summary
            })

        # ✅ 정상 JSON 응답 처리
        response_data = json.loads(bot_response)
        if not isinstance(response_data, dict):
            raise ValueError("응답이 올바른 형식이 아닙니다.")

        for field in ["should_search", "response", "is_final", "conversation_summary"]:
            if field not in response_data:
                raise ValueError(f"필수 필드 '{field}'가 없습니다.")
        if response_data["is_final"] and "final_keywords" not in response_data:
            raise ValueError("최종 응답에는 final_keywords가 필요합니다.")

        logging.info(f'[LOG] 채팅 사용자: {user_id} | 입력: "{message}" → 응답: "{response_data["response"]}"')
        return jsonify(response_data)

    except Exception as e:
        app.logger.error(f"GPT 응답 처리 중 오류: {str(e)}")
        return jsonify({
            "should_search": False,
            "response": "죄송합니다. 잠시 후 다시 시도해주세요.",
            "is_final": False,
            "conversation_summary": "대화 요약을 생성할 수 없습니다."
        })

# =======================
# 🧭 사용자 이벤트 로깅
# =======================
@app.route('/log/event', methods=['POST'])
def log_event():
    try:
        data = request.get_json()
        user_id = request.cookies.get("user_id", "익명")
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_type = data.get("type", "event")

        detail_str = " | ".join([f'{k}: "{v}"' for k, v in data.items() if k != "type"])
        log_msg = f'[LOG] {log_type} | 사용자: {user_id} | {detail_str}'

        app.logger.info(log_msg)
        return '', 204
    except Exception as e:
        app.logger.error(f"[LOG] log_event 실패: {str(e)}")
        return jsonify({'error': '로깅 실패'}), 500

# =======================
# 🧭 SEO 관련 라우터
# =======================
@app.route('/sitemap.xml')
def sitemap():
    return send_file('public/sitemap.xml', mimetype='application/xml')

@app.route('/robots.txt')
def robots():
    return send_file('public/robots.txt', mimetype='text/plain')

# =======================
# 💰 네이버 쇼핑 API - 가격 크롤링
# =======================
def fetch_price_and_link(query):
    headers = {
        "X-Naver-Client-Id": naver_api_client_id,
        "X-Naver-Client-Secret": naver_api_client_secret
    }
    params = {
        "query": query,
        "display": 1,
        "sort": "sim"
    }

    res = requests.get("https://openapi.naver.com/v1/search/shop.json", headers=headers, params=params)

    if res.status_code == 200:
        data = res.json()
        if data["items"]:
            item = data["items"][0]
            return f"{int(item['lprice']):,}원", item["link"]
    return "정보 없음", ""

@app.route('/api/get_price', methods=['POST'])
def get_price():
    data = request.get_json()
    query = data.get('question', '')
    price, link = fetch_price_and_link(query)
    return jsonify({"price": price, "link": link})

# =======================
# 🚪 앱 실행
# =======================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
