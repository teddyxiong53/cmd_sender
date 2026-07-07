#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cmd_sender 图标生成器
根据 icon.svg 生成 .ico 文件（需要 Pillow 库）

用法:
    pip install Pillow
    python generate_icon.py

参考颜色:
    主色: #0078D7 (Windows 蓝)
    箭头色: #FFD700 (金色)
"""

import os
import sys
import struct
import zlib
import io

# ============================================================
# PNG 编码（无需 Pillow，标准库即可生成 32x32 的 PNG 图标）
# ============================================================

def create_png(width, height, pixels):
    """
    从像素数据创建 PNG 文件字节

    pixels: 长度为 width * height 的列表，
            每个元素为 (R, G, B, A) 元组（各 0-255）
    """
    def make_chunk(chunk_type, data):
        chunk = chunk_type + data
        crc = struct.pack(">I", zlib.crc32(chunk) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + chunk + crc

    # IHDR
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)  # 8-bit RGBA

    # IDAT - 过滤 + 压缩
    raw_data = b""
    for y in range(height):
        raw_data += b"\x00"  # filter byte: None
        for x in range(width):
            r, g, b, a = pixels[y * width + x]
            raw_data += struct.pack("BBBB", r, g, b, a)

    compressed = zlib.compress(raw_data)

    # IEND
    png = b"\x89PNG\r\n\x1a\n"
    png += make_chunk(b"IHDR", header)
    png += make_chunk(b"IDAT", compressed)
    png += make_chunk(b"IEND", b"")
    return png


def create_ico(sizes, icon_data_list):
    """
    从多个尺寸的 PNG 数据生成 .ico 文件

    sizes: [(width, height), ...]
    icon_data_list: [png_bytes, ...]
    """
    count = len(sizes)
    # Header: reserved(2) + type=1(2) + count(2)
    header = struct.pack("<HHH", 0, 1, count)

    # Directory entries + image data
    dir_entries = b""
    image_data = b""
    data_offset = 6 + count * 16  # header + directory entries

    for i, (w, h) in enumerate(sizes):
        png_bytes = icon_data_list[i]
        # Directory entry: w, h, palette, reserved, planes, bpp, size, offset
        icon_w = w if w < 256 else 0
        icon_h = h if h < 256 else 0
        dir_entries += struct.pack(
            "<BBBBHHII",
            icon_w, icon_h, 0, 0,  # width, height, palette, reserved
            1, 32,                 # planes, bpp
            len(png_bytes),        # size
            data_offset,           # offset
        )
        image_data += png_bytes
        data_offset += len(png_bytes)

    return header + dir_entries + image_data


# ============================================================
# cmd_sender 图标像素数据 (32x32 和 64x64)
# ============================================================

def make_cmd_sender_pixels(size):
    """
    生成 cmd_sender 图标的 RGBA 像素数据
    - 蓝色圆角矩形背景
    - 白色 >_ 命令提示符
    - 金色发送箭头
    """
    pixels = []
    bg = (0, 120, 215, 255)       # #0078D7
    bg_dark = (0, 90, 158, 255)   # #005A9E
    text_color = (255, 255, 255, 255)
    arrow_color = (255, 215, 0, 255)  # #FFD700
    transparent = (0, 0, 0, 0)

    radius = size * 0.19  # 圆角半径
    cx, cy = size // 2, size // 2

    for y in range(size):
        for x in range(size):
            # 判断是否在圆角矩形内
            dx = x - cx
            dy = y - cy

            # 到四个角的距离
            dist = 0
            if x < cx and y < cy:
                dist = ((x - radius) ** 2 + (y - radius) ** 2) ** 0.5
                in_rect = x >= radius and y >= radius
            elif x >= cx and y < cy:
                dist = ((x - (size - 1 - radius)) ** 2 + (y - radius) ** 2) ** 0.5
                in_rect = x <= size - 1 - radius and y >= radius
            elif x < cx and y >= cy:
                dist = ((x - radius) ** 2 + (y - (size - 1 - radius)) ** 2) ** 0.5
                in_rect = x >= radius and y <= size - 1 - radius
            else:
                dist = ((x - (size - 1 - radius)) ** 2 + (y - (size - 1 - radius)) ** 2) ** 0.5
                in_rect = x <= size - 1 - radius and y <= size - 1 - radius

            # 抗锯齿边缘
            if in_rect:
                pixel = bg
            elif dist < radius + 0.7:
                # 渐变边缘
                alpha = max(0, min(255, int((radius + 0.7 - dist) * 255)))
                if alpha > 0:
                    pixel = (bg[0], bg[1], bg[2], alpha)
                else:
                    pixel = transparent
            else:
                pixel = transparent

            # 渐变效果 (从左上到右下)
            blend = (x + y) / (2 * size)
            if pixel[3] > 0:
                r = int(pixel[0] * (1 - blend * 0.3) + bg_dark[0] * blend * 0.3)
                g = int(pixel[1] * (1 - blend * 0.3) + bg_dark[1] * blend * 0.3)
                b = int(pixel[2] * (1 - blend * 0.3) + bg_dark[2] * blend * 0.3)
                pixel = (r, g, b, pixel[3])

            # 绘制 ">_" 文本 (用像素模拟)
            if pixel[3] > 0:
                # 字符 '>' 的位置
                char_x = int(size * 0.20)
                char_y = int(size * 0.30)
                char_h = int(size * 0.5)
                char_w = int(size * 0.20)
                thick = max(1, size // 16)

                # '>' 字符 - 用两个线段组成
                # 上斜线: 从 (x0, y0) 到 (x0+char_w, y_mid)
                # 下斜线: 从 (x0, y_mid) 到 (x0+char_w, y0+char_h)
                mid_y = char_y + char_h // 2
                end_x = char_x + char_w

                # 上斜线
                if mid_y - char_y > 0:
                    t = (y - char_y) / (mid_y - char_y)
                    line_x = char_x + t * char_w
                    for dx in range(-thick, thick + 1):
                        if abs(x - (line_x + dx)) <= 0.5:
                            pixel = text_color

                # 下斜线
                if char_y + char_h - mid_y > 0:
                    t = (y - mid_y) / (char_y + char_h - mid_y)
                    line_x = char_x + (1 - t) * char_w
                    for dx in range(-thick, thick + 1):
                        if abs(x - (line_x + dx)) <= 0.5:
                            pixel = text_color

                # '_' (下划线) 在 '>' 右侧
                underscore_x = char_x + char_w + int(size * 0.08)
                underscore_y = char_y + char_h + thick
                if (underscore_x <= x <= underscore_x + int(size * 0.15)
                        and abs(y - underscore_y) <= thick - 0.3):
                    pixel = text_color

                # 右下角发送箭头 (金色)
                arrow_cx = int(size * 0.70)
                arrow_cy = int(size * 0.60)
                arrow_size = int(size * 0.28)

                # 箭头形状: 方形底 + 三角形尖
                # 箭头身体
                body_left = arrow_cx - arrow_size // 4
                body_right = arrow_cx + arrow_size // 4
                body_top = arrow_cy - arrow_size // 3
                body_bottom = arrow_cy + arrow_size // 3

                if body_left <= x <= body_right and body_top <= y <= body_bottom:
                    r, g, b, a = pixel
                    pixel = arrow_color

                # 箭头尖 (三角形)
                tip_top = arrow_cy - arrow_size // 2
                tip_bottom = arrow_cy + arrow_size // 2
                tip_right = arrow_cx + arrow_size // 2

                if (tip_top <= y <= tip_bottom and body_right <= x <= tip_right):
                    # 三角形判断
                    dy = y - arrow_cy
                    half_w = (tip_right - body_right) * (1 - abs(dy) / (arrow_size // 2))
                    if x <= body_right + half_w:
                        r, g, b, a = pixel
                        pixel = arrow_color

            pixels.append(pixel)

    return pixels


def main():
    sizes = [(32, 32), (64, 64)]
    png_data_list = []

    for w, h in sizes:
        print(f"  生成 {w}x{h} ...")
        pixels = make_cmd_sender_pixels(w)
        png = create_png(w, h, pixels)
        png_data_list.append(png)

    ico_data = create_ico(sizes, png_data_list)

    output_path = os.path.join(os.path.dirname(__file__), "cmd_sender.ico")
    with open(output_path, "wb") as f:
        f.write(ico_data)

    file_size = len(ico_data)
    print(f"\n✅ 图标已生成: {output_path} ({file_size} 字节)")
    return output_path


if __name__ == "__main__":
    print("cmd_sender 图标生成器")
    print("=" * 50)
    main()
