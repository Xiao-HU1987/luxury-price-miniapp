"""日文 → 中文翻译模块

翻译流程：
1. 查内置字典（LV 专有名词、常见门店名等）
2. 查翻译缓存表（避免重复调用 API）
3. 调用翻译引擎（默认 Google Translate，可配置百度/OpenAI）

翻译引擎配置（在 .env 中）：
    TRANSLATE_ENGINE=google  # google / baidu / openai
    BAIDU_APPID=xxx
    BAIDU_SECRET=xxx
    OPENAI_API_KEY=xxx

使用方式：
    from crawler.translator import translate_text, translate_batch

    # 单条翻译
    cn = translate_text("スピーディ･バンドリエール 20")
    # => "Speedy Bandoulière 20"

    # 批量翻译
    results = translate_batch(["銀座並木通り店", "大阪府"])
    # => {"銀座並木通り店": "银座并木大道店", "大阪府": "大阪府"}
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import time
from typing import Dict, List, Optional

logger = logging.getLogger("lv_crawler.translator")


# ==================== 内置字典 ====================
# LV 专有名词和常见日文词汇的固定翻译
# 优先级最高，避免 API 调用

_LV_DICTIONARY: Dict[str, str] = {
    # ====== LV 经典包款系列（日文片假名 → 官方中文名） ======
    "スピーディ": "Speedy",
    "バンドリエール": "Bandoulière",
    "アルマ": "Alma",
    "ネヴァーフル": "Neverfull",
    "ポシェット": "Pochette",
    "カプシーヌ": "Capucines",
    "トゥルーヴィル": "Trouville",
    "オントゥゴー": "OnTheGo",
    "メイドレーヌ": "Madeleine",
    "マドレーヌ": "Madeleine",
    "ノエ": "Noé",
    "ブールヴァール": "Boulevard",
    "ペリエール": "Périère",
    "キャリーオール": "Carryall",
    "オール･イン": "All-In",
    "オール・イン": "All-In",
    "オールイン": "All-In",
    "ナノ": "Nano",
    "ナノ･": "Nano ",
    "ウォレット オン チェーン": "Wallet On Chain",
    "ウォレット･オン･チェーン": "Wallet On Chain",
    "ウォレットオンチェーン": "Wallet On Chain",
    "アイビー": "Ivy",
    "ブロッサム": "Blossom",
    "ベラ": "Bella",
    "オンザゴー": "OnTheGo",
    "アンティグア": "Antigua",
    "サックプラ": "Sac Plat",
    "ドーフィーヌ": "Dauphine",
    "サイドトランク": "Side Trunk",
    "ポシェット･メティス": "Pochette Metis",
    "ポシェット・メティス": "Pochette Metis",
    "ポシェットメティス": "Pochette Metis",
    "メティス": "Metis",
    "インサイドアウト": "Inside Out",
    "ミュルティ･ポシェット": "Multi Pochette",
    "ミュルティポシェット": "Multi Pochette",
    "バックパック": "背包",
    "トート": "托特",
    "ハンドバッグ": "手提包",
    "ショルダーバッグ": "肩背包",
    "クロスボディ": "斜挎包",

    # ====== 小皮件 ======
    "コインパース": "零钱包",
    "ポルトクレ": "钥匙扣",
    "ポルトフォイユ": "钱包",
    "ポルトモネ": "钱包",
    "カードケース": "卡包",
    "パスケース": "卡套",
    "キーケース": "钥匙包",
    "長財布": "长钱包",
    "二つ折り財布": "对折钱包",

    # ====== 材质 / 工艺 ======
    "モノグラム": "Monogram",
    "アンプラント": "Empreinte",
    "マハイナ": "Mahina",
    "エピ": "Epi",
    "ダミエ": "Damier",
    "ダミエ･エベヌ": "Damier Ebene",
    "ダミエ・アズール": "Damier Azur",
    "ヴェルニ": "Vernis",
    "タイガ": "Taiga",
    "ヌメックレイユ": "NumeGalets",
    "リバーシブル": "双面",
    "レザー": "皮革",
    "キャンバス": "涂层帆布",
    "エンボス加工": "压花工艺",
    "スエード裏地": "麂皮内衬",
    "マイクロファイバー裏地": "超细纤维内衬",
    "金具": "五金件",
    "ヴァルナ": "Varuna",
    "カーフスキン": "小牛皮",
    "ラムスキン": "小羊皮",
    "クロコダイル": "鳄鱼皮",
    "パイソン": "蟒蛇皮",
    "リザード": "蜥蜴皮",
    "オーストリッチ": "鸵鸟皮",
    "スムースレザー": "光滑皮革",
    "グレインドレザー": "颗粒皮革",

    # ====== 尺寸 / 型号 ======
    "ミニ": "迷你",
    "スモール": "小号",
    "ミディアム": "中号",
    "ラージ": "大号",
    "BB": "BB",
    "PM": "PM",
    "MM": "MM",
    "GM": "GM",
    "EW": "EW",
    "イースト･ウエスト": "East West",
    "イースト・ウエスト": "East West",

    # ====== 颜色 ======
    "ノワール": "黑色",
    "ブラック": "黑色",
    "ホワイト": "白色",
    "ブラン": "白色",
    "ルージュ": "红色",
    "レッド": "红色",
    "ブルー": "蓝色",
    "ブルーニュイ": "藏蓝色",
    "ベージュ": "米色",
    "ピンク": "粉色",
    "ローズ": "玫瑰色",
    "グリーン": "绿色",
    "ヴェール": "绿色",
    "イエロー": "黄色",
    "ジョーヌ": "黄色",
    "パープル": "紫色",
    "ヴィオレット": "紫色",
    "グレー": "灰色",
    "グリ": "灰色",
    "ブラウン": "棕色",
    "マロン": "棕色",
    "モノグラム･エクリプス": "Monogram Eclipse",
    "モノグラム・エクリプス": "Monogram Eclipse",
    "リバース": "Reverse",
    "ジャイアント": "Giant",

    # ====== 库存状态 ======
    "在庫あり": "有库存",
    "在庫なし": "无库存",
    "在庫僅少": "库存稀少",
    "残りわずか": "剩余少量",
    "表示不可": "无法显示",
    "オンラインストア在庫あり": "官网有货",
    "オンラインストア在庫なし": "官网无货",

    # ====== 常见都道府县 ======
    "東京都": "东京都",
    "大阪府": "大阪府",
    "愛知県": "爱知县",
    "福岡県": "福冈县",
    "北海道": "北海道",
    "京都府": "京都府",
    "神奈川県": "神奈川县",
    "埼玉県": "埼玉县",
    "千葉県": "千叶县",
    "兵庫県": "兵库县",
    "広島県": "广岛县",
    "宮城県": "宫城县",
    "新潟県": "新潟县",
    "静岡県": "静冈县",
    "沖縄県": "冲绳县",

    # ====== 常见门店区域 / 地标 ======
    "銀座": "银座",
    "並木通り": "并木大道",
    "並木通": "并木大道",
    "六本木": "六本木",
    "表参道": "表参道",
    "新宿": "新宿",
    "渋谷": "涩谷",
    "池袋": "池袋",
    "羽田空港": "羽田机场",
    "成田空港": "成田机场",
    "阪急": "阪急",
    "梅田": "梅田",
    "心斎橋": "心斋桥",
    "御堂筋": "御堂筋",
    "難波": "难波",
    "天神": "天神",
    "博多": "博多",
    "小倉": "小仓",
    "札幌": "札幌",
    "仙台": "仙台",
    "広島": "广岛",
    "横浜": "横滨",
    "川崎": "川崎",
    "千葉": "千叶",
    "柏": "柏",
    "つきみ野": "月见野",
    "国際空港": "国际机场",
    "中部国際空港": "中部国际机场",
    "関西国際空港": "关西国际机场",
    "ユニバーサル・スタジオ・ジャパン": "日本环球影城",
    "USJ": "USJ",
    "ディズニーランド": "迪士尼乐园",
    "ディズニーシー": "迪士尼海洋",

    # ====== 通用后缀 ======
    "店": "店",
    "本店": "总店",
    "支店": "分店",
    "ルイ･ヴィトン": "路易威登",
    "ルイ・ヴィトン": "路易威登",
    "ルイヴィトン": "路易威登",
    "ヴィトン": "威登",
    "ブティック": "精品店",
    "ストア": "门店",
    "ショップ": "店铺",

    # ====== 通用 / 产品描述词汇 ======
    "メゾン": "品牌",
    "アイコンバッグ": "经典包款",
    "シグネチャー": "标志性",
    "エレガント": "优雅",
    "洗練された": "精致的",
    "モダン": "现代的",
    "クラシック": "经典的",
    "トレンディ": "时尚的",
    "デイリー": "日常",
    "ビジネス": "商务",
    "トラベル": "旅行",
    "ギフト": "礼物",
    "プレゼント": "礼物",
    "限定品": "限量款",
    "コレクション": "系列",
    "新作": "新品",
    "人気": "人气",
    "話題": "热门",
    "おすすめ": "推荐",

    # ====== 分隔符标准化 ======
    "･": " ",
    "・": " ",
}


def _dict_lookup(text: str) -> Optional[str]:
    """查内置字典。支持部分匹配组合。"""
    if not text:
        return None

    # 完全匹配
    if text in _LV_DICTIONARY:
        return _LV_DICTIONARY[text]

    # 组合翻译：将日文片段逐个替换为中文
    result = text
    replaced = False
    # 按键长度降序排列，优先匹配长词
    for jp in sorted(_LV_DICTIONARY.keys(), key=len, reverse=True):
        if jp in result:
            result = result.replace(jp, _LV_DICTIONARY[jp])
            replaced = True

    if replaced and result != text:
        return result

    return None


# ==================== 翻译缓存 ====================

class TranslateCache:
    """内存翻译缓存（进程内）。避免同一次批量翻译中重复调用 API。"""

    _cache: Dict[str, str] = {}

    @classmethod
    def get(cls, text: str) -> Optional[str]:
        return cls._cache.get(text)

    @classmethod
    def set(cls, text: str, translation: str) -> None:
        cls._cache[text] = translation

    @classmethod
    def clear(cls) -> None:
        cls._cache.clear()


# ==================== 翻译引擎 ====================

def _translate_google(text: str) -> Optional[str]:
    """Google Translate 免费接口。"""
    try:
        import urllib.request
        import urllib.parse
        import json

        url = "https://translate.googleapis.com/translate_a/single"
        params = urllib.parse.urlencode({
            "client": "gtx",
            "sl": "ja",
            "tl": "zh-CN",
            "dt": "t",
            "q": text,
        })
        full_url = f"{url}?{params}"
        req = urllib.request.Request(full_url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            # Google Translate 返回格式: [[["翻译结果","原文",...],...],...]
            translated = "".join(item[0] for item in data[0] if item[0])
            return translated if translated else None
    except Exception as e:
        logger.debug("Google Translate 失败: %s", e)
        return None


def _translate_baidu(text: str, appid: str, secret: str) -> Optional[str]:
    """百度翻译 API。"""
    try:
        import urllib.request
        import urllib.parse
        import json
        import random

        salt = str(random.randint(32768, 65536))
        sign_str = appid + text + salt + secret
        sign = hashlib.md5(sign_str.encode("utf-8")).hexdigest()

        url = "https://fanyi-api.baidu.com/api/trans/vip/translate"
        params = urllib.parse.urlencode({
            "q": text,
            "from": "jp",
            "to": "zh",
            "appid": appid,
            "salt": salt,
            "sign": sign,
        })
        full_url = f"{url}?{params}"
        req = urllib.request.Request(full_url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if "trans_result" in data:
                return "\n".join(item["dst"] for item in data["trans_result"])
            logger.debug("百度翻译返回异常: %s", data)
            return None
    except Exception as e:
        logger.debug("百度翻译失败: %s", e)
        return None


def _get_engine() -> str:
    """获取配置的翻译引擎。"""
    return os.getenv("TRANSLATE_ENGINE", "google").lower()


def translate_text(text: str) -> Optional[str]:
    """翻译单条日文文本为中文。

    优先级：内置字典 → 缓存 → 翻译引擎
    """
    if not text or not text.strip():
        return None

    text = text.strip()

    # 如果已经是中文/英文/数字，不需要翻译
    if re.match(r"^[\x00-\x7f\u4e00-\u9fff]+$", text):
        return text

    # 1. 查字典
    dict_result = _dict_lookup(text)
    if dict_result:
        return dict_result

    # 2. 查缓存
    cached = TranslateCache.get(text)
    if cached:
        return cached

    # 3. 调用翻译引擎
    engine = _get_engine()
    result: Optional[str] = None

    if engine == "google":
        result = _translate_google(text)
    elif engine == "baidu":
        appid = os.getenv("BAIDU_APPID", "")
        secret = os.getenv("BAIDU_SECRET", "")
        if appid and secret:
            result = _translate_baidu(text, appid, secret)
        else:
            logger.warning("百度翻译未配置 BAIDU_APPID/BAIDU_SECRET，回退到字典")
    else:
        logger.warning("未知翻译引擎: %s，回退到字典", engine)

    if result:
        TranslateCache.set(text, result)

    return result


def translate_batch(texts: List[str]) -> Dict[str, str]:
    """批量翻译。返回 {原文: 翻译} 映射。"""
    results: Dict[str, str] = {}
    api_texts: List[str] = []  # 需要调用 API 的

    for text in texts:
        if not text or not text.strip():
            continue
        text = text.strip()

        # 字典/缓存命中
        dict_result = _dict_lookup(text)
        if dict_result:
            results[text] = dict_result
            continue

        cached = TranslateCache.get(text)
        if cached:
            results[text] = cached
            continue

        api_texts.append(text)

    # 批量调用 API（逐条调用，但合并日志）
    if api_texts:
        logger.info("需要翻译 %d 条文本（API 调用）", len(api_texts))
        for i, text in enumerate(api_texts):
            result = translate_text(text)
            if result:
                results[text] = result
            else:
                # 翻译失败，保留原文
                results[text] = text
                logger.warning("翻译失败，保留原文: %s", text[:50])

            # 避免 API 频率限制
            if i < len(api_texts) - 1:
                time.sleep(0.5)

    return results
