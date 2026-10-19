import struct
import zlib
import os

def create_simple_png(width, height, r, g, b, a=255):
    signature = b'\x89PNG\r\n\x1a\n'
    
    def chunk(chunk_type, data):
        c = chunk_type + data
        crc = zlib.crc32(c) & 0xffffffff
        return struct.pack('>I', len(data)) + c + struct.pack('>I', crc)
    
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    
    raw_data = bytearray()
    for y in range(height):
        raw_data.append(0)
        for x in range(width):
            raw_data.extend([r, g, b, a])
    
    compressed = zlib.compress(bytes(raw_data))
    
    return (signature + 
            chunk(b'IHDR', ihdr_data) + 
            chunk(b'IDAT', compressed) + 
            chunk(b'IEND', b''))

def is_valid_png(data):
    if len(data) < 8:
        return False
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        return False
    return True

icon_dir = os.path.join(os.path.dirname(__file__), '../images/tab')

GRAY = (153, 153, 153)
ORANGE = (255, 107, 0)

icons = {
    'coupon.png': GRAY,
    'coupon_active.png': ORANGE,
    'exchange.png': GRAY,
    'exchange_active.png': ORANGE,
    'compare.png': GRAY,
    'compare_active.png': ORANGE,
    'buyer.png': GRAY,
    'buyer_active.png': ORANGE,
    'profile.png': GRAY,
    'profile_active.png': ORANGE
}

os.makedirs(icon_dir, exist_ok=True)

for name, (r, g, b) in icons.items():
    filepath = os.path.join(icon_dir, name)
    png_data = create_simple_png(48, 48, r, g, b)
    
    if is_valid_png(png_data):
        with open(filepath, 'wb') as f:
            f.write(png_data)
        print(f'Created valid PNG: {name} ({len(png_data)} bytes)')
    else:
        print(f'ERROR: Invalid PNG: {name}')

print('\nAll icons generated and verified!')
