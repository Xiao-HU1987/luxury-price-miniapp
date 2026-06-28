const COUNTRIES = [
  { code: 'CN', name: '中国', currency: 'CNY', currencySymbol: '¥', flag: '🇨🇳' },
  { code: 'US', name: '美国', currency: 'USD', currencySymbol: '$', flag: '🇺🇸' },
  { code: 'FR', name: '法国', currency: 'EUR', currencySymbol: '€', flag: '🇫🇷' },
  { code: 'IT', name: '意大利', currency: 'EUR', currencySymbol: '€', flag: '🇮🇹' },
  { code: 'UK', name: '英国', currency: 'GBP', currencySymbol: '£', flag: '🇬🇧' },
  { code: 'JP', name: '日本', currency: 'JPY', currencySymbol: '¥', flag: '🇯🇵' },
  { code: 'KR', name: '韩国', currency: 'KRW', currencySymbol: '₩', flag: '🇰🇷' },
  { code: 'HK', name: '中国香港', currency: 'HKD', currencySymbol: 'HK$', flag: '🇭🇰' },
  { code: 'SG', name: '新加坡', currency: 'SGD', currencySymbol: 'S$', flag: '🇸🇬' },
  { code: 'AU', name: '澳大利亚', currency: 'AUD', currencySymbol: 'A$', flag: '🇦🇺' },
  { code: 'CH', name: '瑞士', currency: 'CHF', currencySymbol: 'CHF', flag: '🇨🇭' },
  { code: 'CA', name: '加拿大', currency: 'CAD', currencySymbol: 'C$', flag: '🇨🇦' },
  { code: 'TH', name: '泰国', currency: 'THB', currencySymbol: '฿', flag: '🇹🇭' }
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
