// chatbot.js

const API_BASE = window.API_BASE_URL || "http://127.0.0.1:8000";
const chatContainer = document.getElementById("chatContainer");
const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");
const chatStatus = document.getElementById("chatStatus");

// 로그인한 사용자 정보 가져오기
const username = sessionStorage.getItem("username") || sessionStorage.getItem("userName") || "";
const userEmail = sessionStorage.getItem("userEmail") || "";

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

// 프로필 불러오기
async function loadUserProfile() {
  if (!username) {
    console.warn("로그인 정보가 없습니다.");
    return null;
  }

  try {
    const res = await fetch(`${API_BASE}/profile/${encodeURIComponent(username)}`);
    if (!res.ok) {
      console.warn("프로필 불러오기 실패:", await res.text());
      return null;
    }

    const data = await res.json();
    if (data.ok && data.profile) {
      return data.profile;
    }
    return null;
  } catch (err) {
    console.warn("프로필 불러오기 중 에러:", err);
    return null;
  }
}

// 프로필 정보 표시
function displayProfileInfo(profile) {
  const profileBox = document.querySelector(".profile-box");
  if (!profileBox) return;

  let profileHtml = `
    <h3>프로필 정보</h3>
    <p class="profile-box__hint">
      프로필 정보는 <strong><a href="profile.html" style="color: var(--primary);">프로필 업데이트</a></strong>에서 수정할 수 있습니다.
    </p>
  `;

  if (profile) {
    profileHtml += `
      <div style="margin-top: 12px; padding: 12px; background: rgba(255,255,255,0.05); border-radius: 8px; font-size: 0.9rem;">
        ${profile.region ? `<p><strong>지역:</strong> ${profile.region}${profile.region_detail ? ` ${profile.region_detail}` : ""}</p>` : ""}
        ${profile.land_area ? `<p><strong>토지 규모:</strong> ${profile.land_area}</p>` : ""}
        ${profile.capital ? `<p><strong>자본금:</strong> ${profile.capital}</p>` : ""}
        ${profile.experience ? `<p><strong>농업 경험:</strong> ${profile.experience}${profile.experience_years ? ` (${profile.experience_years}년)` : ""}</p>` : ""}
        ${profile.workforce ? `<p><strong>가용 인력:</strong> ${profile.workforce}명</p>` : ""}
      </div>
    `;
  } else {
    profileHtml += `
      <div style="margin-top: 12px; padding: 12px; background: rgba(255,200,0,0.1); border-radius: 8px; font-size: 0.9rem; color: #ffc800;">
        <p>⚠️ 프로필 정보가 없습니다.</p>
        <p style="margin-top: 8px;">챗봇이 더 정확한 답변을 드리기 위해 <a href="profile.html" style="color: var(--primary);">프로필을 등록</a>해주세요.</p>
      </div>
    `;
  }

  profileBox.innerHTML = profileHtml;
}

// 챗봇 API 호출 (/chat)
async function sendMessageToBackend(message) {
  // 로그인한 사용자의 username을 userId로 사용
  const userId = username || "guest";

  // ChatRequest 구조에 맞게: { userId, message }
  const payload = {
    userId: userId,
    message: message,
  };

  const res = await fetch(`${API_BASE}/chat`, {
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

  // 로그인 확인
  if (!username) {
    appendMessage("bot", "로그인이 필요합니다. 먼저 로그인해주세요.");
    setTimeout(() => {
      window.location.href = "login.html";
    }, 2000);
    return;
  }

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
    chatStatus.textContent = "응답 대기 중...";
    // 챗봇 호출 (프로필은 백엔드에서 자동으로 불러옴)
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

// 페이지 로드 시 프로필 불러오기
window.addEventListener("DOMContentLoaded", async () => {
  if (username) {
    const profile = await loadUserProfile();
    displayProfileInfo(profile);
  } else {
    displayProfileInfo(null);
    appendMessage("bot", "로그인이 필요합니다. 먼저 로그인해주세요.");
  }
});
