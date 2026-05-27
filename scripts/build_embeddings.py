"""
scripts/build_embeddings.py
----------------------------
products.json의 모든 질의(키)를 임베딩 벡터로 변환하여
embeddings.json에 저장하는 초기 인덱스 빌드 스크립트

[ 언제 실행하나요? ]
  1. 최초 RAG 시스템 세팅 시 (지금)
  2. products.json에 새 질의(키)를 수동으로 추가했을 때

[ 실행 방법 ]
  # Docker 환경 (권장)
  docker run --rm --env-file .env comon-app python scripts/build_embeddings.py

  # 로컬 환경 (패키지 설치 후)
  python scripts/build_embeddings.py

[ 결과 ]
  static/data-json/embeddings.json 생성/갱신
  {
    "질의 문자열 A": [0.023, -0.011, ...],  ← 1536차원 벡터
    "질의 문자열 B": [0.041,  0.009, ...],
    ...
  }

[ 비용 안내 ]
  text-embedding-3-small 기준 약 $0.00002 / 1K 토큰
  products.json 현재 키 수(~5개) 기준 거의 무료 수준
"""

import json
import os
import sys

# ---------------------------------------------------------------
# 경로 설정
# ---------------------------------------------------------------

# 이 스크립트가 어느 디렉토리에서 실행되더라도
# 프로젝트 루트를 기준으로 경로를 잡습니다.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)  # rag 패키지를 import할 수 있도록 경로 추가

PRODUCTS_PATH   = os.path.join(PROJECT_ROOT, "static", "data-json", "products.json")
EMBEDDINGS_PATH = os.path.join(PROJECT_ROOT, "static", "data-json", "embeddings.json")

# ---------------------------------------------------------------
# rag 패키지의 임베딩 유틸 import
# ---------------------------------------------------------------
from rag.embedder import get_embeddings_batch, get_openai_client, EMBEDDING_MODEL


# ---------------------------------------------------------------
# 헬퍼: 기존 embeddings.json 로드
# ---------------------------------------------------------------

def load_existing_embeddings() -> dict:
    """
    이미 생성된 embeddings.json이 있으면 불러옵니다.
    없으면 빈 딕셔너리를 반환합니다.

    이 값을 기준으로 '이미 임베딩된 키'는 건너뛰어
    불필요한 API 호출을 막습니다. (증분 업데이트)

    Returns:
        dict: { "질의 문자열": [임베딩 벡터] }
    """
    if os.path.exists(EMBEDDINGS_PATH):
        with open(EMBEDDINGS_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


# ---------------------------------------------------------------
# 헬퍼: embeddings.json 저장
# ---------------------------------------------------------------

def save_embeddings(embeddings: dict) -> None:
    """
    임베딩 딕셔너리를 embeddings.json에 저장합니다.

    Args:
        embeddings (dict): { "질의 문자열": [임베딩 벡터] }
    """
    with open(EMBEDDINGS_PATH, "w", encoding="utf-8") as f:
        # ensure_ascii=False → 한글이 유니코드 이스케이프(\uXXXX) 없이 저장됨
        # indent=2 → 사람이 읽기 쉬운 형태로 저장
        json.dump(embeddings, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------
# 메인 빌드 함수
# ---------------------------------------------------------------

def build_embeddings() -> None:
    """
    products.json의 모든 키를 임베딩하여 embeddings.json에 저장합니다.

    동작 흐름:
      1. products.json 읽기 → 모든 질의(키) 추출
      2. 기존 embeddings.json 읽기 → 이미 처리된 키 확인
      3. 새로운 키만 선별 → 배치 임베딩 API 호출
      4. 기존 결과 + 새 결과 합쳐서 embeddings.json 저장
    """

    print("=" * 55)
    print("  RAG 임베딩 인덱스 빌더")
    print(f"  사용 모델: {EMBEDDING_MODEL}")
    print("=" * 55)

    # ── Step 1. products.json 로드 ───────────────────────────
    print("\n[1/4] products.json 로드 중...")
    if not os.path.exists(PRODUCTS_PATH):
        print(f"  오류: 파일을 찾을 수 없습니다 → {PRODUCTS_PATH}")
        sys.exit(1)

    with open(PRODUCTS_PATH, encoding="utf-8") as f:
        products = json.load(f)

    all_keys = list(products.keys())
    print(f"  총 질의(키) 수: {len(all_keys)}개")

    # ── Step 2. 기존 embeddings.json 로드 ───────────────────
    print("\n[2/4] 기존 임베딩 데이터 확인 중...")
    existing = load_existing_embeddings()
    print(f"  기존에 임베딩된 키: {len(existing)}개")

    # 아직 임베딩되지 않은 새 키만 추려냅니다
    new_keys = [k for k in all_keys if k not in existing]
    print(f"  새로 임베딩할 키:   {len(new_keys)}개")

    if not new_keys:
        print("\n  모든 키가 이미 임베딩되어 있습니다. 작업 완료!")
        print(f"  저장 경로: {EMBEDDINGS_PATH}")
        return

    # ── Step 3. 배치 임베딩 API 호출 ────────────────────────
    print("\n[3/4] OpenAI 임베딩 API 호출 중...")
    print("  (새 키 목록)")
    for i, key in enumerate(new_keys, 1):
        # 긴 키는 40자까지만 출력
        preview = key[:40] + "..." if len(key) > 40 else key
        print(f"    {i}. {preview}")

    client = get_openai_client()

    # 여러 키를 한 번에 API 호출 → 비용·속도 최적화
    new_vectors = get_embeddings_batch(new_keys, client=client)

    print(f"\n  완료! {len(new_vectors)}개 벡터 생성됨 (각 {len(new_vectors[0])}차원)")

    # ── Step 4. 저장 ─────────────────────────────────────────
    print("\n[4/4] embeddings.json 저장 중...")

    # 기존 임베딩에 새 임베딩을 추가
    updated = {**existing, **dict(zip(new_keys, new_vectors))}
    save_embeddings(updated)

    print(f"  총 저장된 키: {len(updated)}개")
    print(f"  저장 경로: {EMBEDDINGS_PATH}")
    print("\n  빌드 완료!")
    print("=" * 55)


# ---------------------------------------------------------------
# 진입점
# ---------------------------------------------------------------

if __name__ == "__main__":
    build_embeddings()
