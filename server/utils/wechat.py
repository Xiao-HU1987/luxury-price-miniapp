import httpx
import json
from typing import Optional, Dict

from config import WECHAT_APPID, WECHAT_SECRET

WECHAT_JSCODE2SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"


async def wechat_login(code: str) -> Dict:
    if not WECHAT_APPID or not WECHAT_SECRET:
        return {
            "openid": f"test_{code}",
            "session_key": "test_session_key",
            "unionid": None
        }

    params = {
        "appid": WECHAT_APPID,
        "secret": WECHAT_SECRET,
        "js_code": code,
        "grant_type": "authorization_code"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(WECHAT_JSCODE2SESSION_URL, params=params)
        data = response.json()

    if "errcode" in data and data["errcode"] != 0:
        raise Exception(f"微信登录失败: {data.get('errmsg', '未知错误')}")

    return data


def decrypt_wechat_phone(encrypted_data: str, iv: str, session_key: str) -> str:
    if not WECHAT_APPID or not WECHAT_SECRET:
        return "13800138000"

    try:
        from Crypto.Cipher import AES
        import base64

        session_key_bytes = base64.b64decode(session_key)
        encrypted_bytes = base64.b64decode(encrypted_data)
        iv_bytes = base64.b64decode(iv)

        cipher = AES.new(session_key_bytes, AES.MODE_CBC, iv_bytes)
        decrypted = cipher.decrypt(encrypted_bytes)

        pad = decrypted[-1]
        decrypted = decrypted[:-pad]

        data = json.loads(decrypted.decode('utf-8'))
        return data.get("phoneNumber", "")
    except Exception:
        return ""
