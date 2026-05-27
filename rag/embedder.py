"""
rag/embedder.py
---------------
OpenAI 텍스트 임베딩 생성 유틸리티

[ 임베딩이란? ]
  텍스트를 고차원 숫자 벡터(리스트)로 변환하는 기술입니다.
  의미가 비슷한 문장은 → 방향이 비슷한 벡터로 변환됩니다.

  예시:
    "운동용 이어폰 추천해줘"       → [0.023, -0.011, 0.087, ...]  (1536개)
    "운동할 때 쓸 이어폰 찾고 있어" → [0.021, -0.009, 0.085, ...]  (비슷!)
    "세탁기 추천해줘"               → [-0.041, 0.093, -0.012, ...] (많이 다름)

  이 벡터 간의 각도(코사인 유사도)를 비교하면
  쿼리가 완전히 달라도 "의미상 유사한" 기존 데이터를 찾을 수 있습니다.

[ 사용 모델 ]
  text-embedding-3-small
  - 차원: 1536
  - 한국어 지원
  - 저비용 (text-embedding-3-large 대비 약 1/5 비용)
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

# ---------------------------------------------------------------
# 상수 정의
# ---------------------------------------------------------------

# 사용할 OpenAI 임베딩 모델 이름
EMBEDDING_MODEL = "text-embedding-3-small"

# 임베딩 벡터의 차원 수 (참고용, 실제 계산에는 미사용)
EMBEDDING_DIM = 1536


# ---------------------------------------------------------------
# 클라이언트 초기화
# ---------------------------------------------------------------

def get_openai_client() -> OpenAI:
    """
    OpenAI 클라이언트를 생성하여 반환합니다.

    .env 파일이 존재하면 자동으로 환경 변수를 로드합니다.
    app.py와 독립적으로 동작할 수 있도록 여기서 직접 초기화합니다.

    Returns:
        OpenAI: 초기화된 OpenAI 클라이언트 객체

    Raises:
        EnvironmentError: OPENAI_API_KEY 환경 변수가 없을 때
    """
    if os.path.exists(".env"):
        load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("❌ OPENAI_API_KEY가 설정되지 않았습니다!")

    return OpenAI(api_key=api_key)


# ---------------------------------------------------------------
# 단건 임베딩
# ---------------------------------------------------------------

def get_embedding(text: str, client: OpenAI = None) -> list[float]:
    """
    텍스트 1개를 임베딩 벡터로 변환합니다.

    주로 런타임(사용자 쿼리 입력 시)에 호출됩니다.

    Args:
        text   (str)   : 임베딩할 텍스트 문자열
        client (OpenAI): 재사용할 OpenAI 클라이언트.
                         None이면 내부에서 자동 생성합니다.
                         app.py처럼 클라이언트가 이미 있다면
                         넘겨주면 API 키 재로드를 피할 수 있습니다.

    Returns:
        list[float]: 1536차원의 임베딩 벡터

    Raises:
        ValueError       : text가 비어있을 때
        EnvironmentError : API 키가 없을 때
        openai.APIError  : OpenAI API 호출 실패 시
    """
    # 빈 텍스트 방어
    if not text or not text.strip():
        raise ValueError("임베딩할 텍스트가 비어있습니다.")

    # 클라이언트가 없으면 새로 생성
    if client is None:
        client = get_openai_client()

    # OpenAI 권장 전처리: 줄바꿈을 공백으로 대체
    # (줄바꿈이 많으면 토큰 분리가 달라질 수 있음)
    cleaned_text = text.replace("\n", " ").strip()

    response = client.embeddings.create(
        input=cleaned_text,
        model=EMBEDDING_MODEL
    )

    # response.data[0].embedding → 1536개의 float 리스트
    return response.data[0].embedding


# ---------------------------------------------------------------
# 배치(일괄) 임베딩
# ---------------------------------------------------------------

def get_embeddings_batch(texts: list[str], client: OpenAI = None) -> list[list[float]]:
    """
    텍스트 여러 개를 한 번의 API 호출로 임베딩합니다.

    단건 호출을 N번 하는 것보다 비용·속도 면에서 효율적입니다.
    주로 scripts/build_embeddings.py에서 초기 인덱스 빌드 시 사용합니다.

    Args:
        texts  (list[str]): 임베딩할 텍스트 리스트
        client (OpenAI)   : 재사용할 OpenAI 클라이언트 (None이면 자동 생성)

    Returns:
        list[list[float]]: 입력 순서와 동일한 임베딩 벡터 리스트

    Raises:
        ValueError       : texts가 비어있을 때
        EnvironmentError : API 키가 없을 때
        openai.APIError  : OpenAI API 호출 실패 시

    Example:
        >>> embeddings = get_embeddings_batch(["이어폰 추천", "노트북 추천"])
        >>> len(embeddings)      # 2
        >>> len(embeddings[0])   # 1536
    """
    if not texts:
        raise ValueError("임베딩할 텍스트 리스트가 비어있습니다.")

    if client is None:
        client = get_openai_client()

    # 전처리: 모든 텍스트의 줄바꿈 제거
    cleaned_texts = [t.replace("\n", " ").strip() for t in texts]

    response = client.embeddings.create(
        input=cleaned_texts,
        model=EMBEDDING_MODEL
    )

    # OpenAI는 배치 결과를 index 순서로 반환하지 않을 수 있으므로
    # index 기준으로 정렬하여 입력 순서를 보장합니다.
    sorted_data = sorted(response.data, key=lambda item: item.index)

    return [item.embedding for item in sorted_data]


# ---------------------------------------------------------------
# 간단 동작 확인 (직접 실행 시)
# ---------------------------------------------------------------

if __name__ == "__main__":
    print("🔍 embedder.py 동작 테스트")
    print(f"  모델: {EMBEDDING_MODEL}")
    print(f"  예상 벡터 차원: {EMBEDDING_DIM}\n")

    sample_text = "운동할 때 쓸 이어폰 추천해줘"
    print(f"  입력 텍스트: '{sample_text}'")

    vector = get_embedding(sample_text)
    print(f"  임베딩 차원: {len(vector)}")
    print(f"  벡터 앞 5개 값: {[round(v, 4) for v in vector[:5]]}")
    print("\n✅ 정상 동작 확인!")
