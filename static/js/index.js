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

// 예시 질문 버튼을 불러와서 렌더링
document.addEventListener("DOMContentLoaded", () => {
  fetch('/api/questions')
    .then(res => res.json())
    .then(questions => {
      const list = document.getElementById("example-list");
      if (!list) return;

      questions.forEach(q => {
        const btn = document.createElement("button");
        btn.textContent = q.text;
        btn.id = q.id;
        btn.onclick = () => fillExample(btn);
        list.appendChild(btn);
      });
    })
    .catch(err => {
      console.error("❌ 질문 로딩 실패:", err);
    });
});

// 검색 버튼 클릭 시 결과 페이지로 이동
function goToResult() {
  const query = document.getElementById("userQuery").value;
  if (query.trim()) {
    window.location.href = `result.html?query=${encodeURIComponent(query)}`;
  } else {
    alert("🛠️ 기능 구현 중입니다.\n아래 질문카드를 눌러 테스트해보세요!");
  }
}

function fillExample(el) {
  const input = document.getElementById("userQuery");
  const text = el.textContent.trim();
  input.value = ""; // 기존 입력 초기화

  let index = 0;
  const typingSpeed = 30; // 밀리초 단위 속도 (원하는 속도로 조절)

  // 타이핑 효과 구현
  const typingInterval = setInterval(() => {
    if (index < text.length) {
      input.value += text.charAt(index);
      index++;
    } else {
      clearInterval(typingInterval);

      // 타이핑이 끝난 후 자동 검색 이동
      setTimeout(() => {
        window.location.href = `result.html?query=${encodeURIComponent(text)}`;
      }, 250); // 살짝 여유 주기
    }
  }, typingSpeed);
}

