// ==============================
// 📊 Google Tag Manager 삽입
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
// 🔁 질문 카드 순환 표시 관련 변수
// ==============================

let currentIndex = 0;
let questions = [];


// ==============================
// 🔄 질문 카드 순환 표시 함수
// ==============================

function showNextQuestion() {
  const list = document.getElementById("example-list");
  if (!list || questions.length === 0) return;

  const oldBtn = list.querySelector("button");

  if (oldBtn) {
    // 이전 질문 버튼 사라지는 애니메이션
    oldBtn.classList.remove("fade-slide-in");
    oldBtn.classList.add("fade-slide-out");

    setTimeout(() => {
      list.innerHTML = "";
      insertNewButton(); // 다음 질문 표시
    }, 600); // fade-slide-out와 동일한 시간
  } else {
    insertNewButton();
  }
}


// ==============================
// ➕ 새 질문 버튼 삽입 함수
// ==============================

function insertNewButton() {
  const list = document.getElementById("example-list");
  const q = questions[currentIndex];

  const btn = document.createElement("button");
  btn.textContent = `Q. ${q.text}`;
  btn.dataset.query = q.text;   // 실제 검색 텍스트 저장
  btn.id = q.id;
  btn.classList.add("fade-slide-in");
  btn.onclick = () => fillExample(btn); // 클릭 시 입력창 채우기

  list.appendChild(btn);

  // 다음 인덱스로 순환
  currentIndex = (currentIndex + 1) % questions.length;
}


// ==============================
// 📦 초기 로딩 시 질문 데이터 fetch
// ==============================

document.addEventListener("DOMContentLoaded", () => {
  fetch('/api/questions')
    .then(res => res.json())
    .then(data => {
      questions = data;
      showNextQuestion();                 // 첫 질문 표시
      setInterval(showNextQuestion, 7000); // 7초마다 새 질문 표시
    })
    .catch(err => {
      console.error("❌ 질문 로딩 실패:", err);
    });
});


// ==============================
// 🚀 직접 검색 실행 함수 (수동 입력 시)
// ==============================

function goToResult() {
  const query = document.getElementById("userQuery").value;
  const wrapper = document.querySelector(".wrapper");

  if (query.trim()) {
    // 입력값 존재 시 → 슬라이드 업 후 페이지 이동
    requestAnimationFrame(() => {
      wrapper.classList.add("page-exit-up");
      setTimeout(() => {
        window.location.href = `search?query=${encodeURIComponent(query)}`;
      }, 500);
    });
  } else {
    // 입력값 없을 경우 안내
    alert("🛠️ 기능 구현 중입니다.\n아래 질문카드를 눌러 테스트해보세요!");
  }
}


// ==============================
// ✍️ 질문 카드 클릭 시 입력창 채우고 이동
// ==============================

function fillExample(el) {
  const input = document.getElementById("userQuery");
  const wrapper = document.querySelector(".wrapper");
  const text = el.dataset.query;

  input.value = ""; // 초기화

  let index = 0;
  const typingSpeed = 30;

  const typingInterval = setInterval(() => {
    if (index < text.length) {
      input.value += text.charAt(index);
      index++;
    } else {
      clearInterval(typingInterval);

      // 입력이 끝난 후 페이지 이동 애니메이션 실행
      requestAnimationFrame(() => {
        wrapper.classList.add("page-exit-up");
        setTimeout(() => {
          window.location.href = `search?query=${encodeURIComponent(text)}`;
        }, 500);
      });
    }
  }, typingSpeed);
}
