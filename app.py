from flask import Flask, render_template, request, jsonify, make_response, send_file
import json
import logging
import os
from googlesearch import search
from datetime import datetime
import uuid
from openai import OpenAI
from dotenv import load_dotenv

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

# .env가 존재하면 로드 (로컬에서만 작동)
if os.path.exists(".env"):
    load_dotenv()

# 환경변수에서 API 키 가져오기 (Render 환경에서도 동작)
api_key = os.getenv("OPENAI_API_KEY")

# 안전성 체크
if not api_key:
    raise EnvironmentError("❌ OPENAI_API_KEY가 설정되지 않았습니다!")

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=api_key)

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '데이터가 없습니다.'}), 400
        
        # 쿠키 확인 및 사용자 ID 추출 (없으면 신규 생성)
        user_id = request.cookies.get("user_id")
            
        message = data.get('message', '')
        current_query = data.get('current_query', '')
        conversation_history = data.get('conversation_history', [])
        
        if not message:
            return jsonify({'error': '메시지가 비어있습니다.'}), 400

        # 사용자 메시지 로깅
        # logging.info(f"[LOG] 채팅 user {request.remote_addr} {message}")
            
        # 사용자의 응답을 처리
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

        try:
            messages = [
                {"role": "system", "content": system_content}
            ]
            
            # 이전 대화 내용 추가
            for msg in conversation_history:
                messages.append(msg)
                
            # 현재 메시지 추가
            messages.append({"role": "user", "content": message})

            response = client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.7,
                max_tokens=300,
                timeout=10
            )

            bot_response = response.choices[0].message.content

            # GPT 응답이 JSON이 아닐 때 fallback으로 감쌀 때
            if not bot_response.startswith("{"):
                app.logger.warning(f"[WARNING] 채팅 gpt {request.remote_addr} {bot_response} GPT 응답이 JSON 형식이 아님. 자동 감싸기 처리.")

                # ✅ 최신까지의 사용자 입력을 기반으로 간단한 요약 자동 생성
                user_messages = [msg["content"] for msg in conversation_history if msg["role"] == "user"]
                summary = " / ".join(user_messages[-3:]) if user_messages else "요구사항 요약 실패"

                safe_response = {
                    "should_search": False,
                    "response": bot_response,
                    "is_final": False,
                    "final_keywords": "",
                    "conversation_summary": summary
                }

                # ✅ fallback에서도 사용자 입력/응답 로그
                logging.info(f'[LOG] 채팅 사용자: {user_id} | 입력: "{message}" → 응답: "{bot_response}"')

                return jsonify(safe_response)

            
            # GPT 응답 로깅
            # logging.info(f"[LOG] 채팅 gpt {request.remote_addr} {bot_response}")

            try:
                response_data = json.loads(bot_response)
                if not isinstance(response_data, dict):
                    raise ValueError("응답이 올바른 형식이 아닙니다.")
                
                # ✅ 사용자 대화-응답 한줄 통합 로그
                if response_data.get("response"):
                    logging.info(f'[LOG] 채팅 사용자: {user_id} | 입력: "{message}" → 응답: "{response_data["response"]}"')

                required_fields = ["should_search", "response", "is_final", "conversation_summary"]
                for field in required_fields:
                    if field not in response_data:
                        raise ValueError(f"필수 필드 '{field}'가 없습니다.")
                        
                if response_data["is_final"] and "final_keywords" not in response_data:
                    raise ValueError("최종 응답에는 final_keywords가 필요합니다.")
                        
                return jsonify(response_data)
                
            except json.JSONDecodeError as e:
                app.logger.error(f"JSON 파싱 오류: {str(e)}")
                app.logger.error(f"실패한 GPT 응답:\n{bot_response}")
                return jsonify({
                    "should_search": False,
                    "response": bot_response,
                    "is_final": False,
                    "conversation_summary": "대화 요약을 생성할 수 없습니다."
                })
                
        except Exception as e:
            app.logger.error(f"GPT 응답 처리 중 오류: {str(e)}")
            return jsonify({
                "should_search": False,
                "response": "죄송합니다. 잠시 후 다시 시도해주세요.",
                "is_final": False,
                "conversation_summary": "대화 요약을 생성할 수 없습니다."
            })
            
    except Exception as e:
        app.logger.error(f"채팅 처리 중 오류 발생: {str(e)}")
        return jsonify({
            "should_search": False,
            "response": "죄송합니다. 잠시 후 다시 시도해주세요.",
            "is_final": False,
            "conversation_summary": "대화 요약을 생성할 수 없습니다."
        })

# 이벤트 로깅
@app.route('/log/event', methods=['POST'])
def log_event():
    try:
        data = request.get_json()
        user_id = request.cookies.get("user_id", "익명")
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_type = data.get("type", "event")  # 기본값은 event

        # 구체적 내용 구성
        detail_parts = []
        for key, value in data.items():
            if key != "type":
                detail_parts.append(f'{key}: "{value}"')

        detail_str = " | ".join(detail_parts)
        log_msg = f'[LOG] {log_type} | 사용자: {user_id} | {detail_str}'

        app.logger.info(log_msg)
        return '', 204
    except Exception as e:
        app.logger.error(f"[LOG] log_event 실패: {str(e)}")
        return jsonify({'error': '로깅 실패'}), 500



# SEO 최적화
# sitemap.xml
@app.route('/sitemap.xml')
def sitemap():
    return send_file('public/sitemap.xml', mimetype='application/xml')

# robots.txt
@app.route('/robots.txt')
def robots():
    return send_file('public/robots.txt', mimetype='text/plain')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

