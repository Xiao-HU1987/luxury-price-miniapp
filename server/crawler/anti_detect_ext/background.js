// background.js - Service Worker
// 轮询Python Bridge Server，转发命令给Content Script

const SERVER_URL = 'http://localhost:8899';

// 存储待处理命令结果
const pendingResults = {};

// 接收Content Script的回复
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg && msg.cmd_id && pendingResults[msg.cmd_id]) {
        // 保存结果，后续通过poll返回给Bridge Server
        pendingResults[msg.cmd_id].resolve(msg.result);
        delete pendingResults[msg.cmd_id];
    }
});

// 轮询Bridge Server获取命令
async function pollOnce() {
    try {
        const resp = await fetch(SERVER_URL + '/poll', {
            method: 'GET',
            headers: { 'Cache-Control': 'no-cache' },
            cache: 'no-store'
        });
        if (!resp.ok) return;
        const cmd = await resp.json();
        if (!cmd || !cmd.action || cmd.action === 'none') return;

        // 执行命令：发送到当前活动标签页
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (!tab) {
            postResult(cmd.id, null, 'No active tab');
            return;
        }

        // 发送消息给Content Script
        try {
            const response = await chrome.tabs.sendMessage(tab.id, cmd);
            postResult(cmd.id, response);
        } catch (e) {
            postResult(cmd.id, null, 'Content script not reachable: ' + e.message);
        }
    } catch (e) {
        // Server未就绪或网络错误，静默忽略
    }
}

async function postResult(cmdId, result, error) {
    try {
        await fetch(SERVER_URL + '/result', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: cmdId, result, error: error || null })
        });
    } catch (e) {
        // 忽略发送失败
    }
}

// 每200ms轮询一次
setInterval(pollOnce, 200);
