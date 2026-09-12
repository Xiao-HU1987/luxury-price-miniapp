// content.js - LV爬虫反检测桥接
// 直接轮询Bridge Server获取命令，执行后回传结果
// 不需要background.js，简化扩展架构

const BRIDGE_URL = 'http://localhost:8899';
const POLL_INTERVAL = 200; // ms

// 轮询循环
async function pollLoop() {
    while (true) {
        try {
            // 轮询获取命令
            const resp = await fetch(BRIDGE_URL + '/poll', {
                method: 'GET',
                cache: 'no-store',
                headers: { 'Cache-Control': 'no-cache' }
            });
            
            if (!resp.ok) {
                await sleep(300);
                continue;
            }
            
            const cmd = await resp.json();
            if (cmd && cmd.action && cmd.action !== 'none') {
                const result = await executeCommand(cmd);
                await sendResult(cmd.id, result);
            }
        } catch (e) {
            // Server未就绪，静默等待
        }
        await sleep(POLL_INTERVAL);
    }
}

async function executeCommand(cmd) {
    try {
        switch (cmd.action) {
            case 'evaluate':
                return { result: eval(cmd.script), error: null };

            case 'element_info':
                const el = document.querySelector(cmd.selector);
                if (!el) return { result: null, error: 'Element not found: ' + cmd.selector };
                const rect = el.getBoundingClientRect();
                return {
                    result: {
                        screenX: Math.round(rect.left + rect.width / 2 + window.screenX),
                        screenY: Math.round(rect.top + rect.height / 2 + window.screenY + (window.outerHeight - window.innerHeight)),
                        visible: rect.width > 0 && rect.height > 0,
                        width: Math.round(rect.width),
                        height: Math.round(rect.height),
                        text: (el.innerText || '').substring(0, 200)
                    },
                    error: null
                };

            case 'scroll_to':
                window.scrollTo(cmd.x || 0, cmd.y || 0);
                return { result: { ok: true }, error: null };

            case 'scroll_element_into_view':
                const target = document.querySelector(cmd.selector);
                if (target) {
                    target.scrollIntoView({ behavior: 'instant', block: 'center' });
                    return { result: { ok: true }, error: null };
                }
                return { result: null, error: 'Element not found' };

            default:
                return { result: null, error: 'Unknown action: ' + cmd.action };
        }
    } catch (e) {
        return { result: null, error: String(e) };
    }
}

async function sendResult(cmdId, response) {
    try {
        await fetch(BRIDGE_URL + '/result', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id: cmdId,
                result: response.result,
                error: response.error
            })
        });
    } catch (e) {}
}

function sleep(ms) {
    return new Promise(r => setTimeout(r, ms));
}

// 启动轮询
pollLoop();
console.log('[LV Bridge] Content Script started on', window.location.hostname);
