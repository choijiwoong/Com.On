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
    # 실제 운영 채널로 메시지를 보내지 않도록 requests.post를 mock 처리
    from unittest.mock import patch, MagicMock
    with patch("app.requests.post", return_value=MagicMock(status_code=200)) as mock_post:
        response = client.get("/search?query=TESTING")
    assert response.status_code == 200
    assert mock_post.called

def test_slack_failure_does_not_break_search(client):
    from unittest.mock import patch
    with patch("app.requests.post", side_effect=requests.ConnectionError()):
        response = client.get("/search?query=TESTING")
    assert response.status_code == 200

def test_products_exact_match_without_openai(client):
    import json
    q = json.load(open("static/data-json/questions.json", encoding="utf-8"))[0]["text"]
    response = client.get("/api/products", query_string={"query": q})
    assert response.status_code == 200
    assert response.json["products"]

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



# 14. naver lprice 처리 (명세: 최저가 정보 없으면 0)
def test_fetch_price_and_link_lprice_zero():
    from unittest.mock import patch
    import app as app_module
    with patch.object(app_module.shopping_provider, "_first_item", return_value={"lprice": "0", "link": "http://x"}):
        assert app_module.fetch_price_and_link("q") == ("정보 없음", "http://x")

def test_fetch_price_and_link_normal():
    from unittest.mock import patch
    import app as app_module
    with patch.object(app_module.shopping_provider, "_first_item", return_value={"lprice": "12900", "link": "http://x"}):
        assert app_module.fetch_price_and_link("q") == ("12,900원", "http://x")

def test_fetch_price_and_link_api_failure():
    from unittest.mock import patch
    import app as app_module
    with patch.object(app_module.shopping_provider, "_first_item", return_value=None):
        assert app_module.fetch_price_and_link("q") == ("정보 없음", "")


def test_search_link_provider(monkeypatch):
    from shopping import SearchLinkProvider
    p = SearchLinkProvider()
    price, link = p.price_and_link("무선 이어폰")
    assert price == "정보 없음" and link.startswith("https://search.shopping.naver.com/")
    assert p.image("x") == ""

def test_get_provider_switch(monkeypatch):
    from shopping import get_provider, SearchLinkProvider, NaverShoppingProvider
    monkeypatch.setenv("SHOPPING_PROVIDER", "link")
    assert isinstance(get_provider(), SearchLinkProvider)
    monkeypatch.setenv("SHOPPING_PROVIDER", "naver")
    assert isinstance(get_provider(), NaverShoppingProvider)
