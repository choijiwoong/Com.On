import pytest
from app import app # app.py에서 Flask app 객체를 가져옵니다.

# pytest-flask를 사용하여 테스트용 클라이언트를 생성하는 fixture
@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

# 1. 메인 페이지('/')가 정상적으로 로드되는지 테스트
def test_index_page(client):
    """메인 페이지가 200 OK 응답을 반환하는지 확인"""
    response = client.get('/')
    assert response.status_code == 200
    #assert b"<h1>" in response.data  # 페이지에 특정 내용(<h1> 태그 등)이 포함되어 있는지 확인

# 2. 존재하지 않는 페이지에 대한 404 에러 처리 테스트
def test_404_page(client):
    """없는 URL 접근 시 404 Not Found 응답을 반환하는지 확인"""
    response = client.get('/non_existent_page')
    assert response.status_code == 404

# 3. 특정 API 엔드포인트가 올바른 JSON을 반환하는지 테스트 (API가 있다면)
def test_product_api(client):
    """/api/products 엔드포인트가 JSON 형식으로 응답하는지 확인"""
    # 만약 app.py에 /api/products 라우트가 있다고 가정
    response = client.get('/api/products')
    assert response.status_code == 200
    assert response.is_json
    products = response.get_json()
    assert isinstance(products, list) # 반환된 데이터가 리스트 형태인지 확인