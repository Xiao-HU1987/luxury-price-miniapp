"""LV 爬虫配置

集中管理：
- CDP 调试端口
- 代理 / UA
- 目标 URL 模板
- 关键词过滤（响应 URL / 响应体中是否携带商品字段）
- 抓取节奏（停留、滚动、等待）

注意：所有默认值都是可调参数。第一次实际抓取 LV 时，需要根据
playwright 监听到的真实响应 URL 调整 `RESPONSE_URL_KEYWORDS` 与
`JSON_PRODUCT_HINTS`，再细化解析器。
"""
from pathlib import Path

# ==================== CDP 与代理 ====================
CDP_ENDPOINT = "http://127.0.0.1:9333"

# Chrome 启动命令（终端执行，需要先关闭现有 Chrome）
CHROME_LAUNCH_CMD = (
    'open -n -a "Google Chrome" --args '
    '--remote-debugging-port=9333 '
    '--proxy-server="http://127.0.0.1:7890"'
)

# 代理配置（给 playwright.launch 模式使用）
PROXY_SERVER = "http://127.0.0.1:7890"

# UA / 视口（playwright.launch 模式）
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
VIEWPORT = {"width": 1920, "height": 1080}
LOCALE = "ja-JP"
TIMEZONE_ID = "Asia/Tokyo"

# launch 模式下 Chrome 启动参数（反自动化指纹）
CHROME_STEALTH_ARGS = [
    "--proxy-server=http://127.0.0.1:7890",
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-web-security",
    "--disable-features=IsolateOrigins,site-per-process",
]

# 系统 Chrome 可执行文件路径（macOS）
CHROME_EXECUTABLE = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# ==================== 目标 URL ====================
LV_BASE_URL = "https://jp.louisvuitton.com"

# 分类页（ウィメンズ バッグ）— 用于抓取商品列表
CATEGORY_URL = (
    "https://jp.louisvuitton.com/jpn-jp/women/handbags/_/N-tfr7qdp"
)

# 商品详情页 URL 模板（用 LV 内部 SKU 编号替换）
PRODUCT_DETAIL_URL_TEMPLATE = (
    "https://jp.louisvuitton.com/jpn-jp/products/{slug}"
)

# 商品库存查询 API（按 SKU 与门店 ID 查库存）
# 占位 — 实际值需要在第一次抓取时从 network 面板确认
INVENTORY_API_TEMPLATE = (
    "https://api.louisvuitton.com/api/jpn-jp/catalog/inventory/{sku_id}"
)

# ==================== 抓取节奏（真人节奏优化版 2026-08-06）====================
# 列表页加载后等待时间（毫秒）：列表页内容少，8秒足够，但确保懒加载完成
LIST_PAGE_WAIT_MS = 8000
# 详情页加载后等待时间（毫秒）：模拟真人看完图片/价格再滚动的时间
# 之前 8000ms 太匆忙；现在 12-18 秒让页面完全渲染 + 模拟看图片
DETAIL_PAGE_WAIT_MS = 15000
# 两次请求之间的间隔（秒）— 已改为随机区间，此值为最小值
REQUEST_INTERVAL_MIN_SEC = 3.0
REQUEST_INTERVAL_MAX_SEC = 8.0
# 兼容旧代码
REQUEST_INTERVAL_SEC = 3.0

# 模拟用户行为：滚动到页底（部分站点懒加载）
# 真人滚动节奏：不会匀速800px/400ms，改成缓慢多步、中间停留
SCROLL_TO_BOTTOM = True
SCROLL_STEP_PX = 300         # 每步滚动距离更小，更像人
SCROLL_INTERVAL_MS = 1200    # 每步停顿更长，模拟看内容

# ==================== 反爬策略（真人节奏优化版 2026-08-06）====================
# 分批爬取：每批商品数量，超过后关闭 tab、清除 cookies、冷却等待
BATCH_SIZE = 15
# 批次间冷却时间（秒）— 随机区间
BATCH_COOLDOWN_MIN_SEC = 180    # 3 分钟
BATCH_COOLDOWN_MAX_SEC = 300    # 5 分钟
# 每隔 N 个商品插入一次长暂停（模拟用户思考）
LONG_PAUSE_EVERY = 3            # 之前5个太长；每3个停一次更符合真人节奏
LONG_PAUSE_MIN_SEC = 45         # 45 秒 - 喝口水、翻评论
LONG_PAUSE_MAX_SEC = 120        # 2 分钟 - 被打断处理别的事
# 被反爬拦截后的等待时间（秒）
BLOCK_COOLDOWN_SEC = 600        # 10 分钟
# 连续被拦截多少次后放弃
MAX_CONSECUTIVE_BLOCKS = 3
# 偶尔回退到列表页浏览（模拟真实用户路径）
BROWSE_BACK_EVERY = 8           # 每 8 个商品回退一次列表页
# 进度文件路径
PROGRESS_FILE = Path(__file__).resolve().parent / "crawl_progress.json"

# ==================== 响应过滤 ====================
# 仅处理 louisvuitton.com 域名下的响应
RESPONSE_DOMAIN_ALLOWLIST = [
    "louisvuitton.com",
    "api.louisvuitton.com",
]

# 调试模式：保存所有 LV 域名的 JSON 响应（即使没匹配关键词）
# 第一次抓取时建议开启，便于事后分析 LV 真实的 API 结构
SAVE_ALL_LV_RESPONSES = True

# URL 关键词：响应 URL 包含任一关键词时尝试解析为商品数据
# 实际可观察到的关键词（结合历史脚本与初次抓取后调整）：
# - 包含 product / catalog / sku / stock / availability / inventory 等
# - 包含 /products/ （历史脚本已验证）
# - 包含 /graphql （LV 可能用 GraphQL）
RESPONSE_URL_KEYWORDS = [
    "product",
    "catalog",
    "sku",
    "stock",
    "availability",
    "inventory",
    "searchresult",
    "plp",  # Product Listing Page
    "pdp",  # Product Detail Page
    "/products/",
    "/graphql",
    "store",
    "/api/",
    "category",
    "listing",
    "lvuapi",  # LV 内部 API 域名
    "dam/",  # LV 数字资产管理系统
]

# JSON 字段提示：响应体中若出现以下任一字段，认为该 JSON 可能含商品数据
# （用于应对 URL 不带关键词但 payload 含商品信息的情况）
JSON_PRODUCT_HINTS = [
    "productId",
    "product_id",
    "skuId",
    "sku_id",
    "articleNumber",
    "reference",
    "LVReference",
    "title",
    "name",
    "price",
    "thumbnail",
    "inStock",
    "stock",
]

# ==================== 落盘 ====================
# 原始响应保存目录（用于离线分析未识别的 JSON 结构）
RAW_CAPTURE_DIR = Path(__file__).resolve().parent / "raw_captures"
# 单次保存的最大 JSON 体积（字节），避免把图片 base64 之类的大块数据写盘
RAW_CAPTURE_MAX_BYTES = 256 * 1024  # 256KB
# 是否落盘
RAW_CAPTURE_ENABLED = True

# ==================== 数据库 ====================
# 抓取目标品牌 / 品类 — 必须与 init_data.py 中的 seed 数据一致
LV_BRAND_ID = "LV"
LV_BRAND_NAME = "LV"
LV_BRAND_NAME_CN = "路易威登"
LV_COUNTRY = "JP"
LV_CURRENCY = "JPY"
LV_DEFAULT_CATEGORY_ID = "handbags"

# 干跑模式：只解析与打印，不写库
DRY_RUN = False

# 增量模式：默认启用，跳过数据库中已有的商品
INCREMENTAL = True
