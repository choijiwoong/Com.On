"""
shopping/providers.py
---------------------
제품 가격 / 구매 링크 / 이미지 조회 공급자(Provider) 모음.

특정 쇼핑 플랫폼에 의존하지 않도록 조회 로직을 인터페이스로 분리했습니다.
새 공급자(예: 다른 쇼핑 API)를 쓰려면 ShoppingProvider를 상속해 구현하고
get_provider()에 등록한 뒤, 환경변수 SHOPPING_PROVIDER 값만 바꾸면 됩니다.

  SHOPPING_PROVIDER=naver  (기본) 네이버 쇼핑 검색 API
  SHOPPING_PROVIDER=link          API 없이 가격비교 검색 URL만 제공 (가격/이미지 없음)

모든 공급자는 실패해도 예외를 던지지 않고 "정보 없음" / 빈 이미지를 반환합니다.
"""

import logging
import os
from abc import ABC, abstractmethod
from urllib.parse import quote

import requests

log = logging.getLogger(__name__)

NO_PRICE = "정보 없음"
NAVER_SHOP_URL = "https://openapi.naver.com/v1/search/shop.json"


def search_link(name: str) -> str:
    """특정 판매처에 묶이지 않는 가격비교 검색 URL."""
    return f"https://search.shopping.naver.com/search/all?query={quote(name)}"


class ShoppingProvider(ABC):
    @abstractmethod
    def price_and_link(self, query: str) -> tuple[str, str]:
        """(가격 문자열, 구매 링크). 실패 시 ("정보 없음", "")."""

    @abstractmethod
    def image(self, query: str) -> str:
        """썸네일 이미지 URL. 실패 시 빈 문자열."""


class SearchLinkProvider(ShoppingProvider):
    """API 없이 검색 URL만 제공하는 최소 공급자."""

    def price_and_link(self, query):
        return NO_PRICE, search_link(query)

    def image(self, query):
        return ""


class NaverShoppingProvider(ShoppingProvider):
    """네이버 쇼핑 검색 API (별도 사용 신청이 승인된 앱의 키 필요)."""

    def __init__(self, client_id, client_secret):
        self._headers = {
            "X-Naver-Client-Id": client_id or "",
            "X-Naver-Client-Secret": client_secret or "",
        }

    def _first_item(self, query):
        params = {"query": query, "display": 1, "sort": "sim", "exclude": "used:rental"}
        try:
            res = requests.get(NAVER_SHOP_URL, headers=self._headers, params=params, timeout=5)
        except requests.RequestException as e:
            log.error(f"[NAVER] 요청 실패 | query: {query[:30]} | {type(e).__name__}: {e}")
            return None
        if res.status_code != 200:
            log.error(f"[NAVER] HTTP {res.status_code} | query: {query[:30]} | {res.text[:150]}")
            return None
        items = res.json().get("items") or []
        return items[0] if items else None

    def price_and_link(self, query):
        item = self._first_item(query)
        if not item:
            return NO_PRICE, ""
        try:
            lprice = int(item.get("lprice") or 0)  # 명세: 최저가 정보 없으면 0
        except (TypeError, ValueError):
            lprice = 0
        return (f"{lprice:,}원" if lprice > 0 else NO_PRICE), item.get("link", "")

    def image(self, query):
        item = self._first_item(query)
        return item.get("image", "") if item else ""


def get_provider() -> ShoppingProvider:
    name = os.getenv("SHOPPING_PROVIDER", "naver").lower()
    if name == "link":
        return SearchLinkProvider()
    return NaverShoppingProvider(
        os.getenv("NAVER_API_CLIENT_ID"), os.getenv("NAVER_API_CLIENT_SECRET")
    )
