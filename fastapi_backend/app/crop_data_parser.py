"""
작물 재배 데이터 파싱 모듈
watering.txt, fertilizing.txt, growing_period.txt, sickness.txt 파일을 파싱
"""
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# 전역 캐시
_watering_data: Optional[Dict[str, Dict[str, str]]] = None
_fertilizing_data: Optional[Dict[str, str]] = None
_growing_period_data: Optional[Dict[str, Tuple[int, int]]] = None  # (최소 수확일, 최적 수확일)
_sickness_data: Optional[Dict[str, List[Dict[str, str]]]] = None


def clear_all_cache():
    """모든 캐시 초기화 - 파일 수정 후 호출"""
    global _watering_data, _fertilizing_data, _growing_period_data, _sickness_data
    _watering_data = None
    _fertilizing_data = None
    _growing_period_data = None
    _sickness_data = None
    print("✅ 모든 작물 데이터 캐시가 초기화되었습니다.")


def parse_watering_data() -> Dict[str, Dict[str, str]]:
    """watering.txt 파싱: 작물별 물주기 빈도"""
    global _watering_data
    if _watering_data is not None:
        return _watering_data
    
    _watering_data = {}
    file_path = DATA_DIR / "watering.txt"
    
    if not file_path.exists():
        return _watering_data
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 작물별로 구분
    crops = ["토마토", "감자", "오이", "당근", "부추"]
    current_crop = None
    periods = {}
    
    for line in content.split("\n"):
        line = line.strip()
        if not line:
            continue
        
        # 작물명 확인
        if line in crops:
            if current_crop:
                _watering_data[current_crop] = periods
            current_crop = line
            periods = {}
            continue
        
        # 기간별 물주기 정보 파싱 (예: "0~10일 - 매일/겉흙 마르면" 또는 "35~수확기 - 주2회")
        # "35~수확기" 형식도 처리
        match = re.match(r"(\d+)~(\d+일|수확기)\s*-\s*(.+)", line)
        if match and current_crop:
            period_start = match.group(1)
            period_end = match.group(2)
            frequency = match.group(3).strip()
            
            if period_end == "수확기":
                periods["35+"] = frequency
            else:
                # "10일"에서 "일" 제거
                period_end_clean = period_end.replace("일", "")
                period_key = f"{period_start}~{period_end}"
                periods[period_key] = frequency
    
    # 마지막 작물 저장
    if current_crop:
        _watering_data[current_crop] = periods
    
    return _watering_data


def parse_fertilizing_data() -> Dict[str, str]:
    """fertilizing.txt 파싱: 작물별 비료 주기"""
    global _fertilizing_data
    if _fertilizing_data is not None:
        return _fertilizing_data
    
    _fertilizing_data = {}
    file_path = DATA_DIR / "fertilizing.txt"
    
    if not file_path.exists():
        return _fertilizing_data
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    crops = ["당근", "부추", "감자", "오이", "토마토"]
    current_crop = None
    period_info = None
    
    for line in content.split("\n"):
        line = line.strip()
        if not line:
            # 빈 줄이 나오면 이전 작물 정보 저장
            if current_crop and period_info:
                _fertilizing_data[current_crop] = period_info
                period_info = None
            continue
        
        # 작물명 확인
        if line in crops:
            # 이전 작물 정보 저장
            if current_crop and period_info:
                _fertilizing_data[current_crop] = period_info
            current_crop = line
            period_info = None
            continue
        
        # 비료 주기 정보 파싱
        if current_crop:
            # "비료 주기 : 파종 후 20일 후 정도" 형식
            if "비료 주기" in line:
                match = re.search(r"비료 주기\s*:\s*(.+)", line)
                if match:
                    period_info = match.group(1).strip()
            # ": 10~14일 정도" 형식 (작물명이 없는 경우)
            elif line.startswith(":") and not period_info:
                period_info = line[1:].strip()
            # 대괄호 안의 상세 정보도 포함
            elif line.startswith("[") and period_info:
                period_info += " " + line
    
    # 마지막 작물 정보 저장
    if current_crop and period_info:
        _fertilizing_data[current_crop] = period_info
    
    return _fertilizing_data


def parse_growing_period_data() -> Dict[str, Tuple[int, int]]:
    """growing_period.txt 파싱: 작물별 수확 시기 (최소 수확일, 최적 수확일)"""
    global _growing_period_data
    if _growing_period_data is not None:
        return _growing_period_data
    
    _growing_period_data = {}
    file_path = DATA_DIR / "growing_period.txt"
    
    if not file_path.exists():
        return _growing_period_data
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # "작물명 최소수확일 최적수확일" 형식 파싱 (예: "당근 70 90")
    for line in content.split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or "수확 시기" in line or "형식" in line or "예" in line:
            continue
        
        # 작물명, 최소 수확일, 최적 수확일 추출
        match = re.match(r"(.+?)\s+(\d+)\s+(\d+)", line)
        if match:
            crop_name = match.group(1).strip()
            min_harvest_day = int(match.group(2))
            optimal_harvest_day = int(match.group(3))
            
            _growing_period_data[crop_name] = (min_harvest_day, optimal_harvest_day)
    
    return _growing_period_data


def parse_sickness_data() -> Dict[str, List[Dict[str, str]]]:
    """sickness.txt 파싱: 작물별 병해충 정보"""
    global _sickness_data
    if _sickness_data is not None:
        return _sickness_data
    
    _sickness_data = {}
    file_path = DATA_DIR / "sickness.txt"
    
    if not file_path.exists():
        return _sickness_data
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    crops = ["당근", "부추", "감자", "토마토", "오이"]
    current_crop = None
    sicknesses = []
    
    for line in content.split("\n"):
        line = line.strip()
        if not line or line == "병해충":
            continue
        
        # 작물명 확인
        if line in crops:
            if current_crop:
                _sickness_data[current_crop] = sicknesses
            current_crop = line
            sicknesses = []
            continue
        
        # 병해충 정보 파싱 (병명과 설명)
        if current_crop and ":" in line:
            parts = line.split(":", 1)
            if len(parts) == 2:
                sickness_name = parts[0].strip()
                description = parts[1].strip()
                sicknesses.append({
                    "name": sickness_name,
                    "description": description
                })
    
    # 마지막 작물 저장
    if current_crop:
        _sickness_data[current_crop] = sicknesses
    
    return _sickness_data


def get_watering_frequency(crop_name: str, day: int) -> Optional[str]:
    """특정 날짜에 해당하는 물주기 빈도 반환"""
    watering_data = parse_watering_data()
    crop_data = watering_data.get(crop_name, {})
    
    # 기간별로 확인
    if day < 10:
        return crop_data.get("0~10일")
    elif day < 35:
        return crop_data.get("10~35일")
    else:
        return crop_data.get("35+")


def get_fertilizing_period(crop_name: str) -> Optional[str]:
    """작물의 비료 주기 정보 반환"""
    fertilizing_data = parse_fertilizing_data()
    return fertilizing_data.get(crop_name)


def get_growing_period(crop_name: str) -> Optional[Tuple[int, int]]:
    """작물의 수확 시기 반환: (최소 수확일, 최적 수확일)"""
    growing_period_data = parse_growing_period_data()
    return growing_period_data.get(crop_name)


def get_sickness_info(crop_name: str) -> List[Dict[str, str]]:
    """작물의 병해충 정보 반환"""
    sickness_data = parse_sickness_data()
    return sickness_data.get(crop_name, [])


def extract_temperature_from_text(text: str) -> Optional[Tuple[float, float]]:
    """텍스트에서 온도 범위 추출 (예: "26 ~ 30 'C" -> (26, 30))"""
    # 다양한 패턴 매칭
    patterns = [
        r"(\d+)\s*~\s*(\d+)\s*['℃]?C",  # "26 ~ 30 'C"
        r"(\d+)\s*~(\d+)\s*['℃]?C",      # "26~30'C"
        r"(\d+)\s*['℃]?C\s*~(\d+)\s*['℃]?C",  # "26'C ~ 30'C"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                temp_min = float(match.group(1))
                temp_max = float(match.group(2))
                return (temp_min, temp_max)
            except:
                continue
    
    return None


def extract_humidity_from_text(text: str) -> Optional[Tuple[int, int]]:
    """텍스트에서 습도 범위 추출 (예: "80%이상" -> (80, 100))"""
    patterns = [
        r"(\d+)%\s*이상",  # "80%이상"
        r"(\d+)%\s*~(\d+)%",  # "80%~90%"
        r"(\d+)%\s*이상.*?(\d+)%",  # "80%이상 90%"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                if len(match.groups()) == 1:
                    return (int(match.group(1)), 100)
                else:
                    return (int(match.group(1)), int(match.group(2)))
            except:
                continue
    
    return None

