# 작물 이미지 폴더

이 폴더에는 농업 다마고치 게임에서 사용할 작물 이미지가 저장됩니다.

## 현재 지원 작물 이미지

- `potato.png` - 감자 이미지

## 이미지 추가 방법

1. 이미지 파일을 이 폴더(`client/images/`)에 저장하세요
2. 파일명은 작물 이름(한글)으로 지정하세요
   - 예: `potato.png`, `cucumber.png`, `tomato.png`, `carrot.png`, `chive.png`
3. `recommend.js` 파일의 `CROP_IMAGES` 객체에 경로를 추가하세요

```javascript
const CROP_IMAGES = {
  "감자": "images/potato.png",
  "오이": "images/cucumber.png",  // 이미지 추가 시
  // ...
};
```

## 이미지 파일 형식 권장사항

- **형식**: PNG (투명 배경 권장)
- **크기**: 80x80px ~ 160x160px (정사각형 권장)
- **스타일**: 픽셀 아트 또는 캐릭터 스타일
- **배경**: 투명 또는 단색

## Fallback

이미지가 없거나 로드에 실패하면 자동으로 이모지로 대체됩니다.

