import re

def load_crop_data(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    # 작물별 분리
    crops_raw = re.split(r"\*\*(.+?)\*\*", text)[1:]  # ["당근", "...내용...", "옥수수", "...내용..."]
    crops = []

    for i in range(0, len(crops_raw), 2):
        name = crops_raw[i].strip()
        content = crops_raw[i+1].strip()

        # 각 항목별 정보 추출
        def extract(section):
            pattern = rf"{section}\s*[:：]?\s*(.*?)(?=\n[A-Z가-힣 ]+[:：]|\Z)"
            match = re.search(pattern, content, re.S)
            return match.group(1).strip() if match else ""

        crops.append({
            "작물명": name,
            "재배시기": extract("재배 시기"),
            "재배목적": extract("재배 목적"),
            "난이도": extract("난이도"),
            "환경": extract("밭의 환경 조건"),
        })

    return crops


def recommend_crops(crops, season=None, level=None, sunlight=None):
    results = []
    for crop in crops:
        if season and season not in crop["재배시기"]:
            continue
        if level and level not in crop["난이도"]:
            continue
        if sunlight and sunlight not in crop["환경"]:
            continue
        results.append(crop)
    return results
