const fs = require('fs');
const path = require('path');

const iconDir = path.join(__dirname, '../images/tab');

const createPNG = (width, height, r, g, b, a = 255) => {
  const signature = Buffer.from([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]);
  
  const createChunk = (type, data) => {
    const length = Buffer.alloc(4);
    length.writeUInt32BE(data.length);
    const typeBuffer = Buffer.from(type);
    const crcData = Buffer.concat([typeBuffer, data]);
    let crc = 0xFFFFFFFF;
    for (let i = 0; i < crcData.length; i++) {
      crc ^= crcData[i];
      for (let j = 0; j < 8; j++) {
        crc = (crc >>> 1) ^ (crc & 1 ? 0xEDB88320 : 0);
      }
    }
    crc = (crc ^ 0xFFFFFFFF) >>> 0;
    const crcBuffer = Buffer.alloc(4);
    crcBuffer.writeUInt32BE(crc);
    return Buffer.concat([length, typeBuffer, data, crcBuffer]);
  };
  
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8;
  ihdr[9] = 6;
  ihdr[10] = 0;
  ihdr[11] = 0;
  ihdr[12] = 0;
  
  const rawData = [];
  for (let y = 0; y < height; y++) {
    rawData.push(0);
    for (let x = 0; x < width; x++) {
      rawData.push(r, g, b, a);
    }
  }
  
  const zlib = require('zlib');
  const compressed = zlib.deflateSync(Buffer.from(rawData));
  
  const ihdrChunk = createChunk('IHDR', ihdr);
  const idatChunk = createChunk('IDAT', compressed);
  const iendChunk = createChunk('IEND', Buffer.alloc(0));
  
  return Buffer.concat([signature, ihdrChunk, idatChunk, iendChunk]);
};

const icons = {
  'calc': { normal: [153, 153, 153], active: [255, 107, 0] },
  'calc_active': { normal: [255, 107, 0], active: [255, 107, 0] },
  'rebate': { normal: [153, 153, 153], active: [255, 107, 0] },
  'rebate_active': { normal: [255, 107, 0], active: [255, 107, 0] },
  'index': { normal: [153, 153, 153], active: [255, 107, 0] },
  'index_active': { normal: [255, 107, 0], active: [255, 107, 0] },
  'store': { normal: [153, 153, 153], active: [255, 107, 0] },
  'store_active': { normal: [255, 107, 0], active: [255, 107, 0] }
};

if (!fs.existsSync(iconDir)) {
  fs.mkdirSync(iconDir, { recursive: true });
}

for (const [name, colors] of Object.entries(icons)) {
  const [r, g, b] = colors.normal;
  const png = createPNG(48, 48, r, g, b);
  fs.writeFileSync(path.join(iconDir, `${name}.png`), png);
  console.log(`Created ${name}.png`);
}

console.log('All icons generated!');
