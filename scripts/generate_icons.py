"""Generate high-resolution PNG icons for SupportAI & JARVIS PWA/APK using standard library."""

import zlib
import struct
import math
from pathlib import Path

def create_png(width, height, filename):
    # RGBA image buffer
    raw_rows = []
    cx, cy = width / 2.0, height / 2.0
    radius = width * 0.46
    core_radius = width * 0.16
    ring_radius = width * 0.28
    ring_width = width * 0.035

    for y in range(height):
        row = bytearray(b"\x00")  # Filter type 0 (None)
        for x in range(width):
            dx = x - cx
            dy = y - cy
            dist = math.sqrt(dx * dx + dy * dy)
            angle = math.atan2(dy, dx)

            # Background: Dark rounded squircle
            squircle_dist = (abs(dx)**3.2 + abs(dy)**3.2) ** (1 / 3.2)
            if squircle_dist > radius * 1.05:
                # Transparent outside
                row.extend((0, 0, 0, 0))
                continue

            # Base gradient: Stark Dark Navy/Cyan
            bg_factor = (y / height) * 0.6 + 0.4
            r = int(9 * bg_factor)
            g = int(14 * bg_factor + 10)
            b = int(28 * bg_factor + 25)
            a = 255

            # Outer glowing ring
            if abs(dist - ring_radius) < ring_width:
                # Cyan ring
                ring_glow = 1.0 - (abs(dist - ring_radius) / ring_width)
                r = int(r * (1 - ring_glow) + 6 * ring_glow)
                g = int(g * (1 - ring_glow) + 182 * ring_glow)
                b = int(b * (1 - ring_glow) + 212 * ring_glow)

            # 4 Triangles / Nodes at 0, 90, 180, 270 deg
            for rot in [0, math.pi / 2, math.pi, 3 * math.pi / 2]:
                node_x = cx + math.cos(rot) * ring_radius
                node_y = cy + math.sin(rot) * ring_radius
                ndist = math.sqrt((x - node_x)**2 + (y - node_y)**2)
                if ndist < ring_width * 1.5:
                    r, g, b = 56, 189, 248

            # Inner Core: Glowing Arc Reactor
            if dist < core_radius:
                core_glow = 1.0 - (dist / core_radius)
                r = int(37 * (1 - core_glow) + 255 * core_glow)
                g = int(99 * (1 - core_glow) + 255 * core_glow)
                b = int(235 * (1 - core_glow) + 255 * core_glow)
            elif dist < core_radius * 1.3:
                # Core halo
                halo_glow = (1.0 - (dist - core_radius) / (core_radius * 0.3)) * 0.7
                r = min(255, int(r + 37 * halo_glow))
                g = min(255, int(g + 99 * halo_glow))
                b = min(255, int(b + 235 * halo_glow))

            row.extend((min(255, max(0, r)), min(255, max(0, g)), min(255, max(0, b)), a))
        raw_rows.append(bytes(row))

    raw_data = b"".join(raw_rows)
    compressed_data = zlib.compress(raw_data, 9)

    # PNG chunks
    def chunk(chunk_type, data):
        return (
            struct.pack(">I", len(data))
            + chunk_type
            + data
            + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
        )

    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    png_data = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr_data)
        + chunk(b"IDAT", compressed_data)
        + chunk(b"IEND", b"")
    )

    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    with open(filename, "wb") as f:
        f.write(png_data)
    print(f"Generated {filename} ({width}x{height})")

if __name__ == "__main__":
    create_png(192, 192, "src/static/icon-192.png")
    create_png(512, 512, "src/static/icon-512.png")
    create_png(512, 512, "src/static/icon-maskable.png")
