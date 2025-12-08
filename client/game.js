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
  "부추": "chives"
};

// 작물별 이미지 상태 매핑 (파일명 차이 처리)
const CROP_IMAGE_CONFIG = {
  "감자": {
    // 감자는 Lv2, Lv3에서 watering 사용
    useWateringForLv2Lv3: true,
    // 병해충 이미지 이름 (모든 레벨에서 sickness)
    sicknessName: "sickness",
    // 비료 애니메이션 사용 여부 (fertilizer2가 있는지)
    hasFertilizer2: false
  },
  "토마토": {
    // 토마토는 모든 레벨에서 water 사용
    useWateringForLv2Lv3: false,
    // 병해충 이미지 이름 (Lv1은 sickness, Lv2~4는 sick)
    sicknessName: {
      1: "sickness",
      2: "sick",
      3: "sick",
      4: "sick"
    },
    // 비료 애니메이션 사용 여부 (fertilizer2가 있는지)
    hasFertilizer2: true,
    // fertilizer2 파일명 (토마토는 오타 fertilzer2)
    fertilizer2Name: "fertilzer2"
  },
  "오이": {
    // 병해충 이미지 이름 (모든 레벨에서 sick)
    sicknessName: "sick",
    // 비료 애니메이션 사용 여부
    hasFertilizer2: true,
    // Lv4의 normal 이미지는 특수 형식 (언더스코어 없이 CucumberLv4.png)
    normalFallback: {
      4: null  // Lv4만 CucumberLv4.png 형식
    },
    specialNormalFormat: true,
    // normal 이미지 파일명이 소문자로 시작 (cucumberLv1_normal.png)
    lowercaseNormal: true
  },
  "당근": {
    // 병해충 이미지 이름 (모든 레벨에서 sick)
    sicknessName: "sick",
    // 비료 애니메이션 사용 여부
    hasFertilizer2: true,
    // Lv2의 pesticide 오타 처리 (persticide)
    pesticideTypo: {
      2: "persticide"
    }
  },
  "부추": {
    // 병해충 이미지 이름 (모든 레벨에서 sick)
    sicknessName: "sick",
    // 비료 애니메이션 사용 여부
    hasFertilizer2: true
  }
};

// 작물별 재배 기간 캐시
let cropGrowingPeriod = null;

// 작물별 비료 주기 정보 (직접 정의)
const FERTILIZING_INFO = {
  "당근": "파종 후 20일 후 정도 [1회 웃거름은 20일 후, 2회 웃거름은 50일 후, 3회 웃거름은 70일 정도]",
  "부추": "2달 하고 2주 [봄에 움트기 전 4월 상순과 6월 상순, 가을엔 9월 중순]",
  "감자": "20~25일 정도",
  "오이": "10~14일 정도",
  "토마토": "2주 정도"
};

// 작물별 물주기 정보 (직접 정의)
const WATERING_INFO = {
  "토마토": {
    "0~10일": "매일/겉흙 마르면",
    "10~35일": "주 2~3회",
    "35+": "주 2회"
  },
  "감자": {
    "0~10일": "겉흙 마르면",
    "10~35일": "주 1~2회",
    "35+": "주 2회"
  },
  "오이": {
    "0~10일": "매일/겉흙 마르면",
    "10~35일": "주 2~3회",
    "35+": "주 2~3회"
  },
  "당근": {
    "0~10일": "2~3일마다",
    "10~35일": "주 1~2회",
    "35+": "주 1회"
  },
  "부추": {
    "0~10일": "겉흙 마르면",
    "10~35일": "주 2~3회",
    "35+": "주 1~2회"
  }
};

// 작물 재배 기간 가져오기
async function loadCropGrowingPeriod() {
  if (cropGrowingPeriod !== null) {
    return cropGrowingPeriod;
  }
  
  try {
    const response = await fetch(`${API_BASE}/crops/${encodeURIComponent(gameState.cropName)}`);
    if (response.ok) {
      const data = await response.json();
      // harvest_period가 있으면 사용, 없으면 growing_period 사용 (하위 호환성)
      if (data.harvest_period && Array.isArray(data.harvest_period)) {
        cropGrowingPeriod = data.harvest_period;  // [최소 수확일, 최적 수확일]
      } else if (data.growing_period) {
        // 하위 호환성: 기존 형식이면 최적 수확일로 사용
        cropGrowingPeriod = [Math.floor(data.growing_period * 0.7), data.growing_period];
      }
      return cropGrowingPeriod;
    }
  } catch (error) {
    console.error("재배 기간 가져오기 실패:", error);
  }
  
  // 기본값: [105일, 150일] (5개월 기준)
  return 150;
}

// 날짜에 따른 레벨 계산 (재배 기간을 4구간으로 나눔)
async function calculateLevel(day) {
  const growingPeriod = await loadCropGrowingPeriod();
  
  if (!growingPeriod) {
    // 재배 기간 정보가 없으면 기본값 사용 (7일마다 레벨 증가)
    if (day < 7) return 1;
    if (day < 14) return 2;
    if (day < 21) return 3;
    return 4;
  }
  
  // 새 형식: [최소 수확일, 최적 수확일] 배열인 경우 최적 수확일 사용
  // 기존 형식: 숫자 하나인 경우 그대로 사용
  const period = Array.isArray(growingPeriod) ? growingPeriod[1] : growingPeriod;
  
  // 재배 기간을 4구간으로 나눔
  const quarter = period / 4;
  
  if (day < quarter) return 1;           // 0~25%
  if (day < quarter * 2) return 2;      // 25~50%
  if (day < quarter * 3) return 3;      // 50~75%
  return 4;                              // 75~100%
}

// 동기 버전 (이미 재배 기간을 로드한 경우)
function calculateLevelSync(day) {
  if (cropGrowingPeriod === null) {
    // 아직 로드되지 않았으면 기본값 사용
    if (day < 7) return 1;
    if (day < 14) return 2;
    if (day < 21) return 3;
    return 4;
  }
  
  // 새 형식: [최소 수확일, 최적 수확일] 배열인 경우 최적 수확일 사용
  // 기존 형식: 숫자 하나인 경우 그대로 사용
  const period = Array.isArray(cropGrowingPeriod) ? cropGrowingPeriod[1] : cropGrowingPeriod;
  
  const quarter = period / 4;
  
  if (day < quarter) return 1;
  if (day < quarter * 2) return 2;
  if (day < quarter * 3) return 3;
  return 4;
}

// 물주기 애니메이션 관련 변수
let wateringAnimationInterval = null;
let wateringImageIndex = 0; // 0 또는 1 (water 또는 water2)

// 비료주기 애니메이션 관련 변수
let fertilizerAnimationInterval = null;
let fertilizerImageIndex = 0; // 0 또는 1 (fertilizer 또는 fertilizer2)

// 배경 이미지 애니메이션 관련 변수
let backgroundAnimationInterval = null;
let backgroundImageIndex = 0;

// 날씨별 배경 이미지 매핑
const BACKGROUND_IMAGES = {
  // 맑음 배경 (바람 포함)
  sunny: [
    "images/background/main_background.png"
  ],
  // 흐림 배경
  cloudy: [
    "images/background/backgroud_cloud1.png",
    "images/background/backgroud_cloud2.png"
  ],
  // 눈 올 때 배경
  snow: [
    "images/background/background_snow1.png",
    "images/background/background_snow2.png"
  ],
  // 비 올 때 배경 (비, 천둥)
  rain: [
    "images/background/background_rain1.png",
    "images/background/background_rain2.png"
  ],
  // 안개 배경
  foggy: [
    "images/background/background_foggy.png"
  ]
};

// 날씨에 따른 배경 타입 결정
function getBackgroundTypeByWeather(weather) {
  switch (weather) {
    case "눈":
      return "snow";
    case "비":
    case "천둥":
      return "rain";
    case "흐림":
      return "cloudy";
    case "안개":
      return "foggy";
    case "맑음":
    case "바람":
    default:
      return "sunny";
  }
}

// 배경 이미지 업데이트
function updateBackgroundImage() {
  const gameContainer = document.querySelector(".game-container");
  if (!gameContainer) return;
  
  const weather = gameState.currentWeather || "맑음";
  const bgType = getBackgroundTypeByWeather(weather);
  const bgImages = BACKGROUND_IMAGES[bgType];
  
  if (!bgImages || bgImages.length === 0) return;
  
  // 현재 인덱스의 배경 이미지 적용
  const currentBgImage = bgImages[backgroundImageIndex % bgImages.length];
  gameContainer.style.backgroundImage = `url('${currentBgImage}')`;
  gameContainer.style.backgroundSize = "cover";
  gameContainer.style.backgroundPosition = "center";
  gameContainer.style.backgroundRepeat = "no-repeat";
}

// 배경 애니메이션 시작
function startBackgroundAnimation() {
  // 기존 애니메이션 정리
  stopBackgroundAnimation();
  
  backgroundImageIndex = 0;
  
  // 첫 번째 이미지 즉시 표시
  updateBackgroundImage();
  
  // 1초마다 이미지 번갈아가며 표시
  backgroundAnimationInterval = setInterval(() => {
    backgroundImageIndex++;
    updateBackgroundImage();
  }, 1000); // 1초 간격
}

// 배경 애니메이션 중지
function stopBackgroundAnimation() {
  if (backgroundAnimationInterval) {
    clearInterval(backgroundAnimationInterval);
    backgroundAnimationInterval = null;
  }
}

// 날씨 변경 시 배경 업데이트 (애니메이션 재시작)
function updateBackgroundForWeather() {
  // 배경 인덱스 초기화 및 애니메이션 재시작
  backgroundImageIndex = 0;
  
  // 애니메이션이 실행 중이 아니면 시작
  if (!backgroundAnimationInterval) {
    startBackgroundAnimation();
  } else {
    // 이미 실행 중이면 이미지만 즉시 업데이트
    updateBackgroundImage();
  }
}

// 작물 이미지 경로 생성
function getCropImagePath(state = null, useAlternate = false) {
  const cropFolder = CROP_FOLDER_NAMES[gameState.cropName];
  if (!cropFolder) {
    // 이미지가 없는 작물은 이모지 사용
    return null;
  }
  
  const level = calculateLevelSync(gameState.day || 0);
  const cropConfig = CROP_IMAGE_CONFIG[gameState.cropName] || {};
  
  // 상태 우선순위: 명시적 상태(행동 중) > 병해충 > HP 기반 sad > 일반 상태
  let imageState;
  
  // 명시적으로 전달된 상태가 있으면 우선 사용 (watering, fertilizer, pesticide)
  if (state && (state === "watering" || state === "fertilizer" || state === "pesticide")) {
    // 물주기 상태 처리
    if (state === "watering") {
      // HP가 70 미만이면 sad&water 또는 sad&water2 사용
      if (gameState.hp < 70) {
        if (useAlternate) {
          imageState = "sad&water2";
        } else {
          // 오이처럼 sad&water가 없는 레벨은 sad&water2 사용
          if (cropConfig.useWater2Only && level === 4) {
            imageState = "sad&water2";
          } else {
            imageState = "sad&water";
          }
        }
      } else {
        // 정상 상태에서 물주기
        if (useAlternate) {
          imageState = "water2";
        } else {
          // 오이처럼 water가 없고 water2만 있는 작물
          if (cropConfig.useWater2Only) {
            imageState = "water2";
          }
          // 작물별 설정에 따라 water 또는 watering 사용
          else if (cropConfig.useWateringForLv2Lv3 && (level === 2 || level === 3)) {
            imageState = "watering";
          } else {
            imageState = "water";
          }
        }
      }
    }
    // 비료주기 상태 처리
    else if (state === "fertilizer") {
      // 오이처럼 fertilizer가 없고 fertilizer2만 있는 작물
      if (cropConfig.useFertilizer2Only) {
        // HP가 70 미만이면 sad&fertilizer 또는 sad&fertilizer2 사용
        if (gameState.hp < 70) {
          imageState = useAlternate ? "sad&fertilizer2" : "sad&fertilizer";
        } else {
          imageState = "fertilizer2";
        }
      } else if (useAlternate && cropConfig.hasFertilizer2) {
        // 작물별 fertilizer2 파일명 사용 (오타 처리)
        imageState = cropConfig.fertilizer2Name || "fertilizer2";
      } else {
        imageState = "fertilizer";
      }
    }
    // 농약 상태 처리
    else if (state === "pesticide") {
      // HP가 70 미만이면 sad&pesticide 또는 sad&pesticide2 사용 (오이)
      if (cropConfig.useFertilizer2Only && gameState.hp < 70) {
        imageState = useAlternate ? "sad&pesticide2" : "sad&pesticide";
      } else {
        // 레벨별 pesticide 오타 처리 (당근 Lv2: persticide)
        let pesticideName = "pesticide";
        if (cropConfig.pesticideTypo && cropConfig.pesticideTypo[level]) {
          pesticideName = cropConfig.pesticideTypo[level];
        }
        imageState = useAlternate ? pesticideName + "2" : pesticideName;
      }
    }
  }
  // 병해충이 있으면 sickness/sick 우선 (행동 중이 아닐 때)
  else if (gameState.hasPest) {
    // 작물별 병해충 이미지 이름 결정
    if (cropConfig.sicknessName) {
      if (typeof cropConfig.sicknessName === "string") {
        imageState = cropConfig.sicknessName;
      } else {
        // 레벨별로 다른 이름 사용
        imageState = cropConfig.sicknessName[level] || "sickness";
      }
    } else {
      imageState = "sickness";
    }
  }
  // HP가 70 미만이면 sad 표시
  else if (gameState.hp < 70) {
    // 오이처럼 sad 단독 이미지가 없는 경우 대체 이미지 사용
    if (cropConfig.sadFallback) {
      imageState = cropConfig.sadFallback;
    } else {
      imageState = "sad";
    }
  }
  // 그 외에는 normal 또는 전달된 상태
  else {
    imageState = state || gameState.currentImageState || "normal";
    
    // normal 이미지가 없는 작물의 경우 대체 이미지 사용
    if (imageState === "normal" && cropConfig.normalFallback) {
      const fallback = cropConfig.normalFallback[level];
      if (fallback !== null && fallback !== undefined) {
        imageState = fallback;
      } else if (cropConfig.specialNormalFormat && fallback === null) {
        // Lv4 오이처럼 특수 형식의 normal 이미지 (CucumberLv4.png)
        const cropNameEng = cropFolder.charAt(0).toUpperCase() + cropFolder.slice(1);
        return `images/${cropFolder}/${cropNameEng}Lv${level}.png`;
      }
    }
    
    // 소문자 normal 이미지 파일명 처리 (cucumberLv1_normal.png)
    if (imageState === "normal" && cropConfig.lowercaseNormal) {
      return `images/${cropFolder}/${cropFolder}Lv${level}_${imageState}.png`;
    }
  }
  
  // 작물 이름을 영어로 변환 (첫 글자 대문자)
  const cropNameEng = cropFolder.charAt(0).toUpperCase() + cropFolder.slice(1);
  
  return `images/${cropFolder}/${cropNameEng}Lv${level}_${imageState}.png`;
}

// 물주기 애니메이션 시작
function startWateringAnimation() {
  // 기존 애니메이션 정리
  stopWateringAnimation();
  
  wateringImageIndex = 0;
  
  // 첫 번째 이미지 즉시 표시
  updateCropImage("watering", false);
  
  // 0.5초마다 이미지 번갈아가며 표시
  wateringAnimationInterval = setInterval(() => {
    wateringImageIndex = wateringImageIndex === 0 ? 1 : 0;
    const useWater2 = wateringImageIndex === 1;
    updateCropImage("watering", useWater2);
  }, 500); // 0.5초 간격
}

// 물주기 애니메이션 중지
function stopWateringAnimation() {
  if (wateringAnimationInterval) {
    clearInterval(wateringAnimationInterval);
    wateringAnimationInterval = null;
  }
}

// 비료주기 애니메이션 시작
function startFertilizerAnimation() {
  // 기존 애니메이션 정리
  stopFertilizerAnimation();
  
  fertilizerImageIndex = 0;
  
  // 첫 번째 이미지 즉시 표시
  updateCropImage("fertilizer", false);
  
  // 0.5초마다 이미지 번갈아가며 표시
  fertilizerAnimationInterval = setInterval(() => {
    fertilizerImageIndex = fertilizerImageIndex === 0 ? 1 : 0;
    const useAlternate = fertilizerImageIndex === 1;
    updateCropImage("fertilizer", useAlternate);
  }, 500); // 0.5초 간격
}

// 비료주기 애니메이션 중지
function stopFertilizerAnimation() {
  if (fertilizerAnimationInterval) {
    clearInterval(fertilizerAnimationInterval);
    fertilizerAnimationInterval = null;
  }
}

// 작물 이미지 업데이트
function updateCropImage(state = null, useAlternate = false) {
  const displayElement = document.getElementById("cropDisplay");
  if (!displayElement) {
    console.warn("cropDisplay 요소를 찾을 수 없습니다.");
    return;
  }
  
  // 물주기 상태가 아니고 애니메이션이 실행 중이 아니면 애니메이션 중지
  if (state !== "watering" && !wateringAnimationInterval) {
    stopWateringAnimation();
  }
  
  // 비료주기 상태가 아니고 애니메이션이 실행 중이 아니면 애니메이션 중지
  if (state !== "fertilizer" && !fertilizerAnimationInterval) {
    stopFertilizerAnimation();
  }
  
  // state가 null이고 currentImageState도 null이면 실제 상태에 맞게 결정
  // (병해충 > HP 기반 sad > normal)
  if (state === null && gameState.currentImageState === null) {
    state = null; // getCropImagePath에서 자동으로 결정하도록
  }
  
  const imagePath = getCropImagePath(state, useAlternate);
  
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
  1: [  // 1월 (겨울) - 습도 관련 날씨: 약 0.33
    { type: "맑음", probability: 0.67 },
    { type: "눈", probability: 0.2 },
    { type: "흐림", probability: 0.08 },
    { type: "비", probability: 0.05 }
  ],
  2: [  // 2월 (겨울) - 습도 관련 날씨: 약 0.33
    { type: "맑음", probability: 0.67 },
    { type: "눈", probability: 0.15 },
    { type: "흐림", probability: 0.12 },
    { type: "비", probability: 0.06 }
  ],
  3: [  // 3월 (봄) - 습도 관련 날씨: 약 0.33
    { type: "맑음", probability: 0.67 },
    { type: "비", probability: 0.2 },
    { type: "흐림", probability: 0.1 },
    { type: "바람", probability: 0.03 }
  ],
  4: [  // 4월 (봄) - 습도 관련 날씨: 약 0.33
    { type: "맑음", probability: 0.67 },
    { type: "비", probability: 0.18 },
    { type: "흐림", probability: 0.12 },
    { type: "바람", probability: 0.03 }
  ],
  5: [  // 5월 (봄) - 습도 관련 날씨: 약 0.33
    { type: "맑음", probability: 0.67 },
    { type: "비", probability: 0.15 },
    { type: "흐림", probability: 0.15 },
    { type: "바람", probability: 0.03 }
  ],
  6: [  // 6월 (여름 초) - 습도 관련 날씨: 약 0.33
    { type: "맑음", probability: 0.67 },
    { type: "비", probability: 0.15 },
    { type: "흐림", probability: 0.12 },
    { type: "천둥", probability: 0.06 }
  ],
  7: [  // 7월 (여름) - 습도 관련 날씨: 약 0.33
    { type: "맑음", probability: 0.67 },
    { type: "비", probability: 0.12 },
    { type: "천둥", probability: 0.12 },
    { type: "흐림", probability: 0.09 }
  ],
  8: [  // 8월 (여름) - 습도 관련 날씨: 약 0.33
    { type: "맑음", probability: 0.67 },
    { type: "천둥", probability: 0.15 },
    { type: "비", probability: 0.12 },
    { type: "흐림", probability: 0.06 }
  ],
  9: [  // 9월 (가을) - 습도 관련 날씨: 약 0.33
    { type: "맑음", probability: 0.67 },
    { type: "흐림", probability: 0.18 },
    { type: "비", probability: 0.12 },
    { type: "바람", probability: 0.03 }
  ],
  10: [  // 10월 (가을) - 습도 관련 날씨: 약 0.33
    { type: "맑음", probability: 0.67 },
    { type: "흐림", probability: 0.18 },
    { type: "비", probability: 0.12 },
    { type: "바람", probability: 0.03 }
  ],
  11: [  // 11월 (가을) - 습도 관련 날씨: 약 0.33
    { type: "맑음", probability: 0.67 },
    { type: "흐림", probability: 0.18 },
    { type: "비", probability: 0.12 },
    { type: "안개", probability: 0.03 }
  ],
  12: [  // 12월 (겨울) - 습도 관련 날씨: 약 0.33
    { type: "맑음", probability: 0.67 },
    { type: "눈", probability: 0.18 },
    { type: "흐림", probability: 0.1 },
    { type: "비", probability: 0.05 }
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

// 작물일기 관련 요소
const diaryButton = document.getElementById("diaryButton");
const diaryModal = document.getElementById("diaryModal");
const diaryClose = document.getElementById("diaryClose");
const diaryEntries = document.getElementById("diaryEntries");
const characterManageMenuItem = document.getElementById("characterManageMenuItem");
const logoutMenuItem = document.getElementById("logoutMenuItem");

// 도감 관련 요소
const collectionButton = document.getElementById("collectionButton");
const collectionModal = document.getElementById("collectionModal");
const collectionClose = document.getElementById("collectionClose");
const collectionGrid = document.getElementById("collectionGrid");
const totalHarvests = document.getElementById("totalHarvests");
const uniqueCrops = document.getElementById("uniqueCrops");

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

  // 작물 재배 기간 로드
  await loadCropGrowingPeriod();
  
  // 게임 상태 불러오기
  await loadGameState();
  
  // UI 업데이트
  updateUI();
  
  // 배경 애니메이션 시작
  startBackgroundAnimation();
  
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

  // 작물일기 버튼 이벤트 리스너
  if (diaryButton) {
    diaryButton.addEventListener("click", async (e) => {
      e.preventDefault();
      await showDiary();
    });
  }

  // 작물일기 닫기 버튼 이벤트 리스너
  if (diaryClose) {
    diaryClose.addEventListener("click", (e) => {
      e.preventDefault();
      hideDiary();
    });
  }

  // 작물일기 모달 외부 클릭 시 닫기
  if (diaryModal) {
    diaryModal.addEventListener("click", (e) => {
      if (e.target === diaryModal) {
        hideDiary();
      }
    });
  }
  
  // 도감 버튼 이벤트 리스너
  if (collectionButton) {
    collectionButton.addEventListener("click", async (e) => {
      e.preventDefault();
      await showCollection();
    });
  }

  // 도감 닫기 버튼 이벤트 리스너
  if (collectionClose) {
    collectionClose.addEventListener("click", (e) => {
      e.preventDefault();
      hideCollection();
    });
  }

  // 도감 모달 외부 클릭 시 닫기
  if (collectionModal) {
    collectionModal.addEventListener("click", (e) => {
      if (e.target === collectionModal) {
        hideCollection();
      }
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
  stopWateringAnimation();
  stopFertilizerAnimation();
  stopBackgroundAnimation();
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
    const previousWeather = gameState.currentWeather;
    gameState.currentWeather = selectWeatherByMonth(currentMonth);
    gameState.weatherDate = currentDay;
    
    // 날씨가 변경되었으면 배경도 업데이트
    if (previousWeather !== gameState.currentWeather) {
      updateBackgroundForWeather();
    }
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

// 특정 날짜의 날씨 계산 (날짜 기반)
function getWeatherForDay(day) {
  const currentMonth = getCurrentMonth();
  // 날짜를 기반으로 날씨 계산 (같은 날짜면 같은 날씨)
  // 간단한 해시 함수를 사용하여 날짜별로 일관된 날씨 생성
  const seed = day * 1000 + currentMonth;
  const random = ((seed * 9301 + 49297) % 233280) / 233280;
  
  const weatherOptions = WEATHER_BY_MONTH[currentMonth] || WEATHER_BY_MONTH[12];
  let cumulativeProbability = 0;
  for (const option of weatherOptions) {
    cumulativeProbability += option.probability;
    if (random <= cumulativeProbability) {
      return option.type;
    }
  }
  return weatherOptions[weatherOptions.length - 1].type;
}

// 전날 행동들을 평가하는 함수
async function evaluatePreviousDayActions(previousDay) {
  try {
    const previousHp = gameState.hp;
    
    // 전날의 행동들 필터링
    const previousDayActions = gameState.actions.filter(a => a.day === previousDay);
    
    // 전날의 날씨 정보 찾기
    // 행동이 있으면 첫 번째 행동의 날씨 사용, 없으면 해당 날짜의 날씨 계산
    let weatherOnThatDay = null;
    if (previousDayActions.length > 0) {
      weatherOnThatDay = previousDayActions[0]?.weather || null;
    }
    
    // 행동이 없거나 날씨 정보가 없으면 날짜 기반으로 날씨 계산
    if (!weatherOnThatDay) {
      weatherOnThatDay = getWeatherForDay(previousDay);
      console.log(`📅 전날(${previousDay}일) 날씨 계산됨: ${weatherOnThatDay} (행동에 날씨 정보 없음)`);
    } else {
      console.log(`📅 전날(${previousDay}일) 날씨 사용: ${weatherOnThatDay} (행동에서 가져옴)`);
    }
    
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
    
    // HP 변화에 따라 이미지 상태 업데이트
    gameState.currentImageState = null; // 실제 상태에 맞게 결정하도록
    updateCropImage();
    
    // 말풍선 대사 표시 (백엔드에서 제공한 말풍선 대사 사용)
    if (result.speechBubble) {
      // 백엔드에서 제공한 작물 캐릭터의 말풍선 대사 표시
      showCropSpeechBubble(result.speechBubble, 7000);
    } else if (result.feedbacks && result.feedbacks.length > 0) {
      // 말풍선 대사가 없으면 피드백 기반으로 말풍선 생성
      const mainFeedback = result.feedbacks[0];
      
      // 관리 소홀 부분 파악
      let managementIssue = "";
      if (mainFeedback.includes("과습") || mainFeedback.includes("물")) {
        managementIssue = "물을 너무 많이 주셨어요. 습한 날씨에는 물을 주지 않는 게 좋아요.";
      } else if (mainFeedback.includes("비료")) {
        managementIssue = "비료를 너무 많이 주셨어요. 적당한 양을 주는 게 중요해요.";
      } else if (mainFeedback.includes("방치")) {
        managementIssue = "관리를 제대로 해주지 않아서 힘들어요. 물과 비료를 꾸준히 주세요.";
      } else if (hpChange > 0) {
        managementIssue = "좋은 관리 감사해요! 이렇게 계속 챙겨주시면 더 건강해질 거예요! 💚";
      } else if (hpChange < 0) {
        // 피드백에서 핵심만 추출
        managementIssue = mainFeedback.replace(/\([^)]*\)/g, "").trim();
      } else {
        // HP 변화가 없을 때
        managementIssue = "괜찮아요! 조금만 더 신경 써주시면 더 좋을 것 같아요! ☀️";
      }
      
      if (managementIssue) {
      showCropSpeechBubble(managementIssue, 6000);
      }
    } else if (hpChange !== 0) {
      // 피드백도 없고 말풍선도 없을 때 기본 메시지
      if (hpChange > 0) {
      showCropSpeechBubble("좋은 관리 감사해요! 이렇게 계속 챙겨주시면 더 건강해질 거예요! 💚", 5000);
      } else if (hpChange < 0) {
        showCropSpeechBubble("조금 힘들어요... 날씨를 확인하고 적절한 시기에 관리해주시면 좋겠어요! 🌱", 5000);
      }
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
      gameState.currentImageState = null; // 실제 상태에 맞게 결정하도록
      updateCropImage();
      
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
        gameState.currentImageState = null; // 실제 상태에 맞게 결정하도록
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

// 날씨별 온도 범위 (월별 평균 온도 기반)
const TEMPERATURE_BY_MONTH = {
  1: { min: -5, max: 5 },   // 1월: -5~5°C
  2: { min: -2, max: 8 },   // 2월: -2~8°C
  3: { min: 3, max: 15 },   // 3월: 3~15°C
  4: { min: 10, max: 20 },  // 4월: 10~20°C
  5: { min: 15, max: 25 },  // 5월: 15~25°C
  6: { min: 20, max: 28 },  // 6월: 20~28°C
  7: { min: 23, max: 32 },  // 7월: 23~32°C
  8: { min: 23, max: 32 },  // 8월: 23~32°C
  9: { min: 18, max: 26 },  // 9월: 18~26°C
  10: { min: 12, max: 20 }, // 10월: 12~20°C
  11: { min: 5, max: 15 },  // 11월: 5~15°C
  12: { min: -2, max: 8 }   // 12월: -2~8°C
};

// 날씨별 온도 보정값 (기본 온도에서 조정)
const TEMPERATURE_ADJUSTMENT = {
  "맑음": 0,      // 기본 온도
  "비": -3,       // 비 오면 3도 낮음
  "눈": -8,       // 눈 오면 8도 낮음
  "흐림": -2,     // 흐리면 2도 낮음
  "안개": -1,     // 안개면 1도 낮음
  "천둥": -1,     // 천둥이면 1도 낮음
  "바람": -2      // 바람이면 2도 낮음
};

// 날씨별 습도 범위
const HUMIDITY_BY_WEATHER = {
  "맑음": { min: 40, max: 60 },
  "비": { min: 75, max: 95 },
  "눈": { min: 60, max: 80 },
  "흐림": { min: 65, max: 85 },
  "안개": { min: 85, max: 95 },
  "천둥": { min: 70, max: 90 },
  "바람": { min: 30, max: 50 }
};

// 현재 온도 계산
function calculateCurrentTemperature() {
  const month = getCurrentMonth();
  const weather = gameState.currentWeather || "맑음";
  const monthTemp = TEMPERATURE_BY_MONTH[month] || TEMPERATURE_BY_MONTH[12];
  const adjustment = TEMPERATURE_ADJUSTMENT[weather] || 0;
  
  // 기본 온도 범위에서 랜덤 선택 후 보정
  const baseTemp = monthTemp.min + Math.random() * (monthTemp.max - monthTemp.min);
  const currentTemp = Math.round(baseTemp + adjustment);
  
  return currentTemp;
}

// 현재 습도 계산
function calculateCurrentHumidity() {
  const weather = gameState.currentWeather || "맑음";
  const humidityRange = HUMIDITY_BY_WEATHER[weather] || HUMIDITY_BY_WEATHER["맑음"];
  
  const humidity = Math.round(
    humidityRange.min + Math.random() * (humidityRange.max - humidityRange.min)
  );
  
  return humidity;
}

// 일조량 계산 (날씨 기반)
function calculateSunlight() {
  const weather = gameState.currentWeather || "맑음";
  const sunlightMap = {
    "맑음": "강함",
    "비": "약함",
    "눈": "약함",
    "흐림": "보통",
    "안개": "약함",
    "천둥": "보통",
    "바람": "보통"
  };
  
  return sunlightMap[weather] || "보통";
}

// 토양 온도 계산 (대기 온도보다 약간 낮음)
function calculateSoilTemperature() {
  const airTemp = calculateCurrentTemperature();
  // 토양 온도는 대기 온도보다 2~5도 낮음
  const soilTemp = Math.round(airTemp - (2 + Math.random() * 3));
  return soilTemp;
}

// 환경 정보 UI 업데이트 (실시간 날씨 기반)
function updateEnvironmentUI() {
  if (!gameState.currentWeather) {
    return;
  }
  
  const currentTemp = calculateCurrentTemperature();
  const currentHumidity = calculateCurrentHumidity();
  const currentSunlight = calculateSunlight();
  const currentSoilTemp = calculateSoilTemperature();
  
  const tempEl = document.getElementById("envTemperature");
  const humidityEl = document.getElementById("envHumidity");
  const sunlightEl = document.getElementById("envSunlight");
  const soilTempEl = document.getElementById("envSoilTemp");
  
  if (tempEl) {
    tempEl.textContent = `${currentTemp}°C`;
  }
  if (humidityEl) {
    humidityEl.textContent = `${currentHumidity}%`;
  }
  if (sunlightEl) {
    sunlightEl.textContent = currentSunlight;
  }
  if (soilTempEl) {
    soilTempEl.textContent = `${currentSoilTemp}°C`;
  }
}

// UI 업데이트
function updateUI() {
  // 작물 이름
  cropNameEl.textContent = gameState.cropName;
  
  // 작물 이미지 업데이트 (상태에 따라)
  // 물주기 애니메이션이 실행 중이면 이미지 업데이트 건너뛰기
  if (!wateringAnimationInterval) {
    updateCropImage();
  }
  
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
  
  // 환경 정보 UI 업데이트 (현재 날씨 기반 실시간 온도/습도)
  updateEnvironmentUI();
  
  // 수확 버튼은 항상 표시
  if (harvestButton) {
    harvestButton.style.display = "block";
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
      // 물주기인 경우 애니메이션 시작
      if (actionType === "water") {
        // 물주기 애니메이션 시작
        startWateringAnimation();
        
        // 2초 후 애니메이션 중지하고 원래 상태로 복귀
        setTimeout(() => {
          stopWateringAnimation();
          // currentImageState를 null로 설정하여 실제 상태에 맞게 이미지 결정
          gameState.currentImageState = null;
          updateCropImage();
        }, 2000);
      } 
      // 비료주기인 경우 애니메이션 시작
      else if (actionType === "fertilizer") {
        // 비료주기 애니메이션 시작
        startFertilizerAnimation();
        
        // 2초 후 애니메이션 중지하고 원래 상태로 복귀
        setTimeout(() => {
          stopFertilizerAnimation();
          // currentImageState를 null로 설정하여 실제 상태에 맞게 이미지 결정
          gameState.currentImageState = null;
          updateCropImage();
        }, 2000);
      }
      // 농약은 일반 이미지 표시
      else {
        updateCropImage(actionImageState);
        
        // 2초 후 원래 상태로 복귀
        setTimeout(() => {
          // currentImageState를 null로 설정하여 실제 상태에 맞게 이미지 결정
          gameState.currentImageState = null;
          updateCropImage();
        }, 2000);
      }
    }

    // 즉시 평가하지 않고 행동만 기록 (다음날에 피드백)
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
  
  // 수확 시기 확인 (최소 수확일 미만이어도 수확 가능하지만 F등급)
  const harvestPeriod = await loadCropGrowingPeriod();
  if (harvestPeriod && Array.isArray(harvestPeriod) && harvestPeriod.length === 2) {
    const [minHarvestDay, optimalHarvestDay] = harvestPeriod;
    if (currentDay < minHarvestDay) {
      const remainingDays = minHarvestDay - currentDay;
      if (!confirm(`${gameState.cropName}을(를) 아직 수확 시기가 아닙니다.\n\n현재 ${currentDay}일째이며, 최소 수확일은 ${minHarvestDay}일입니다.\n${remainingDays}일 더 키우면 더 좋은 등급을 받을 수 있습니다.\n\n그래도 지금 수확하시겠습니까? (F등급으로 등록됩니다)`)) {
        return;
      }
    }
  } else if (harvestPeriod && typeof harvestPeriod === 'number') {
    // 하위 호환성: 숫자면 기존 로직 사용
    const harvestThreshold = harvestPeriod * 0.9;
    if (currentDay < harvestThreshold) {
      const remainingDays = Math.ceil(harvestThreshold - currentDay);
      if (!confirm(`아직 수확 시기가 아닙니다. 약 ${remainingDays}일 후에 수확할 수 있습니다.\n\n그래도 지금 수확하시겠습니까?`)) {
        return;
      }
    }
  }

  // 수확 확인 (등급으로만 판단)
  if (!confirm(`${gameState.cropName}을(를) 수확하시겠습니까?\n\n수확하면 작물이 도감에 등록되고, 현재 키우던 작물은 사라집니다.`)) {
    return;
  }

  try {
    // 수확하고 도감에 추가
    const response = await fetch(`${API_BASE}/game/harvest-and-collect`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        userId: gameState.userId,
        cropName: gameState.cropName,
        finalHp: gameState.hp,
        totalDays: currentDay
      })
    });

    if (!response.ok) {
      throw new Error("수확 요청 실패");
    }

    const result = await response.json();
    
    if (!result.success) {
      showFeedback(result.message || "수확 처리 중 오류가 발생했습니다.", "error");
      return;
    }
    
    // 등급별 이모지
    const gradeEmoji = {
      "S": "🏆",
      "A": "🥇",
      "B": "🥈",
      "C": "🥉",
      "D": "📝",
      "F": "⚠️"
    };
    
    // 성공 메시지 표시
    const emoji = gradeEmoji[result.grade] || "🌾";
    alert(`🎉 수확 완료!\n\n${result.message}\n\n${emoji} 등급: ${result.grade}\n📊 건강도: ${gameState.hp}/100\n📅 재배 일수: ${currentDay}일\n📚 도감 등록 횟수: ${result.collectionCount}회`);
    
    // 게임 완료 처리
    sessionStorage.setItem("lastGameResult", JSON.stringify({
      cropName: gameState.cropName,
      finalHp: gameState.hp,
      totalDays: currentDay,
      grade: result.grade,
      success: true
    }));
    
    // 현재 작물 정보 삭제
    sessionStorage.removeItem("cropName");

    // 캐릭터 선택 화면으로 이동 (새 작물 선택 또는 도감 확인)
    window.location.href = "character-select.html";

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
      return {
        guide: data.guide || "",
        wateringInfo: data.watering_info || {},
        fertilizingPeriod: data.fertilizing_period || null
      };
    }
  } catch (error) {
    console.error("작물 가이드 가져오기 실패:", error);
  }
  return null;
}

// 수확 가이드 가져오기
async function getHarvestGuide() {
  try {
    const cropData = await getCropGuide();
    const growingPeriod = await loadCropGrowingPeriod();
    const currentDay = calculateCurrentDay();
    
    let harvestMessage = `🌾 ${gameState.cropName} 수확 가이드\n\n`;
    harvestMessage += `═══════════════════════════════\n`;
    harvestMessage += `📅 수확 시기\n`;
    harvestMessage += `═══════════════════════════════\n\n`;
    
    const harvestPeriod = await loadCropGrowingPeriod();
    if (harvestPeriod && Array.isArray(harvestPeriod) && harvestPeriod.length === 2) {
      const [minHarvestDay, optimalHarvestDay] = harvestPeriod;
      harvestMessage += `• 수확 가능 시기: ${minHarvestDay}일부터\n`;
      harvestMessage += `• 최적 수확 시기: ${optimalHarvestDay}일\n`;
      harvestMessage += `• 현재 재배 일수: ${currentDay}일\n\n`;
      
      if (currentDay < minHarvestDay) {
        harvestMessage += `⚠️ 아직 수확할 수 없습니다. ${minHarvestDay - currentDay}일 더 키워주세요.\n\n`;
      } else if (currentDay >= optimalHarvestDay) {
        harvestMessage += `✅ 최적 수확 시기입니다!\n\n`;
      } else {
        harvestMessage += `💡 최적 수확 시기까지 ${optimalHarvestDay - currentDay}일 남았습니다.\n\n`;
      }
    } else if (harvestPeriod && typeof harvestPeriod === 'number') {
      // 하위 호환성
      const harvestThreshold = Math.ceil(harvestPeriod * 0.9);
      harvestMessage += `• 재배 기간: 약 ${harvestPeriod}일\n`;
      harvestMessage += `• 수확 가능 시기: ${harvestThreshold}일 이후\n`;
      harvestMessage += `• 현재 재배 일수: ${currentDay}일\n\n`;
    } else {
      harvestMessage += `• 수확 시기 정보를 불러올 수 없습니다.\n\n`;
    }
    
    harvestMessage += `═══════════════════════════════\n`;
    harvestMessage += `💧 물주기 가이드\n`;
    harvestMessage += `═══════════════════════════════\n\n`;
    
    if (cropData && cropData.wateringInfo) {
      const wateringInfo = cropData.wateringInfo;
      if (wateringInfo["0~10일"]) {
        harvestMessage += `• 0~10일: ${wateringInfo["0~10일"]}\n`;
      }
      if (wateringInfo["10~35일"]) {
        harvestMessage += `• 10~35일: ${wateringInfo["10~35일"]}\n`;
      }
      if (wateringInfo["35+"]) {
        harvestMessage += `• 35일 이후: ${wateringInfo["35+"]}\n`;
      }
      if (Object.keys(wateringInfo).length === 0) {
        harvestMessage += `• 물주기 정보가 없습니다.\n`;
      }
    } else {
      harvestMessage += `• 물주기 정보를 불러올 수 없습니다.\n`;
    }
    
    harvestMessage += `\n`;
    harvestMessage += `═══════════════════════════════\n`;
    harvestMessage += `🌿 비료 주기 가이드\n`;
    harvestMessage += `═══════════════════════════════\n\n`;
    
    if (cropData && cropData.fertilizingPeriod) {
      harvestMessage += `• 비료 주기: ${cropData.fertilizingPeriod}\n`;
    } else {
      harvestMessage += `• 비료 주기 정보가 없습니다.\n`;
    }
    
    harvestMessage += `\n`;
    harvestMessage += `═══════════════════════════════\n`;
    harvestMessage += `✅ 수확 조건\n`;
    harvestMessage += `═══════════════════════════════\n\n`;
    harvestMessage += `• 최소 수확일 이상 경과\n`;
    harvestMessage += `• 수확 시기와 HP 상태에 따라 등급(S, A, B, C, D, F)이 결정됩니다\n`;
    harvestMessage += `• 최적 수확 시기에 가까울수록, HP가 높을수록 높은 등급을 받습니다\n`;
    harvestMessage += `• 위 조건을 만족하면 수확 버튼을 눌러 수확하세요!\n\n`;
    
    if (cropData && cropData.guide) {
      harvestMessage += `═══════════════════════════════\n`;
      harvestMessage += `📖 ${gameState.cropName} 재배 정보\n`;
      harvestMessage += `═══════════════════════════════\n\n`;
      // 가이드에서 수확 관련 정보 추출
      const guideLines = cropData.guide.split('\n').filter(line => line.trim());
      const relevantLines = guideLines.filter(line => 
        line.includes('수확') || 
        line.includes('재배') || 
        line.includes('시기') ||
        line.includes('기간')
      );
      
      if (relevantLines.length > 0) {
        harvestMessage += relevantLines.slice(0, 10).join('\n');
      } else {
        harvestMessage += guideLines.slice(0, 10).join('\n');
      }
      
      if (guideLines.length > 10) {
        harvestMessage += '\n\n... (더 자세한 정보는 게임을 진행하며 확인하세요)';
      }
    }
    
    return harvestMessage;
  } catch (error) {
    console.error("수확 가이드 가져오기 실패:", error);
    return null;
  }
}

// 도움말 버튼 - 직접 정의된 데이터 사용
document.getElementById("helpButton").addEventListener("click", async (e) => {
  e.preventDefault();
  
  const cropName = gameState.cropName;
  const currentDay = calculateCurrentDay();
  
  let helpMessage = `🌱 ${cropName} 작물 관리 가이드\n\n`;
  
  // 수확 시기 정보
  helpMessage += `═══════════════════════════════\n`;
  helpMessage += `📅 수확 시기\n`;
  helpMessage += `═══════════════════════════════\n\n`;
  
  const harvestPeriod = await loadCropGrowingPeriod();
  if (harvestPeriod && Array.isArray(harvestPeriod) && harvestPeriod.length === 2) {
    const [minHarvestDay, optimalHarvestDay] = harvestPeriod;
    helpMessage += `• 수확 가능: ${minHarvestDay}일부터\n`;
    helpMessage += `• 최적 수확: ${optimalHarvestDay}일\n`;
    helpMessage += `• 현재: ${currentDay}일차\n\n`;
  } else {
    helpMessage += `• 수확 시기 정보가 없습니다.\n\n`;
  }
  
  // 물주기 정보 (직접 정의된 데이터)
  helpMessage += `═══════════════════════════════\n`;
  helpMessage += `💧 물주기 가이드\n`;
  helpMessage += `═══════════════════════════════\n\n`;
  
  const wateringInfo = WATERING_INFO[cropName];
  if (wateringInfo) {
    if (wateringInfo["0~10일"]) {
      helpMessage += `• 0~10일: ${wateringInfo["0~10일"]}\n`;
    }
    if (wateringInfo["10~35일"]) {
      helpMessage += `• 10~35일: ${wateringInfo["10~35일"]}\n`;
    }
    if (wateringInfo["35+"]) {
      helpMessage += `• 35일 이후: ${wateringInfo["35+"]}\n`;
    }
  } else {
    helpMessage += `• 물주기 정보가 없습니다.\n`;
  }
  
  // 비료 주기 정보 (직접 정의된 데이터)
  helpMessage += `\n`;
  helpMessage += `═══════════════════════════════\n`;
  helpMessage += `🌿 비료 주기 가이드\n`;
  helpMessage += `═══════════════════════════════\n\n`;
  
  const fertilizingInfo = FERTILIZING_INFO[cropName];
  if (fertilizingInfo) {
    helpMessage += `• 비료 주기: ${fertilizingInfo}\n`;
  } else {
    helpMessage += `• 비료 주기 정보가 없습니다.\n`;
  }
  
  // 기본 관리 팁
  helpMessage += `\n`;
  helpMessage += `═══════════════════════════════\n`;
  helpMessage += `📌 관리 팁\n`;
  helpMessage += `═══════════════════════════════\n\n`;
  helpMessage += `💧 습한 날씨(비/눈)에는 물주기 금지\n`;
  helpMessage += `🌿 비료는 적당한 간격으로\n`;
  helpMessage += `💊 병해충 발생 시 농약 사용\n`;
  
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

// 작물일기 표시
async function showDiary() {
  if (!diaryModal || !diaryEntries) return;

  diaryModal.classList.add("show");
  
  try {
    const response = await fetch(`${API_BASE}/game/diary/${gameState.userId}/${encodeURIComponent(gameState.cropName)}`);
    if (!response.ok) {
      throw new Error("작물일기 조회 실패");
    }

    const data = await response.json();
    const entries = data.entries || [];

    if (entries.length === 0) {
      diaryEntries.innerHTML = '<div class="diary-empty">아직 작물일기가 없어요. 작물을 관리하면 일기가 작성됩니다! 🌱</div>';
      return;
    }

    // 일기 목록 생성 (백엔드에서 이미 최신순으로 정렬됨)
    diaryEntries.innerHTML = entries.map(entry => {
      const hpChange = entry.hpChange || 0;
      const hpClass = hpChange > 0 ? "positive" : hpChange < 0 ? "negative" : "neutral";
      const hpText = hpChange > 0 ? `+${hpChange}` : hpChange < 0 ? `${hpChange}` : "0";
      
      // 날짜 포맷팅
      let dateText = "";
      if (entry.timestamp) {
        try {
          const date = new Date(entry.timestamp);
          dateText = date.toLocaleDateString("ko-KR", {
            year: "numeric",
            month: "long",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit"
          });
        } catch (e) {
          dateText = entry.timestamp;
        }
      }

      return `
        <div class="diary-entry">
          <div class="diary-entry-header">
            <span class="diary-entry-day">${entry.day}일차</span>
            <span class="diary-entry-hp ${hpClass}">HP ${hpText}</span>
          </div>
          <div class="diary-entry-text">${entry.entry}</div>
          ${dateText ? `<div class="diary-entry-date">${dateText}</div>` : ""}
        </div>
      `;
    }).join("");
  } catch (error) {
    console.error("작물일기 조회 실패:", error);
    diaryEntries.innerHTML = '<div class="diary-empty">작물일기를 불러오는 중 오류가 발생했습니다. 😢</div>';
  }
}

// 작물일기 숨기기
function hideDiary() {
  if (diaryModal) {
    diaryModal.classList.remove("show");
  }
}

// 도감 표시
async function showCollection() {
  if (!collectionModal || !collectionGrid) return;

  collectionModal.classList.add("show");
  
  try {
    // 도감 요약 정보 가져오기
    const response = await fetch(`${API_BASE}/game/collection/${gameState.userId}/summary`);
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
  if (collectionModal) {
    collectionModal.classList.remove("show");
  }
}

// 페이지 로드 시 초기화
window.addEventListener("DOMContentLoaded", () => {
  initGame();
  initAdminMode();
});

