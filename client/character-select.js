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

// 도감 표시
async function showCollection() {
  const collectionModal = document.getElementById("collectionModal");
  const collectionGrid = document.getElementById("collectionGrid");
  const totalHarvests = document.getElementById("totalHarvests");
  const uniqueCrops = document.getElementById("uniqueCrops");
  
  if (!collectionModal || !collectionGrid) return;

  collectionModal.classList.add("show");
  
  const username = await checkLogin();
  if (!username) return;
  
  try {
    // 도감 요약 정보 가져오기
    const response = await fetch(`${API_BASE}/game/collection/${encodeURIComponent(username)}/summary`);
    if (!response.ok) {
      throw new Error("도감 조회 실패");
    }

    const data = await response.json();
    
    // 통계 업데이트
    if (totalHarvests) {
      totalHarvests.textContent = data.totalHarvests || 0;
    }
    if (uniqueCrops) {
      uniqueCrops.textContent = data.uniqueCrops || 0;
    }
    
    const crops = data.crops || [];

    if (crops.length === 0) {
      collectionGrid.innerHTML = '<div class="collection-empty">아직 수확한 작물이 없어요. 작물을 키워서 수확해보세요! 🌱</div>';
      return;
    }

    // 도감 목록 생성
    collectionGrid.innerHTML = crops.map(crop => {
      const icon = CROP_ICONS[crop.cropName] || "🌱";
      const gradeClass = `grade-${crop.bestGrade}`;
      
      return `
        <div class="collection-item">
          <div class="collection-item-icon">${icon}</div>
          <div class="collection-item-name">${crop.cropName}</div>
          <div class="collection-item-grade ${gradeClass}">${crop.bestGrade}</div>
          <div class="collection-item-hp">최고 HP: ${crop.bestHp}</div>
          <div class="collection-item-count">수확 ${crop.harvestCount}회</div>
        </div>
      `;
    }).join("");
  } catch (error) {
    console.error("도감 조회 실패:", error);
    collectionGrid.innerHTML = '<div class="collection-empty">도감을 불러오는 중 오류가 발생했습니다. 😢</div>';
  }
}

// 도감 숨기기
function hideCollection() {
  const collectionModal = document.getElementById("collectionModal");
  if (collectionModal) {
    collectionModal.classList.remove("show");
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
  
  // 도감 버튼 이벤트 리스너
  const collectionButton = document.getElementById("collectionButton");
  if (collectionButton) {
    collectionButton.addEventListener("click", async (e) => {
      e.preventDefault();
      await showCollection();
    });
  }

  // 도감 닫기 버튼 이벤트 리스너
  const collectionClose = document.getElementById("collectionClose");
  if (collectionClose) {
    collectionClose.addEventListener("click", (e) => {
      e.preventDefault();
      hideCollection();
    });
  }

  // 도감 모달 외부 클릭 시 닫기
  const collectionModal = document.getElementById("collectionModal");
  if (collectionModal) {
    collectionModal.addEventListener("click", (e) => {
      if (e.target === collectionModal) {
        hideCollection();
      }
    });
  }
}

// 전역 함수로 내보내기 (HTML에서 사용하기 위해)
window.deleteCrop = deleteCrop;

// 페이지 로드 시 초기화
window.addEventListener("DOMContentLoaded", init);

