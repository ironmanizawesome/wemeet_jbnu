// 캐릭터 선택 페이지 스크립트

const API_BASE = window.API_BASE_URL || "http://127.0.0.1:8000";

// 작물 아이콘 매핑
const CROP_ICONS = {
  "감자": "🥔",
  "오이": "🥒",
  "토마토": "🍅",
  "당근": "🥕",
  "부추": "🌿"
};

// 기상 아이콘 매핑
const WEATHER_ICONS = {
  "맑음": "☀️",
  "비": "🌧️",
  "눈": "❄️",
  "흐림": "☁️",
  "안개": "🌫️",
  "천둥": "⛈️",
  "바람": "💨"
};

// 로그인 정보 확인
async function checkLogin() {
  const username = sessionStorage.getItem("username") || sessionStorage.getItem("userName") || "";
  
  if (!username) {
    alert("로그인이 필요합니다.");
    window.location.href = "login.html";
    return null;
  }
  
  return username;
}

// 작물 목록 불러오기
async function loadCrops() {
  const username = await checkLogin();
  if (!username) return;
  
  try {
    const response = await fetch(`${API_BASE}/game/crops/${encodeURIComponent(username)}`);
    if (!response.ok) {
      throw new Error("작물 목록 불러오기 실패");
    }
    
    const data = await response.json();
    return data.crops || [];
  } catch (error) {
    console.error("작물 목록 불러오기 오류:", error);
    return [];
  }
}

// 작물 카드 렌더링
function renderCropCard(crop, index) {
  const card = document.createElement("div");
  card.className = "crop-card";
  
  const hp = crop.hp || 100;
  const day = crop.day || 0;
  const weather = crop.currentWeather || "맑음";
  
  card.innerHTML = `
    <button class="delete-button" data-crop-name="${crop.cropName}" onclick="event.stopPropagation(); deleteCrop('${crop.cropName}')" title="작물 삭제">×</button>
    <div>
      <div class="crop-icon">${CROP_ICONS[crop.cropName] || "🌱"}</div>
      <div class="crop-name">${crop.cropName}</div>
      <div class="crop-info">
        <div class="crop-stat">
          <span class="crop-stat-label">건강도</span>
          <span class="crop-stat-value">${hp} / 100</span>
        </div>
        <div class="hp-bar">
          <div class="hp-bar-fill" style="width: ${hp}%"></div>
        </div>
        <div class="crop-stat">
          <span class="crop-stat-label">재배 일수</span>
          <span class="crop-stat-value">${day}일차</span>
        </div>
        <div class="weather-info">
          <span>${WEATHER_ICONS[weather] || "☀️"}</span>
          <span>${weather}</span>
        </div>
      </div>
    </div>
  `;
  
  card.addEventListener("click", () => {
    selectCrop(crop.cropName);
  });
  
  return card;
}

// 빈 슬롯 카드 렌더링
function renderEmptySlot() {
  const card = document.createElement("div");
  card.className = "crop-card empty";
  
  card.innerHTML = `
    <div class="empty-slot">
      <div class="empty-icon">➕</div>
      <div style="font-size: 18px; font-weight: 600;">빈 슬롯</div>
      <p style="color: var(--muted); margin: 0;">새 작물을 추가하세요</p>
      <button class="add-button" onclick="window.location.href='recommend.html'">
        작물 추가하기
      </button>
    </div>
  `;
  
  return card;
}

// 작물 선택
function selectCrop(cropName) {
  sessionStorage.setItem("cropName", cropName);
  window.location.href = "game.html";
}

// 작물 삭제
async function deleteCrop(cropName) {
  if (!confirm(`정말 ${cropName} 작물을 삭제하시겠습니까? 모든 진행 상황이 삭제됩니다.`)) {
    return;
  }
  
  const username = await checkLogin();
  if (!username) return;
  
  try {
    const response = await fetch(`${API_BASE}/game/crop/${encodeURIComponent(username)}/${encodeURIComponent(cropName)}`, {
      method: "DELETE"
    });
    
    if (!response.ok) {
      throw new Error("작물 삭제 실패");
    }
    
    // 페이지 새로고침
    location.reload();
  } catch (error) {
    console.error("작물 삭제 오류:", error);
    alert("작물 삭제에 실패했습니다.");
  }
}

// 페이지 초기화
async function init() {
  const username = await checkLogin();
  if (!username) return;
  
  const crops = await loadCrops();
  const cropsGrid = document.getElementById("cropsGrid");
  cropsGrid.innerHTML = "";
  
  // 작물 카드 렌더링
  crops.forEach((crop, index) => {
    const card = renderCropCard(crop, index);
    cropsGrid.appendChild(card);
  });
  
  // 빈 슬롯 추가 (최대 2개까지)
  const emptySlots = Math.max(0, 2 - crops.length);
  for (let i = 0; i < emptySlots; i++) {
    const emptyCard = renderEmptySlot();
    cropsGrid.appendChild(emptyCard);
  }
}

// 전역 함수로 내보내기 (HTML에서 사용하기 위해)
window.deleteCrop = deleteCrop;

// 페이지 로드 시 초기화
window.addEventListener("DOMContentLoaded", init);

