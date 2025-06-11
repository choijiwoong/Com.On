let currentQuery = "{{ query }}";
let conversationHistory = [];

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

    // 대화 기록에 추가
    if (sender === 'user') {
    conversationHistory.push({
        role: "user",
        content: message
    });
    } else {
    conversationHistory.push({
        role: "assistant",
        content: message
    });
    }
}

function sendMessage() {
    const messageInput = document.getElementById("message-input");
    const message = messageInput.value.trim();
    if (!message) return;

    // 사용자 메시지 추가
    addMessage(message, "user");
    messageInput.value = "";

    // 로딩 표시
    const loadingDiv = document.createElement("div");
    loadingDiv.className = "message bot";
    loadingDiv.innerHTML = '<div class="loading-dots"><span></span><span></span><span></span></div>';
    document.querySelector(".chat-messages").appendChild(loadingDiv);

    // 서버에 메시지 전송
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
        // 로딩 제거
        loadingDiv.remove();

        // 봇 응답 추가
        addMessage(data.response, "bot");

        // 대화 요약 표시
        if (data.conversation_summary) {
        const summaryDiv = document.createElement("div");
        summaryDiv.className = "conversation-summary";
        summaryDiv.innerHTML = `<strong>확인된 요구사항:</strong> ${data.conversation_summary}`;
        document.querySelector(".chat-messages").appendChild(summaryDiv);
        }

        // 최종 응답인 경우 검색 버튼 표시
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
        document.querySelector(".chat-messages").appendChild(searchButton);
        }
    })
    .catch((error) => {
        console.error("Error:", error);
        loadingDiv.remove();
        addMessage("죄송합니다. 잠시 후 다시 시도해주세요.", "bot");
    });
}

function sendQuickQuestion(question) {
    // 화면에 AI 질문처럼 보이게 추가
    addMessage(question, "bot");
}


document.addEventListener("DOMContentLoaded", function () {
    document.getElementById("message-input").addEventListener("keydown", function (e) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
});


// 채팅창 토글 함수
function toggleChat() {
    const chatContainer = document.querySelector('.chat-container');
    const minimizeButton = document.querySelector('.minimize-button');
    chatContainer.classList.toggle('minimized');
    minimizeButton.textContent = chatContainer.classList.contains('minimized') ? '+' : '−';
}