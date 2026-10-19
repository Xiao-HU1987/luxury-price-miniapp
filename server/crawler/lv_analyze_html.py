"""分析已保存的弹窗HTML，提取弹窗DOM结构，确认登录门禁/库存逻辑。"""
import re
import sys
from pathlib import Path

f = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/lv_diag_out/step2_result.html")
html = f.read_text(encoding="utf-8")


def find_balanced(s, start):
    """从 start 处找 <div 的完整开闭块（粗略，按标签栈）。"""
    i = s.find(">", start)
    if i < 0:
        return None
    return i


# 提取 .lv-locate-in-store 弹窗节点
m = re.search(r'class="[^"]*lv-locate-in-store[^"]*"', html)
print("=== 弹窗锚点 ===")
print(f"找到 .lv-locate-in-store: {bool(m)}")
if m:
    # 从锚点向前找最近的 <div 或 <aside 起始
    anchor = m.start()
    prev = html.rfind("<", 0, anchor)
    print(f"锚点前的标签起始: {html[prev:anchor+40]}")

# 查找所有 class 含 store 的节点
print("\n=== 含 'store' 的 class 节点（去重） ===")
classes = set(re.findall(r'class="([^"]*store[^"]*)"', html))
for c in sorted(classes):
    # 只显示有意义的（含 store 的类）
    if 'store' in c:
        print(f"  .{c.split(' ')[0] if ' ' in c else c}")

# 查找登录/会话相关提示
print("\n=== 登录/会话/错误提示关键词 ===")
for kw in ["ログイン", "ログインが必要", "サインイン", "会員", "ようこそ",
           "見つかりません", "該当", "エラー", "エラーが発生", "少々お待ち",
           "読み込み", "loading", "ローディング", "在庫状況を確認するには"]:
    if kw.lower() in html:
        idx = html.find(kw)
        print(f"  '{kw}': ...{html[max(0,idx-60):idx+80]}...")

# 查找可能的内嵌JSON数据（门店/库存）
print("\n=== 内嵌 JSON 数据线索 ===")
for kw in ["storePosition", "storeCode", "availability", "inventory", "storeName",
           "__NUXT__", "__NEXT_DATA__", "posList", "storeList", "geolocation"]:
    if kw in html:
        idx = html.find(kw)
        print(f"  '{kw}' 出现于 # {idx}")