// 농업 다마고치 게임 스크립트

const API_BASE = window.API_BASE_URL || "http://127.0.0.1:8000";

// 작물 아이콘 매핑 (폴백용)
const CROP_ICONS = {
  "감자": "🥔",
  "오이": "🥒",
  "토마토": "🍅",
  "당근": "🥕",
  "부추": "🌿"
};

// 작물 영어 이름 매핑 (이미지 폴더명)
const CROP_FOLDER_NAMES = {
  "감자": "potato",
  "오이": "cucumber",
  "토마토": "tomato",
  "당근": "carrot",
  "부추": "chive"
};

// 날짜에 따른 레벨 계산 (7일마다 레벨 증가)
function calculateLevel(day) {
  if (day < 7) return 1;
  if (day < 14) return 2;
  if (day < 21) return 3;
  return 4;
}

// 작물 이미지 경로 생성
function getCropImagePath(state = null) {
  const cropFolder = CROP_FOLDER_NAMES[gameState.cropName];
  if (!cropFolder) {
    // 이미지가 없는 작물은 이모지 사용
    return null;
  }
  
  const level = calculateLevel(gameState.day || 0);
  
  // 상태 우선순위: 명시적 상태(행동 중) > 병해충 > HP 기반 sad > 일반 상태
  let imageState;
  
  // 명시적으로 전달된 상태가 있으면 우선 사용 (watering, fertilizer, pesticide)
  if (state && (state === "watering" || state === "fertilizer" || state === "pesticide")) {
    imageState = state;
  }
  // 병해충이 있으면 sickness 우선
  else if (gameState.hasPest) {
    imageState = "sickness";
  }
  // HP가 70 미만이면 sad 표시
  else if (gameState.hp < 70) {
    imageState = "sad";
  }
  // 그 외에는 normal 또는 전달된 상태
  else {
    imageState = state || gameState.currentImageState || "normal";
  }
  
  // 작물 이름을 영어로 변환 (첫 글자 대문자)
  const cropNameEng = cropFolder.charAt(0).toUpperCase() + cropFolder.slice(1);
  
  return `images/${cropFolder}/${cropNameEng}Lv${level}_${imageState}.png`;
}

// 작물 이미지 업데이트
function updateCropImage(state = null) {
  const displayElement = document.getElementById("cropDisplay");
  if (!displayElement) {
    console.warn("cropDisplay 요소를 찾을 수 없습니다.");
    return;
  }
  
  const imagePath = getCropImagePath(state);
  
  if (imagePath) {
    // img 태그로 변경
    if (displayElement.tagName !== "IMG") {
      const img = document.createElement("img");
      img.id = "cropDisplay";
      img.className = displayElement.className || "crop-display";
      // 인라인 스타일 제거 - CSS에서 크기 제어
      img.style.objectFit = "contain";
      displayElement.parentNode.replaceChild(img, displayElement);
      img.src = imagePath;
      img.alt = `${gameState.cropName} ${state || gameState.currentImageState || "normal"}`;
      // 이미지 로드 실패 시 콘솔에 경로 출력 (디버깅용)
      img.onerror = () => {
        console.error(`이미지 로드 실패: ${imagePath}`);
      };
    } else {
      // 기존 인라인 스타일 제거
      displayElement.style.width = "";
      displayElement.style.height = "";
      displayElement.src = imagePath;
      displayElement.alt = `${gameState.cropName} ${state || gameState.currentImageState || "normal"}`;
      // 이미지 로드 실패 시 콘솔에 경로 출력 (디버깅용)
      displayElement.onerror = () => {
        console.error(`이미지 로드 실패: ${imagePath}`);
      };
    }
  } else {
    // 이미지가 없으면 이모지 사용
    if (displayElement.tagName === "IMG") {
      const div = document.createElement("div");
      div.id = "cropDisplay";
      div.className = "crop-display";
      displayElement.parentNode.replaceChild(div, displayElement);
      div.textContent = CROP_ICONS[gameState.cropName] || "🌱";
    } else {
      displayElement.textContent = CROP_ICONS[gameState.cropName] || "🌱";
    }
  }
}

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

// 월별 가능한 기상 상황 및 확률 정의
const WEATHER_BY_MONTH = {
  1: [  // 1월 (겨울)
    { type: "눈", probability: 0.4 },
    { type: "맑음", probability: 0.3 },
    { type: "흐림", probability: 0.2 },
    { type: "비", probability: 0.1 }
  ],
  2: [  // 2월 (겨울)
    { type: "눈", probability: 0.3 },
    { type: "맑음", probability: 0.3 },
    { type: "흐림", probability: 0.25 },
    { type: "비", probability: 0.15 }
  ],
  3: [  // 3월 (봄)
    { type: "비", probability: 0.35 },
    { type: "맑음", probability: 0.3 },
    { type: "흐림", probability: 0.25 },
    { type: "바람", probability: 0.1 }
  ],
  4: [  // 4월 (봄)
    { type: "비", probability: 0.3 },
    { type: "맑음", probability: 0.35 },
    { type: "흐림", probability: 0.25 },
    { type: "바람", probability: 0.1 }
  ],
  5: [  // 5월 (봄)
    { type: "맑음", probability: 0.4 },
    { type: "비", probability: 0.25 },
    { type: "흐림", probability: 0.25 },
    { type: "바람", probability: 0.1 }
  ],
  6: [  // 6월 (여름 초)
    { type: "맑음", probability: 0.35 },
    { type: "비", probability: 0.3 },
    { type: "흐림", probability: 0.25 },
    { type: "천둥", probability: 0.1 }
  ],
  7: [  // 7월 (여름)
    { type: "맑음", probability: 0.4 },
    { type: "비", probability: 0.25 },
    { type: "천둥", probability: 0.2 },
    { type: "흐림", probability: 0.15 }
  ],
  8: [  // 8월 (여름)
    { type: "맑음", probability: 0.4 },
    { type: "천둥", probability: 0.25 },
    { type: "비", probability: 0.2 },
    { type: "흐림", probability: 0.15 }
  ],
  9: [  // 9월 (가을)
    { type: "맑음", probability: 0.35 },
    { type: "흐림", probability: 0.3 },
    { type: "비", probability: 0.25 },
    { type: "바람", probability: 0.1 }
  ],
  10: [  // 10월 (가을)
    { type: "맑음", probability: 0.35 },
    { type: "흐림", probability: 0.3 },
    { type: "비", probability: 0.25 },
    { type: "바람", probability: 0.1 }
  ],
  11: [  // 11월 (가을)
    { type: "흐림", probability: 0.3 },
    { type: "맑음", probability: 0.3 },
    { type: "비", probability: 0.25 },
    { type: "안개", probability: 0.15 }
  ],
  12: [  // 12월 (겨울)
    { type: "눈", probability: 0.35 },
    { type: "맑음", probability: 0.3 },
    { type: "흐림", probability: 0.2 },
    { type: "비", probability: 0.15 }
  ]
};

// 게임 설정: 1일 = 실제 시간 1시간 (밀리초 단위)
const GAME_DAY_LENGTH_MS = 60 * 60 * 1000; // 1시간 = 3600000ms
// 테스트용으로 더 짧게 설정하려면 아래 주석을 해제하세요:
// const GAME_DAY_LENGTH_MS = 10 * 60 * 1000; // 10분

// 테스트 모드: true이면 버튼으로 날짜 진행, false이면 시간 기반 진행
const TEST_MODE = true; // 테스트 단계에서는 true, 실제 운영 시 false로 변경

// 게임 상태
let gameState = {
  userId: "",
  cropName: "",
  hp: 100,
  day: 0,
  actions: [], // [{type: "water", day: 1, timestamp: "..."}, ...]
  lastFeedback: null,
  gameStartTime: null, // 게임 시작 시간 (ISO string)
  lastUpdateTime: null, // 마지막 업데이트 시간 (ISO string)
  currentWeather: null, // 현재 기상 상황
  weatherDate: null, // 기상이 결정된 날짜
  currentImageState: "normal", // 현재 이미지 상태 (normal, watering, fertilizer, pesticide, sad, sickness)
  hasPest: false // 병해충 발생 여부
};

let timeCheckInterval = null; // 시간 체크 인터벌

// DOM 요소
const hpBar = document.getElementById("hpBar");
const hpValue = document.getElementById("hpValue");
const cropNameEl = document.getElementById("cropName");
const cropDisplay = document.getElementById("cropDisplay");
const dayCount = document.getElementById("dayCount");
const waterButton = document.getElementById("waterButton");
const fertilizerButton = document.getElementById("fertilizerButton");
const pesticideButton = document.getElementById("pesticideButton");
const harvestButton = document.getElementById("harvestButton");
const feedbackMessage = document.getElementById("feedbackMessage");
const nextDayButton = document.getElementById("nextDayButton");
const cropSpeechBubble = document.getElementById("cropSpeechBubble");
const speechBubbleContent = document.getElementById("speechBubbleContent");

// 기상 정보 관련 요소
const weatherIcon = document.getElementById("weatherIcon");
const weatherText = document.getElementById("weatherText");

// Admin 모드 관련 요소
const adminPanel = document.getElementById("adminPanel");
const adminClose = document.getElementById("adminClose");
const adminCurrentDay = document.getElementById("adminCurrentDay");
const adminSkipDay = document.getElementById("adminSkipDay");
const adminSetDay = document.getElementById("adminSetDay");
const adminSetDayBtn = document.getElementById("adminSetDayBtn");
const adminSetHp = document.getElementById("adminSetHp");
const adminSetHpBtn = document.getElementById("adminSetHpBtn");
const adminResetGame = document.getElementById("adminResetGame");

// 게임 오버 모달 관련 요소
const gameOverModal = document.getElementById("gameOverModal");
const restartGameBtn = document.getElementById("restartGameBtn");
const selectCropBtn = document.getElementById("selectCropBtn");

// 그만두기 버튼
const exitButton = document.getElementById("exitButton");

// 메뉴 관련 요소
const menuButton = document.getElementById("menuButton");
const menuDropdown = document.getElementById("menuDropdown");
const characterManageMenuItem = document.getElementById("characterManageMenuItem");
const logoutMenuItem = document.getElementById("logoutMenuItem");

// 로그인 정보 확인 및 게임 상태 로드
async function initGame() {
  const username = sessionStorage.getItem("username") || sessionStorage.getItem("userName") || "";
  const selectedCropName = sessionStorage.getItem("cropName");

  if (!username) {
    alert("로그인이 필요합니다.");
    window.location.href = "login.html";
    return;
  }

  if (!selectedCropName) {
    alert("작물을 먼저 선택해주세요.");
    window.location.href = "recommend.html";
    return;
  }

  gameState.userId = username;
  gameState.cropName = selectedCropName;

  // 게임 상태 불러오기
  await loadGameState();
  
  // UI 업데이트
  updateUI();
  
  // 시간 체크 시작 (1분마다 체크)
  startTimeCheckInterval();
  
  // 다음 날 버튼 이벤트 리스너 등록 (테스트 모드일 때만)
  if (nextDayButton && TEST_MODE) {
    nextDayButton.addEventListener("click", async () => {
      await proceedToNextDay();
    });
  }
  
  // 게임 오버 모달 버튼 이벤트 리스너
  if (restartGameBtn) {
    restartGameBtn.addEventListener("click", async () => {
      await restartGame();
    });
  }
  
  if (selectCropBtn) {
    selectCropBtn.addEventListener("click", () => {
      selectDifferentCrop();
    });
  }
  
  // 그만두기 버튼 이벤트 리스너
  if (exitButton) {
    exitButton.addEventListener("click", (e) => {
      e.preventDefault();
      exitGame();
    });
  }
  
  // 메뉴 버튼 이벤트 리스너
  if (menuButton) {
    menuButton.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      toggleMenu();
    });
  }
  
  // 내 캐릭터 관리 메뉴 아이템
  if (characterManageMenuItem) {
    characterManageMenuItem.addEventListener("click", async (e) => {
      e.preventDefault();
      await goToCharacterManage();
    });
  }
  
  // 로그아웃 메뉴 아이템
  if (logoutMenuItem) {
    logoutMenuItem.addEventListener("click", async (e) => {
      e.preventDefault();
      await logout();
    });
  }
  
  // 메뉴 외부 클릭 시 닫기
  document.addEventListener("click", (e) => {
    if (menuDropdown && menuButton && menuDropdown.classList.contains("show")) {
      if (!menuDropdown.contains(e.target) && !menuButton.contains(e.target)) {
        closeMenu();
      }
    }
  });
  
  // ESC 키로 메뉴 닫기
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && menuDropdown && menuDropdown.classList.contains("show")) {
      closeMenu();
    }
  });
}

// 시간 체크 인터벌 시작
function startTimeCheckInterval() {
  // 테스트 모드일 때는 시간 기반 진행 비활성화
  if (TEST_MODE) {
    return;
  }
  
  // 기존 인터벌 제거
  if (timeCheckInterval) {
    clearInterval(timeCheckInterval);
  }
  
  // 1분마다 시간 체크 및 날짜 업데이트
  timeCheckInterval = setInterval(async () => {
    await updateDayBasedOnTime();
    updateUI(); // UI도 함께 업데이트
  }, 60 * 1000); // 1분 = 60000ms
  
  // 실시간 날짜 표시를 위해 더 자주 UI 업데이트 (30초마다)
  setInterval(() => {
    updateUI();
  }, 30 * 1000); // 30초마다 UI 업데이트
}

// 페이지 언로드 시 인터벌 정리
window.addEventListener("beforeunload", () => {
  if (timeCheckInterval) {
    clearInterval(timeCheckInterval);
  }
});

// 게임 상태 로드
async function loadGameState() {
  try {
    // 새로운 구조에서 작물 목록 가져오기
    const cropsResponse = await fetch(`${API_BASE}/game/crops/${encodeURIComponent(gameState.userId)}`);
    
    if (cropsResponse.ok) {
      const cropsData = await cropsResponse.json();
      const crops = cropsData.crops || [];
      
      // 선택한 작물 찾기
      const currentCrop = crops.find(c => c.cropName === gameState.cropName);
      
      if (currentCrop) {
        // 기존 작물 데이터 로드
        gameState.hp = currentCrop.hp || 100;
        gameState.day = currentCrop.day || 0;
        gameState.gameStartTime = currentCrop.gameStartTime || new Date().toISOString();
        gameState.lastUpdateTime = currentCrop.lastUpdateTime || new Date().toISOString();
        gameState.currentWeather = currentCrop.currentWeather || null;
        gameState.weatherDate = currentCrop.weatherDate || null;
        
        // 게임 시작 시간이 없으면 현재 시간으로 설정
        if (!gameState.gameStartTime) {
          gameState.gameStartTime = new Date().toISOString();
          await saveGameState();
        }
        
        // 시간 기반 날짜 계산 및 업데이트
        await updateDayBasedOnTime();
        return;
      }
    }
    
    // 하위 호환성: 기존 구조 확인
    const response = await fetch(`${API_BASE}/game/state/${encodeURIComponent(gameState.userId)}`);
    if (response.ok) {
      const data = await response.json();
      if (data.state && data.state.cropName === gameState.cropName) {
        gameState = { ...gameState, ...data.state };
        
        if (!gameState.gameStartTime) {
          gameState.gameStartTime = new Date().toISOString();
          await saveGameState();
        }
        
        await updateDayBasedOnTime();
        return;
      }
    }
    
    // 새 게임 시작
    gameState.gameStartTime = new Date().toISOString();
    gameState.day = 0;
    gameState.hp = 100;
    gameState.actions = [];
    gameState.currentWeather = null;
    gameState.weatherDate = null;
    gameState.currentImageState = "normal";
    gameState.hasPest = false;
    await saveGameState();
    
  } catch (error) {
    console.error("게임 상태 불러오기 실패:", error);
    // 오류 시 새 게임으로 시작
    gameState.gameStartTime = new Date().toISOString();
    gameState.day = 0;
    gameState.hp = 100;
    gameState.actions = [];
    gameState.currentWeather = null;
    gameState.weatherDate = null;
    gameState.currentImageState = "normal";
    gameState.hasPest = false;
  }
}

// 현재 날짜(실제 시간)에서 월 가져오기
function getCurrentMonth() {
  const now = new Date();
  return now.getMonth() + 1; // 0-11을 1-12로 변환
}

// 확률 기반 기상 선택
function selectWeatherByMonth(month) {
  const weatherOptions = WEATHER_BY_MONTH[month] || WEATHER_BY_MONTH[12]; // 기본값: 12월
  const random = Math.random();
  
  let cumulativeProbability = 0;
  for (const option of weatherOptions) {
    cumulativeProbability += option.probability;
    if (random <= cumulativeProbability) {
      return option.type;
    }
  }
  
  // 마지막 옵션 반환 (예외 처리)
  return weatherOptions[weatherOptions.length - 1].type;
}

// 날짜 기반 기상 업데이트
function updateWeatherBasedOnDate() {
  const currentMonth = getCurrentMonth();
  const currentDay = calculateCurrentDay();
  
  // 날짜가 바뀌었거나 기상이 아직 설정되지 않았으면 새로 선택
  if (gameState.weatherDate !== currentDay || !gameState.currentWeather) {
    gameState.currentWeather = selectWeatherByMonth(currentMonth);
    gameState.weatherDate = currentDay;
  }
  
  return gameState.currentWeather;
}

// 시간 기반 날짜 계산
function calculateCurrentDay() {
  // 테스트 모드일 때는 gameState.day를 직접 사용
  if (TEST_MODE) {
    return gameState.day || 0;
  }
  
  if (!gameState.gameStartTime) {
    return 0;
  }
  
  const startTime = new Date(gameState.gameStartTime);
  const currentTime = new Date();
  const elapsedMs = currentTime - startTime;
  const currentDay = Math.floor(elapsedMs / GAME_DAY_LENGTH_MS);
  
  return Math.max(0, currentDay);
}

// 작물 말풍선 표시
function showCropSpeechBubble(message, duration = 5000) {
  if (!cropSpeechBubble || !speechBubbleContent) return;
  
  speechBubbleContent.textContent = message;
  cropSpeechBubble.classList.add("show");
  
  // 일정 시간 후 자동으로 숨김
  setTimeout(() => {
    cropSpeechBubble.classList.remove("show");
  }, duration);
}

// 전날 행동들을 평가하는 함수
async function evaluatePreviousDayActions(previousDay) {
  try {
    const previousHp = gameState.hp;
    
    // 전날의 행동들 필터링
    const previousDayActions = gameState.actions.filter(a => a.day === previousDay);
    
    if (previousDayActions.length === 0) {
      // 전날 행동이 없으면 방치 페널티만 적용
      gameState.hp = Math.max(0, gameState.hp - 3);
      if (gameState.hp > 0) {
        showFeedback("방치로 인해 작물 건강도가 약간 감소했습니다... (-3)", "bad");
        showCropSpeechBubble("물과 비료를 제대로 주지 않아서 힘들어요...", 5000);
      }
      return;
    }
    
    // 전날의 날씨 정보 찾기 (첫 번째 행동의 날씨 사용)
    const weatherOnThatDay = previousDayActions[0]?.weather || null;
    
    // 전날 행동들을 일괄 평가
    const response = await fetch(`${API_BASE}/game/evaluate-previous-day`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        userId: gameState.userId,
        cropName: gameState.cropName,
        day: previousDay,
        currentHp: gameState.hp,
        actions: gameState.actions,
        previousActions: gameState.actions.filter(a => a.day < previousDay).slice(-5),
        weatherOnThatDay: weatherOnThatDay
      })
    });

    if (!response.ok) {
      console.error("전날 행동 평가 실패");
      return;
    }

    const result = await response.json();
    
    // HP 업데이트
    gameState.hp = Math.max(0, Math.min(100, result.newHp));
    const hpChange = gameState.hp - previousHp;
    
    // HP가 감소했을 때 일시적으로 sad 표시
    if (hpChange < 0 && !gameState.hasPest) {
      gameState.currentImageState = "sad";
      updateCropImage("sad");
      
      // 3초 후 HP에 따라 상태 결정
      setTimeout(() => {
        if (!gameState.hasPest) {
          if (gameState.hp < 70) {
            // HP가 70 미만이면 계속 sad 유지
            gameState.currentImageState = "sad";
          } else {
            // HP가 70 이상이면 normal로 복귀
            gameState.currentImageState = "normal";
          }
          updateCropImage();
        }
      }, 3000);
    } else {
      // HP가 증가하거나 변화가 없을 때는 HP에 따라 상태 결정
      if (!gameState.hasPest) {
        if (gameState.hp < 70) {
          gameState.currentImageState = "sad";
        } else {
          gameState.currentImageState = "normal";
        }
        updateCropImage();
      }
    }
    
    // HP가 감소했을 때 말풍선으로 피드백 표시
    if (hpChange < 0 && result.feedbacks && result.feedbacks.length > 0) {
      // 피드백에서 핵심 메시지 추출
      const mainFeedback = result.feedbacks[0];
      
      // 관리 소홀 부분 파악
      let managementIssue = "";
      if (mainFeedback.includes("과습") || mainFeedback.includes("물")) {
        managementIssue = "물을 너무 많이 주셨어요. 습한 날씨에는 물을 주지 않는 게 좋아요.";
      } else if (mainFeedback.includes("비료")) {
        managementIssue = "비료를 너무 많이 주셨어요. 적당한 양을 주는 게 중요해요.";
      } else if (mainFeedback.includes("방치")) {
        managementIssue = "관리를 제대로 해주지 않아서 힘들어요. 물과 비료를 꾸준히 주세요.";
      } else {
        // 피드백에서 핵심만 추출
        managementIssue = mainFeedback.replace(/\([^)]*\)/g, "").trim();
      }
      
      showCropSpeechBubble(managementIssue, 6000);
    }
    
    // 피드백 표시 (여러 피드백이 있으면 모두 표시)
    if (result.feedbacks && result.feedbacks.length > 0) {
      // 첫 번째 피드백을 즉시 표시
      const firstFeedback = result.feedbacks[0];
      const feedbackType = result.totalHpChange > 0 ? "good" : result.totalHpChange < 0 ? "bad" : "neutral";
      showFeedback(firstFeedback, feedbackType);
      
      // 나머지 피드백이 있으면 약간의 지연 후 표시
      if (result.feedbacks.length > 1) {
        setTimeout(() => {
          const combinedFeedback = result.feedbacks.slice(1).join(" ");
          showFeedback(combinedFeedback, feedbackType);
        }, 3000);
      }
    }
    
  } catch (error) {
    console.error("전날 행동 평가 실패:", error);
  }
}

// 병해충 발생 체크
async function checkPestOccurrence(day) {
  try {
    const response = await fetch(`${API_BASE}/game/check-pest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        userId: gameState.userId,
        cropName: gameState.cropName,
        day: day,
        currentHp: gameState.hp,
        actions: gameState.actions,
        currentWeather: gameState.currentWeather
      })
    });

    if (!response.ok) {
      return; // 오류 시 무시
    }

    const result = await response.json();
    
    if (result.pestOccurred) {
      // 병해충 발생 시 HP 감소
      gameState.hp = Math.max(0, gameState.hp + result.hpChange);
      gameState.hasPest = true; // 병해충 상태 설정
      gameState.currentImageState = "sickness";
      updateCropImage("sickness");
      
      if (result.feedback) {
        showFeedback(result.feedback, "bad");
        // 병해충 발생 시 말풍선으로 피드백
        const pestMessage = `${result.pestName}이(가) 발생했어요! 농약을 살포해주세요.`;
        showCropSpeechBubble(pestMessage, 6000);
      }
      return true;
    }
    
    // 병해충이 해결되었는지 확인 (농약 살포 후)
    if (gameState.hasPest) {
      const recentPesticide = gameState.actions.filter(
        a => a.type === "pesticide" && a.day >= (gameState.day || 0) - 1
      );
      if (recentPesticide.length > 0) {
      // 농약을 살포했으면 병해충 상태 해제
      gameState.hasPest = false;
      if (gameState.hp < 70) {
        gameState.currentImageState = "sad";
      } else {
        gameState.currentImageState = "normal";
      }
      updateCropImage();
      }
    }
    
    return false;
  } catch (error) {
    console.error("병해충 체크 실패:", error);
    return false;
  }
}

// 시간 기반 날짜 업데이트 (날짜가 증가하면 자동 처리)
async function updateDayBasedOnTime() {
  // 테스트 모드일 때는 이 함수를 사용하지 않음
  if (TEST_MODE) {
    return gameState.day || 0;
  }
  
  const calculatedDay = calculateCurrentDay();
  const previousDay = gameState.day || 0;
  
  // 날짜가 증가했을 때만 처리
  if (calculatedDay > previousDay) {
    const daysPassed = calculatedDay - previousDay;
    
    // 각 증가한 날짜에 대해 자동 평가
    for (let d = previousDay + 1; d <= calculatedDay; d++) {
      // 전날(d-1)의 행동들을 평가 (다음 날에 효과가 나타남)
      if (d > 0) {
        await evaluatePreviousDayActions(d - 1);
      }
      
      // 병해충 발생 체크 (날짜가 진행될 때마다)
      if (d > 0) {
        await checkPestOccurrence(d);
      }
    }
    
    gameState.day = calculatedDay;
    gameState.lastUpdateTime = new Date().toISOString();
    
    // 날짜가 변경되었으므로 기상 업데이트
    updateWeatherBasedOnDate();
    
    await saveGameState();
    updateUI();
  }
  
  return calculatedDay;
}

// 다음 날로 진행 (테스트 모드용)
async function proceedToNextDay() {
  if (!TEST_MODE) {
    showFeedback("테스트 모드가 아닙니다.", "error");
    return;
  }
  
  // 버튼 비활성화 (중복 클릭 방지)
  if (nextDayButton) {
    nextDayButton.disabled = true;
  }
  
  try {
    const currentDay = gameState.day || 0;
    const nextDay = currentDay + 1;
    
    // 전날(현재 날짜)의 행동들을 평가 (다음 날에 효과가 나타남)
    if (currentDay >= 0) {
      await evaluatePreviousDayActions(currentDay);
    }
    
    gameState.day = nextDay;
    gameState.lastUpdateTime = new Date().toISOString();
    
    // 날짜가 변경되었으므로 기상 업데이트
    updateWeatherBasedOnDate();
    
    // 병해충 발생 체크 (다음 날로 진행할 때)
    if (nextDay > 0) {
      await checkPestOccurrence(nextDay);
    }
    
    await saveGameState();
    updateUI();
    
    showFeedback(`다음 날로 진행했습니다! (Day ${nextDay})`, "neutral");
  } catch (error) {
    console.error("날짜 진행 실패:", error);
    showFeedback("날짜 진행 중 오류가 발생했습니다.", "error");
  } finally {
    // 버튼 재활성화
    if (nextDayButton) {
      nextDayButton.disabled = false;
    }
  }
}

// 게임 상태 저장
async function saveGameState() {
  try {
    // 새로운 구조로 작물 저장 (여러 작물 지원)
    const cropData = {
      cropName: gameState.cropName,
      hp: gameState.hp,
      day: gameState.day,
      gameStartTime: gameState.gameStartTime,
      lastUpdateTime: gameState.lastUpdateTime || new Date().toISOString(),
      currentWeather: gameState.currentWeather,
      weatherDate: gameState.weatherDate,
      currentImageState: gameState.currentImageState || "normal",
      hasPest: gameState.hasPest || false
    };
    
    const response = await fetch(`${API_BASE}/game/crop`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        userId: gameState.userId,
        crop: cropData
      })
    });
    
    if (!response.ok) {
      throw new Error("게임 상태 저장 실패");
    }
    
    // 하위 호환성을 위해 기존 API도 호출
    await fetch(`${API_BASE}/game/state`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        userId: gameState.userId,
        state: gameState
      })
    });
  } catch (error) {
    console.error("게임 상태 저장 실패:", error);
  }
}

// UI 업데이트
function updateUI() {
  // 작물 이름
  cropNameEl.textContent = gameState.cropName;
  
  // 작물 이미지 업데이트 (상태에 따라)
  updateCropImage();
  
  // HP 바
  const currentHp = Math.max(0, Math.min(100, gameState.hp));
  hpValue.textContent = currentHp;
  hpBar.style.width = `${currentHp}%`;
  
  // 날짜 표시 (테스트 모드에서는 gameState.day 사용)
  const currentDay = calculateCurrentDay();
  dayCount.textContent = currentDay;
  
  // 기상 정보 업데이트 및 표시
  updateWeatherBasedOnDate();
  if (weatherIcon && weatherText && gameState.currentWeather) {
    weatherIcon.textContent = WEATHER_ICONS[gameState.currentWeather] || "☀️";
    weatherText.textContent = gameState.currentWeather;
  }
  
  // 수확 버튼 표시 여부 (예: 7일 이상 되면)
  if (currentDay >= 7) {
    harvestButton.style.display = "block";
  } else {
    harvestButton.style.display = "none";
  }
  
  // 다음 날 버튼 표시 여부 (테스트 모드일 때만)
  if (nextDayButton) {
    if (TEST_MODE) {
      nextDayButton.style.display = "block";
    } else {
      nextDayButton.style.display = "none";
    }
  }
  
  // HP가 0이면 게임 오버 모달 표시
  if (currentHp <= 0) {
    showGameOverModal();
  } else {
    hideGameOverModal();
  }
}

// 행동 실행 (물주기, 비료주기, 농약살포)
async function performAction(actionType) {
  if (gameState.hp <= 0) {
    showGameOverModal();
    return;
  }

  // 먼저 시간 기반 날짜 업데이트 (테스트 모드가 아닐 때만)
  if (!TEST_MODE) {
    await updateDayBasedOnTime();
  }

  // 버튼 비활성화
  const buttons = [waterButton, fertilizerButton, pesticideButton];
  buttons.forEach(btn => btn.disabled = true);

  try {
    // 현재 날짜 계산
    const currentDay = calculateCurrentDay();
    const actionTimestamp = new Date().toISOString();
    
    // 기상 정보 업데이트 (행동 시점의 날씨 기록)
    updateWeatherBasedOnDate();
    
    // 행동 기록 (날짜 증가 없이 행동만 기록, 날씨 정보도 함께 저장)
    gameState.actions.push({
      type: actionType,
      day: currentDay,
      timestamp: actionTimestamp,
      weather: gameState.currentWeather // 행동 시점의 날씨 저장
    });

    // 행동에 맞는 이미지로 변경
    const imageStateMap = {
      "water": "watering",
      "fertilizer": "fertilizer",
      "pesticide": "pesticide"
    };
    const actionImageState = imageStateMap[actionType];
    
    if (actionImageState) {
      // 즉시 이미지 변경 (updateUI를 호출하지 않고 직접 이미지만 업데이트)
      updateCropImage(actionImageState);
      
      // 2초 후 HP에 따라 상태 결정
      setTimeout(() => {
        if (!gameState.hasPest) {
          if (gameState.hp < 70) {
            gameState.currentImageState = "sad";
          } else {
            gameState.currentImageState = "normal";
          }
          updateCropImage();
        }
      }, 2000);
    }

    // 즉시 평가하지 않고 행동만 기록
    // 간단한 확인 메시지만 표시
    const actionNames = {
      "water": "물",
      "fertilizer": "비료",
      "pesticide": "농약"
    };
    const actionName = actionNames[actionType] || "관리";
    showFeedback(`${actionName}을(를) 주었습니다. 내일 효과가 나타날 거예요!`, "neutral");

    // 게임 상태 저장
    await saveGameState();
    
    // UI 업데이트 (이미지는 이미 변경했으므로 제외)
    // updateUI()는 이미지를 다시 업데이트하므로 호출하지 않음
    // 대신 필요한 UI 요소만 업데이트
    const currentDayForUI = calculateCurrentDay();
    if (dayCount) {
      dayCount.textContent = currentDayForUI;
    }

  } catch (error) {
    console.error("행동 실행 실패:", error);
    showFeedback("오류가 발생했습니다. 다시 시도해주세요.", "error");
  } finally {
    // 버튼 재활성화
    buttons.forEach(btn => btn.disabled = false);
  }
}

// 게임 오버 모달 표시
function showGameOverModal() {
  if (gameOverModal) {
    gameOverModal.classList.add("show");
    // 모든 행동 버튼 비활성화
    [waterButton, fertilizerButton, pesticideButton, harvestButton, nextDayButton].forEach(btn => {
      if (btn) btn.disabled = true;
    });
  }
}

// 게임 오버 모달 숨김
function hideGameOverModal() {
  if (gameOverModal) {
    gameOverModal.classList.remove("show");
  }
}

// 게임 처음부터 다시 시작
async function restartGame() {
  if (!confirm("정말 처음부터 다시 시작하시겠습니까? 현재 진행 상황이 모두 초기화됩니다.")) {
    return;
  }
  
  gameState.gameStartTime = new Date().toISOString();
  gameState.day = 0;
  gameState.hp = 100;
  gameState.actions = [];
  gameState.lastFeedback = null;
  gameState.lastUpdateTime = null;
  gameState.currentWeather = null;
  gameState.weatherDate = null;
  gameState.currentImageState = "normal";
  gameState.hasPest = false;
  
  await saveGameState();
  hideGameOverModal();
  updateUI();
  
  // 버튼 재활성화
  [waterButton, fertilizerButton, pesticideButton].forEach(btn => {
    if (btn) btn.disabled = false;
  });
  
  showFeedback("게임이 처음부터 다시 시작되었습니다!", "good");
}

// 다른 작물 선택하기
function selectDifferentCrop() {
  if (!confirm("다른 작물을 선택하시겠습니까? 현재 게임 진행 상황은 저장되지 않습니다.")) {
    return;
  }
  
  // 작물 선택 화면으로 이동
  window.location.href = "recommend.html";
}

// 게임 포기하기
async function exitGame() {
  if (!confirm("게임을 그만두시겠습니까? 현재 진행 상황은 저장됩니다. 나중에 다시 돌아올 수 있습니다.")) {
    return;
  }
  
  // 게임 상태 저장 (현재 상태 그대로 저장)
  await saveGameState();
  
  // 캐릭터 관리 페이지로 이동
  window.location.href = "character-select.html";
}

// 메뉴 토글
function toggleMenu() {
  if (menuDropdown) {
    menuDropdown.classList.toggle("show");
  }
}

// 메뉴 닫기
function closeMenu() {
  if (menuDropdown) {
    menuDropdown.classList.remove("show");
  }
}

// 내 캐릭터 관리 페이지로 이동
async function goToCharacterManage() {
  // 게임 상태 저장
  await saveGameState();
  closeMenu();
  window.location.href = "character-select.html";
}

// 로그아웃
async function logout() {
  if (!confirm("로그아웃하시겠습니까? 현재 진행 상황은 저장됩니다.")) {
    return;
  }
  
  // 게임 상태 저장
  await saveGameState();
  
  // 세션 스토리지 정리
  sessionStorage.removeItem("username");
  sessionStorage.removeItem("userName");
  sessionStorage.removeItem("userEmail");
  sessionStorage.removeItem("cropName");
  sessionStorage.removeItem("selectedCrop");
  
  closeMenu();
  
  // 로그인 페이지로 이동
  window.location.href = "login.html";
}

// 피드백 메시지 표시
function showFeedback(message, type = "neutral") {
  feedbackMessage.textContent = message;
  feedbackMessage.className = `feedback-message show ${type}`;
  
  setTimeout(() => {
    feedbackMessage.classList.remove("show");
  }, 5000);
}

// 수확하기
async function harvest() {
  // 먼저 시간 기반 날짜 업데이트 (테스트 모드가 아닐 때만)
  if (!TEST_MODE) {
    await updateDayBasedOnTime();
  }
  
  const currentDay = calculateCurrentDay();
  
  if (gameState.hp < 70) {
    showFeedback("작물 건강도가 70 미만입니다. 더 잘 키워주세요!", "error");
    return;
  }

  try {
    // 수확 전 피드백 요청
    const response = await fetch(`${API_BASE}/game/harvest-feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        userId: gameState.userId,
        cropName: gameState.cropName,
        finalHp: gameState.hp,
        totalDays: currentDay,
        actions: gameState.actions
      })
    });

    if (!response.ok) {
      throw new Error("피드백 요청 실패");
    }

    const result = await response.json();
    
    // 성공 메시지 표시
    alert(`🎉 수확 성공!\n\n${result.message}\n\n최종 건강도: ${gameState.hp}/100`);
    
    // 게임 완료 처리
    sessionStorage.setItem("lastGameResult", JSON.stringify({
      cropName: gameState.cropName,
      finalHp: gameState.hp,
      totalDays: currentDay,
      success: true
    }));

    // 메인으로 이동
    window.location.href = "main.html";

  } catch (error) {
    console.error("수확 실패:", error);
    showFeedback("수확 처리 중 오류가 발생했습니다.", "error");
  }
}

// 버튼 이벤트 리스너
waterButton.addEventListener("click", () => performAction("water"));
fertilizerButton.addEventListener("click", () => performAction("fertilizer"));
pesticideButton.addEventListener("click", () => performAction("pesticide"));
harvestButton.addEventListener("click", harvest);

// 작물 관리 가이드 가져오기
async function getCropGuide() {
  try {
    const response = await fetch(`${API_BASE}/game/crop-guide/${encodeURIComponent(gameState.cropName)}`);
    if (response.ok) {
      const data = await response.json();
      return data.guide || "";
    }
  } catch (error) {
    console.error("작물 가이드 가져오기 실패:", error);
  }
  return null;
}

// 도움말 버튼
document.getElementById("helpButton").addEventListener("click", async (e) => {
  e.preventDefault();
  
  const guide = await getCropGuide();
  
  let helpMessage = `🌱 ${gameState.cropName} 작물 관리 가이드\n\n`;
  helpMessage += `═══════════════════════════════\n`;
  helpMessage += `📌 기본 관리 방법\n`;
  helpMessage += `═══════════════════════════════\n\n`;
  helpMessage += `💧 물 주기:\n`;
  helpMessage += `  • 적절한 시기에 물을 주세요\n`;
  helpMessage += `  • 습한 날씨(비, 눈, 천둥)에는 물을 주지 마세요\n`;
  helpMessage += `  • 과습은 뿌리를 썩게 할 수 있어요\n\n`;
  helpMessage += `🌿 비료 주기:\n`;
  helpMessage += `  • 작물에 맞는 비료를 적당한 양만 주세요\n`;
  helpMessage += `  • 너무 많이 주면 오히려 해로울 수 있어요\n\n`;
  helpMessage += `💊 농약 살포:\n`;
  helpMessage += `  • 병해충이 발생했을 때 사용하세요\n`;
  helpMessage += `  • 예방 차원에서 주기적으로 사용할 수도 있어요\n\n`;
  helpMessage += `═══════════════════════════════\n`;
  helpMessage += `💡 게임 팁\n`;
  helpMessage += `═══════════════════════════════\n\n`;
  helpMessage += `• 행동을 하면 다음 날에 효과가 나타나요\n`;
  helpMessage += `• 작물 건강도가 70 이상이면 수확할 수 있어요\n`;
  helpMessage += `• 날씨에 따라 관리 방법을 조절하세요\n`;
  helpMessage += `• 작물이 말풍선으로 피드백을 줄 거예요\n\n`;
  
  if (guide) {
    helpMessage += `═══════════════════════════════\n`;
    helpMessage += `📖 ${gameState.cropName} 상세 정보\n`;
    helpMessage += `═══════════════════════════════\n\n`;
    // 가이드 텍스트를 간단하게 정리
    const guideLines = guide.split('\n').filter(line => line.trim());
    const importantLines = guideLines.slice(0, 15); // 처음 15줄만 표시
    helpMessage += importantLines.join('\n');
    if (guideLines.length > 15) {
      helpMessage += '\n\n... (더 자세한 정보는 게임을 진행하며 확인하세요)';
    }
  }
  
  alert(helpMessage);
});

// Admin 모드 활성화/비활성화
function toggleAdminPanel() {
  adminPanel.classList.toggle("show");
  if (adminPanel.classList.contains("show")) {
    updateAdminPanel();
  }
}

function updateAdminPanel() {
  const currentDay = calculateCurrentDay();
  adminCurrentDay.value = `Day ${currentDay}`;
}

// Admin 모드: 다음날로 건너뛰기
async function skipDay() {
  const currentDay = calculateCurrentDay();
  const targetDay = currentDay + 1;
  
  // gameStartTime을 조정하여 다음날이 되도록 설정
  const currentTime = new Date();
  const targetTime = new Date(gameState.gameStartTime);
  targetTime.setTime(targetTime.getTime() - (targetDay * GAME_DAY_LENGTH_MS));
  
  gameState.gameStartTime = targetTime.toISOString();
  gameState.lastUpdateTime = currentTime.toISOString();
  
  await saveGameState();
  await updateDayBasedOnTime();
  updateUI();
  updateAdminPanel();
  
  showFeedback(`관리자: 다음날로 건너뛰었습니다! (Day ${targetDay})`, "neutral");
}

// Admin 모드: 날짜 직접 설정
async function setDay() {
  const dayValue = parseInt(adminSetDay.value);
  if (isNaN(dayValue) || dayValue < 0) {
    showFeedback("올바른 날짜를 입력해주세요 (0 이상)", "error");
    return;
  }
  
  const currentTime = new Date();
  const targetTime = new Date(currentTime);
  targetTime.setTime(targetTime.getTime() - (dayValue * GAME_DAY_LENGTH_MS));
  
  gameState.gameStartTime = targetTime.toISOString();
  gameState.lastUpdateTime = currentTime.toISOString();
  gameState.day = dayValue;
  
  await saveGameState();
  await updateDayBasedOnTime();
  updateUI();
  updateAdminPanel();
  adminSetDay.value = "";
  
  showFeedback(`관리자: 날짜를 Day ${dayValue}로 설정했습니다!`, "neutral");
}

// Admin 모드: HP 직접 설정
async function setHp() {
  const hpValue = parseInt(adminSetHp.value);
  if (isNaN(hpValue) || hpValue < 0 || hpValue > 100) {
    showFeedback("올바른 HP를 입력해주세요 (0-100)", "error");
    return;
  }
  
  gameState.hp = hpValue;
  await saveGameState();
  updateUI();
  adminSetHp.value = "";
  
  showFeedback(`관리자: HP를 ${hpValue}로 설정했습니다!`, "neutral");
}

// Admin 모드: 게임 초기화
async function resetGame() {
  if (!confirm("정말 게임을 초기화하시겠습니까? 모든 진행 상황이 삭제됩니다.")) {
    return;
  }
  
  gameState.gameStartTime = new Date().toISOString();
  gameState.day = 0;
  gameState.hp = 100;
  gameState.actions = [];
  gameState.lastFeedback = null;
  gameState.lastUpdateTime = null;
  gameState.currentWeather = null;
  gameState.weatherDate = null;
  gameState.currentImageState = "normal";
  gameState.hasPest = false;
  
  await saveGameState();
  updateUI();
  updateAdminPanel();
  
  showFeedback("관리자: 게임이 초기화되었습니다!", "neutral");
}

// Admin 모드 이벤트 리스너 설정
function initAdminMode() {
  // 키보드 단축키: Ctrl+Shift+D
  document.addEventListener("keydown", (e) => {
    if (e.ctrlKey && e.shiftKey && e.key === "D") {
      e.preventDefault();
      toggleAdminPanel();
    }
  });
  
  // Admin 패널 닫기
  adminClose.addEventListener("click", () => {
    adminPanel.classList.remove("show");
  });
  
  // Admin 패널 외부 클릭 시 닫기
  adminPanel.addEventListener("click", (e) => {
    if (e.target === adminPanel) {
      adminPanel.classList.remove("show");
    }
  });
  
  // Admin 기능 버튼들
  adminSkipDay.addEventListener("click", skipDay);
  adminSetDayBtn.addEventListener("click", setDay);
  adminSetHpBtn.addEventListener("click", setHp);
  adminResetGame.addEventListener("click", resetGame);
}

// 페이지 로드 시 초기화
window.addEventListener("DOMContentLoaded", () => {
  initGame();
  initAdminMode();
});

