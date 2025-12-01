# 프로젝트 구조 문서

## 📁 전체 디렉토리 구조

```
wemeet_jbnu/
├── client/                          # 프론트엔드 (순수 HTML/CSS/JavaScript)
│   ├── login.html                   # 로그인 페이지
│   ├── recommend.html               # 다마고치(작물) 선택 화면
│   ├── game.html                    # 게임 메인 화면 (작물 키우기)
│   ├── game.js                      # 게임 로직 (상태 관리, AI 연동)
│   ├── recommend.js                 # 작물 추천 및 선택 로직
│   ├── chatbot.html                 # 챗봇 페이지
│   ├── chatbot.js                   # 챗봇 로직
│   ├── main.html                    # 메인 페이지 (기존)
│   ├── profile.html                 # 프로필 페이지
│   ├── calendar.html                # 캘린더 페이지
│   ├── feedback.html                # 피드백 페이지
│   ├── settings.html                # 설정 페이지
│   ├── policy.html                  # 정책 페이지
│   ├── script.js                    # 공통 스크립트
│   ├── style.css                    # 공통 스타일
│   ├── styles.css                   # 추가 스타일
│   ├── profile.css                  # 프로필 스타일
│   ├── ui.html                      # UI 참고 파일
│   └── images/                      # 이미지 파일
│       └── potato.png               # 감자 이미지 (예시)
│
├── fastapi_backend/                 # 백엔드 (FastAPI)
│   ├── app/
│   │   ├── main.py                  # FastAPI 메인 애플리케이션
│   │   │                             # - 인증, 프로필, 챗봇, 추천, 게임 API
│   │   ├── recommendation.py        # 작물 추천 서비스
│   │   │                             # - 작물 데이터 파싱
│   │   │                             # - 필터링 로직 (계절, 난이도, 일조량)
│   │   ├── game_service.py          # 게임 서비스
│   │   │                             # - 작물 가이드라인 추출
│   │   │                             # - crop_info.txt 파싱
│   │   │                             # - AI 판단용 가이드 제공
│   │   └── data/
│   │       ├── 작물들.txt            # 작물 기본 정보 (재배 시기, 목적 등)
│   │       └── crop_info.txt         # 작물 상세 정보 (물주기, 비료, 병해충)
│   │
│   ├── .env                         # 환경 변수 (생성 필요)
│   │                                 # - OPENAI_API_KEY
│   │                                 # - OPENAI_MODEL
│   │                                 # - MONGO_URI
│   │                                 # - MONGO_DB_NAME
│   │
│   └── test_api.http                # API 테스트 파일
│
├── requirements.txt                 # Python 의존성
├── README.md                        # 프로젝트 소개 및 실행 방법
├── RUN.md                           # 실행 가이드
├── LICENSE                          # 라이선스
└── PROJECT_STRUCTURE.md             # 이 문서
```

---

## 🎮 게임 플로우

```
1. 로그인 (login.html)
   ↓
2. 작물 선택 (recommend.html)
   - 필터링 (계절, 난이도, 일조량)
   - 추천받기 버튼 클릭
   - 작물 카드 선택
   ↓
3. 게임 시작 (game.html)
   - 작물 키우기 (물주기, 비료주기, 해충퇴치)
   - AI 판단 (HP 증감 결정)
   - 다음 날 버튼 (테스트 모드)
   - 수확하기 (7일 이상, HP 70 이상)
```

---

## 🔧 백엔드 구조 (FastAPI)

### `fastapi_backend/app/main.py`

**주요 기능:**
- FastAPI 애플리케이션 초기화
- MongoDB 연결
- LangChain + OpenAI 설정
- CORS 설정

**API 엔드포인트:**

#### 인증 및 프로필
- `POST /auth/login` - 로그인
- `GET /profile/{user_id}` - 프로필 조회
- `POST /profile` - 프로필 저장

#### 챗봇
- `POST /chat` - 챗봇 대화 (캐싱 지원)
- `GET /chat/cache/stats` - 캐시 통계
- `DELETE /chat/cache/clear` - 캐시 전체 삭제
- `DELETE /chat/cache/{cache_key}` - 특정 캐시 삭제

#### 작물 추천
- `POST /recommendations` - 작물 추천 (필터링 지원)

#### 게임
- `POST /game/evaluate` - 게임 행동 평가 (AI 판단)
- `POST /game/state` - 게임 상태 저장
- `GET /game/state/{user_id}` - 게임 상태 조회
- `POST /game/harvest-feedback` - 수확 피드백 생성

**MongoDB 컬렉션:**
- `users` - 사용자 정보
- `profiles` - 사용자 프로필
- `games` - 게임 상태
- `chat_responses` - 챗봇 응답 캐시

---

### `fastapi_backend/app/recommendation.py`

**주요 기능:**
- `작물들.txt` 파일 파싱
- 작물 데이터 구조화
- 필터링 로직 (계절, 난이도, 일조량)

**클래스:**
- `CropRecommendationService` - 작물 추천 서비스

---

### `fastapi_backend/app/game_service.py`

**주요 기능:**
- `작물들.txt`에서 기본 가이드라인 추출
- `crop_info.txt`에서 상세 정보 추출 (물주기, 비료, 병해충)
- AI 판단용 가이드라인 포맷팅

**함수:**
- `load_crop_info(crop_name)` - 작물별 상세 정보 로드
- `get_crop_guide_for_game(crop_name)` - 게임용 가이드라인 생성

---

## 🎨 프론트엔드 구조 (Client)

### 주요 페이지

#### `client/login.html`
- 로그인 폼
- 세션 스토리지에 사용자 정보 저장
- 로그인 성공 시 `recommend.html`로 리다이렉트

#### `client/recommend.html`
- 작물 선택 화면
- 필터 패널 (계절, 난이도, 일조량)
- "추천받기" 버튼
- 작물 카드 표시
- 초기 5개 작물만 선택 가능 (나머지는 "추후 예정")
- 선택 시 `game.html`로 이동

#### `client/game.html`
- 게임 메인 화면
- HP 바
- 작물 정보 표시
- 행동 버튼 (물주기, 비료주기, 해충퇴치)
- 다음 날 버튼 (테스트 모드)
- 수확 버튼 (7일 이상, HP 70 이상)
- Admin 패널 (Ctrl+Shift+D)

---

### 주요 JavaScript 파일

#### `client/game.js`

**게임 상태:**
```javascript
gameState = {
  userId: string,
  cropName: string,
  hp: number (0-100),
  day: number,
  actions: Array<{type, day, timestamp}>,
  lastFeedback: string,
  gameStartTime: ISO string,
  lastUpdateTime: ISO string
}
```

**주요 함수:**
- `initGame()` - 게임 초기화
- `loadGameState()` - 게임 상태 로드
- `saveGameState()` - 게임 상태 저장
- `calculateCurrentDay()` - 현재 날짜 계산 (시간 기반 또는 테스트 모드)
- `updateDayBasedOnTime()` - 시간 기반 날짜 업데이트
- `proceedToNextDay()` - 다음 날로 진행 (테스트 모드)
- `performAction(actionType)` - 행동 실행 (물주기, 비료주기, 해충퇴치)
- `harvest()` - 수확 처리
- `updateUI()` - UI 업데이트

**설정:**
- `TEST_MODE = true` - 테스트 모드 (버튼으로 날짜 진행)
- `GAME_DAY_LENGTH_MS` - 게임 하루 길이 (밀리초)

**Admin 모드:**
- `Ctrl+Shift+D` - Admin 패널 토글
- 날짜 건너뛰기, 날짜 직접 설정, HP 조정, 게임 초기화

---

#### `client/recommend.js`

**주요 기능:**
- 작물 데이터 로드
- 필터링 로직
- 작물 카드 렌더링
- 초기 작물만 선택 가능 처리

**상수:**
- `INITIAL_CROPS = ["감자", "오이", "토마토", "당근", "부추"]`

---

## 📊 데이터 구조

### `fastapi_backend/app/data/작물들.txt`
- 작물 기본 정보
- 형식: `**작물명**` + 내용
- 포함 정보: 재배 시기, 재배 목적, 난이도, 일조량 등

### `fastapi_backend/app/data/crop_info.txt`
- 작물 상세 정보
- 형식: `### 작물명 (난이도)` 섹션
- 포함 정보:
  - 물주기 (물주기 주기, 방법)
  - 비료 (시비 시기, 종류, 방법)
  - 병해충 (병해, 해충, 예방/대응)

---

## 🔄 데이터 흐름

### 게임 행동 평가 흐름

```
1. 사용자가 행동 버튼 클릭 (game.js)
   ↓
2. performAction() 호출
   ↓
3. POST /game/evaluate 요청
   - cropName, actionType, day, currentHp, actions
   ↓
4. main.py의 evaluate_game_action()
   - get_crop_guide_for_game()로 가이드라인 가져오기
   - crop_info.txt의 상세 정보 포함
   ↓
5. AI (LangChain) 판단
   - 가이드라인에 따라 행동 평가
   - HP 증감 결정 (-10 ~ +10)
   - 피드백 메시지 생성
   ↓
6. 응답 반환
   - newHp, hpChange, feedback
   ↓
7. game.js에서 UI 업데이트
   - HP 바 업데이트
   - 피드백 메시지 표시
   - 게임 상태 저장
```

---

## 🗄️ MongoDB 스키마

### `users` 컬렉션
```javascript
{
  _id: ObjectId,
  username: string,
  password: string (해시)
}
```

### `profiles` 컬렉션
```javascript
{
  _id: ObjectId,
  userId: string,
  name: string,
  age: number,
  location: string,
  experience: string,
  interest: string,
  // ... 기타 프로필 정보
}
```

### `games` 컬렉션
```javascript
{
  _id: ObjectId,
  userId: string,
  state: {
    cropName: string,
    hp: number,
    day: number,
    actions: Array,
    gameStartTime: ISO string,
    lastUpdateTime: ISO string
  }
}
```

### `chat_responses` 컬렉션
```javascript
{
  _id: ObjectId,
  cache_key: string (hash),
  user_message: string,
  profile_hint: string,
  answer: string,
  created_at: ISO string
}
```

---

## 🔑 환경 변수

### `fastapi_backend/.env`
```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=chatbot_db
```

---

## 🎯 주요 기능 요약

### 1. 인증 시스템
- 로그인 (세션 스토리지 기반)
- 프로필 관리

### 2. 작물 추천 시스템
- 필터링 (계절, 난이도, 일조량)
- 초기 5개 작물만 선택 가능

### 3. 게임 시스템
- 작물 키우기 (물주기, 비료주기, 해충퇴치)
- AI 기반 행동 평가
- HP 시스템 (0-100)
- 날짜 진행 (테스트 모드: 버튼, 실제: 시간 기반)
- 수확 시스템 (7일 이상, HP 70 이상)

### 4. 챗봇 시스템
- LangChain + OpenAI
- 응답 캐싱 (일관성 보장)
- 프로필 기반 맞춤 응답

### 5. Admin 모드
- 날짜 건너뛰기
- 날짜 직접 설정
- HP 조정
- 게임 초기화

---

## 📝 참고사항

### 테스트 모드
- `TEST_MODE = true`일 때: 버튼으로 날짜 진행
- `TEST_MODE = false`일 때: 실제 시간 기반 진행 (1시간 = 1일)

### 캐싱 시스템
- 챗봇 응답 캐싱으로 일관성 보장
- 동일한 입력에 대해 동일한 응답 반환
- MongoDB에 저장

### 작물 정보
- 기본 정보: `작물들.txt`
- 상세 정보: `crop_info.txt`
- AI 판단 시 두 정보 모두 활용

---

## 🚀 실행 순서

1. MongoDB 실행
2. FastAPI 서버 실행
3. 프론트엔드 서버 실행
4. 브라우저에서 `http://127.0.0.1:3000/login.html` 접속

자세한 실행 방법은 `README.md` 참고.

