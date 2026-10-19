#!/usr/bin/env python3
"""
生成微信小程序 TabBar 图标
每个选项有未选中(灰色)和选中(橙色)两个版本
"""
import struct
import zlib
import os

SIZE = 81  # 81px，符合微信要求的 81x81
OUT_DIR = '/Users/huxiao/Public/测试项目-1-26.6.27/images/tab'

# 颜色定义
GRAY = (153, 153, 153, 255)
ORANGE = (255, 107, 0, 255)
WHITE = (255, 255, 255, 255)
TRANSPARENT = (0, 0, 0, 0)

def png_chunk(chunk_type, data):
    """生成PNG块"""
    chunk = chunk_type + data
    crc = zlib.crc32(chunk) & 0xffffffff
    return struct.pack('>I', len(data)) + chunk + struct.pack('>I', crc)

def create_png_header():
    """PNG文件头 + IHDR块"""
    ihdr_data = struct.pack('>IIBBBBB',
        SIZE, SIZE,   # 宽高
        8,            # 位深 8
        6,            # 颜色类型 6 (RGBA)
        0, 0, 0      # 压缩/过滤/隔行
    )
    return b'\x89PNG\r\n\x1a\n' + png_chunk(b'IHDR', ihdr_data)

def pixels_to_png_data(pixels):
    """将像素数组转换为PNG原始数据"""
    raw_rows = []
    for row in pixels:
        raw_rows.append(b'\x00' + b''.join(struct.pack('BBBB', r, g, b, a) for r, g, b, a in row))
    raw_data = b''.join(raw_rows)
    compressed = zlib.compress(raw_data, 9)
    return png_chunk(b'IDAT', compressed) + png_chunk(b'IEND', b'')

def set_pixel(pixels, x, y, color):
    """设置像素 (带边界检查)"""
    if 0 <= x < SIZE and 0 <= y < SIZE:
        pixels[y][x] = color

def fill_circle(pixels, cx, cy, r, color):
    """绘制实心圆"""
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx*dx + dy*dy <= r*r:
                set_pixel(pixels, cx + dx, cy + dy, color)

def fill_rect(pixels, x, y, w, h, color):
    """绘制实心矩形"""
    for dy in range(h):
        for dx in range(w):
            set_pixel(pixels, x + dx, y + dy, color)

def fill_round_rect(pixels, x, y, w, h, r, color):
    """绘制圆角矩形"""
    # 四角
    for dy in range(-r, 0):
        for dx in range(-r, 0):
            if dx*dx + dy*dy <= r*r:
                set_pixel(pixels, x + dx, y + dy, color)
                set_pixel(pixels, x + w - 1 + dx, y + dy, color)
                set_pixel(pixels, x + dx, y + h - 1 + dy, color)
                set_pixel(pixels, x + w - 1 + dx, y + h - 1 + dy, color)
    # 主体
    fill_rect(pixels, x, y + r, w, h - 2*r, color)
    fill_rect(pixels, x + r, y, w - 2*r, h, color)

def fill_triangle(pixels, x1, y1, x2, y2, x3, y3, color):
    """绘制实心三角形"""
    min_x = min(x1, x2, x3)
    max_x = max(x1, x2, x3)
    min_y = min(y1, y2, y3)
    max_y = max(y1, y2, y3)
    for y in range(min_y, max_y + 1):
        for x in range(min_x, max_x + 1):
            # 重心法判断点是否在三角形内
            d1 = sign(x, y, x1, y1, x2, y2)
            d2 = sign(x, y, x2, y2, x3, y3)
            d3 = sign(x, y, x3, y3, x1, y1)
            has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
            has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
            if not (has_neg and has_pos):
                set_pixel(pixels, x, y, color)

def sign(x, y, x1, y1, x2, y2):
    return (x - x2) * (y1 - y2) - (x1 - x2) * (y - y2)

def draw_horizontal_line(pixels, x, y, length, color):
    for i in range(length):
        set_pixel(pixels, x + i, y, color)

def draw_vertical_line(pixels, x, y, length, color):
    for i in range(length):
        set_pixel(pixels, x, y + i, color)

# ============================================================
# 图标设计
# ============================================================

def draw_icon_coupon(pixels, color):
    """优惠图标 - 标签/优惠券样式"""
    # 主体标签形状
    fill_round_rect(pixels, 10, 24, 61, 38, 6, color)
    # 左侧圆形装饰（模拟撕边效果）
    fill_circle(pixels, 10, 43, 12, TRANSPARENT)
    fill_circle(pixels, 10, 43, 8, (255, 255, 255, 255))
    # 内部百分比符号
    # % 字 - 两个小圆 + 一条斜线
    fill_circle(pixels, 30, 33, 4, WHITE)
    fill_circle(pixels, 50, 51, 4, WHITE)
    # 斜线
    for i in range(26):
        x = 25 + i
        y = 29 + int(i * 0.85)
        set_pixel(pixels, x, y, WHITE)
        set_pixel(pixels, x + 1, y, WHITE)
    # 右侧小圆装饰
    fill_circle(pixels, 65, 35, 3, WHITE)
    fill_circle(pixels, 67, 50, 3, WHITE)

def draw_icon_exchange(pixels, color):
    """汇率图标 - 双向箭头交换"""
    cx, cy = 40, 40
    # 上箭头 (从右向左)
    for i in range(14):
        y = 20 + i
        w = 14 - i
        fill_rect(pixels, cx - w//2, y, w, 1, color)
    fill_triangle(pixels, cx - 11, 20, cx + 11, 20, cx, 8, color)

    # 下箭头 (从左向右)
    for i in range(14):
        y = 60 - i
        w = 14 - i
        fill_rect(pixels, cx - w//2, y, w, 1, color)
    fill_triangle(pixels, cx - 11, 60, cx + 11, 60, cx, 72, color)

def draw_icon_compare(pixels, color):
    """比价图标 - 三条价格柱状图"""
    # 三根柱子
    fill_round_rect(pixels, 14, 42, 12, 24, 3, color)   # 短
    fill_round_rect(pixels, 34, 28, 12, 38, 3, color)   # 中
    fill_round_rect(pixels, 54, 14, 12, 52, 3, color)   # 长（最高）
    # 底部基准线
    fill_rect(pixels, 10, 66, 60, 3, color)

def draw_icon_buyer(pixels, color):
    """买手图标 - 购物袋 + 手"""
    # 购物袋主体
    fill_round_rect(pixels, 18, 36, 44, 34, 5, color)
    # 袋口
    fill_rect(pixels, 14, 32, 52, 6, color)
    # 提手
    fill_round_rect(pixels, 28, 16, 24, 18, 5, color)
    fill_round_rect(pixels, 32, 16, 16, 12, 5, TRANSPARENT)
    # 袋内物品（小方块）
    fill_round_rect(pixels, 26, 46, 10, 12, 2, WHITE)
    fill_round_rect(pixels, 44, 50, 10, 8, 2, WHITE)

def draw_icon_profile(pixels, color):
    """我的图标 - 人物头像"""
    # 头部（圆形）
    fill_circle(pixels, 40, 26, 14, color)
    # 身体（半圆/梯形）
    fill_triangle(pixels, 16, 72, 64, 72, 40, 44, color)
    # 简化身体 - 用圆角矩形代替
    fill_round_rect(pixels, 20, 44, 40, 30, 10, color)

# ============================================================
# 主程序
# ============================================================

def generate_icon(name, draw_func, inactive_color, active_color):
    """生成一对图标"""
    os.makedirs(OUT_DIR, exist_ok=True)

    # 未选中状态 - 无后缀
    pixels = [[TRANSPARENT] * SIZE for _ in range(SIZE)]
    draw_func(pixels, inactive_color)
    png_data = create_png_header() + pixels_to_png_data(pixels)
    filepath = os.path.join(OUT_DIR, f'{name}.png')
    with open(filepath, 'wb') as f:
        f.write(png_data)
    print(f'  ✓ {name}.png (gray)')

    # 选中状态 - _active 后缀
    pixels = [[TRANSPARENT] * SIZE for _ in range(SIZE)]
    draw_func(pixels, active_color)
    png_data = create_png_header() + pixels_to_png_data(pixels)
    filepath = os.path.join(OUT_DIR, f'{name}_active.png')
    with open(filepath, 'wb') as f:
        f.write(png_data)
    print(f'  ✓ {name}_active.png (orange)')

# 图标映射
ICONS = [
    ('coupon',  draw_icon_coupon),    # 优惠
    ('exchange', draw_icon_exchange), # 汇率
    ('compare',  draw_icon_compare),  # 比价
    ('buyer',    draw_icon_buyer),    # 买手
    ('profile',  draw_icon_profile),  # 我的
]

print('开始生成 TabBar 图标...')
for name, draw_func in ICONS:
    print(f'  生成 {name}...')
    generate_icon(name, draw_func, GRAY, ORANGE)

print(f'\n完成！共生成 {len(ICONS) * 2} 个图标')
print(f'输出目录: {OUT_DIR}')
