"""LV 日本官网数据采集模块

详见 ``lv_crawler.py`` 顶部文档。启动方式::

    1. 关闭所有 Chrome
    2. open -n -a "Google Chrome" --args --remote-debugging-port=9222 \\
        --proxy-server="http://127.0.0.1:7890"
    3. 在 Chrome 中打开 https://jp.louisvuitton.com 验证
    4. venv/bin/python -m crawler.lv_crawler --mode list
"""
