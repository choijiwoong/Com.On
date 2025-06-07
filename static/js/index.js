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

let currentIndex = 0;
let questions = [];

function showNextQuestion() {
  const list = document.getElementById("example-list");
  if (!list || questions.length === 0) return;

  // 기존 버튼 제거 애니메이션
  const oldBtn = list.querySelector("button");
  if (oldBtn) {
    oldBtn.classList.remove("fade-slide-in");
    oldBtn.classList.add("fade-slide-out");

    setTimeout(() => {
      list.innerHTML = ""; // 완전히 제거
      insertNewButton();
    }, 600); // fade-slide-out 지속시간과 맞춤
  } else {
    insertNewButton();
  }
}

function insertNewButton() {
  const list = document.getElementById("example-list");
  const q = questions[currentIndex];

  const btn = document.createElement("button");
  btn.textContent = `Q. ${q.text}`;
  btn.dataset.query = q.text;              // 실제 검색용 텍스트 저장(Q. 제거)
  btn.id = q.id;
  btn.classList.add("fade-slide-in");
  btn.onclick = () => fillExample(btn);

  list.appendChild(btn);

  // 인덱스 순환
  currentIndex = (currentIndex + 1) % questions.length;
}

document.addEventListener("DOMContentLoaded", () => {
  fetch('/api/questions')
    .then(res => res.json())
    .then(data => {
      questions = data;
      showNextQuestion(); // 첫 질문 표시
      setInterval(showNextQuestion, 7000); // 7초마다 순환
    })
    .catch(err => {
      console.error("❌ 질문 로딩 실패:", err);
    });
});


// 검색 버튼 클릭 시 결과 페이지로 이동
function goToResult() {
  const query = document.getElementById("userQuery").value;
  if (query.trim()) {
    window.location.href = `search?query=${encodeURIComponent(query)}`;
  } else {
    alert("🛠️ 기능 구현 중입니다.\n아래 질문카드를 눌러 테스트해보세요!");
  }
}

function fillExample(el) {
  const input = document.getElementById("userQuery");
  const text = el.dataset.query;  // ✅ 실제 질문 텍스트 가져오기
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
        window.location.href = `search?query=${encodeURIComponent(text)}`;
      }, 250); // 살짝 여유 주기
    }
  }, typingSpeed);
}

