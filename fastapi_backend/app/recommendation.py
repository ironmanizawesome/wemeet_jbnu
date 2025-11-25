from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "작물들.txt"


def _extract(section: str, content: str) -> str:
    """Grab a section body until the next uppercase/kor heading."""
    pattern = rf"{section}\s*[:：]?\s*(.*?)(?=\n[A-Z가-힣 ]+[:：]|\Z)"
    match = re.search(pattern, content, re.S)
    return match.group(1).strip() if match else ""


def load_crop_data(file_path: Path) -> List[Dict[str, str]]:
    text = file_path.read_text(encoding="utf-8")
    chunks = re.split(r"\*\*(.+?)\*\*", text)[1:]

    crops: List[Dict[str, str]] = []
    for idx in range(0, len(chunks), 2):
        name = chunks[idx].strip()
        content = chunks[idx + 1].strip()
        crops.append(
            {
                "name": name,
                "season": _extract("재배 시기", content),
                "purpose": _extract("재배 목적", content),
                "level": _extract("난이도", content),
                "environment": _extract("밭의 환경 조건", content),
            }
        )
    return crops


def recommend_crops(
    crops: List[Dict[str, str]],
    season: Optional[str] = None,
    level: Optional[str] = None,
    sunlight: Optional[str] = None,
) -> List[Dict[str, str]]:
    results: List[Dict[str, str]] = []
    for crop in crops:
        if season and season not in crop.get("season", ""):
            continue
        if level and level not in crop.get("level", ""):
            continue
        if sunlight and sunlight not in crop.get("environment", ""):
            continue
        results.append(crop)
    return results


class CropRecommendationService:
    def __init__(self, data_path: Path = DATA_PATH):
        if not data_path.exists():
            raise FileNotFoundError(f"Crop data file not found: {data_path}")
        self._crops = load_crop_data(data_path)

    def recommend(
        self,
        season: Optional[str] = None,
        level: Optional[str] = None,
        sunlight: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        return recommend_crops(self._crops, season, level, sunlight)

