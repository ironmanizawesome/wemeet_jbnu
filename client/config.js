// API 설정 파일
// 배포 환경에 따라 아래 URL을 변경하세요

// 🌐 배포용 (Render)
window.API_BASE_URL = "https://wemeet-jbnu.onrender.com";

// 🏠 로컬 개발용 (주석 해제하면 로컬 서버 사용)
// window.API_BASE_URL = "http://127.0.0.1:8000";

// 기타 API URL들 (API_BASE_URL 기반으로 자동 설정)
window.RECOMMENDATION_API_URL = window.API_BASE_URL + "/recommendations";
window.CROP_API_URL = window.API_BASE_URL;
