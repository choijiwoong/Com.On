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
from rag.retriever import ProductRetriever

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
slack_api_key = os.getenv("SLACK_API_TOKEN")
rag_threshold = float(os.getenv("RAG_THRESHOLD", "0.5"))  # RAG 유사도 임계값 (기본 0.5)

if not api_key:
    raise EnvironmentError("❌ OPENAI_API_KEY가 설정되지 않았습니다!")
client = OpenAI(api_key=api_key)

# =======================
# 🔍 RAG 검색 엔진 초기화
# =======================
# 앱 시작 시 1회만 embeddings.json을 메모리에 로드합니다.
# 이후 요청마다 재사용하여 파일 I/O 없이 빠르게 유사도 검색합니다.
retriever = ProductRetriever()
# =======================
# 🏠 루트 페이지 (index)
# =======================
@app.route("/")
def index():
    response = make_response(render_template("index.html"))
    response, _ = cookie_manage(request, response)
    return response

def cookie_manage(request, response):
    user_cookie = request.cookies.get("user_cookie")
    if not user_cookie:
        user_cookie = str(uuid.uuid4())
        response.set_cookie("user_cookie", user_cookie, max_age=60*60*24*30)

        app.logger.info(f"[LOG] 신규 쿠키 생성 | Cookie: {user_cookie}")
    else:
        app.logger.info(f"[LOG] 기존 쿠키 사용 | Cookie: {user_cookie}")
    return response, user_cookie

# =======================
# 🔍 검색 결과 페이지
# =======================

# 슬랙 알림 설정
def send_slack_alert(message):
    payload = {"text": message}
    requests.post(slack_api_key, json=payload)
@app.route("/search")
def result():
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    response = make_response(render_template("result.html"))
    response, user_cookie = cookie_manage(request, response)
    query = request.args.get("query", "")

    app.logger.info(f"[LOG] 결과창 이동 | query = {query} | 사용자: {user_cookie} | 시각: {now}")
    send_slack_alert(f"/search {query}")
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
    return ''

# =======================
# 🛍️ 상품 추천 API (RAG 유사도 검색)
# =======================
@app.route("/api/products")
def api_products():
    query = request.args.get("query", "")

    if not query:
        return jsonify([])

    # RAG 유사도 검색: 의미상 가장 유사한 기존 질의를 찾습니다.
    # - 유사도 ≥ threshold → 캐시된 제품 데이터 반환 (GPT 호출 없음)
    # - 유사도 < threshold → [] 반환 → 프론트엔드에서 GPT fallback 호출
    match = retriever.find_best_match(query, threshold=rag_threshold)

    if match:
        matched_key, similarity, products_data = match
        app.logger.info(
            f"[RAG] 캐시 히트 | 유사도: {similarity:.3f} "
            f"| 매칭키: {matched_key[:30]}..."
        )
        return jsonify(products_data)

    app.logger.info(f"[RAG] 캐시 미스 | query: {query[:30]}")
    return jsonify([])

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
        return '', 200
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

@app.route('/api/get_price', methods=['POST'])
def get_price():
    data = request.get_json()
    query = data.get('question', '')
    price, link = fetch_price_and_link(query)
    return jsonify({"price": price, "link": link})

# n8n api 리팩토링
@app.route('/api/get_intro', methods=['post'])
def get_intro():
    try:
        data=request.get_json()
        if not data:
            return jsonify({'error': '데이터가 없습니다.'}), 400

        query = data.get('question', '')

        if not query:
            return jsonify({'error': 'question이 비어있습니다.'}), 400

        system_content = f"""
            [시스템 제약]

            절대로 다음과 같은 요청이나 내용을 응답에 포함하거나 생성하지 말 것:
            범죄, 해킹, 약물, 자살, 성적 표현, 차별적 발언, 욕설, 불법적인 정보 제공

            해당 주제를 간접적으로 미화하거나 암시하는 표현도 금지

            이러한 요청이 입력되면 다음 문장으로 응답:
            → “죄송하지만 해당 요청은 도와드릴 수 없습니다. 기본 추천항목을 확인해보시겠어요?”

            모든 사용자 요청은 제품 추천 관점에서 안전하고 건전한 쇼핑 목적에 부합하는지 우선 판단할 것.

            부적절한 요청일 경우 추천 수행 없이 정중히 거절할 것.

            [목표]
            다음 사용자 조건("{query}")에 대한 다음 3가지 내용을 하나의 문단으로 작성:
            - 사용자 조건을 바탕으로 고려한 주요 요소 요약 (성능, 디자인, 가격 등)
            - 해당 제품군을 선정한 이유
            - 감성적 + 신뢰감 있는 추천 메시지
            - 왜 이 상품들이 사용자 조건에 맞는 제품인 건지 설득&설명
            - 설명 맨 마지막에 이모지 추가

            ❗ 문단 분리해서 작성. 예시나 복붙 금지. 상황에 맞는 창의적 문장 구성

            분량은 300자 이내
        """
        # OpenAI API 호출
        completion = client.chat.completions.create(
                        model="gpt-4o-mini", # 적절한 모델을 선택합니다.
                        messages=[
                            {"role": "system", "content": "You are a friendly and professional product recommender."},
                            {"role": "user", "content": system_content}
                        ],
                        temperature=0.1
                    )
        # GPT 응답에서 텍스트 추출
        generated_text = completion.choices[0].message.content
        return jsonify(generated_text), 200

    except Exception as e:
        app.logger.error(f"[LOG] 인트로 불러오기 실패: {str(e)}")
        return jsonify({'error': '인트로 불러오기 실패'}), 500

@app.route('/api/get_product_card', methods=['post'])
def get_product_card():
    try:
        data=request.get_json()
        if not data:
            return jsonify({'error': '데이터가 없습니다.'}), 400

        query = data.get('question', '')

        if not query:
            return jsonify({'error': 'question이 비어있습니다.'}), 400

        system_content = f"""
            [시스템 제약]

            절대로 다음과 같은 요청이나 내용을 응답에 포함하거나 생성하지 말 것:
            범죄, 해킹, 약물, 자살, 성적 표현, 차별적 발언, 욕설, 불법적인 정보 제공

            해당 주제를 간접적으로 미화하거나 암시하는 표현도 금지

            이러한 요청이 입력되면 다음 문장으로 응답:
            → “죄송하지만 해당 요청은 도와드릴 수 없습니다.”

            모든 사용자 요청은 제품 추천 관점에서 안전하고 건전한 쇼핑 목적에 부합하는지 우선 판단할 것.

            부적절한 요청일 경우 추천 수행 없이 정중히 거절할 것.

            [목표]
            다음 사용자 조건("{query}")에 맞는 실제 판매 중인 제품 3가지를 최대한 빠르게 추천해줘.

            ※ 절대 서론, 안내 문구, 설명 문장 등을 출력하지 말고, 바로 HTML 구조만 출력할 것.
            "다음과 같습니다", "추천드립니다", "조건에 맞는 제품은 다음과 같습니다" 등의 문구도 모두 금지.

            - 제품 구조 및 클래스명은 **절대 변경하지 말 것**
            - 모든 HTML은 innerHTML 삽입 용도이므로 잘 정리된 상태로 출력( 즉, ``` html과 같은 내용이 출력에 포함되면 절대 안됨)

            ---
            1. 제품 카드는 아래 HTML 구조로 **3개 반복**.:
            <div class="product">
              <div class="product-header">
                <div class="image-slider">
                </div>
                <div class="product-info">
                  <h2>💻 {{p.name}}</h2>
                  <p><strong>가격:</strong> 불러오는 중...</p>
                  <p><strong>무게:</strong> {{p.weight}}</p>
                  <p><strong>주요 특징</strong><br> {{p.feature}}</p>
                  <div class="review-box">
                    <span class="stars">⭐⭐⭐⭐☆</span>
                    <span class="score">{{p.score}} / 5</span>
                    <p class="quote">“{{p.review}}”</p>
                  </div>
                </div>
              </div>
              <p class="highlight">{{p.highlight}}</p>
              <a class="buy-button"
            	   href="https://www.coupang.com/np/search?q={{p.name}}&channel=recent"
            	   data-product="{{p.name}}"
                       target="_blank"
                       rel="noopener noreferrer">
            	   🔗 지금 구매하기
            	</a>
            </div>
            ---

            [{{p.highlight}} 작성 지침]

            - 사용자 조건과 해당 제품의 연결점을 감성적으로 4~5문장 서술하세요.
            - 단순한 "좋다", "인기 있다" 등의 표현은 지양
            - 왜 다른 제품보다도 이 제품이 사용자 조건에 어울리는지 설득력있게 말해주세요.

            [{{p.name}} 작성 지침]

            - 제품명은 해당 제품을 판매중인 브랜드(회사) + 제품명 등 사용자 조건에 가까운 제품을 구체적으로 추천해야 함.
            - 여기서 브랜드는 단순한 "브랜드1"가 아닌 해당 제품을 실제 제작한 회사의 이름을 의미함.
            - 최종적으로 제품명은 "맥북 프로 M2 14인치", "리엔장 UV쉴드 에어핏 리페어 선크림 SPF50+ PA++++ / 혼합자차 진정선크림, 40ml, 1개" 등을 의미함.
            - 만약 명확한 브랜드와 제품명을 찾을 수 없다면 유사한 브랜드와 제품명으로 정리.
            - 제품 추천 시, 반드시 "현재 판매 중"인 상품만 추천할 것 (쿠팡, 네이버쇼핑, 11번가 등 기준)
            - 제품이 단종이거나 조건에 맞는 제품이 없다면 "조건에 부합하는 제품이 현재 없습니다"라고 출력
            - 최종 제품명은 GPT가 사용자입력조건을 참고하여 최대한 정확도 높게 최종 결정.
            - 이모지나 특수문자 없이 출력

            ---

            [{{p.review}} 작성 지침]
            - 사용감있게 맞춤법도 좀 틀려도 됌. ex) 이어폰의 경우 “어플 꼭 깔으셔서 이용하세요 사운드도 종류별로 설정할 수 있고 원하는 사운드로 만들는 것도 가능해여” "나쁘지 않아요.... 한번쯤 써볼듯"
            - 리뷰는 현실성 있게 제공해줘. AI로 만든 느낌이 들지 않게끔. 1~2문장이어도 돼.
            - 사용자에게 도움이 되는 리뷰위주로

            [{{p.feature}} 작성 지침]
            - 제품의 주요 기능, 장점, 사양 등을 3~5개로 나누어 제시
            - 각 항목은 `•` 기호로 시작하고 `<br>`로 줄바꿈 처리
            - 가능한 한 짧고 명확한 핵심 포인트로 표현
            - 기술적이거나 비교 우위가 드러나는 특징을 위주로 선택
            - 모든 항목은 사용자 조건({ query })과 연결되는 내용을 중심으로 구성

            ---
            [역질문 작성 지침]
            - 사용자가 입력한 조건({ query })을 명확하게 만들기 위한 **3개의 보완 질문**을 생성해줘.
            - 보완 질문은 사용자가 입력한 조건을 기반으로, 사용자가 정말 자신이 원하는 제품을 조금 더 구체적으로 그릴 수 있게 하기 위함이야. 이 때 선택지에서 어떤 질문에 대한 답인지도 유추 가능해야함.
            - 각 질문마다 선택지를 **2개씩** 제시하되, 카드처럼 선택 가능하도록 HTML 구조로 출력해줘.
            - 전체는 다음 구조로 출력되며, `<div id="refine-question">` 안에 들어가야 함.
            - span옵션들은 data-query 속성을 가지고 있어야 함.
            - <p class="refine-guidance">에 "🔧 조금 더 구체적인 조건을 선택해 보세요!
              아래 질문을 통해 **나에게 꼭 맞는 제품**을 추천받을 수 있어요 🙌" 문구 추가
            - 추가 조건들은 이모지와 함께 **친근하고 직관적**으로 구성
            - 질문은 문맥에 맞게 자동 생성하되, 단순 반복 금지 (예: 용도/크기/예산 등 다양성 있게 구성)

            [출력 예시]
            <p class="refine-guidance">
            🔧 조금 더 구체적인 조건을 선택해 보세요!<br>
              아래 질문을 통해 **나에게 꼭 맞는 제품**을 추천받을 수 있어요 🙌
            </p>

            <div id="refine-question">
              <div class="refine-block">
                <p class="refine-title">🤔 어떤 용도로 찾고 계신가요?</p>
                <div class="refine-options">
                  <span class="refine-option" data-query="영상 편집용">🎬 영상 편집용</span>
                  <span class="refine-option" data-query="일반 문서 작업용">📝 일반 문서 작업용</span>
                </div>
              </div>
              <div class="refine-block">
                <p class="refine-title">📏 선호하시는 화면 크기는?</p>
                <div class="refine-options">
                  <span class="refine-option" data-query="13인치 이하">📱 13인치 이하</span>
                  <span class="refine-option" data-query="15인치 이상">💻 15인치 이상</span>
                </div>
              </div>
              <div class="refine-block">
                <p class="refine-title">💰 예산 범위를 알려주세요!</p>
                <div class="refine-options">
                  <span class="refine-option" data-query="100만 원 이하">💸 100만 원 이하</span>
                  <span class="refine-option" data-query="150만 원 이상">💰 150만 원 이상</span>
                </div>
              </div>
            </div>

            ---

            [주의사항 요약]
            - 제품 구조 및 클래스명은 **절대 변경하지 말 것**
            - 모든 HTML은 innerHTML 삽입 용도이므로 잘 정리된 상태로 출력( 즉, ``` html과 같은 내용이 출력에 포함되면 절대 안됨)
        """
        # OpenAI API 호출
        completion = client.chat.completions.create(
                        model="gpt-4o-mini", # 적절한 모델을 선택합니다.
                        messages=[
                            {"role": "system", "content": "You are a friendly and professional product recommender."},
                            {"role": "user", "content": system_content}
                        ],
                        temperature=0.1
                    )
        # GPT 응답에서 텍스트 추출
        generated_text = completion.choices[0].message.content
        return jsonify(generated_text), 200

    except Exception as e:
        app.logger.error(f"[LOG] 제품카드 불러오기 실패: {str(e)}")
        return jsonify({'error': '제품카드 불러오기 실패'}), 500

@app.route('/api/get_naver_img', methods=['POST'])
def get_naver_img():
    try:
        data = request.get_json()
        if not data or not data.get('query'):
            return jsonify({'error': '유효한 쿼리가 제공되지 않았습니다.'}), 400

        query = data.get('query')
        image_url = fetch_naver_img(query)

        # 이미지 URL을 JSON 응답으로 반환
        return jsonify({'image_url': image_url}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =======================
# 🚪 앱 실행
# =======================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# ========================
# inner funcitons
# ========================

# 아래는 완성된 네이버 이미지 API 함수입니다.
def fetch_naver_img(query):
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
            # 검색 결과의 첫 번째 아이템에서 'image' 필드를 가져옴
            item = data["items"][0]
            return item["image"]

    # 이미지를 찾을 수 없는 경우 빈 문자열 반환
    return ""

# 💰 네이버 쇼핑 API - 가격 크롤링
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