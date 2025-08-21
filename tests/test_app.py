import pytest, os, uuid, requests
from app import app # app.py에서 Flask app 객체를 가져옵니다.
from app import cookie_manage
from dotenv import load_dotenv

# =======================
# 🔐 환경 변수 및 API 키 로드
# =======================
if os.path.exists(".env"):
    load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
naver_api_client_id = os.getenv("NAVER_API_CLIENT_ID")
naver_api_client_secret = os.getenv("NAVER_API_CLIENT_SECRET")
slack_api_key=os.getenv("SLACK_API_TOKEN")

# github push test(token expired)
# pytest-flask를 사용하여 테스트용 클라이언트를 생성하는 fixture
@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_cookie_manage_new_user(client):
    # given
    # when
    response = client.get('/')
    # then
    assert response.status_code == 200
    assert "user_cookie" in response.headers['Set-Cookie']
def test_cookie_manage_existing_user(client):
    # given
    response = client.get('/') # first visit
    # when
    response = client.get('/') # second visit
    # then
    assert 'Set-Cookie' not in response.headers
    assert response.status_code == 200

def test_slack_api(client):
    # given
    # when
    response1 = requests.get(slack_api_key)
    response2 = requests.post(slack_api_key, json={"text": "slack api test"})# wrong request
    # then
    assert response1.status_code == 400 # 서버에서 응답이 오긴 하는지
    assert response2.status_code == 200 # 테스트 메시지 발송여부 확인

# 1. 메인 페이지('/')가 정상적으로 로드되는지 테스트
def test_index_page(client):
    """메인 페이지가 200 OK 응답을 반환하는지 확인"""
    response = client.get('/')
    assert response.status_code == 200

# 2. 존재하지 않는 페이지에 대한 404 에러 처리 테스트
def test_404_page(client):
    """없는 URL 접근 시 404 Not Found 응답을 반환하는지 확인"""
    response = client.get('/non_existent_page')
    assert response.status_code == 404

# 3. server keep-alive
def test_receive_ping(client):
    response = client.get("/api/keep-alive")
    assert response.status_code == 200

# 4. get questions
def test_api_questions(client):
    response = client.get("/api/questions")
    assert response.status_code == 200
    assert response.is_json

# 5. get data json
def test_search_api(client):
    response = client.get("/search?query=운동할 때 쓸 이어폰 찾고 있어! 10만원 이하에 베이스 잘 들리고 생활방수 되는 제품 추천 좀 해줘!")

# 6. log test
def test_log_click(client):
    data = {"product_name": "TESTING", "product_query": "TESTING"}
    response = client.post("/log/click", json = data)
    assert response.status_code == 200

# 7. chat test************************
def test_chat(client):
    data = {"message": "TESTING", "current_query": "TESTING", 'conversation_history': "TESTING"}
    response = client.post("/log/click", json = data)
    assert response.status_code == 200

# 8. log event test
def test_log_event(client):
    data = {"type": "TESTING", "product_query": "TESTING"}
    response = client.post("/log/click", json = data)
    assert response.status_code == 200

# 9. SEO
def test_sitemap(client):
    response = client.get("/sitemap.xml")
    assert response.status_code == 200

    response = client.get("/robots.txt")
    assert response.status_code == 200

# 10. naver price api(key none)
def test_get_price(client):
    data = {"question": "커피원두"}
    response = client.post("/api/get_price", json = data)
    assert response.status_code == 200

# 11. naver img api(key none)
def test_get_price(client):
    data = {"query": "커피원두"}
    response = client.post("/api/get_naver_img", json = data)
    assert response.status_code == 200

# 12. get intro message
# 13. get product card

