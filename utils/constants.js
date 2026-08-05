const COUNTRIES = [
  { code: 'CN', name: '中国', currency: 'CNY', currencySymbol: '¥', flag: '🇨🇳' },
  { code: 'JP', name: '日本', currency: 'JPY', currencySymbol: '¥', flag: '🇯🇵' },
  { code: 'KR', name: '韩国', currency: 'KRW', currencySymbol: '₩', flag: '🇰🇷' }
];

const BRANDS = [
  { id: 'b001', name: 'Louis Vuitton', nameCn: '路易威登', logo: 'LV', category: '箱包' },
  { id: 'b002', name: 'Gucci', nameCn: '古驰', logo: 'G', category: '箱包服饰' },
  { id: 'b003', name: 'Hermès', nameCn: '爱马仕', logo: 'H', category: '箱包' },
  { id: 'b004', name: 'Chanel', nameCn: '香奈儿', logo: 'C', category: '箱包服饰' },
  { id: 'b005', name: 'Dior', nameCn: '迪奥', logo: 'D', category: '服饰箱包' },
  { id: 'b006', name: 'Rolex', nameCn: '劳力士', logo: 'R', category: '腕表' },
  { id: 'b007', name: 'Cartier', nameCn: '卡地亚', logo: 'Ca', category: '珠宝腕表' },
  { id: 'b008', name: 'Prada', nameCn: '普拉达', logo: 'P', category: '箱包' }
];

const CATEGORIES = [
  { id: 'c001', name: '箱包', icon: '👜' },
  { id: 'c002', name: '腕表', icon: '⌚' },
  { id: 'c003', name: '珠宝', icon: '💎' },
  { id: 'c004', name: '服饰', icon: '👗' },
  { id: 'c005', name: '鞋履', icon: '👠' },
  { id: 'c006', name: '配饰', icon: '🕶️' }
];

module.exports = {
  COUNTRIES,
  BRANDS,
  CATEGORIES
};
