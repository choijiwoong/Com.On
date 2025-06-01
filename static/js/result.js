// URL 파라미터에서 'query' 값을 추출
const params = new URLSearchParams(window.location.search);
const query = params.get("query");

// 네이버 이미지 API에서 유효한 썸네일 URL 가져오기
async function getValidImageURL(query) {
  try {
    const res = await fetch("https://n8n.1000.school/webhook/naver-image", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query })
    });
    const items = await res.json();

    for (const item of items) {
      const isValid = await validateImage(item.thumbnail);
      if (isValid) return item.thumbnail;
    }
  } catch (err) {
    console.error("이미지 검색 오류:", err);
  }
  return null;
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
  container.innerHTML = "🌀 맞춤형 추천을 불러오는 중...";

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
      const img = product.querySelector("img");
      if (title && img) {
        const newImageUrl = await getValidImageURL(title);
        if (newImageUrl) {
          img.src = newImageUrl;
        }
      }
    }
  } catch (error) {
    container.innerHTML = `<p>❌ 기본 추천을 불러오지 못했어요: ${error.message}</p>`;
  }
};

// 추천 상품 HTML 블록을 문자열로 생성
const renderProduct = (p) => `
  <div class="product">
    <div class="product-header">
      <img src="${p.image}" alt="${p.name}">
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
