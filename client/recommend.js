// 다마고치 선택 게임 스크립트 (추천 시스템 포함)

const API_URL = window.RECOMMENDATION_API_URL || "http://127.0.0.1:8000/recommendations";

// 초기 작물 목록: 감자, 오이, 토마토, 당근, 부추
const INITIAL_CROPS = ["감자", "오이", "토마토", "당근", "부추"];

// 작물 아이콘 매핑 (더 많은 작물 지원)
const CROP_ICONS = {
  "감자": "🥔",
  "오이": "🥒",
  "토마토": "🍅",
  "당근": "🥕",
  "부추": "🌿",
  "고구마": "🍠",
  "고추": "🌶️",
  "상추": "🥬",
  "배추": "🥬",
  "양파": "🧅",
  "마늘": "🧄",
  "옥수수": "🌽",
  "콩": "🫘",
  "딸기": "🍓",
  "수박": "🍉"
};

// 난이도 색상 매핑
const LEVEL_COLORS = {
  "하": "easy",
  "중": "medium",
  "상": "hard",
  "최상": "hard"
};

let allCrops = [];
let filteredCrops = [];
let selectedCrop = null;
const container = document.getElementById("cropContainer");
const selectButton = document.getElementById("selectButton");
const filterForm = document.getElementById("filterForm");
const filterStatus = document.getElementById("filterStatus");

// 초기 작물만 필터링하는 함수
function filterInitialCrops(crops) {
  return crops.filter(crop => INITIAL_CROPS.includes(crop.name));
}

// 작물 정보 로드 (초기 또는 필터 적용)
async function loadCrops(filters = {}, showInitial = false) {
  try {
    container.className = "loading";
    container.innerHTML = `
      <div class="spinner"></div>
      <p>작물 정보를 불러오는 중...</p>
    `;

    // API 호출
    const response = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        season: filters.season || null,
        level: filters.level || null,
        sunlight: filters.sunlight || null
      })
    });

    if (!response.ok) {
      throw new Error(`API 호출 실패 (${response.status})`);
    }

    const data = await response.json();
    allCrops = data.results || [];

    // 필터가 있으면 필터링된 결과 표시
    if (showInitial || (filters.season || filters.level || filters.sunlight)) {
      if (showInitial) {
        // 초기 작물만 표시 (필터 없이 추천받기 버튼 클릭 시)
        filteredCrops = filterInitialCrops(allCrops);
        filteredCrops.sort((a, b) => {
          const orderA = INITIAL_CROPS.indexOf(a.name);
          const orderB = INITIAL_CROPS.indexOf(b.name);
          return orderA - orderB;
        });
        filterStatus.style.display = "none";
      } else {
        // 필터 적용된 결과
        filteredCrops = allCrops;
        updateFilterStatus(filters);
      }
      renderCrops(filteredCrops);
    } else {
      // 필터도 없고 초기 표시도 아니면 빈 상태
      container.className = "empty-state";
      container.innerHTML = `
        <p style="color: var(--muted);">👆 왼쪽에서 조건을 선택하고 "추천받기"를 눌러주세요</p>
        <p style="font-size: 14px; margin-top: 12px; color: var(--muted);">또는 필터 없이 추천받기를 누르면 초기 작물을 볼 수 있습니다</p>
      `;
      selectButton.style.display = "none";
    }
  } catch (error) {
    console.error(error);
    container.className = "empty-state";
    container.innerHTML = `
      <p style="color: var(--danger);">⚠️ 작물 정보를 불러오지 못했습니다.</p>
      <p style="font-size: 14px; margin-top: 8px;">FastAPI 서버를 확인해주세요.</p>
    `;
  }
}

// 필터 상태 표시 업데이트
function updateFilterStatus(filters) {
  const conditions = [];
  if (filters.season) conditions.push(`재배 시기: ${filters.season}`);
  if (filters.level) conditions.push(`난이도: ${filters.level}`);
  if (filters.sunlight) conditions.push(`햇빛: ${filters.sunlight}`);

  if (conditions.length > 0) {
    filterStatus.textContent = `현재 조건: ${conditions.join(", ")}`;
    filterStatus.style.display = "block";
  } else {
    filterStatus.style.display = "none";
  }
}

// 작물 카드 렌더링
function renderCrops(crops) {
  if (!crops || crops.length === 0) {
    container.className = "empty-state";
    container.innerHTML = `
      <p>조건에 맞는 작물이 없습니다.</p>
      <p style="font-size: 14px; margin-top: 8px; color: var(--muted);">다른 조건으로 검색해보세요.</p>
    `;
    selectButton.style.display = "none";
    return;
  }

  container.className = "crop-grid";
  selectButton.style.display = "block";

  // 초기 작물 우선 표시 (감자, 오이, 토마토, 당근, 부추)
  const initialCropsList = crops.filter(c => INITIAL_CROPS.includes(c.name));
  const otherCropsList = crops.filter(c => !INITIAL_CROPS.includes(c.name));

  // 초기 작물 먼저, 나머지는 그 뒤에
  const sortedCrops = [...initialCropsList, ...otherCropsList];

  container.innerHTML = sortedCrops.map((crop, index) => {
    const icon = CROP_ICONS[crop.name] || "🌱";
    const level = crop.level || "중";
    const levelClass = LEVEL_COLORS[level] || "medium";
    const isAvailable = INITIAL_CROPS.includes(crop.name);
    
    // 재배 시기 정보 추출 (간단하게)
    let seasonText = crop.season || "정보 없음";
    if (seasonText.length > 30) {
      seasonText = seasonText.substring(0, 30) + "...";
    }
    
    // 재배 목적 정보 추출 (간단하게)
    let purposeText = crop.purpose || "정보 없음";
    if (purposeText.length > 40) {
      purposeText = purposeText.substring(0, 40) + "...";
    }

    return `
      <div class="crop-card ${isAvailable ? '' : 'disabled'}" 
           data-crop-name="${crop.name}" 
           data-index="${index}"
           data-available="${isAvailable}">
        ${!isAvailable ? '<div class="coming-soon-badge">추후 예정</div>' : ''}
        <div class="crop-icon" style="animation-delay: ${index * 0.1}s; opacity: ${isAvailable ? '1' : '0.5'}">${icon}</div>
        <div class="crop-name" style="opacity: ${isAvailable ? '1' : '0.5'}">${crop.name}</div>
        <div class="crop-info" style="opacity: ${isAvailable ? '1' : '0.5'}">📅 ${seasonText}</div>
        <div class="crop-info" style="opacity: ${isAvailable ? '1' : '0.5'}">💡 ${purposeText}</div>
        <div class="crop-level ${levelClass}" style="opacity: ${isAvailable ? '1' : '0.5'}">난이도: ${level}</div>
      </div>
    `;
  }).join("");

  // 카드 클릭 이벤트
  document.querySelectorAll(".crop-card").forEach(card => {
    const isAvailable = card.dataset.available === "true";
    
    if (!isAvailable) {
      card.style.cursor = "not-allowed";
    }
    
    card.addEventListener("click", () => {
      // 선택 불가능한 작물은 클릭 무시
      if (!isAvailable) {
        return;
      }

      // 기존 선택 제거
      document.querySelectorAll(".crop-card").forEach(c => {
        c.classList.remove("selected");
      });

      // 새 선택
      card.classList.add("selected");
      selectedCrop = allCrops.find(c => c.name === card.dataset.cropName);
      selectButton.disabled = false;
    });
  });
}

// 필터 폼 제출
filterForm.addEventListener("submit", (e) => {
  e.preventDefault();
  
  const formData = new FormData(filterForm);
  const filters = {
    season: formData.get("season") || null,
    level: formData.get("level") || null,
    sunlight: formData.get("sunlight") || null
  };

  // 필터가 하나라도 있으면 추천 검색, 없으면 초기 작물만 표시
  if (filters.season || filters.level || filters.sunlight) {
    loadCrops(filters, false);
  } else {
    // 필터 없이 추천받기를 누르면 초기 작물만 표시
    loadCrops({}, true);
  }

  // 선택 초기화
  selectedCrop = null;
  selectButton.disabled = true;
});

// 작물 선택 처리
selectButton.addEventListener("click", async () => {
  if (!selectedCrop) return;

  // 로그인 정보 확인
  const username = sessionStorage.getItem("username") || sessionStorage.getItem("userName") || "";
  
  if (!username) {
    alert("로그인이 필요합니다. 먼저 로그인해주세요.");
    window.location.href = "login.html";
    return;
  }

  // 선택한 작물을 세션에 저장
  sessionStorage.setItem("selectedCrop", JSON.stringify(selectedCrop));
  sessionStorage.setItem("cropName", selectedCrop.name);

  // 선택 완료 처리
  selectButton.disabled = true;
  selectButton.textContent = "선택 중...";
  
  setTimeout(() => {
    selectButton.textContent = "✓ 선택 완료!";
    selectButton.style.background = "linear-gradient(135deg, var(--success), #16a34a)";
    
    setTimeout(() => {
      window.location.href = "game.html";
    }, 800);
  }, 500);
});

// 페이지 로드 시
window.addEventListener("DOMContentLoaded", () => {
  // 이미 선택한 작물이 있으면 확인
  const existingCrop = sessionStorage.getItem("cropName");
  if (existingCrop) {
    const confirmChange = confirm(`이미 선택한 작물(${existingCrop})이 있습니다. 새로 선택하시겠습니까?`);
    if (!confirmChange) {
      window.location.href = "main.html";
      return;
    } else {
      sessionStorage.removeItem("selectedCrop");
      sessionStorage.removeItem("cropName");
    }
  }
  
  // 초기에는 작물 표시 안 함 (추천받기 버튼을 눌러야 표시)
  container.className = "empty-state";
  container.innerHTML = `
    <p style="color: var(--muted);">👆 왼쪽에서 조건을 선택하고 "추천받기"를 눌러주세요</p>
    <p style="font-size: 14px; margin-top: 12px; color: var(--muted);">또는 필터 없이 추천받기를 누르면 초기 작물을 볼 수 있습니다</p>
  `;
  selectButton.style.display = "none";
});
