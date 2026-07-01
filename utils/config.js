const ENV = 'development';

const config = {
  development: {
    BASE_URL: 'http://localhost:8000',
    DEBUG: true
  },
  production: {
    BASE_URL: 'https://api.kuaibi.com',
    DEBUG: false
  }
};

module.exports = {
  ...config[ENV],
  ENV
};
