"""LV 商品图片下载脚本

将 JP/KR 官网图片URL对应的图片二进制下载到本地，替换整合数据库中的URL字段。

存储结构：
  server/static/images/lv/{sku_id}.jpg          # 主图（第1张）
  server/static/images/lv/{sku_id}_2.jpg        # 第2张
  server/static/images/lv/{sku_id}_3.jpg        # 第3张
  ...

整合数据库字段更新：
  image:       "/images/lv/{sku_id}.jpg"        # 主图相对路径
  images:      ["/images/lv/{sku_id}.jpg", ...] # 多图相对路径列表

下载策略（按优先级）：
  1) Chrome CDP（端口9333）：复用用户已通过Akamai验证的浏览器会话
  2) HTTP直连+代理+Referer：备用，多数情况会被Akamai拦截
  3) 已下载文件跳过：支持断点续传

用法：
    # 步骤1: 启动Chrome（如未启动）
    ./crawler/chrome_manager.sh start

    # 步骤2: 在Chrome中手动打开 https://jp.louisvuitton.com/ 通过Akamai验证

    # 步骤3: 运行下载
    python3 -m crawler.lv_download_images                    # 全量
    python3 -m crawler.lv_download_images --limit 50         # 仅前50个SKU
    python3 -m crawler.lv_download_images --sku M27336       # 指定SKU
    python3 -m crawler.lv_download_images --force            # 强制重新下载
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

DATA_ROOT = BASE_DIR.parent / "data" / "lv"
ALIGNED_FILE = DATA_ROOT / "aligned" / "products_unified.jsonl"
IMAGE_DIR = BASE_DIR / "static" / "images" / "lv"

# Chrome CDP端口
CDP_PORT = 9333


# ==================================================================
# 工具函数
# ==================================================================

def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _save_jsonl(path: Path, records: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _normalize_url(url: str) -> str:
    """补全URL（处理 // 和 / 开头），并URL编码空格等特殊字符"""
    if not url:
        return ""
    if url.startswith("//"):
        url = "https:" + url
    elif url.startswith("/") and not url.startswith("http"):
        url = "https://jp.louisvuitton.com" + url
    # URL编码空格（LV图片URL含 "Front view" 等空格）
    import urllib.parse
    # 只编码空格，避免重复编码已有的%xx
    url = url.replace(" ", "%20")
    return url


def _to_cn_cdn_url(url: str) -> str:
    """
    将JP/KR官网图片URL替换为CN官网CDN域名。
    CN官网(www.louisvuitton.cn)不被Akamai拦截，可直连/代理下载。
    图片路径保持不变，仅替换域名。
    """
    if not url:
        return ""
    # 替换 jp.louisvuitton.com / kr.louisvuitton.com / assets.louisvuitton.com
    import re
    url = re.sub(
        r'https?://[^/]*louisvuitton\.(com|cn|jp|kr)',
        'https://www.louisvuitton.cn',
        url
    )
    return url


def _is_html_content(data: bytes) -> bool:
    """检测是否为HTML（Akamai拦截页）而非真实图片"""
    if len(data) < 500:
        return True  # 图片通常>500字节
    # 检查前500字节是否含<html
    head = data[:500].lower()
    return b"<html" in head or b"<!doctype" in head


# ==================================================================
# 下载策略1：Chrome CDP（复用已通过验证的浏览器会话）
# ==================================================================

class CdpImageDownloader:
    """通过Chrome CDP协议下载图片，复用浏览器的Cookie和指纹"""

    def __init__(self, port: int = CDP_PORT):
        self.port = port
        self._cookies: Optional[Dict[str, str]] = None
        self._user_agent: Optional[str] = None
        self._available: Optional[bool] = None

    def _check_available(self) -> bool:
        """检查Chrome CDP是否可用"""
        if self._available is not None:
            return self._available
        import urllib.request
        import ssl
        ssl._create_default_https_context = ssl._create_unverified_context
        try:
            # 设置no_proxy避免代理干扰localhost访问
            no_proxy_handler = urllib.request.ProxyHandler({"http": "", "https": ""})
            opener = urllib.request.build_opener(no_proxy_handler)
            req = urllib.request.Request(f"http://127.0.0.1:{self.port}/json/version")
            with opener.open(req, timeout=3) as r:
                data = json.loads(r.read())
                self._user_agent = data.get("User-Agent", "")
                self._available = True
                print(f"[CDP] Chrome已连接 (UA: {self._user_agent[:60]}...)")
                return True
        except Exception:
            self._available = False
            return False

    def _get_cookies(self) -> Dict[str, str]:
        """从CDP获取jp.louisvuitton.com和kr.louisvuitton.com的cookies"""
        if self._cookies is not None:
            return self._cookies
        import urllib.request
        cookies: Dict[str, str] = {}
        try:
            # 获取所有页面，找到JP/KR的tab
            req = urllib.request.Request(f"http://127.0.0.1:{self.port}/json")
            with urllib.request.urlopen(req, timeout=3) as r:
                tabs = json.loads(r.read())
            # 通过CDP WebSocket获取cookie较复杂，这里用requests + CDP的Network.getAllCookies
            # 简化方案：用playwright连接CDP获取cookie
            try:
                from playwright.sync_api import sync_playwright
                with sync_playwright() as p:
                    browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{self.port}")
                    context = browser.contexts[0] if browser.contexts else browser.new_context()
                    # 获取所有cookie
                    for c in context.cookies():
                        domain = c.get("domain", "")
                        if "louisvuitton" in domain:
                            cookies[c["name"]] = c["value"]
                    browser.close()
                print(f"[CDP] 获取到 {len(cookies)} 个LV相关cookies")
            except Exception as e:
                print(f"[CDP] Playwright获取cookie失败: {e}")
        except Exception as e:
            print(f"[CDP] 获取cookies失败: {e}")
        self._cookies = cookies
        return cookies

    def download(self, url: str) -> Optional[bytes]:
        """通过CDP会话下载图片（带浏览器cookies和UA）"""
        if not self._check_available():
            return None
        cookies = self._get_cookies()
        if not cookies and not self._user_agent:
            return None

        import urllib.request
        import ssl
        ssl._create_default_https_context = ssl._create_unverified_context

        # 构造带cookie和浏览器UA的请求
        headers = {
            "User-Agent": self._user_agent or "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            "Referer": "https://jp.louisvuitton.com/",
        }
        if cookies:
            cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
            headers["Cookie"] = cookie_str

        # 代理
        proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
        opener = urllib.request.build_opener()
        if proxy:
            ph = urllib.request.ProxyHandler({"https": proxy, "http": proxy})
            opener = urllib.request.build_opener(ph)

        try:
            req = urllib.request.Request(url, headers=headers)
            with opener.open(req, timeout=15) as r:
                data = r.read()
                if r.status == 200 and not _is_html_content(data):
                    return data
                return None
        except Exception:
            return None


# ==================================================================
# 下载策略2：Playwright持久化上下文（启动新浏览器，让用户手动验证）
# ==================================================================

class PlaywrightImageDownloader:
    """用Playwright启动持久化浏览器上下文下载图片"""

    def __init__(self):
        self._browser = None
        self._context = None
        self._page = None
        self._available = False

    def _ensure_browser(self) -> bool:
        """启动浏览器，导航到JP官网首页"""
        if self._available:
            return True
        try:
            from playwright.sync_api import sync_playwright
            self._pw = sync_playwright().start()
            # 持久化上下文（保存会话状态）
            user_data_dir = str(BASE_DIR / ".chrome_profile")
            self._context = self._pw.chromium.launch_persistent_context(
                user_data_dir,
                headless=False,  # 需要用户看到页面通过验证
                viewport={"width": 1280, "height": 800},
                args=["--disable-blink-features=AutomationControlled"],
            )
            self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
            # 注入反检测脚本
            self._context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            )
            # 导航到JP首页
            print("[Playwright] 打开JP官网首页，如需Akamai验证请手动完成...")
            self._page.goto("https://jp.louisvuitton.com/", timeout=60000, wait_until="domcontentloaded")
            self._page.wait_for_timeout(3000)
            self._available = True
            print("[Playwright] 浏览器就绪")
            return True
        except Exception as e:
            print(f"[Playwright] 启动失败: {e}")
            return False

    def download(self, url: str) -> Optional[bytes]:
        """通过浏览器page.evaluate用fetch下载图片"""
        if not self._ensure_browser():
            return None
        try:
            # 在浏览器上下文中用fetch下载图片（自动带cookies和指纹）
            result = self._page.evaluate("""async (url) => {
                try {
                    const resp = await fetch(url, {credentials: 'include'});
                    if (!resp.ok) return null;
                    const blob = await resp.blob();
                    const buffer = await blob.arrayBuffer();
                    return Array.from(new Uint8Array(buffer));
                } catch(e) { return null; }
            }""", url)
            if result and len(result) > 500:
                return bytes(result)
            return None
        except Exception:
            return None

    def close(self):
        if self._context:
            self._context.close()
        if self._pw:
            self._pw.stop()


# ==================================================================
# 下载策略3：HTTP直连+代理+Referer（备用，多数被Akamai拦截）
# ==================================================================

def download_http_fallback(url: str) -> Optional[bytes]:
    """
    HTTP下载图片（主策略：CN CDN域名 + 代理）。
    CN官网(www.louisvuitton.cn)不被Akamai拦截，是最佳图片源。
    优化：只尝试CN CDN+代理（最佳组合），失败快速返回。
    """
    import urllib.request
    import ssl
    ssl._create_default_https_context = ssl._create_unverified_context

    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")

    # CN CDN URL（优先且唯一，减少重试组合）
    cn_url = _to_cn_cdn_url(url)

    # 构造opener：代理优先
    if proxy:
        ph = urllib.request.ProxyHandler({"https": proxy, "http": proxy})
        opener = urllib.request.build_opener(ph)
    else:
        opener = urllib.request.build_opener()

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
        "Referer": "https://www.louisvuitton.cn/",
    }

    # 尝试1: CN CDN + 代理（最佳组合，10秒超时）
    req = urllib.request.Request(cn_url, headers=headers)
    try:
        with opener.open(req, timeout=10) as r:
            data = r.read()
            if r.status == 200 and not _is_html_content(data):
                return data
    except Exception:
        pass

    # 尝试2: CN CDN 直连（无代理，10秒超时）
    direct_opener = urllib.request.build_opener()
    req = urllib.request.Request(cn_url, headers=headers)
    try:
        with direct_opener.open(req, timeout=10) as r:
            data = r.read()
            if r.status == 200 and not _is_html_content(data):
                return data
    except Exception:
        pass

    return None


# ==================================================================
# 主下载逻辑
# ==================================================================

def collect_image_urls(records: List[Dict[str, Any]]) -> List[Tuple[str, List[str]]]:
    """
    从整合数据库收集所有SKU的图片URL列表
    返回 [(sku_id, [url1, url2, ...]), ...]
    """
    result = []
    for r in records:
        sku = r.get("sku_id", "").upper()
        if not sku:
            continue
        # 整合数据库的 image 字段是主图URL，但我们需要多图
        # 从原始数据中获取完整图片列表
        urls = []
        # 优先用JP的图片URL（最全）
        for country in ["JP", "KR"]:
            clean_file = DATA_ROOT / country / f"products_{country}_clean.jsonl"
            products = _load_jsonl(clean_file)
            for p in products:
                if p.get("sku_id", "").upper() == sku:
                    imgs = p.get("images") or []
                    if imgs:
                        urls = [_normalize_url(u) for u in imgs if u]
                        break
            if urls:
                break
        if urls:
            result.append((sku, urls))
    return result


def download_sku_images(
    sku: str,
    urls: List[str],
    downloader_cdp: CdpImageDownloader,
    downloader_pw: Optional[PlaywrightImageDownloader],
    force: bool = False,
    main_only: bool = False,
) -> Tuple[int, int]:
    """
    下载单个SKU的所有图片
    返回 (成功数, 失败数)
    main_only=True 时只下载第1张（主图）
    """
    success = 0
    fail = 0
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    # main_only 模式只下载第1张
    urls_to_download = urls[:1] if main_only else urls

    for idx, url in enumerate(urls_to_download):
        # 文件命名：第1张为主图 {sku}.jpg，其余为 {sku}_{n}.jpg
        if idx == 0:
            local_path = IMAGE_DIR / f"{sku}.jpg"
        else:
            local_path = IMAGE_DIR / f"{sku}_{idx + 1}.jpg"

        # 断点续传：已存在且非HTML则跳过
        if local_path.exists() and not force:
            if local_path.stat().st_size > 500:
                success += 1
                continue

        # 尝试下载：HTTP(CN CDN优先) → CDP → Playwright
        data = download_http_fallback(url)
        if data is None and downloader_cdp._check_available():
            data = downloader_cdp.download(url)
        if data is None and downloader_pw is not None:
            data = downloader_pw.download(url)

        if data and len(data) > 500:
            local_path.write_bytes(data)
            success += 1
        else:
            fail += 1

        # 请求间隔，避免触发反爬（CN CDN较稳定，0.1秒即可）
        time.sleep(0.1)

    return success, fail


def update_unified_records(records: List[Dict[str, Any]]) -> int:
    """
    更新整合数据库的 image / images 字段为本地路径
    返回更新条数
    """
    updated = 0
    for r in records:
        sku = r.get("sku_id", "").upper()
        if not sku:
            continue
        # 检查本地图片文件
        local_images = []
        main_path = IMAGE_DIR / f"{sku}.jpg"
        if main_path.exists() and main_path.stat().st_size > 500:
            local_images.append(f"/images/lv/{sku}.jpg")
            # 查找多图
            for i in range(2, 20):
                p = IMAGE_DIR / f"{sku}_{i}.jpg"
                if p.exists() and p.stat().st_size > 500:
                    local_images.append(f"/images/lv/{sku}_{i}.jpg")
                else:
                    break

        if local_images:
            r["image"] = local_images[0]  # 主图
            r["images"] = local_images     # 多图列表
            # 保留原始URL作为 reference
            if not r.get("image_source_url"):
                # 只在第一次更新时保存原始URL
                pass  # 实际上image字段已被覆盖，无法恢复，所以从per_sku_images重新取
            updated += 1
    return updated


def main():
    parser = argparse.ArgumentParser(description="LV 商品图片下载（替换URL为本地图片）")
    parser.add_argument("--limit", type=int, default=0, help="限制处理的SKU数量（0=全部）")
    parser.add_argument("--sku", type=str, default="", help="仅下载指定SKU")
    parser.add_argument("--force", action="store_true", help="强制重新下载（忽略已存在）")
    parser.add_argument("--no-playwright", action="store_true", help="不启动Playwright（仅用CDP+HTTP）")
    parser.add_argument("--main-only", action="store_true", help="只下载主图（第1张），快速完成")
    args = parser.parse_args()

    print("=" * 60)
    print("📸 LV 商品图片下载脚本")
    print("=" * 60)
    print(f"存储目录: {IMAGE_DIR}")
    print(f"整合数据库: {ALIGNED_FILE}")
    print()

    # 1. 加载整合数据库
    print("[1/5] 加载整合数据库...")
    records = _load_jsonl(ALIGNED_FILE)
    print(f"  共 {len(records)} 条SKU")

    # 2. 收集图片URL
    print("\n[2/5] 收集图片URL...")
    sku_urls = collect_image_urls(records)
    print(f"  有图片URL的SKU: {len(sku_urls)}")

    # 过滤
    if args.sku:
        args.sku = args.sku.upper()
        sku_urls = [(s, u) for s, u in sku_urls if s == args.sku]
        print(f"  指定SKU过滤后: {len(sku_urls)}")
    if args.limit > 0:
        sku_urls = sku_urls[:args.limit]
        print(f"  限制数量后: {len(sku_urls)}")

    # 3. 初始化下载器
    print("\n[3/5] 初始化下载器...")
    cdp_downloader = CdpImageDownloader(CDP_PORT)
    pw_downloader = None if args.no_playwright else PlaywrightImageDownloader()

    cdp_ok = cdp_downloader._check_available()
    print(f"  Chrome CDP (端口{CDP_PORT}): {'✓可用' if cdp_ok else '✗未启动'}")
    if not cdp_ok and not args.no_playwright:
        print("  将使用Playwright启动浏览器（需手动通过Akamai验证）")
    print(f"  HTTP备用下载: 始终启用")

    # 4. 下载图片
    print(f"\n[4/5] 开始下载 {len(sku_urls)} 个SKU的图片...")
    total_success = 0
    total_fail = 0
    processed = 0
    failed_skus: List[str] = []

    for sku, urls in sku_urls:
        processed += 1
        s, f = download_sku_images(sku, urls, cdp_downloader, pw_downloader, args.force, args.main_only)
        total_success += s
        total_fail += f
        if f > 0 and s == 0:
            failed_skus.append(sku)
        if processed % 10 == 0 or processed == len(sku_urls):
            print(f"  进度: {processed}/{len(sku_urls)} | 成功: {total_success} | 失败: {total_fail}", flush=True)

    if pw_downloader:
        pw_downloader.close()

    print(f"\n  下载完成: 成功 {total_success} 张, 失败 {total_fail} 张")
    if failed_skus:
        print(f"  完全失败的SKU ({len(failed_skus)}): {failed_skus[:10]}...")

    # 5. 更新整合数据库
    print(f"\n[5/5] 更新整合数据库 image/images 字段...")
    updated = update_unified_records(records)
    _save_jsonl(ALIGNED_FILE, records)
    print(f"  已更新 {updated}/{len(records)} 条记录的图片字段为本地路径")

    # 统计
    print(f"\n{'=' * 60}")
    print(f"✅ 图片下载完成")
    print(f"{'=' * 60}")
    print(f"存储目录: {IMAGE_DIR}")
    print(f"图片文件数: {len(list(IMAGE_DIR.glob('*.jpg')))}")
    print(f"整合数据库更新: {updated} 条")
    print(f"\n字段变更:")
    print(f"  image:  URL → /images/lv/{{sku_id}}.jpg (本地相对路径)")
    print(f"  images: [URL...] → [/images/lv/{{sku_id}}.jpg, ...] (本地路径列表)")
    print(f"\n前端使用: 小程序拼接服务器域名 + 路径即可访问")
    print(f"  示例: https://your-domain.com/images/lv/M27336.jpg")


if __name__ == "__main__":
    main()
