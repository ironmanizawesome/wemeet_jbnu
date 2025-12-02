"""
작물 키우기 게임 서비스
작물 가이드라인 추출 및 판단 시스템
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Optional

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "작물들.txt"
CROP_INFO_PATH = BASE_DIR / "data" / "crop_info.txt"


def _extract(section: str, content: str) -> str:
    """섹션 내용 추출"""
    pattern = rf"{section}\s*[:：]?\s*(.*?)(?=\n[A-Z가-힣 ]+[:：]|\Z)"
    match = re.search(pattern, content, re.S)
    return match.group(1).strip() if match else ""


def load_crop_info(crop_name: str) -> Dict[str, str]:
    """crop_info.txt에서 작물별 상세 정보 로드 (물주기, 비료, 병해충)"""
    if not CROP_INFO_PATH.exists():
        return {}
    
    text = CROP_INFO_PATH.read_text(encoding="utf-8")
    crop_info = {
        "watering": "",
        "fertilizer": "",
        "pest_disease": ""
    }
    
    # 작물명 정규화
    crop_name_clean = crop_name.strip()
    
    # 물주기 섹션 찾기 (난이도 포함 가능: "### 당근 (중)" 또는 "### 당근(중)")
    watering_match = re.search(r"## 물주기\s*\n(.*?)(?=\n## |\Z)", text, re.S)
    if watering_match:
        watering_content = watering_match.group(1)
        # 작물명으로 시작하는 섹션 찾기 (괄호와 난이도 제외)
        crop_watering = re.search(
            rf"###\s*{re.escape(crop_name_clean)}\s*(?:\([^)]+\))?\s*\n(.*?)(?=\n###\s+|\Z)",
            watering_content,
            re.S
        )
        if crop_watering:
            crop_info["watering"] = crop_watering.group(1).strip()
    
    # 병해충 섹션 찾기 (난이도 없음: "### 당근")
    pest_match = re.search(r"## 병해충\s*\n(.*?)(?=\n## |\Z)", text, re.S)
    if pest_match:
        pest_content = pest_match.group(1)
        crop_pest = re.search(
            rf"###\s*{re.escape(crop_name_clean)}\s*\n(.*?)(?=\n###\s+|\Z)",
            pest_content,
            re.S
        )
        if crop_pest:
            crop_info["pest_disease"] = crop_pest.group(1).strip()
    
    # 비료 섹션 찾기 (난이도 없음: "### 당근")
    fertilizer_match = re.search(r"## 비료\s*\n(.*?)(?=\Z)", text, re.S)
    if fertilizer_match:
        fertilizer_content = fertilizer_match.group(1)
        crop_fertilizer = re.search(
            rf"###\s*{re.escape(crop_name_clean)}\s*\n(.*?)(?=\n###\s+|\Z)",
            fertilizer_content,
            re.S
        )
        if crop_fertilizer:
            crop_info["fertilizer"] = crop_fertilizer.group(1).strip()
    
    return crop_info


def load_crop_guide(crop_name: str) -> Optional[Dict[str, str]]:
    """특정 작물의 가이드라인 로드"""
    if not DATA_PATH.exists():
        return None

    text = DATA_PATH.read_text(encoding="utf-8")
    chunks = re.split(r"\*\*(.+?)\*\*", text)[1:]

    for idx in range(0, len(chunks), 2):
        name = chunks[idx].strip()
        if name == crop_name:
            content = chunks[idx + 1].strip()
            return {
                "name": name,
                "season": _extract("재배 시기", content),
                "purpose": _extract("재배 목적", content),
                "level": _extract("난이도", content),
                "labor": _extract("필수 재배 노동과정", content),  # 필수 재배 노동과정
                "environment": _extract("밭의 환경 조건", content),
                "full_content": content,  # 전체 내용
            }
    return None


def get_crop_guide_for_game(crop_name: str) -> str:
    """게임 판단을 위한 작물 가이드라인 텍스트 생성 (crop_info.txt 포함)"""
    guide = load_crop_guide(crop_name)
    crop_info = load_crop_info(crop_name)
    
    if not guide:
        return f"{crop_name} 작물의 가이드라인을 찾을 수 없습니다."

    # 물주기 정보가 있으면 추가
    watering_section = ""
    if crop_info.get("watering"):
        watering_section = f"""
물주기 관리:
{crop_info['watering']}
"""
    
    # 비료 정보가 있으면 추가
    fertilizer_section = ""
    if crop_info.get("fertilizer"):
        fertilizer_section = f"""
비료 관리:
{crop_info['fertilizer']}
"""
    
    # 병해충 정보가 있으면 추가
    pest_section = ""
    if crop_info.get("pest_disease"):
        pest_section = f"""
병해충 관리:
{crop_info['pest_disease']}
"""

    guide_text = f"""
작물명: {guide['name']}
난이도: {guide.get('level', '정보 없음')}

재배 시기:
{guide.get('season', '정보 없음')}

필수 재배 노동과정:
{guide.get('labor', '정보 없음')}

밭의 환경 조건:
{guide.get('environment', '정보 없음')}
{watering_section}
{fertilizer_section}
{pest_section}
"""
    return guide_text.strip()

