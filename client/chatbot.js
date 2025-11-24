// chatbot.js

const chatContainer = document.getElementById("chatContainer");
const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");
const chatStatus = document.getElementById("chatStatus");

// 말풍선 추가 함수
function appendMessage(role, text) {
  const row = document.createElement("div");
  row.className = `message-row ${role}`;

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;

  row.appendChild(bubble);
  chatContainer.appendChild(row);

  chatContainer.scrollTop = chatContainer.scrollHeight;
}

// 1) 프로필 저장 API 호출 (/profile)
async function saveProfileIfNeeded() {
  const userId = document.getElementById("userId").value.trim();
  const region = document.getElementById("region").value.trim();
  const land_area = document.getElementById("land_area").value.trim();
  const capital = document.getElementById("capital").value.trim();
  const experience = document.getElementById("experience").value.trim();

  if (!userId) {
    // userId가 없으면 프로필 저장도 하지 않고 바로 리턴
    return null;
  }

  const profilePayload = {
    userId: userId,
    region: region || null,
    land_area: land_area || null,
    capital: capital || null,
    experience: experience || null,
  };

  try {
    const res = await fetch("http://127.0.0.1:8000/profile", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        accept: "application/json",
      },
      body: JSON.stringify(profilePayload),
    });

    if (!res.ok) {
      console.warn("프로필 저장 실패:", await res.text());
      return null;
    }

    const data = await res.json();
    console.log("프로필 저장 결과:", data);
    return data.profile || null;
  } catch (err) {
    console.warn("프로필 저장 중 에러:", err);
    return null;
  }
}

// 2) 챗봇 API 호출 (/chat)
async function sendMessageToBackend(message) {
  let userId = document.getElementById("userId").value.trim();
  if (!userId) {
    // userId 비어 있으면 기본값 사용
    userId = "guest";
  }

  // ChatRequest 구조에 맞게: { userId, message }
  const payload = {
    userId: userId,
    message: message,
  };

  const res = await fetch("http://127.0.0.1:8000/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      accept: "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`서버 에러 (${res.status}) : ${errorText}`);
  }

  const data = await res.json();
  console.log("서버 응답(/chat):", data);

  // ChatResponse(answer: str) 이므로 data.answer 사용
  return data.answer;
}

// 폼 제출 이벤트
chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const message = messageInput.value.trim();
  if (!message) return;

  // 내 메시지 추가
  appendMessage("user", message);
  messageInput.value = "";
  messageInput.focus();

  // "생각 중입니다..." 말풍선
  const loadingRow = document.createElement("div");
  loadingRow.className = "message-row bot";
  const loadingBubble = document.createElement("div");
  loadingBubble.className = "bubble";
  loadingBubble.textContent = "생각 중입니다... 🤔";
  loadingRow.appendChild(loadingBubble);
  chatContainer.appendChild(loadingRow);
  chatContainer.scrollTop = chatContainer.scrollHeight;

  try {
    chatStatus.textContent = "프로필 저장 중...";
    // 1) 프로필 저장 (실패해도 일단 무시하고 진행)
    await saveProfileIfNeeded();

    chatStatus.textContent = "응답 대기 중...";
    // 2) 챗봇 호출
    const reply = await sendMessageToBackend(message);

    loadingBubble.textContent = reply;
    chatStatus.textContent = "온라인";
  } catch (err) {
    console.error(err);
    loadingBubble.textContent =
      "에러가 발생했습니다.\n\n" +
      (err.message || "자세한 에러 메시지가 없습니다.");
    chatStatus.textContent = "오프라인?";
  }
});
