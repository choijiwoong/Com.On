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
