"""
rag/retriever.py
-----------------
임베딩 기반 유사도 검색 엔진 (RAG의 핵심 Retrieval 부분)

[ 동작 원리 ]
  1. 앱 시작 시 embeddings.json과 products.json을 메모리에 로드
  2. 사용자 쿼리가 들어오면 → 쿼리를 임베딩 벡터로 변환
  3. 저장된 모든 벡터와 코사인 유사도를 계산
  4. 가장 유사한 항목이 임계값(threshold) 이상이면 → 캐시된 제품 반환
  5. 미달이면 → None 반환 (호출부에서 GPT fallback 처리)

[ 코사인 유사도란? ]
  두 벡터가 이루는 각도의 코사인 값 (범위: -1 ~ 1)
  - 1.0 에 가까울수록 → 두 문장의 의미가 거의 동일
  - 0.0 에 가까울수록 → 의미가 무관함
  - 실사용 임계값: 0.80 ~ 0.92 사이가 적절

  공식: cos(θ) = (A · B) / (|A| × |B|)
"""

import json
import logging
import os
import numpy as np
from openai import OpenAI
from rag.embedder import get_embedding, get_openai_client

log = logging.getLogger(__name__)

# ---------------------------------------------------------------
# 경로 상수
# ---------------------------------------------------------------

# 이 파일 기준으로 프로젝트 루트를 계산합니다.
_HERE        = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(_HERE)

EMBEDDINGS_PATH = os.path.join(PROJECT_ROOT, "static", "data-json", "embeddings.json")
PRODUCTS_PATH   = os.path.join(PROJECT_ROOT, "static", "data-json", "products.json")


# ---------------------------------------------------------------
# 코사인 유사도 계산 (numpy 사용)
# ---------------------------------------------------------------

def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    두 벡터 사이의 코사인 유사도를 계산합니다.

    Args:
        a, b (np.ndarray): 비교할 두 임베딩 벡터

    Returns:
        float: 유사도 값 (-1.0 ~ 1.0)
               임베딩 벡터는 항상 양수 방향이므로 실제론 0.0 ~ 1.0
    """
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    # 영벡터 방어 (정상 임베딩에서는 발생하지 않음)
    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(np.dot(a, b) / (norm_a * norm_b))


# ---------------------------------------------------------------
# 검색 엔진 클래스
# ---------------------------------------------------------------

class ProductRetriever:
    """
    embeddings.json을 메모리에 로드하고
    코사인 유사도 기반으로 가장 유사한 제품 데이터를 검색합니다.

    앱 시작 시 1번만 초기화하고, 이후 검색 시마다 재사용합니다. (싱글턴 패턴)

    Usage:
        retriever = ProductRetriever()
        result = retriever.find_best_match("운동용 이어폰 추천해줘")
        if result:
            key, similarity, products_data = result
    """

    def __init__(self):
        """
        embeddings.json과 products.json을 로드하여 메모리에 준비합니다.

        Raises:
            FileNotFoundError: embeddings.json 또는 products.json이 없을 때
                               → scripts/build_embeddings.py를 먼저 실행해야 합니다.
        """
        self._client: OpenAI = None  # 지연 초기화 (첫 검색 시 생성)

        # embeddings.json 로드: { "질의 문자열": [float, ...] }
        if not os.path.exists(EMBEDDINGS_PATH):
            raise FileNotFoundError(
                f"embeddings.json을 찾을 수 없습니다: {EMBEDDINGS_PATH}\n"
                "먼저 scripts/build_embeddings.py를 실행해 주세요."
            )
        with open(EMBEDDINGS_PATH, encoding="utf-8") as f:
            raw_embeddings = json.load(f)

        # products.json 로드: { "질의 문자열": { explanation, products } }
        if not os.path.exists(PRODUCTS_PATH):
            raise FileNotFoundError(f"products.json을 찾을 수 없습니다: {PRODUCTS_PATH}")
        with open(PRODUCTS_PATH, encoding="utf-8") as f:
            self._products = json.load(f)

        # 빠른 유사도 계산을 위해 numpy 배열로 변환하여 캐싱
        # keys[i] ↔ vectors[i] 인덱스가 반드시 일치해야 합니다.
        self._keys    = list(raw_embeddings.keys())
        self._vectors = np.array(list(raw_embeddings.values()), dtype=np.float32)
        # shape: (N개 질의, 1536차원)

    # ── 내부 유틸 ─────────────────────────────────────────────

    def _get_client(self) -> OpenAI:
        """OpenAI 클라이언트를 지연 생성합니다. (첫 호출 시 1회만 초기화)"""
        if self._client is None:
            self._client = get_openai_client()
        return self._client

    # ── 핵심 검색 메서드 ──────────────────────────────────────

    def find_best_match(
        self,
        query: str,
        threshold: float = 0.82
    ) -> tuple[str, float, dict] | None:
        """
        입력 쿼리와 의미상 가장 유사한 기존 제품 데이터를 반환합니다.

        동작:
          1. query를 임베딩 벡터로 변환
          2. 저장된 모든 벡터와 코사인 유사도 계산 (numpy 배치 연산)
          3. 최고 유사도 > threshold → 해당 제품 데이터 반환
          4. 최고 유사도 ≤ threshold → None 반환

        Args:
            query     (str)  : 사용자 검색 쿼리
            threshold (float): 캐시 히트 최소 유사도 (기본 0.82)
                               높을수록 엄격, 낮을수록 관대

        Returns:
            (matched_key, similarity, products_data) 또는 None
              - matched_key   : 매칭된 기존 질의 문자열
              - similarity    : 코사인 유사도 (0.0 ~ 1.0)
              - products_data : { "explanation": ..., "products": [...] }
        """
        if not query or not query.strip():
            return None

        if not self._keys:
            return None

        # Step 1. 쿼리 임베딩
        query_vector = np.array(
            get_embedding(query, client=self._get_client()),
            dtype=np.float32
        )

        # Step 2. 배치 코사인 유사도 계산
        # 분모: (N,) 벡터 — 각 저장 벡터의 norm
        norms = np.linalg.norm(self._vectors, axis=1)          # shape: (N,)
        query_norm = np.linalg.norm(query_vector)

        if query_norm == 0:
            return None

        # 내적 계산: (N, 1536) × (1536,) → (N,)
        dot_products  = self._vectors @ query_vector            # shape: (N,)
        similarities  = dot_products / (norms * query_norm)    # shape: (N,)

        # Step 3. 최고 유사도 인덱스 찾기
        best_idx        = int(np.argmax(similarities))
        best_similarity = float(similarities[best_idx])
        best_key        = self._keys[best_idx]

        # Step 4. 임계값 판단 (히트/미스 모두 유사도 로깅)
        if best_similarity < threshold:
            log.info(
                f"[RAG] 캐시 미스 | 최고유사도: {best_similarity:.3f} (threshold: {threshold}) "
                f"| 최근접키: {best_key[:30]}..."
            )
            return None  # 유사한 항목 없음 → GPT fallback

        products_data = self._products.get(best_key)
        if products_data is None:
            return None  # embeddings.json과 products.json 간 불일치

        return best_key, best_similarity, products_data

    # ── 캐시 추가 (Phase 5 — 자동 학습) ─────────────────────

    def add_to_cache(self, query: str, products_data: dict) -> None:
        """
        새로 GPT가 생성한 결과를 임베딩과 함께 저장합니다.
        다음 유사 쿼리 시 GPT 호출 없이 재사용할 수 있게 됩니다.

        Args:
            query        (str) : 새로 추가할 질의 문자열
            products_data(dict): { "explanation": ..., "products": [...] }
        """
        if query in self._keys:
            return  # 이미 존재하면 스킵

        # 임베딩 생성
        new_vector = np.array(
            get_embedding(query, client=self._get_client()),
            dtype=np.float32
        )

        # 메모리 업데이트
        self._keys.append(query)
        self._vectors = np.vstack([self._vectors, new_vector])  # 행 추가
        self._products[query] = products_data

        # ── embeddings.json 파일 업데이트 ──
        existing_embeddings = {}
        if os.path.exists(EMBEDDINGS_PATH):
            with open(EMBEDDINGS_PATH, encoding="utf-8") as f:
                existing_embeddings = json.load(f)

        existing_embeddings[query] = new_vector.tolist()
        with open(EMBEDDINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(existing_embeddings, f, ensure_ascii=False, indent=2)

        # ── products.json 파일 업데이트 ──
        with open(PRODUCTS_PATH, "w", encoding="utf-8") as f:
            json.dump(self._products, f, ensure_ascii=False, indent=2)
