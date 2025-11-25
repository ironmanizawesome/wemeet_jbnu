const API_URL =
  window.RECOMMENDATION_API_URL || "http://127.0.0.1:8000/recommendations";

const form = document.getElementById("recommend-form");
const listEl = document.getElementById("recommend-list");
const emptyEl = document.getElementById("recommend-empty");
const conditionEl = document.getElementById("condition-card");
const statusEl = document.getElementById("recommend-status");

const fields = ["season", "level", "sunlight"];

const params = new URLSearchParams(window.location.search);
fields.forEach((name) => {
  const value = params.get(name) || "";
  if (value && form.elements[name]) {
    form.elements[name].value = value;
  }
});

if (fields.some((name) => params.get(name))) {
  requestRecommendations(false);
} else {
  emptyEl.hidden = false;
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  requestRecommendations();
});

async function requestRecommendations(pushState = true) {
  const payload = formDataToPayload(new FormData(form));
  updateCondition(payload);
  setStatus("추천을 계산하는 중입니다...");
  emptyEl.hidden = true;
  listEl.innerHTML = "";

  if (pushState) {
    const next = new URL(window.location.href);
    fields.forEach((key) => {
      if (payload[key]) {
        next.searchParams.set(key, payload[key]);
      } else {
        next.searchParams.delete(key);
      }
    });
    history.replaceState({}, "", next);
  }

  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        season: payload.season || null,
        level: payload.level || null,
        sunlight: payload.sunlight || null,
      }),
    });

    if (!response.ok) {
      throw new Error(`API 호출 실패 (${response.status})`);
    }

    const data = await response.json();
    renderResults(data.results || []);
    setStatus("추천 결과가 업데이트되었습니다.");
  } catch (error) {
    console.error(error);
    setStatus("⚠️ 추천 정보를 불러오지 못했습니다. FastAPI 서버를 확인해주세요.");
    emptyEl.hidden = false;
    emptyEl.textContent = "⚠️ 추천 정보를 불러오지 못했습니다.";
  }
}

function formDataToPayload(formData) {
  return fields.reduce((acc, key) => {
    const value = (formData.get(key) || "").trim();
    if (value) {
      acc[key] = value;
    }
    return acc;
  }, {});
}

function updateCondition(filters) {
  conditionEl.innerHTML = `
    <p><strong>현재 조건</strong></p>
    <p>재배 시기: ${filters.season || "모든 시기"}</p>
    <p>난이도: ${filters.level || "모든 수준"}</p>
    <p>햇빛 조건: ${filters.sunlight || "상관없음"}</p>
  `;
}

function renderResults(results) {
  listEl.innerHTML = "";
  if (!results.length) {
    emptyEl.hidden = false;
    emptyEl.textContent = "조건에 맞는 작물이 없습니다.";
    return;
  }

  emptyEl.hidden = true;
  results.forEach((crop) => {
    const li = document.createElement("li");
    li.className = "result-item";
    li.innerHTML = `
      <h3>${crop.name}</h3>
      <p><b>재배 시기:</b> ${crop.season || "정보 없음"}</p>
      <p><b>재배 목적:</b> ${crop.purpose || "정보 없음"}</p>
      <p><b>난이도:</b> ${crop.level || "정보 없음"}</p>
      <p><b>밭의 환경 조건:</b> ${crop.environment || "정보 없음"}</p>
    `;
    listEl.appendChild(li);
  });
}

function setStatus(message) {
  statusEl.textContent = message;
}

