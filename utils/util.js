const { COUNTRIES } = require('./constants.js');

function formatPrice(amount, currencyCode) {
  const country = COUNTRIES.find(c => c.currency === currencyCode);
  const symbol = country ? country.currencySymbol : '';
  const num = Number(amount);
  if (currencyCode === 'JPY' || currencyCode === 'KRW') {
    return symbol + String(Math.round(num)).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  }
  return symbol + num.toFixed(2);
}

function convertCurrency(amount, fromCurrency, toCurrency, rates) {
  if (!rates || !rates.rates) return amount;
  const fromRate = rates.rates[fromCurrency] || 1;
  const toRate = rates.rates[toCurrency] || 1;
  const inBase = amount / fromRate;
  return inBase * toRate;
}

function formatTime(dateStr) {
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now - date;
  if (diff < 60000) return '刚刚';
  if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前';
  if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前';
  if (diff < 2592000000) return Math.floor(diff / 86400000) + '天前';
  return formatDate(dateStr);
}

function formatDate(dateStr) {
  const date = new Date(dateStr);
  return date.getFullYear() + '-' + 
    String(date.getMonth() + 1).padStart(2, '0') + '-' + 
    String(date.getDate()).padStart(2, '0');
}

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

function getCountryByCode(code) {
  return COUNTRIES.find(c => c.code === code) || COUNTRIES[0];
}

module.exports = {
  formatPrice,
  convertCurrency,
  formatTime,
  formatDate,
  debounce,
  getCountryByCode
};
