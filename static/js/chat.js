// ==============================
// 📌 전역 변수 선언
// ==============================

let currentQuery = "{{ query }}";
let conversationHistory = [];


// ==============================
// 💬 메시지 추가 함수 (화면 + 기록)
// ==============================

function addMessage(message, sender) {
    const chatMessages = document.getElementById("chat-messages");

    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${sender}`;

    const contentDiv = document.createElement("div");
    contentDiv.className = "message-content";
    contentDiv.innerHTML = message;

    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // 대화 기록 저장
    conversationHistory.push({
        role: sender === "user" ? "user" : "assistant",
        content: message
    });
}


// ==============================
// 📤 사용자 메시지 전송 처리
// ==============================

function sendMessage() {
    const messageInput = document.getElementById("message-input");
    const message = messageInput.value.trim();
    if (!message) return;

    // 1. 사용자 메시지 화면에 출력
    addMessage(message, "user");
    messageInput.value = "";

    // 2. 로딩 UI 추가
    const loadingDiv = document.createElement("div");
    loadingDiv.className = "message bot";
    loadingDiv.innerHTML = '<div class="loading-dots"><span></span><span></span><span></span></div>';
    document.querySelector(".chat-messages").appendChild(loadingDiv);

    // 3. 서버에 메시지 POST
    fetch("/chat", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            message: message,
            current_query: currentQuery,
            conversation_history: conversationHistory
        }),
    })
    .then((response) => response.json())
    .then((data) => {
        // 4. 로딩 제거
        loadingDiv.remove();

        // 5. AI 응답 표시
        addMessage(data.response, "bot");

        // 6. 대화 요약 있을 경우 표시
        if (data.conversation_summary) {
            const summaryDiv = document.createElement("div");
            summaryDiv.className = "conversation-summary";
            summaryDiv.innerHTML = `<strong>확인된 요구사항:</strong> ${data.conversation_summary}`;
            document.querySelector(".chat-messages").appendChild(summaryDiv);
        }

        // 7. 최종 응답일 경우 → 검색 버튼 추가
        if (data.is_final && data.final_keywords) {
            const searchButton = document.createElement("div");
            searchButton.className = "search-button-container";
            searchButton.innerHTML = `
                <div class="search-suggestion">
                    <strong>이 키워드로 검색해보세요:</strong>
                    <span class="keywords">${data.final_keywords}</span>
                </div>
                <button class="search-button" onclick="window.location.href='/search?query=${encodeURIComponent(data.final_keywords)}'">
                    검색하기
                </button>
            `;

            logEvent({
                type: "채팅종료",
                entry_point: "",             // 시작 위치
                current_query: data.final_keywords,
                note: ""
            });

            document.querySelector(".chat-messages").appendChild(searchButton);
        }
    })
    .catch((error) => {
        console.error("Error:", error);
        loadingDiv.remove();
        addMessage("죄송합니다. 잠시 후 다시 시도해주세요.", "bot");
    });
}


// ==============================
// ⚡ 빠른 질문 전송 (시작 프롬프트용)
// ==============================

function sendQuickQuestion(question) {
    addMessage(question, "bot");  // 첫 메시지는 bot처럼 표시
    logEvent({
        type: "채팅시작",
        entry_point: "",
        current_query: question,
        note: ""
    });
}


// ==============================
// ⌨️ Enter 키 전송 이벤트
// ==============================

document.addEventListener("DOMContentLoaded", function () {
    document.getElementById("message-input").addEventListener("keydown", function (e) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
});


// ==============================
// 🔃 채팅창 열기/닫기 토글
// ==============================

function toggleChat() {
    const chatContainer = document.getElementById("chat-container");
    const toggleButton = document.getElementById("chat-toggle-button");

    const isMinimized = chatContainer.classList.toggle("minimized");
    toggleButton.style.display = isMinimized ? "block" : "none";
}
