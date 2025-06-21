// ==============================
// 📝 logEvent()
// 사용자 행동 또는 이벤트를 서버에 기록합니다.
// 호출 위치: 채팅 시작/종료 등 이벤트 발생 시
// ==============================

function logEvent(dataObject) {
  fetch("/log/event", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(dataObject)
  }).catch((error) => {
    console.error("이벤트 로그 전송 실패:", error);
  });
}

/*
📌 매개변수 예시 (dataObject):
{
  type: "채팅시작" | "채팅종료",
  entry_point: "홈페이지" | "결과페이지" | ...,
  current_query: "사용자 입력 쿼리 문자열",
  note: "추가 메모 또는 상태 정보"
}
*/
