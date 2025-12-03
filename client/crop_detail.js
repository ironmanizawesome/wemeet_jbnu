const API_URL = window.CROP_API_URL || "http://127.0.0.1:8000";

// URL 파라미터에서 작물명 가져오기
const params = new URLSearchParams(window.location.search);
const cropName = params.get("crop");

if (!cropName) {
  document.getElementById("loading").style.display = "none";
  document.getElementById("error").style.display = "block";
} else {
  loadCropDetail(cropName);
}

async function loadCropDetail(name) {
  try {
    const response = await fetch(`${API_URL}/crops/${encodeURIComponent(name)}`);
    
    if (!response.ok) {
      throw new Error(`API 호출 실패 (${response.status})`);
    }

    const data = await response.json();
    renderCropDetail(data);
  } catch (error) {
    console.error(error);
    document.getElementById("loading").style.display = "none";
    document.getElementById("error").style.display = "block";
  }
}

function renderCropDetail(crop) {
  document.getElementById("loading").style.display = "none";
  document.getElementById("cropDetail").style.display = "block";

  // 기본 정보
  document.getElementById("cropName").textContent = crop.name || "작물명";
  document.getElementById("seasonInfo").textContent = crop.season || "정보 없음";
  document.getElementById("purposeInfo").textContent = crop.purpose || "정보 없음";
  document.getElementById("levelInfo").textContent = crop.level || "정보 없음";
  document.getElementById("environmentInfo").textContent = crop.environment || "정보 없음";

  // 환경 정보
  const env = crop.environment_data || {};
  
  document.getElementById("temperature").textContent = 
    env.temperature || "정보 없음";
  document.getElementById("tempNote").textContent = 
    env.temperature_note || "생육 최적 온도 범위";
  
  document.getElementById("humidity").textContent = 
    env.humidity || "정보 없음";
  document.getElementById("humidityNote").textContent = 
    env.humidity_note || "권장 습도 범위";
  
  document.getElementById("sunlight").textContent = 
    env.sunlight || "정보 없음";
  document.getElementById("sunlightNote").textContent = 
    env.sunlight_note || "필요한 햇빛 조건";
  
  document.getElementById("soilTemp").textContent = 
    env.soil_temperature || "정보 없음";
  document.getElementById("soilTempNote").textContent = 
    env.soil_temperature_note || "파종/정식 적정 지온";

  // 물주기 정보
  document.getElementById("wateringInfo").textContent = 
    crop.watering || "정보 없음";
}

