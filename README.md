# [🛍️ Com.On: 감성 기반 AI 쇼핑 추천 플랫폼](https://com-on.onrender.com/)

Com.On은 사용자의 자연어 질의를 기반으로 감성적이며 직관적인 쇼핑 추천을 제공하는 AI 기반 웹 서비스입니다. GPT-4를 활용해 단순 검색을 넘어서, 진짜 '조건에 맞는' 제품을 정리된 카드 형태로 제공합니다.

---

## 📌 주요 기능

### 🔍 1. 자연어 기반 쇼핑 질의
- 사용자의 요구를 대화형 인터페이스로 수집
- GPT-4를 통해 조건 분석 및 요약

### 🎯 2. 제품 추천
- `products.json`에 기반한 사전 추천
- 실시간으로 누락된 제품은 n8n Webhook을 통해 GPT 호출 및 보완
- 네이버 쇼핑 API로 가격 및 링크 자동 조회

### 🧠 3. 이어 대화 추천
- 챗봇 UI에서 조건 보완형 질문 제시
- 대화 이력을 바탕으로 `final_keywords` 추출 → 최종 검색

### 📈 4. 사용자 행동 로깅
- 클릭, 검색 이동, 이벤트 발생 등 로깅
- UUID 기반 식별자 쿠키로 사용자 추적

### 🌐 5. SEO 및 SNS 공유 최적화
- OG 태그, Twitter 카드, robots.txt, sitemap.xml 구성

---

## 📁 디렉토리 구조

```bash
📦 project-root/
├── app.py                       # Flask 서버 진입점
├── static/
│   ├── css/                     # 스타일 시트들 (style.css, chat.css 등)
│   ├── js/                      # 클라이언트 JS (result.js, logger.js 등)
│   └── data-json/              # 📁 JSON 데이터 폴더
│       ├── products.json       # 추천 제품 데이터
│       └── questions.json      # 사용자 질의 샘플
│       └── readme.md           # json 데이터 구조 설명
├── templates/
│   ├── index.html              # 메인 페이지
│   ├── result.html             # 추천 결과 페이지
│   └── 404.html                # 커스텀 오류 페이지
├── public/
│   ├── sitemap.xml             # SEO용 사이트맵
│   └── robots.txt              # 크롤링 설정
├── .env                        # 환경 변수 설정 (OpenAI, Naver API 키 등)
└── README.md                   # 프로젝트 설명 문서
```

---

## ⚙️ 환경 설정 및 실행 방법

1. `.env` 파일 생성
```bash
OPENAI_API_KEY=your_openai_api_key
NAVER_API_CLIENT_ID=your_client_id
NAVER_API_CLIENT_SECRET=your_client_secret
```

2. 필요한 패키지 설치
```bash
pip install flask openai python-dotenv requests googlesearch-python
```

3. 서버 실행
```bash
python app.py
```

4. 로컬 접속
```
http://localhost:5000
```

---

## 💬 주요 엔드포인트 요약

| 경로 | 설명 |
|------|------|
| `/` | 메인 페이지 렌더링 |
| `/search` | 추천 결과 페이지 렌더링 |
| `/api/questions` | 질의 샘플 리스트(JSON) |
| `/api/products` | 추천 제품 결과(JSON, 없을 경우 n8n Webhook 통해 동적 생성) |
| `/api/get_price` | 네이버 API로 가격/링크 조회 |
| `/chat` | 대화형 추천 응답 처리 (GPT-4o-mini 연동) |
| `/log/click` | 제품 클릭 이벤트 로깅 |
| `/log/event` | 일반 이벤트 로깅 |
| `/robots.txt`, `/sitemap.xml` | SEO 대응 |

---

## 🧪 향후 확장 계획

- [ ] 사용자 계정/히스토리 기반 개인화 추천
- [ ] 관리자용 대시보드 (조회수, 클릭률, 전환률)
- [ ] 실시간 트렌드 분석 기반 추천
- [ ] Whisper 기반 음성 질의 추천
- [ ] GPT-4o-mini 도입 (멀티모달 응답 포함)
- [ ] 파트너 제휴 링크 시스템 고도화

---

## 👨‍💻 제작 팀

**Team GRIT**
- 최지웅 (기획, 백엔드, GPT 파인튜닝)
- 안성환 (시장조사, 프론트 UI, 사용자 인터뷰)

---

## 📄 라이선스

MIT License. 자유롭게 사용 및 수정하되, 출처를 남겨주세요.

---

> "조건을 읽고, 감성까지 추천합니다."
> 
> — Com.On
