// 云开发配置 - 密钥从环境变量读取，不硬编码
// 部署时设置环境变量: TENCENT_SECRET_ID, TENCENT_SECRET_KEY
const cloud_config = {
  secretId: process.env.TENCENT_SECRET_ID || "",
  secretKey: process.env.TENCENT_SECRET_KEY || "",
  env: "lv-miniapp-prod"
};

module.exports = cloud_config;
