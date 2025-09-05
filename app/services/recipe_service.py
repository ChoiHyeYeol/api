import os
import re
import json
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple, Optional

import pandas as pd

# ---- 경로 설정 (필요시 환경변수로 교체 가능)
DATA_ROOT = os.getenv("APP_DATA_ROOT", "/app/data")
RECIPES_DIR = os.path.join(DATA_ROOT, "recipes/recipes")
NUTR_FOOD_PATH = os.path.join(DATA_ROOT, "share/음식 영양성분.xlsx")
NUTR_RAW_PATH = os.path.join(DATA_ROOT, "share/원재료 영양성분.xlsx")
LOW_SUGAR_MAP_PATH = os.path.join(DATA_ROOT, "recipes/저당레시피 매핑 데이터셋.csv")
# (참고) GI 참고 자료(PDF)는 코드에서 직접 파싱하지 않고 수동 매핑 테이블로 보완


# -------------------------
# (2번) 크롤링 스텁 – 시그니처만 제공
from selenium import webdriver as wb
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import json
import time
from selenium.common.exceptions import NoAlertPresentException
import os

import tempfile, shutil, uuid
from selenium import webdriver as wb
from selenium.webdriver.chrome.options import Options
# -------------------------
def crawl_recipe_stub(url: str) -> Dict[str, Any]:
    """만개의 레시피 URL → food*.json 파싱 (여기서는 비워둠/주석)
    # TODO: BeautifulSoup, playwright 등으로 구현
    """
    
    

    def safe_get_text(driver, by, selector, default=""):
        """요소가 있으면 text, 없으면 default 반환"""
        elems = driver.find_elements(by, selector)
        return elems[0].text.strip() if elems else default

    def safe_get_attr(driver, by, selector, attr, default=""):
        """요소가 있으면 속성(attr), 없으면 default 반환"""
        elems = driver.find_elements(by, selector)
        return elems[0].get_attribute(attr) if elems else default

    tmp_dir = tempfile.mkdtemp(prefix=f"chrome-profile-{uuid.uuid4()}-")  # ✅ 매 요청마다 고유 폴더
    options = Options()
    options.add_argument("--headless=new")           # ✅ 헤드리스
    options.add_argument("--no-sandbox")             # ✅ 컨테이너/서버 필수
    options.add_argument("--disable-dev-shm-usage")  # ✅ /dev/shm 이슈 회피
    options.add_argument(f"--user-data-dir={tmp_dir}")  # ✅ 고유 프로필 디렉토리
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,2000")

    driver = None

    try:
        driver = wb.Chrome(options=options)
        driver.get(url)
        # ✅ alert 있으면 닫고 스킵
        try:
            alert = driver.switch_to.alert
            print(f"⚠️ Alert 발생: {alert.text} → 스킵")
            alert.accept()
        except NoAlertPresentException:
            pass  # alert 없으면 그대로 진행
        
        mainImg = safe_get_attr(driver, By.CSS_SELECTOR, "#main_thumbs","src")
        writer  = safe_get_text(driver, By.CLASS_NAME, 'user_info2_name')
        title   = safe_get_text(driver, By.CSS_SELECTOR, '#contents_area_full > div.view2_summary.st3 > h3')
        summary = safe_get_text(driver, By.CSS_SELECTOR, '#recipeIntro')
        portion = safe_get_text(driver, By.CLASS_NAME, 'view2_summary_info1')
        cook_time    = safe_get_text(driver, By.CLASS_NAME, 'view2_summary_info2')
        level   = safe_get_text(driver, By.CLASS_NAME, 'view2_summary_info3')

        # 재료/양념 리스트
        ingredient_list = [li.text.split("\n") for li in driver.find_elements(
            By.CSS_SELECTOR, '#divConfirmedMaterialArea > ul:nth-child(1) > li')]
        sauce_list = [li.text.split("\n") for li in driver.find_elements(
            By.CSS_SELECTOR, '#divConfirmedMaterialArea > ul:nth-child(2) > li')]

        # 맨 뒤만 value, 앞쪽 join → key
        ingredient = {
            " ".join(x[0]): x[1] if len(x) > 1 else ""
            for x in ingredient_list if x
        }
        sauce = {
            " ".join(x[0]): x[1] if len(x) > 1 else ""
            for x in sauce_list if x
        }

        # 노하우(링크 리스트)
        knowHow = list({
            item.get_attribute("href")
            for item in driver.find_elements(By.CSS_SELECTOR, '.swiper-slide > a')
        })

        # 조리 단계 (있을 수도 없을 수도 있음)
        step = driver.find_elements(By.CSS_SELECTOR, '.view_step_cont.media')
        step_list = [{
            s.text.replace("\n",""):
            (s.find_element(By.TAG_NAME,'img').get_attribute('src') if s.find_elements(By.TAG_NAME,'img') else 0)
        } for s in step]

        # 팁 (없을 경우 "")
        tip = safe_get_text(driver, By.CSS_SELECTOR, '#obx_recipe_step_start > dl > dd')

        review_dicts = {
            "mainImg":mainImg,
            "writer": writer,
            "title": title,
            "summary": summary,
            "portion": portion,
            "time": cook_time,
            "level": level,
            "ingredient": ingredient,
            "sauce": sauce,
            "knowHow": knowHow,
            "step_list": step_list,
            "tip": tip
        }

        print(review_dicts)
        
        return review_dicts
        
    except Exception as e:
        print(f"⚠️ 페이지 로딩 실패: {link} ({e})")
    finally:
        try:
            if driver:
                driver.quit()
        finally:
            # ✅ 프로필 디렉토리 정리(안 하면 /tmp 쌓임)
            shutil.rmtree(tmp_dir, ignore_errors=True)

    # 있으면 가져오고 없으면 기본값 ""
    


# -------------------------
# 유틸: JSON 로딩/정리
# -------------------------
def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _strip_categories(recipe: Dict[str, Any]) -> Dict[str, Any]:
    # category_time/category_menu 제거
    for k in ["category_time", "category_menu"]:
        if k in recipe:
            recipe.pop(k, None)
    return recipe


# -------------------------
# 치환 룰(저당 매핑)
# -------------------------
@dataclass
class SubRule:
    pattern: re.Pattern
    replace_with: str
    note: str


def _default_sub_rules() -> List[SubRule]:
    """필수 기본 치환 규칙 (키워드 기반)
    - 설탕/물엿/올리고당/꿀 → 에리스리톨/알룰로스/스테비아 조합
    - 흰쌀/백미 → 현미/잡곡/콜리플라워 라이스
    - 밀가루 → 통밀가루/귀리 가루/아몬드 가루
    - 빵가루 → 통밀빵가루/귀리빵가루
    - 전분/감자전분 → 타피오카 소량 or 도토리전분(선택)
    """
    pairs: List[Tuple[str, str, str]] = [
        (r"설탕|백설탕|흑설탕|갈색설탕|슈가", "에리스리톨 (동량)", "당류 대체"),
        (r"물엿|올리고당|조청|시럽|매실청|청\b", "알룰로스 (1/2~2/3량)", "당류 대체"),
        (r"꿀", "스테비아 소량 + 물", "당류 대체"),
        (r"흰쌀|백미|쌀밥|흰밥|맵쌀", "현미 또는 콜리플라워 라이스", "저GI 곡물/대체"),
        (r"찹쌀|멥쌀가루|쌀가루|떡", "잡곡가루/현미떡 (양 20%↓)", "저GI 곡물"),
        (r"밀가루|박력분|중력분|강력분", "통밀가루/귀리 가루/아몬드가루", "저GI 가루"),
        (r"빵가루", "통밀빵가루", "저GI 빵가루"),
        (r"감자전분|옥수수전분|전분", "(가능시) 도토리/타피오카 소량", "전분 조절"),
        (r"라면|중면|소면|스파게티", "통밀/귀리/콩면 (양 20%↓)", "면류 저당"),
        (r"케첩|달콤 소스|단짠", "무가당 토마토소스 + 식초 소량", "소스 저당"),
        (r"마요네즈", "요거트 마요 or 저지방 마요", "지방/당 저감"),
        (r"우유", "무가당 두유/저지방 우유", "당/지방 저감"),
        (r"요거트", "무가당 그릭요거트", "당 저감"),
    ]
    return [SubRule(re.compile(p), r, note) for p, r, note in pairs]


def _load_external_low_sugar_map() -> Dict[str, str]:
    """low_sugar_recipes.json에서 자주 쓰이는 재료 이름을 힌트 맵으로 구성
    (파일이 레시피 모음이라 완전한 맵은 아니므로 히ュー리스틱 보조용)"""
    try:
        data = _load_json(LOW_SUGAR_MAP_PATH)
    except Exception:
        return {}
    freq: Dict[str, int] = {}
    repl: Dict[str, str] = {}
    for rec in data:
        # sauce/ingredient 키에서 '스테비아', '현미', '귀리' 등 저당 키워드 빈도를 본다
        for sect in ("ingredient", "sauce"):
            sec = rec.get(sect, {}) or {}
            for name in sec.keys():
                if any(key in name for key in ["스테비아", "에리스리톨", "알룰로스", "현미", "귀리", "통밀", "두부"]):
                    freq[name] = freq.get(name, 0) + 1
    # 빈도 상위 항목을 자기 자신으로 매핑(치환 후보로 노출)
    for k, _ in sorted(freq.items(), key=lambda x: x[1], reverse=True)[:64]:
        repl[k] = k
    return repl


def apply_low_sugar_mapping(recipe: Dict[str, Any], user_type: str) -> Dict[str, Any]:
    """재료/양념을 저당 친화적으로 치환. user_type에 따라 강도 조절.
    - FPG_HIGH (공복): 밤 늦은 탄수화물/과당 줄이기, 곡물은 저GI 위주
    - PPG_HIGH (식후): 전분/설탕 치환 강하게, 식초/섬유 보강
    - WEIGHT_GAIN (체중): 유지/에너지 밀도 감소
    - INSULIN (인슐린): 과도한 단당 제한 + 저GI 유지
    """
    recipe = json.loads(json.dumps(recipe, ensure_ascii=False))  # deep copy
    ing = recipe.get("ingredient", {}) or {}
    sauce = recipe.get("sauce", {}) or {}

    rules = _default_sub_rules()
    hints = _load_external_low_sugar_map()

    def _replace_section(section: Dict[str, str]) -> Dict[str, str]:
        replaced: Dict[str, str] = {}
        for name, qty in section.items():
            new_name = name
            for rule in rules:
                if rule.pattern.search(name):
                    new_name = rule.pattern.sub(rule.replace_with, name)
                    break
            # 힌트: 저당 키워드가 이미 있으면 유지
            replaced[new_name] = qty
        return replaced

    recipe["ingredient"] = _replace_section(ing)
    recipe["sauce"] = _replace_section(sauce)

    # user_type 보정 (간단 스케일/추가 메모)
    recipe.setdefault("notes", [])
    if user_type.upper() == "PPG_HIGH":
        recipe["notes"].append("식후혈당형: 전분/당 대체 강도↑, 식초 1작은술 추가 권장")
        # 식초 권장 (양념에 추가 메모)
        recipe["sauce"]["식초 소량"] = recipe["sauce"].get("식초 소량", "1작은술")
    elif user_type.upper() == "FPG_HIGH":
        recipe["notes"].append("공복혈당형: 곡물 저GI 교체 및 야식 금지 권장")
    elif user_type.upper() == "WEIGHT_GAIN":
        recipe["notes"].append("체중증가형: 유지/견과/오일 20% 감량 권장")
        # 오일류 감량 표시
        for k in list(recipe["sauce"].keys()):
            if any(x in k for x in ["오일", "기름", "버터", "마요"]):
                recipe["sauce"][k] = f"{recipe['sauce'][k]} (20% 감량)"
    elif user_type.upper() == "INSULIN":
        recipe["notes"].append("인슐린 사용형: 저GI 유지 + 단당 제한 유지")

    return recipe


# -------------------------
# 영양/GI 계산기
# -------------------------
@dataclass
class NutrRow:
    name: str
    per: float  # 기준량(g)
    carb: float
    prot: float
    fat: float
    sugar: float
    iron: float


class NutritionResolver:
    def __init__(self):
        # 두 소스 병합 (가용 컬럼명 가정)
        self.food = self._load(NUTR_FOOD_PATH)
        self.raw = self._load(NUTR_RAW_PATH)
        self.df = pd.concat([self.food, self.raw], ignore_index=True, sort=False)
        # 표준 컬럼 매핑
        self.name_col = self._pick(["식품명", "원재료명", "name"])  # 이름
        self.base_col = self._pick(["기준량(g)", "섭취단위(g)", "base_g"])  # 기준량
        self.cols = {
            "carb": self._pick(["탄수화물(g)", "carbohydrate_g", "carb_g"]),
            "prot": self._pick(["단백질(g)", "protein_g", "prot_g"]),
            "fat": self._pick(["지방(g)", "fat_g"]),
            "sugar": self._pick(["당류(g)", "sugars_g", "sugar_g"]),
            "iron": self._pick(["철분(mg)", "iron_mg"]),
        }

    def _load(self, path: str) -> pd.DataFrame:
        try:
            if path.lower().endswith(".xlsx"):
                return pd.read_excel(path)
            return pd.read_csv(path)
        except Exception:
            return pd.DataFrame()

    def _pick(self, candidates: List[str]) -> Optional[str]:
        for c in candidates:
            if c in self.df.columns:
                return c
        return None

    @staticmethod
    def _parse_qty(s: str) -> float:
        """'200g', '1컵', '1숟가락' 등에서 g(그램) 근사치 추출. 단위 변환은 보수적.
        - ml는 g로 근사(=1) 처리 (수분 위주 재료 고려)
        - 숟가락/작은술 등은 대략치 (15g/5g) 사용
        - 명시 수치 없으면 기준량 1배로 간주
        """
        if not s:
            return float('nan')
        s = str(s)
        # 숫자 + g/ml
        m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(g|그램|ml|mL)", s)
        if m:
            val = float(m.group(1))
            return val  # ml도 g 근사
        # 컵/숟가락/티스푼
        if "컵" in s:
            m = re.search(r"([0-9]+)\s*컵", s)
            n = float(m.group(1)) if m else 1.0
            return 200.0 * n  # 보수적 1컵=200g
        if "숟가락" in s or "스푼" in s:
            m = re.search(r"([0-9]+)\s*(큰|작은)?숟가락|스푼", s)
            n = 1.0
            if m:
                try:
                    n = float(m.group(1))
                except Exception:
                    n = 1.0
            if "작" in s:
                return 5.0 * n
            return 15.0 * n
        # 숫자만
        m = re.search(r"([0-9]+(?:\.[0-9]+)?)", s)
        if m:
            return float(m.group(1))
        return float('nan')

    def lookup(self, name: str) -> Optional[NutrRow]:
        if self.df.empty or not self.name_col:
            return None
        # 간단 부분일치 우선
        cand = self.df[self.df[self.name_col].astype(str).str.contains(name, regex=False, na=False)]
        if cand.empty:
            # 공백 제거/축약 재시도
            key = name.replace(" ", "")
            cand = self.df[self.df[self.name_col].astype(str).str.replace(" ", "").str.contains(key, regex=False, na=False)]
        if cand.empty:
            return None
        row = cand.iloc[0]
        base = float(row.get(self.base_col, 100) or 100)
        return NutrRow(
            name=str(row[self.name_col]),
            per=base,
            carb=float(row.get(self.cols["carb"], 0) or 0),
            prot=float(row.get(self.cols["prot"], 0) or 0),
            fat=float(row.get(self.cols["fat"], 0) or 0),
            sugar=float(row.get(self.cols["sugar"], 0) or 0),
            iron=float(row.get(self.cols["iron"], 0) or 0),
        )

    def totalize(self, ingredient: Dict[str, str]) -> Dict[str, float]:
        total = dict(carb=0.0, prot=0.0, fat=0.0, sugar=0.0, iron=0.0)
        for name, qty in (ingredient or {}).items():
            qty_g = self._parse_qty(str(qty))
            row = self.lookup(name)
            if not row:
                continue
            # 기준량 대비 배수
            mult = (qty_g / row.per) if (qty_g == qty_g and row.per) else 1.0  # NaN 체크
            total["carb"] += row.carb * mult
            total["prot"] += row.prot * mult
            total["fat"] += row.fat * mult
            total["sugar"] += row.sugar * mult
            total["iron"] += row.iron * mult
        return total


class GIResolver:
    """간단 GI 추정 (부분 매핑 + 휴리스틱)
    - 정확한 GI 테이블 사전구축 시 이 클래스를 교체/보완
    """
    def __init__(self):
        # 대표 식품 키워드 기반 GI (글루코스=100 기준)
        self.map = {
            "현미": 55, "잡곡": 50, "퀴노아": 53, "귀리": 55, "통밀": 58,
            "흰쌀": 73, "백미": 73, "찹쌀": 82, "감자": 78, "고구마": 63,
            "면": 70, "콩면": 35, "두부": 15, "우유": 47, "요거트": 36,
            "사과": 38, "바나나": 52, "당근": 47, "브로콜리": 15,
            "빵": 75, "통밀빵": 62, "현미밥": 55, "콜리플라워": 10,
            "올리고당": 90, "설탕": 65, "꿀": 61, "에리스리톨": 0, "스테비아": 0, "알룰로스": 0,
        }

    def estimate_recipe_gi(self, ingredient: Dict[str, str], nutrition_share: Dict[str, float]) -> float:
        # 가중치는 탄수화물 기여도로 설정
        total_carb = nutrition_share.get("carb", 0) or 0
        if total_carb <= 0:
            return 45.0  # 기본 저GI 추정
        weighted_sum, seen = 0.0, 0.0
        for name, qty in (ingredient or {}).items():
            gi = None
            for key, val in self.map.items():
                if key in name:
                    gi = val
                    break
            if gi is None:
                continue
            # 탄수화물 비중 근사 – 수량 텍스트로 대략 가중치
            w = NutritionResolver._parse_qty(str(qty)) or 0
            weighted_sum += gi * w
            seen += w
        if seen <= 0:
            return 55.0
        return max(10.0, min(95.0, weighted_sum / seen))


# -------------------------
# 메인 파이프라인 (3번)
# -------------------------

def _clean_recipe(food: Dict[str, Any]) -> Dict[str, Any]:
    # 응답 포맷: 최상위에 food{} 배치
    if "food" in food:
        food_obj = food["food"]
    else:
        food_obj = food
    return _strip_categories(food_obj)


def _apply_allergy_filter(recipe: Dict[str, Any], allergies: List[str]) -> Dict[str, Any]:
    if not allergies:
        return recipe
    def _filter(sec: Dict[str, str]) -> Dict[str, str]:
        res = {}
        for k, v in (sec or {}).items():
            if any(a for a in allergies if a and a in k):
                continue
            res[k] = v
        return res
    recipe["ingredient"] = _filter(recipe.get("ingredient", {}))
    recipe["sauce"] = _filter(recipe.get("sauce", {}))
    return recipe


def transform_recipe_from_dict(food_json: Dict[str, Any], user_type: str, allergies: List[str]) -> Dict[str, Any]:
    # 1) 정리
    recipe = _clean_recipe(food_json)
    # 2) 저당 매핑 치환
    recipe = apply_low_sugar_mapping(recipe, user_type)
    # 3) 알러지 필터
    recipe = _apply_allergy_filter(recipe, allergies)
    # 4) 영양 합산
    nutr = NutritionResolver()
    totals = nutr.totalize(recipe.get("ingredient", {}))
    # 5) GI 추정
    gi = GIResolver().estimate_recipe_gi(recipe.get("ingredient", {}), totals)
    # 6) 출력 포맷
    out = {
        "food": recipe,
        "GI_VAL": round(gi, 1),
        "CH_VAL": round(totals.get("carb", 0), 1),
        "PR_VAL": round(totals.get("prot", 0), 1),
        "FAT_VAL": round(totals.get("fat", 0), 1),
        "IC_VAL": round(totals.get("iron", 0), 2),
    }
    return out
