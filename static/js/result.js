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
    container.innerHTML = `<p id="queryExplanation"> (안내 메시지: 현재 구현 중인 기능입니다. 간단한 포맷을 참고해주시고 피드백해주시면 감사드리겠습니다.)</p>` + html;

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
            <span class="stars">⭐⭐⭐⭐☆</span>
            <span class="score">${p.score} / 5</span>
            <p class="quote">“${p.review}”</p>
          </div>
        </div>
      </div>
      <p class="highlight">${p.highlight}</p>
      <a class="buy-button" href="${p.link}" target="_blank">🔗 상세페이지에서 자세히 보기</a>
    </div>
  `;
};

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



// 페이지 로딩 시, query값에 따라 API 요청 및 HTML 렌더링
document.addEventListener("DOMContentLoaded", async () => {
  const queryBox = document.getElementById("queryText");
  const explanationBox = document.getElementById("queryExplanation");
  const container = document.getElementById("product-container");

  if (query) {
    queryBox.innerText = `💬 “${query}” 조건에 맞는 추천 리스트입니다.`;

    try {
      const res = await fetch(`/api/products?query=${encodeURIComponent(query)}`);
      const data = await res.json();

      explanationBox.innerText = data.explanation || "";

      if (!data.products || data.products.length === 0) {
        await fetchFallbackFromN8N(query);
        return;
      }

      data.products.forEach(p => {
        container.insertAdjacentHTML("beforeend", renderProduct(p));
      });

    } catch (error) {
      queryBox.innerText = "추천 상품을 불러오는 데 문제가 발생했어요.";
      await fetchFallbackFromN8N(query);
    }

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

  const interval = setInterval(() => {
    const increment = Math.floor(Math.random() * 4) + 2;
    count += increment;

    if (count >= 92) {
      clearInterval(interval);
      countSpan.textContent = "약 92";
      docText.innerHTML = `📄 약 92개의 문서를 탐색했습니다.<br>잠시만 기다려주세요...`;
    } else {
      countSpan.textContent = count;
    }
  }, 350);

  return () => clearInterval(interval);
}
