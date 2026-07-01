import hashlib
import uuid
import random
import string
from typing import Dict
from decimal import Decimal
from config import WECHAT_APPID, WECHAT_MCH_ID, WECHAT_PAY_KEY, WECHAT_NOTIFY_URL, DEBUG


def generate_out_trade_no(prefix: str = "VIP") -> str:
    import time
    timestamp = str(int(time.time() * 1000))
    random_str = ''.join(random.choices(string.digits, k=6))
    return f"{prefix}{timestamp}{random_str}"


def wechat_pay_sign(params: Dict) -> str:
    if not WECHAT_PAY_KEY:
        return ""
    
    sorted_params = sorted(params.items())
    sign_str = '&'.join([f"{k}={v}" for k, v in sorted_params if v])
    sign_str += f"&key={WECHAT_PAY_KEY}"
    sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest().upper()
    return sign


def wechat_pay_sign_v3_sign(params: Dict) -> str:
    if not WECHAT_PAY_KEY:
        return ""
    
    sorted_params = sorted(params.items())
    sign_str = '&'.join([f"{k}={v}" for k, v in sorted_params if v])
    sign_str += f"&key={WECHAT_PAY_KEY}"
    sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest().upper()
    return sign


def create_vip_payment(
    out_trade_no: str,
    openid: str,
    total_fee: int,
    body: str,
    notify_url: str = ""
) -> Dict:
    if not WECHAT_APPID or not WECHAT_MCH_ID or not WECHAT_PAY_KEY:
        return {
            "appId": WECHAT_APPID or "mock_appid",
            "timeStamp": str(int(__import__('time').time())),
            "nonceStr": uuid.uuid4().hex,
            "package": f"prepay_id=mock_prepay_id",
            "signType": "MD5",
            "paySign": "mock_pay_sign"
        }
    
    import time
    import httpx
    
    nonce_str = uuid.uuid4().hex
    params = {
        "appid": WECHAT_APPID,
        "mch_id": WECHAT_MCH_ID,
        "nonce_str": nonce_str,
        "body": body,
        "out_trade_no": out_trade_no,
        "total_fee": total_fee,
        "spbill_create_ip": "127.0.0.1",
        "notify_url": notify_url or WECHAT_NOTIFY_URL or "",
        "trade_type": "JSAPI",
        "openid": openid
    }
    
    params["sign"] = wechat_pay_sign(params)
    
    import xml.etree.ElementTree as ET
    xml_data = "<xml>"
    for k, v in params.items():
        xml_data += f"<{k}>{v}</{k}>"
    xml_data += "</xml>"
    
    try:
        response = httpx.post(
            "https://api.mch.weixin.qq.com/pay/unifiedorder",
            content=xml_data.encode('utf-8'),
            headers={"Content-Type": "application/xml"}
        )
        
        root = ET.fromstring(response.text)
        result = {}
        for child in root:
            result[child.tag] = child.text
        
        if result.get("return_code") == "SUCCESS" and result.get("result_code") == "SUCCESS":
            prepay_id = result.get("prepay_id", "")
            
            pay_params = {
                "appId": WECHAT_APPID,
                "timeStamp": str(int(time.time())),
                "nonceStr": uuid.uuid4().hex,
                "package": f"prepay_id={prepay_id}",
                "signType": "MD5"
            }
            pay_params["paySign"] = wechat_pay_sign(pay_params)
            
            return pay_params
        else:
            raise Exception(f"微信支付统一下单失败: {result.get('err_code_des', '未知错误')}")
    except Exception as e:
        if DEBUG:
            return {
                "appId": WECHAT_APPID,
                "timeStamp": str(int(time.time())),
                "nonceStr": uuid.uuid4().hex,
                "package": f"prepay_id=mock_prepay_id",
                "signType": "MD5",
                "paySign": "mock_pay_sign"
            }
        raise e


def verify_payment_notify(xml_data: str) -> Dict:
    import xml.etree.ElementTree as ET
    
    root = ET.fromstring(xml_data)
    result = {}
    for child in root:
        result[child.tag] = child.text
    
    if not WECHAT_PAY_KEY:
        return result
    
    sign = result.pop("sign", "")
    calculated_sign = wechat_pay_sign(result)
    
    if sign and sign.upper() != calculated_sign.upper():
        raise Exception("签名验证失败")
    
    return result
