const ENV = 'production';

const config = {
  development: {
    BASE_URL: 'http://localhost:8000',
    DEBUG: true
  },
  production: {
    // 上线前替换为你的 HTTPS 域名（必须在微信公众平台配置为 request 合法域名）
    BASE_URL: 'https://flask-ie22-282058-9-1453887688.sh.run.tcloudbase.com',
    DEBUG: false
  }
};

module.exports = {
  ...config[ENV],
  ENV
};
