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
        btn.onclick = () => {
          document.getElementById("userQuery").value = q.text;
        };
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

// 예시 버튼 클릭 시 입력창에 텍스트 채워넣기
function fillExample(el) {
  document.getElementById("userQuery").value = el.textContent;
}

// 👉 이미지 슬라이더 터치 전환 기능 (모바일)
document.addEventListener("DOMContentLoaded", () => {
  const sliders = document.querySelectorAll(".image-slider");

  sliders.forEach(slider => {
    let startX = 0;
    let currentIndex = 0;
    const slides = slider.querySelectorAll(".slide");

    slider.addEventListener("touchstart", (e) => {
      startX = e.touches[0].clientX;
    });

    slider.addEventListener("touchend", (e) => {
      const endX = e.changedTouches[0].clientX;
      const diff = startX - endX;

      if (Math.abs(diff) > 30) {
        slides[currentIndex].classList.remove("active");

        if (diff > 0) {
          // swipe left → next
          currentIndex = (currentIndex + 1) % slides.length;
        } else {
          // swipe right → prev
          currentIndex = (currentIndex - 1 + slides.length) % slides.length;
        }

        slides[currentIndex].classList.add("active");
      }
    });
  });
});
