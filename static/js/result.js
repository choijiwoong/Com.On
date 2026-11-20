// ==============================
// 📦 Google Tag Manager 삽입
// ==============================
(function (w, d, s, l, i) {
  w[l] = w[l] || [];
  w[l].push({ 'gtm.start': new Date().getTime(), event: 'gtm.js' });
  var f = d.getElementsByTagName(s)[0],
      j = d.createElement(s),
      dl = l != 'dataLayer' ? '&l=' + l : '';
  j.async = true;
  j.src = 'https://www.googletagmanager.com/gtm.js?id=' + i + dl;
  f.parentNode.insertBefore(j, f);
})(window, document, 'script', 'dataLayer', 'GTM-MZHQSKG5');


// ==============================
// 🔍 URL 파라미터에서 'query' 추출
// ==============================
const params = new URLSearchParams(window.location.search);
const query = params.get("query");
let stopLoadingAnimation; // 로딩 애니메이션 종료 함수 보관용


// ==============================
// 🖼️ 이미지 유효성 검사 및 선택
// ==============================
async function getValidImageURLs(questionText, max = 2) {
  const validImages = [];
  try {
    const res = await fetch("/api/get_naver_img", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: questionText })
    });
    const data = await res.json();
    const imageUrl = data.image_url;

    // 썸네일 이미지가 실제 표시 가능한지 확인
    const isValid = await validateImage(imageUrl);
    if (isValid) {
      validImages.push(imageUrl);
    }

  } catch (err) {
    console.error("이미지 오류:", err);
  }
  return validImages;
}

// 이미지 주소가 실제로 로딩 가능한지 확인
function validateImage(url) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve(true);
    img.onerror = () => resolve(false);
    img.src = url;
  });
}


// ==============================
// ⌨️ 텍스트 타이핑 애니메이션
// ==============================
function typeText(text, el, speed = 30) {
  let i = 0;
  const type = () => {
    if (i < text.length) {
      el.textContent += text.charAt(i++);
      setTimeout(type, speed);
    }
  };
  type();
  startFancyLoading(); // 로딩 애니메이션 시작
}

// open ai단에서 가져온 html코드에서 ```html표시가 있다면 제거
function extractHtmlCode(codeBlock) {
  if (typeof codeBlock !== 'string') {
    return ''; // Return an empty string if the input is not a string
  }

  const trimmedCode = codeBlock.trim();

  if (trimmedCode.startsWith('```html') && trimmedCode.endsWith('```')) {
    // Remove the starting and ending markers
    logEvent({
      type: "openai ```html태그 제거 완료",
      query: query
    });
    return trimmedCode.substring(7, trimmedCode.length - 3).trim();
  }

  // Return the original string if the markers are not found
  return codeBlock;
}

// ==============================
// 🔁 추천 HTML을 n8n에서 불러와 렌더링
// ==============================
const fetchFallbackProductData = async (questionText) => {
  const container = document.getElementById("product-container");
  const startTime = performance.now();
  const stopLoading = startFancyLoading();

  try {
    const introPromise = fetch('/api/get_intro', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: questionText })
    }).then(res => {
      if (!res.ok) throw new Error("인트로 추천 불러오기 실패");
      return res.json();
    });

    const productPromise = fetch('/api/get_product_card', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: questionText })
    }).then(res => {
      if (!res.ok) throw new Error("제품카드 불러오기 실패");
      return res.json();
    });

    startFancyLoading();

    introPromise.then(introText => {
      typeText(extractHtmlCode(introText), document.getElementById("queryExplanation"));
    });

    // 제품 HTML이 도착하면, 다음 로직을 순차적으로 실행합니다.
    productPromise.then(async (html) => {
      const loader = document.getElementById("loading-visual");
      if (loader) loader.remove();
      if (typeof stopLoading === "function") stopLoading();
      container.innerHTML += extractHtmlCode(html);

      // === 이 부분부터 비동기 로직이 시작됩니다. ===
      // 6. 각 제품에 이미지와 가격/링크 비동기 삽입
      const products = container.querySelectorAll(".product");
      const updateTasks = Array.from(products).map(async (product) => {
        const title = product.querySelector("h2")?.textContent.replace("💻", "").trim();
        const slider = product.querySelector(".image-slider");

        if (!title || !slider) return;

        const [images, { price, link }] = await Promise.all([
          getValidImageURLs(title, 2),
          fetchPriceAndLink(title)
        ]);

        // 이미지 삽입
        if (images.length > 0) {
          slider.innerHTML = `
            ${images.map((img, i) => `
              <img src="${img}" class="slide ${i === 0 ? 'active' : ''}" alt="${title} 이미지 ${i + 1}">
            `).join('')}
            ${images.length > 1 ? `
              <button class="slider-btn prev">&#10094;</button>
              <button class="slider-btn next">&#10095;</button>
            ` : ''}
          `;
        }

        // 가격 정보 삽입
        const priceTag = product.querySelector(".product-info p:nth-child(2)");
        if (priceTag) priceTag.innerHTML = `<strong>가격:</strong> ${price}`;

        // 구매 버튼 링크 삽입
        const buyBtn = product.querySelector(".buy-button");
        if (buyBtn) {
          buyBtn.setAttribute("href", link);
          buyBtn.setAttribute("data-link", link);
        }
      });

      await Promise.all(updateTasks); // 모든 삽입 작업 완료까지 대기

      // 5. 소요 시간 기록 및 전송
      const durationSec = Number(((performance.now() - startTime) / 1000).toFixed(2));
      logEvent({
        type: "결과창 이동 완료",
        duration_sec: durationSec,
        query: questionText
      });
    });
  } catch (error) {
    container.innerHTML = `<p>❌ 기본 추천을 불러오지 못했어요: ${error.message}</p>`;
  }
};


// ==============================
// ⭐ 별점 표시 유틸
// ==============================
function renderStars(score) {
  const fullStars = Math.floor(score);
  const hasHalfStar = score - fullStars >= 0.25 && score - fullStars < 0.75;
  const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);

  let starsHTML = '';
  for (let i = 0; i < fullStars; i++) starsHTML += '★';
  if (hasHalfStar) starsHTML += '☆';  // 반 별 처리
  for (let i = 0; i < emptyStars; i++) starsHTML += '☆';

  return starsHTML;
}


// ==============================
// 🧾 클릭 로그 전송
// ==============================
function trackProductClick(productName, productLink, query_) {
  fetch('/log/click', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      product_name: productName,
      product_link: productLink,
      product_query: query_,
      timestamp: new Date().toISOString()
    })
  }).catch(err => console.error('❌ 로그 전송 실패:', err));
}


// ==============================
// 🧱 추천 카드 HTML 생성기
// ==============================
const renderProduct = (p) => {
  const images = p.images || [p.image]; // 이미지가 여러 개인 경우 슬라이더 구성

  return `
    <div class="product">
      <div class="product-header">
        <div class="image-slider">
          ${images.map((img, i) => `
            <img src="${img}" class="slide ${i === 0 ? 'active' : ''}" alt="${p.name} 이미지 ${i + 1}">
          `).join('')}
          ${images.length > 1 ? `
            <button class="slider-btn prev">&#10094;</button>
            <button class="slider-btn next">&#10095;</button>
          ` : ''}
        </div>
        <div class="product-info">
          <h2>💻 ${p.name}</h2>
          <p><strong>가격:</strong> ${p.price}</p>
          <p><strong>무게:</strong> ${p.weight}</p>
          <p><strong>주요 기능:</strong> ${p.feature}</p>
          <div class="review-box">
            <span class="stars">${renderStars(p.score)}</span>
            <span class="score">${p.score} / 5</span>
            <p class="quote">“${p.review}”</p>
          </div>
        </div>
      </div>
      <p class="highlight">${p.highlight}</p>
      <a class="buy-button"
         href="${p.link}"
         target="_blank"
         data-product="${p.name}"
         data-link="${p.link}">
         🔗 최저가 확인하기
      </a>
    </div>
  `;
};

// ✅ [클릭 이벤트 - 구매 버튼 클릭 시 로그 기록]
document.addEventListener("click", (e) => {
  const btn = e.target.closest(".buy-button");
  if (!btn) return;
  const productName = btn.getAttribute("data-product");
  const productLink = btn.getAttribute("data-link");
  const queryFromAttr = query; // fallback 용 (data-query 삭제된 경우 대비)
  trackProductClick(productName, productLink, queryFromAttr);
});

// ✅ [클릭 이벤트 - 슬라이더 버튼 클릭 시 이미지 전환]
document.addEventListener("click", (e) => {
  if (!e.target.classList.contains("slider-btn")) return;

  const slider = e.target.closest(".image-slider");
  const slides = slider.querySelectorAll(".slide");
  const currentIndex = Array.from(slides).findIndex((s) => s.classList.contains("active"));

  slides[currentIndex].classList.remove("active");

  let nextIndex = e.target.classList.contains("next")
    ? (currentIndex + 1) % slides.length
    : (currentIndex - 1 + slides.length) % slides.length;

  slides[nextIndex].classList.add("active");
});

// ✅ [유틸 함수 - 일정 시간 지연 처리용]
function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ✅ [하단 안내 문구 삽입]
function insertFooter() {
  const footer = document.createElement("footer");
  footer.style.marginTop = "60px";
  footer.style.padding = "20px 0";
  footer.style.textAlign = "center";
  footer.style.fontSize = "0.9rem";
  footer.style.color = "#888";
  footer.innerText = "가격과 재고는 판매처 사정에 따라 달라질 수 있으니, 구매 전 판매 페이지에서 꼭 확인해 주세요.";
  document.body.appendChild(footer);
}

// ✅ [초기 페이지 렌더링 로직 - query 기반 추천 리스트 요청 및 출력]
document.addEventListener("DOMContentLoaded", async () => {
  const queryBox = document.getElementById("queryText");
  const explanationBox = document.getElementById("queryExplanation");
  const container = document.getElementById("product-container");

  if (query) {
    queryBox.innerText = `💬 “${query}” 조건에 맞는 추천 리스트입니다.`;

    try {
      startFancyLoading();                 // 로딩 애니메이션 시작
      insertFeedbackSection();            // 피드백 섹션 추가

      const res = await fetch(`/api/products?query=${encodeURIComponent(query)}`);
      const data = await res.json();

      // 👉 제품 데이터가 없는 경우 N8N fallback 호출
      if (!data.products || data.products.length === 0) {
        await fetchFallbackProductData(query);
        bindRefineOptionClick();          // refine 클릭 이벤트 바인딩
        renderFollowupSearchBox();        // 이어 검색창 표시
        return;
      }

      await new Promise(r => setTimeout(r, Math.random() * 2000 + 3000)); // 일부러 딜레이
      container.innerHTML = "";           // 기존 로딩 화면 제거

      explanationBox.innerText = data.explanation || "";
      data.products.forEach(p => {
        container.insertAdjacentHTML("beforeend", renderProduct(p));
      });

    } catch (error) {
      queryBox.innerText = "추천 상품을 불러오는 데 문제가 발생했어요.";
      await fetchFallbackProductData(query); // 예외 발생 시 N8N fallback
    }

    renderFollowupSearchBox();  // 이어서 검색 박스 렌더링
    insertFooter();             // 하단 고지 삽입

  } else {
    // query 없을 때 기본 추천
    queryBox.innerText = "💬 조건을 인식하지 못했어요. 기본 추천 리스트를 보여드릴게요.";
    await fetchFallbackProductData("기본 추천 리스트 보여줘");
  }
});

// ✅ [Fancy 로딩 애니메이션 구성 및 실행]
function startFancyLoading() {
  const container = document.getElementById("product-container");
  container.innerHTML = `
    <div id="loading-visual" class="loading-visual">
      <div class="doc-count">
        🛒 <span id="doc-count">0</span>개의 상품을 비교 중입니다...
      </div>
      <div class="doc-icons">
        <span class="doc-icon">📦</span>
        <span class="doc-icon">💳</span>
        <span class="doc-icon">🧾</span>
        <span class="doc-icon">📦</span>
        <span class="doc-icon">📦</span>
        <span class="doc-icon">🛍️</span>
        <span class="doc-icon">📦</span>
      </div>
    </div>
    <p id="queryExplanation" style="margin-top: 1rem;"></p>
  `;

  let count = 0;
  const countSpan = document.getElementById("doc-count");
  const docText = document.querySelector(".doc-count");
  const targetCount = Math.floor(Math.random() * 41) + 80;

  const interval = setInterval(() => {
    const increment = Math.floor(Math.random() * 4) + 2;
    count += increment;

    if (count >= targetCount) {
      clearInterval(interval);
      countSpan.textContent = `약 ${targetCount}`;
      docText.innerHTML = `🛒 약 ${targetCount}개의 상품을 비교했습니다.<br>맞춤 추천을 준비 중입니다...`;
    } else {
      countSpan.textContent = count;
    }
  }, 300);

  return () => clearInterval(interval); // 정지 함수 반환
}

// ✅ [피드백 섹션 삽입 - 오픈채팅 안내 포함]
function insertFeedbackSection() {
  const section = document.createElement("div");
  section.style.marginTop = "40px";
  section.style.padding = "20px";
  section.style.textAlign = "center";
  section.style.fontSize = "0.95rem";
  section.style.color = "#555";

  section.innerHTML = `
    <p>📬 서비스에 대한 피드백이 있으신가요?<br>
    아래 오픈채팅방을 통해 언제든지<br>의견을 나눠주세요!</p>
    
    <a href="https://open.kakao.com/o/glqkU8zh" target="_blank" style="display:inline-block; margin: 10px; font-weight: bold; color: #0068ff; text-decoration: none;">
      👉 오픈채팅방 바로가기
    </a>
    
    <div style="margin-top: 15px;">
      <img src="https://velog.velcdn.com/images/gogogi313/post/35554d94-8b43-444a-8dc9-f31d5a168065/image.png" 
           alt="오픈채팅방 QR코드" 
           style="width: 130px; height: 130px; border: 1px solid #eee; border-radius: 8px;">
      <p style="margin-top: 8px; font-size: 0.85rem; color: #999;">QR로도 참여하실 수 있어요</p>
    </div>
  `;

  document.body.appendChild(section);
}

// ✅ [이어검색 UI 삽입 - query 존재 시에만 출력]
function renderFollowupSearchBox() {
  if (!query) return;

  const container = document.getElementById("followup-search");
  if (!container) return;

  container.innerHTML = `
  <div class="followup-box">
    <p class="description">
      🔍 더 원하는 조건이 있으신가요?<br>
      추가 키워드를 이어서 입력해 보세요!
    </p>
    <form class="search-box" onsubmit="followupSearch(); return false;">
      <input
        type="text"
        id="followupInput"
        placeholder="예: 마음이 바뀌었어!"
      />
      <button type="submit">검색</button>
    </form>
  </div>
`;
}

// ✅ [이어검색 처리 로직 - 입력된 텍스트를 기존 query에 덧붙여 검색]
function followupSearch() {
  const extra = document.getElementById("followupInput").value.trim();
  if (!extra) return;

  const newQuery = `${query} ${extra}`.trim();

  logEvent({
    type: "이어검색",
    newQuery: extra,
    query: query
  });

  location.href = `/search?query=${encodeURIComponent(newQuery)}`;
}

// ✅ [역질문(리파인) 카드 클릭 시 followupInput에 키워드 자동 추가]
function bindRefineOptionClick() {
  document.querySelectorAll('.refine-option').forEach(el => {
    el.addEventListener('click', () => {
      const extra = el.dataset.query;
      const input = document.getElementById('followupInput');
      if (!extra || !input) return;

      logEvent({
        type: "역질문 클릭",
        selected_card: extra,
        prev_selected_card: input.value,
        query: query
      });

      // 기존 입력값 뒤에 공백을 두고 이어 붙이기
      input.value = `${input.value} ${extra}`;
    });
  });
}

// ✅ [가격 및 링크 정보를 /api/get_price 에서 가져오기]
async function fetchPriceAndLink(name) {
  try {
    const res = await fetch('/api/get_price', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: name })
    });

    const data = await res.json();
    return {
      price: data.price || '정보 없음',
      link: data.link || `https://search.shopping.naver.com/search/all?query=${encodeURIComponent(name)}`
    };
  } catch (err) {
    console.error(`❌ 가격 정보 가져오기 실패 (${name}):`, err);
    return {
      price: '정보 없음',
      link: `https://search.shopping.naver.com/search/all?query=${encodeURIComponent(name)}`
    };
  }
}
