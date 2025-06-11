// Google Tag Manager 삽입
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

// URL 파라미터에서 'query' 값을 추출
const params = new URLSearchParams(window.location.search);
const query = params.get("query");

async function getValidImageURLs(query, max = 5) {
  const validImages = [];
  try {
    const res = await fetch("https://n8n.1000.school/webhook/naver-image", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query })
    });
    const items = await res.json();
    for (const item of items) {
      const isValid = await validateImage(item.thumbnail);
      if (isValid) {
        validImages.push(item.thumbnail);
        if (validImages.length >= max) break;
      }
    }
  } catch (err) {
    console.error("이미지 오류:", err);
  }
  return validImages;
}


// 이미지 URL이 실제로 표시 가능한지 검사
function validateImage(url) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve(true);
    img.onerror = () => resolve(false);
    img.src = url;
  });
}

// 추천 HTML을 서버에서 가져오고, 이미지 자동 교체
const fetchFallbackFromN8N = async (questionText) => {
  const container = document.getElementById("product-container");
  container.innerHTML = `<p class="loading-animated">🌀 맞춤형 추천을 불러오는 중</p>`;
  startFancyLoading();
  try {
    const response = await fetch('https://n8n.1000.school/webhook/c932befe-195e-46b0-8502-39c9b1c69cc2', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: questionText || "기본 추천 리스트 보여줘" })
    });

    if (!response.ok) throw new Error("네트워크 오류 발생");

    const html = await response.text();
    container.innerHTML = `<p id="queryExplanation"></p>` + html;

    // 썸네일 이미지 자동 교체
    const products = container.querySelectorAll(".product");
    for (const product of products) {
	  const title = product.querySelector("h2")?.textContent.replace("💻", "").trim();
	  const slider = product.querySelector(".image-slider");

	  if (title && slider) {
		const images = await getValidImageURLs(title);
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
	  }
	}
  } catch (error) {
    container.innerHTML = `<p>❌ 기본 추천을 불러오지 못했어요: ${error.message}</p>`;
  }
};

function renderStars(score) {
  const fullStars = Math.floor(score);
  const hasHalfStar = score - fullStars >= 0.25 && score - fullStars < 0.75;
  const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);

  let starsHTML = '';

  for (let i = 0; i < fullStars; i++) {
    starsHTML += '★';
  }

  if (hasHalfStar) {
    starsHTML += '☆'; // 또는 다른 반 별 문자 사용 
  }

  for (let i = 0; i < emptyStars; i++) {
    starsHTML += '☆';
  }

  return starsHTML;
}

function trackProductClick(productName, productLink, query_) {
    fetch('/log/click', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        product_name: productName,
        product_link: productLink,
        product_query: query_,// query_
        timestamp: new Date().toISOString()
      })
    }).catch(err => console.error('❌ 로그 전송 실패:', err));
  }

// 추천 상품 HTML 블록을 문자열로 생성
const renderProduct = (p) => {
  const images = p.images || [p.image];
  return `
    <div class="product">
      <div class="product-header">
        <div class="image-slider">
          ${images.map((img, i) => `
            <img src="${img}" class="slide ${i === 0 ? 'active' : ''}" alt="${p.name} 이미지 ${i+1}">
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
	   🔗 지금 구매하기
	</a>

    </div>
  `;
};

// JS 하단에 클릭 이벤트 위임 추가
document.addEventListener("click", (e) => {
  const btn = e.target.closest(".buy-button");
  if (!btn) return;
  const productName = btn.getAttribute("data-product");
  const productLink = btn.getAttribute("data-link");
  const queryFromAttr = query; // fallback(프롬프트에 data-query삭제 필요)
  trackProductClick(productName, productLink, queryFromAttr);
});

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

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function insertFooter() {
  const footer = document.createElement("footer");
  footer.style.marginTop = "60px";
  footer.style.padding = "20px 0";
  footer.style.textAlign = "center";
  footer.style.fontSize = "0.9rem";
  footer.style.color = "#888";
  footer.innerText = '"위 결과는 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."';

  document.body.appendChild(footer);
}


// 페이지 로딩 시, query값에 따라 API 요청 및 HTML 렌더링
document.addEventListener("DOMContentLoaded", async () => {
  const queryBox = document.getElementById("queryText");
  const explanationBox = document.getElementById("queryExplanation");
  const container = document.getElementById("product-container");

  if (query) {
    queryBox.innerText = `💬 “${query}” 조건에 맞는 추천 리스트입니다.`;

    try {
    
      startFancyLoading(); // 로딩 시작
      insertFeedbackSection();
      const res = await fetch(`/api/products?query=${encodeURIComponent(query)}`);
      const data = await res.json();

      

      if (!data.products || data.products.length === 0) {
        await fetchFallbackFromN8N(query);
        //insertFeedbackSection();
		bindRefineOptionClick();
        renderFollowupSearchBox();
        return;
      }
      
      await new Promise(r => setTimeout(r, Math.random() * 2000 + 3000)); // 3~5초 대기
      container.innerHTML = ""; // 로딩 화면 제거
      
      explanationBox.innerText = data.explanation || "";
      data.products.forEach(p => {
        container.insertAdjacentHTML("beforeend", renderProduct(p));
      });

    } catch (error) {
      queryBox.innerText = "추천 상품을 불러오는 데 문제가 발생했어요.";
      await fetchFallbackFromN8N(query);
    }
    renderFollowupSearchBox();
    //insertFeedbackSection();
    insertFooter();
  } else {
    queryBox.innerText = "💬 조건을 인식하지 못했어요. 기본 추천 리스트를 보여드릴게요.";
    await fetchFallbackFromN8N("기본 추천 리스트 보여줘");
  }
});


function startFancyLoading() {
  const container = document.getElementById("product-container");
  container.innerHTML = `
    <div id="loading-visual" class="loading-visual">
      <div class="doc-count">
        📄 <span id="doc-count">0</span>개의 문서를 탐색 중입니다...
      </div>
      <div class="doc-icons">
        <span class="doc-icon">📄</span>
        <span class="doc-icon">🗂️</span>
        <span class="doc-icon">📁</span>
        <span class="doc-icon">📃</span>
        <span class="doc-icon">📄</span>
        <span class="doc-icon">📄</span>
        <span class="doc-icon">📄</span>
      </div>
    </div>
  `;

  let count = 0;
  const countSpan = document.getElementById("doc-count");
  const docText = document.querySelector(".doc-count");

  // 80 ~ 120 사이의 랜덤 목표값 설정
  const targetCount = Math.floor(Math.random() * 41) + 80;

  const interval = setInterval(() => {
    const increment = Math.floor(Math.random() * 4) + 2;
    count += increment;

    if (count >= targetCount) {
      clearInterval(interval);
      countSpan.textContent = `약 ${targetCount}`;
      docText.innerHTML = `📄 약 ${targetCount}개의 문서를 탐색했습니다.<br>잠시만 기다려주세요...`;
    } else {
      countSpan.textContent = count;
    }
  }, 350);

  return () => clearInterval(interval);
}

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

function followupSearch() {
  const extra = document.getElementById("followupInput").value.trim();
  if (!extra) return;

  const newQuery = `${query} ${extra}`.trim();
  location.href = `/search?query=${encodeURIComponent(newQuery)}`;
}


function bindRefineOptionClick() {
  document.querySelectorAll('.refine-option').forEach(el => {
    el.addEventListener('click', () => {
      const extra = el.dataset.query;
      const input = document.getElementById('followupInput');
      if (!extra || !input) return;

      // 기존 입력 내용과 공백으로 구분하여 덧붙이기
	  input.value = `${input.value} ${extra}`;
    });
  });
}

