import os
import zlib
import struct

def create_png(width, height, r, g, b, a=255):
    signature = b'\x89PNG\r\n\x1a\n'
    
    def crc32(data):
        crc = 0xFFFFFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                crc = (crc >> 1) ^ (0xEDB88320 if crc & 1 else 0)
        return (crc ^ 0xFFFFFFFF) & 0xFFFFFFFF
    
    def create_chunk(chunk_type, data):
        length = struct.pack('>I', len(data))
        crc_data = chunk_type + data
        crc = struct.pack('>I', crc32(crc_data))
        return length + chunk_type + data + crc
    
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    ihdr_chunk = create_chunk(b'IHDR', ihdr)
    
    raw_data = []
    for y in range(height):
        raw_data.append(0)
        for x in range(width):
            raw_data.extend([r, g, b, a])
    
    compressed = zlib.compress(bytes(raw_data))
    idat_chunk = create_chunk(b'IDAT', compressed)
    
    iend_chunk = create_chunk(b'IEND', b'')
    
    return signature + ihdr_chunk + idat_chunk + iend_chunk

icon_dir = os.path.join(os.path.dirname(__file__), '../images/tab')

icons = {
    'coupon': (153, 153, 153),
    'coupon_active': (255, 107, 0),
    'exchange': (153, 153, 153),
    'exchange_active': (255, 107, 0),
    'compare': (153, 153, 153),
    'compare_active': (255, 107, 0),
    'buyer': (153, 153, 153),
    'buyer_active': (255, 107, 0)
}

os.makedirs(icon_dir, exist_ok=True)

for name, (r, g, b) in icons.items():
    png = create_png(48, 48, r, g, b)
    with open(os.path.join(icon_dir, f'{name}.png'), 'wb') as f:
        f.write(png)
    print(f'Created {name}.png')

print('All icons generated!')
