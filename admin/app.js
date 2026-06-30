const API_BASE = '/api/admin';
const AUTH_BASE = '/api/admin/auth';

let state = {
    token: localStorage.getItem('admin_token') || '',
    user: JSON.parse(localStorage.getItem('admin_user') || 'null'),
    currentPage: 'dashboard',
    pageData: {},
    loading: false
};

function api(url, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
    if (state.token) headers['Authorization'] = `Bearer ${state.token}`;
    return fetch(`${url.startsWith('/api') ? '' : API_BASE}${url.startsWith('/api') ? url : url}`, {
        ...options,
        headers
    }).then(async res => {
        const data = await res.json();
        if (res.status === 401) {
            logout();
            throw new Error('登录已过期');
        }
        if (data.code !== 0) throw new Error(data.message || '请求失败');
        return data.data;
    });
}

function login(username, password) {
    return fetch(`${AUTH_BASE}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
    }).then(async res => {
        const data = await res.json();
        if (data.code !== 0) throw new Error(data.message || '登录失败');
        state.token = data.data.access_token;
        state.user = data.data.user;
        localStorage.setItem('admin_token', state.token);
        localStorage.setItem('admin_user', JSON.stringify(state.user));
        return data.data;
    });
}

function logout() {
    state.token = '';
    state.user = null;
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_user');
    render();
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str || '';
    return div.innerHTML;
}

function formatDate(str) {
    if (!str) return '-';
    const d = new Date(str);
    if (isNaN(d.getTime())) return str;
    return d.toLocaleString('zh-CN', { hour12: false });
}

// ============ 渲染入口 ============
function render() {
    const app = document.getElementById('app');
    if (!state.token) {
        app.innerHTML = renderLoginPage();
        bindLoginEvents();
    } else {
        app.innerHTML = renderLayout();
        bindLayoutEvents();
        renderContent();
    }
}

// ============ 登录页 ============
function renderLoginPage() {
    return `
    <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-600 via-purple-600 to-pink-500">
        <div class="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-md fade-in">
            <div class="text-center mb-8">
                <div class="w-16 h-16 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-2xl flex items-center justify-center mx-auto mb-4">
                    <i class="ri-dashboard-3-line text-white text-3xl"></i>
                </div>
                <h1 class="text-2xl font-bold text-gray-800">奢侈品比价管理后台</h1>
                <p class="text-gray-500 mt-2">请使用管理员账号登录</p>
            </div>
            <form id="loginForm" class="space-y-5">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">账号</label>
                    <div class="relative">
                        <i class="ri-user-line absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"></i>
                        <input type="text" id="username" class="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition" placeholder="请输入管理员账号" required>
                    </div>
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">密码</label>
                    <div class="relative">
                        <i class="ri-lock-line absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"></i>
                        <input type="password" id="password" class="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition" placeholder="请输入密码" required>
                    </div>
                </div>
                <button type="submit" id="loginBtn" class="w-full bg-gradient-to-r from-indigo-500 to-purple-500 text-white py-3 rounded-lg font-medium hover:from-indigo-600 hover:to-purple-600 transition shadow-lg hover:shadow-xl">
                    登 录
                </button>
            </form>
            <p id="loginError" class="text-red-500 text-sm text-center mt-3 hidden"></p>
        </div>
    </div>`;
}

function bindLoginEvents() {
    const form = document.getElementById('loginForm');
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        const btn = document.getElementById('loginBtn');
        const errorEl = document.getElementById('loginError');
        btn.disabled = true;
        btn.textContent = '登录中...';
        errorEl.classList.add('hidden');
        try {
            await login(username, password);
            render();
        } catch (err) {
            errorEl.textContent = err.message;
            errorEl.classList.remove('hidden');
        } finally {
            btn.disabled = false;
            btn.textContent = '登 录';
        }
    });
}

// ============ 主布局 ============
const menuItems = [
    { id: 'dashboard', name: '仪表盘', icon: 'ri-dashboard-line' },
    { id: 'products', name: '商品管理', icon: 'ri-shopping-bag-line' },
    { id: 'brands', name: '品牌管理', icon: 'ri-price-tag-3-line' },
    { id: 'categories', name: '品类管理', icon: 'ri-apps-line' },
    { id: 'stores', name: '门店管理', icon: 'ri-store-2-line' },
    { id: 'coupons', name: '优惠券管理', icon: 'ri-coupon-line' },
    { id: 'buyers', name: '买手管理', icon: 'ri-user-star-line' },
    { id: 'demands', name: '需求管理', icon: 'ri-file-list-3-line' },
    { id: 'rebates', name: '返点管理', icon: 'ri-percent-line' },
    { id: 'exchange', name: '汇率管理', icon: 'ri-exchange-dollar-line' },
    { id: 'users', name: '用户管理', icon: 'ri-user-line' }
];

function renderLayout() {
    return `
    <div class="flex h-screen overflow-hidden">
        <aside class="w-64 bg-white border-r border-gray-200 flex flex-col">
            <div class="h-16 flex items-center px-5 border-b border-gray-100">
                <div class="w-9 h-9 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-lg flex items-center justify-center mr-3">
                    <i class="ri-dashboard-3-line text-white text-lg"></i>
                </div>
                <span class="font-bold text-gray-800">管理后台</span>
            </div>
            <nav class="flex-1 py-4 overflow-y-auto">
                ${menuItems.map(item => `
                    <a href="#" data-page="${item.id}" class="sidebar-item flex items-center px-5 py-3 text-gray-600 hover:bg-gray-50 transition ${state.currentPage === item.id ? 'active' : ''}">
                        <i class="${item.icon} mr-3 text-lg"></i>
                        <span class="text-sm">${item.name}</span>
                    </a>
                `).join('')}
            </nav>
            <div class="p-4 border-t border-gray-100">
                <div class="flex items-center">
                    <div class="w-10 h-10 bg-gradient-to-r from-indigo-400 to-purple-400 rounded-full flex items-center justify-center text-white font-medium">
                        ${(state.user?.nickname || state.user?.user_id || 'A').charAt(0).toUpperCase()}
                    </div>
                    <div class="ml-3 flex-1 min-w-0">
                        <p class="text-sm font-medium text-gray-700 truncate">${escapeHtml(state.user?.nickname || '管理员')}</p>
                        <p class="text-xs text-gray-500 truncate">${escapeHtml(state.user?.user_id || '')}</p>
                    </div>
                    <button id="logoutBtn" class="p-2 text-gray-400 hover:text-red-500 transition" title="退出登录">
                        <i class="ri-logout-box-r-line text-lg"></i>
                    </button>
                </div>
            </div>
        </aside>
        <main class="flex-1 overflow-y-auto">
            <header class="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6 sticky top-0 z-10">
                <h2 id="pageTitle" class="text-lg font-semibold text-gray-800">仪表盘</h2>
                <div class="flex items-center space-x-3">
                    <span class="text-sm text-gray-500">${new Date().toLocaleDateString('zh-CN')}</span>
                </div>
            </header>
            <div id="pageContent" class="p-6"></div>
        </main>
    </div>
    <div id="modalContainer"></div>`;
}

function bindLayoutEvents() {
    document.querySelectorAll('.sidebar-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            state.currentPage = item.dataset.page;
            render();
        });
    });
    document.getElementById('logoutBtn').addEventListener('click', logout);
}

const pageTitles = {
    dashboard: '仪表盘',
    products: '商品管理',
    brands: '品牌管理',
    categories: '品类管理',
    stores: '门店管理',
    coupons: '优惠券管理',
    buyers: '买手管理',
    demands: '需求管理',
    rebates: '返点管理',
    exchange: '汇率管理',
    users: '用户管理'
};

function renderContent() {
    const titleEl = document.getElementById('pageTitle');
    const contentEl = document.getElementById('pageContent');
    titleEl.textContent = pageTitles[state.currentPage] || '';
    switch (state.currentPage) {
        case 'dashboard': renderDashboard(contentEl); break;
        case 'products': renderProducts(contentEl); break;
        case 'brands': renderBrands(contentEl); break;
        case 'categories': renderCategories(contentEl); break;
        case 'stores': renderStores(contentEl); break;
        case 'coupons': renderCoupons(contentEl); break;
        case 'buyers': renderBuyers(contentEl); break;
        case 'demands': renderDemands(contentEl); break;
        case 'rebates': renderRebates(contentEl); break;
        case 'exchange': renderExchange(contentEl); break;
        case 'users': renderUsers(contentEl); break;
    }
}

// ============ 仪表盘 ============
async function renderDashboard(container) {
    container.innerHTML = '<div class="flex items-center justify-center h-64"><i class="ri-loader-4-line text-indigo-500 text-4xl animate-spin"></i></div>';
    try {
        const stats = await api('/dashboard/stats');
        const statCards = [
            { label: '商品总数', value: stats.total_products, icon: 'ri-shopping-bag-line', color: 'from-blue-500 to-blue-600' },
            { label: '品牌数量', value: stats.total_brands, icon: 'ri-price-tag-3-line', color: 'from-purple-500 to-purple-600' },
            { label: '买手数量', value: stats.total_buyers, icon: 'ri-user-star-line', color: 'from-green-500 to-green-600' },
            { label: '需求总数', value: stats.total_demands, icon: 'ri-file-list-3-line', color: 'from-orange-500 to-orange-600' },
            { label: '优惠券数', value: stats.total_coupons, icon: 'ri-coupon-line', color: 'from-pink-500 to-pink-600' },
            { label: '门店数量', value: stats.total_stores, icon: 'ri-store-2-line', color: 'from-teal-500 to-teal-600' },
            { label: '用户总数', value: stats.total_users, icon: 'ri-user-line', color: 'from-indigo-500 to-indigo-600' },
            { label: '返点活动', value: stats.total_rebates, icon: 'ri-percent-line', color: 'from-red-500 to-red-600' }
        ];
        container.innerHTML = `
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
                ${statCards.map(card => `
                    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5 hover:shadow-md transition">
                        <div class="flex items-center justify-between">
                            <div>
                                <p class="text-gray-500 text-sm">${card.label}</p>
                                <p class="text-2xl font-bold text-gray-800 mt-1">${card.value}</p>
                            </div>
                            <div class="w-12 h-12 bg-gradient-to-br ${card.color} rounded-xl flex items-center justify-center">
                                <i class="${card.icon} text-white text-xl"></i>
                            </div>
                        </div>
                    </div>
                `).join('')}
            </div>
            <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                <h3 class="text-lg font-semibold text-gray-800 mb-4">快捷操作</h3>
                <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
                    ${[
                        { id: 'products', name: '商品管理', icon: 'ri-shopping-bag-line' },
                        { id: 'brands', name: '品牌管理', icon: 'ri-price-tag-3-line' },
                        { id: 'stores', name: '门店管理', icon: 'ri-store-2-line' },
                        { id: 'coupons', name: '优惠券', icon: 'ri-coupon-line' },
                        { id: 'buyers', name: '买手管理', icon: 'ri-user-star-line' },
                        { id: 'users', name: '用户管理', icon: 'ri-user-line' }
                    ].map(item => `
                        <button data-page="${item.name}" class="quick-btn flex flex-col items-center p-4 rounded-lg border border-gray-200 hover:border-indigo-300 hover:bg-indigo-50 transition" data-target="${item.id}">
                            <i class="${item.icon} text-2xl text-indigo-500 mb-2"></i>
                            <span class="text-sm text-gray-700">${item.name}</span>
                        </button>
                    `).join('')}
                </div>
            </div>
        `;
        container.querySelectorAll('.quick-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                state.currentPage = btn.dataset.target;
                render();
            });
        });
    } catch (err) {
        container.innerHTML = `<div class="text-red-500">加载失败: ${escapeHtml(err.message)}</div>`;
    }
}

// ============ 通用列表页渲染函数 ============
function renderListPage(config) {
    const container = document.getElementById('pageContent');
    if (!state.pageData[config.key]) state.pageData[config.key] = { page: 1, pageSize: 20, keyword: '', list: [], total: 0, loading: false };
    const pd = state.pageData[config.key];

    container.innerHTML = `
        <div class="bg-white rounded-xl shadow-sm border border-gray-100">
            <div class="p-5 border-b border-gray-100 flex items-center justify-between">
                <div class="flex items-center space-x-3">
                    <div class="relative">
                        <i class="ri-search-line absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"></i>
                        <input type="text" id="searchInput" class="pl-10 pr-4 py-2 border border-gray-300 rounded-lg w-64 focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm" placeholder="搜索${config.searchPlaceholder || ''}" value="${escapeHtml(pd.keyword)}">
                    </div>
                    ${config.filters ? config.filters.map(f => `
                        <select id="filter_${f.key}" class="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
                            <option value="">${f.label}</option>
                            ${f.options.map(o => `<option value="${o.value}">${o.label}</option>`).join('')}
                        </select>
                    `).join('') : ''}
                </div>
                <button id="addBtn" class="bg-indigo-500 hover:bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition flex items-center">
                    <i class="ri-add-line mr-1"></i> 新增${config.itemName}
                </button>
            </div>
            <div class="overflow-x-auto">
                <table class="w-full">
                    <thead class="bg-gray-50">
                        <tr>
                            ${config.columns.map(col => `<th class="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">${col.label}</th>`).join('')}
                            <th class="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-32">操作</th>
                        </tr>
                    </thead>
                    <tbody id="tableBody" class="divide-y divide-gray-100">
                        <tr><td colspan="${config.columns.length + 1}" class="px-5 py-8 text-center text-gray-400">加载中...</td></tr>
                    </tbody>
                </table>
            </div>
            <div class="px-5 py-4 border-t border-gray-100 flex items-center justify-between">
                <p class="text-sm text-gray-500">共 <span id="totalCount">0</span> 条记录</p>
                <div class="flex items-center space-x-2">
                    <button id="prevPage" class="px-3 py-1.5 border border-gray-300 rounded text-sm hover:bg-gray-50 transition disabled:opacity-50" disabled>上一页</button>
                    <span id="pageInfo" class="text-sm text-gray-600 px-2">1 / 1</span>
                    <button id="nextPage" class="px-3 py-1.5 border border-gray-300 rounded text-sm hover:bg-gray-50 transition disabled:opacity-50" disabled>下一页</button>
                </div>
            </div>
        </div>
    `;

    async function loadData() {
        pd.loading = true;
        const params = new URLSearchParams({
            page: pd.page,
            page_size: pd.pageSize,
            keyword: pd.keyword
        });
        if (config.filters) {
            config.filters.forEach(f => {
                const el = document.getElementById(`filter_${f.key}`);
                if (el && el.value) params.append(f.key, el.value);
            });
        }
        try {
            const result = await api(`/${config.apiPath}?${params.toString()}`);
            pd.list = result.list;
            pd.total = result.total;
            renderTable();
        } catch (err) {
            document.getElementById('tableBody').innerHTML = `<tr><td colspan="${config.columns.length + 1}" class="px-5 py-8 text-center text-red-500">加载失败: ${escapeHtml(err.message)}</td></tr>`;
        }
        pd.loading = false;
    }

    function renderTable() {
        const tbody = document.getElementById('tableBody');
        document.getElementById('totalCount').textContent = pd.total;
        const totalPages = Math.ceil(pd.total / pd.pageSize) || 1;
        document.getElementById('pageInfo').textContent = `${pd.page} / ${totalPages}`;
        document.getElementById('prevPage').disabled = pd.page <= 1;
        document.getElementById('nextPage').disabled = pd.page >= totalPages;

        if (pd.list.length === 0) {
            tbody.innerHTML = `<tr><td colspan="${config.columns.length + 1}" class="px-5 py-12 text-center text-gray-400">暂无数据</td></tr>`;
            return;
        }

        tbody.innerHTML = pd.list.map((item, idx) => `
            <tr class="table-row">
                ${config.columns.map(col => `<td class="px-5 py-3 text-sm text-gray-700">${col.render ? col.render(item) : escapeHtml(item[col.key] || '-')}</td>`).join('')}
                <td class="px-5 py-3 text-sm">
                    <button class="edit-btn text-indigo-600 hover:text-indigo-800 mr-3" data-index="${idx}">编辑</button>
                    <button class="delete-btn text-red-500 hover:text-red-700" data-index="${idx}">删除</button>
                </td>
            </tr>
        `).join('');

        tbody.querySelectorAll('.edit-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const item = pd.list[parseInt(btn.dataset.index)];
                config.onEdit(item, () => loadData());
            });
        });
        tbody.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const item = pd.list[parseInt(btn.dataset.index)];
                if (confirm(`确定要删除该${config.itemName}吗？`)) {
                    api(`/${config.apiPath}/${item[config.idKey]}`, { method: 'DELETE' })
                        .then(() => {
                            alert('删除成功');
                            loadData();
                        })
                        .catch(err => alert('删除失败: ' + err.message));
                }
            });
        });
    }

    document.getElementById('searchInput').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            pd.keyword = e.target.value;
            pd.page = 1;
            loadData();
        }
    });

    if (config.filters) {
        config.filters.forEach(f => {
            const el = document.getElementById(`filter_${f.key}`);
            if (el) el.addEventListener('change', () => { pd.page = 1; loadData(); });
        });
    }

    document.getElementById('prevPage').addEventListener('click', () => {
        if (pd.page > 1) { pd.page--; loadData(); }
    });
    document.getElementById('nextPage').addEventListener('click', () => {
        const totalPages = Math.ceil(pd.total / pd.pageSize);
        if (pd.page < totalPages) { pd.page++; loadData(); }
    });

    document.getElementById('addBtn').addEventListener('click', () => {
        config.onAdd(() => loadData());
    });

    loadData();
}

// ============ 模态框 ============
function showModal(title, contentHtml, onSubmit, submitText = '保存') {
    const container = document.getElementById('modalContainer');
    container.innerHTML = `
        <div class="fixed inset-0 z-50 flex items-center justify-center modal-overlay fade-in">
            <div class="bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4 max-h-[90vh] flex flex-col">
                <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
                    <h3 class="text-lg font-semibold text-gray-800">${title}</h3>
                    <button id="closeModal" class="text-gray-400 hover:text-gray-600 transition">
                        <i class="ri-close-line text-xl"></i>
                    </button>
                </div>
                <div id="modalBody" class="p-6 overflow-y-auto flex-1">${contentHtml}</div>
                <div class="px-6 py-4 border-t border-gray-100 flex justify-end space-x-3">
                    <button id="cancelModal" class="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition text-sm">取消</button>
                    <button id="submitModal" class="px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg transition text-sm">${submitText}</button>
                </div>
            </div>
        </div>
    `;
    function close() { container.innerHTML = ''; }
    document.getElementById('closeModal').addEventListener('click', close);
    document.getElementById('cancelModal').addEventListener('click', close);
    document.getElementById('submitModal').addEventListener('click', async () => {
        try {
            await onSubmit(close);
        } catch (err) {
            alert(err.message);
        }
    });
    return close;
}

// ============ 品牌管理 ============
function renderBrands() {
    renderListPage({
        key: 'brands',
        itemName: '品牌',
        apiPath: 'brands',
        idKey: 'brand_id',
        searchPlaceholder: '品牌名称',
        columns: [
            { key: 'brand_id', label: '品牌ID' },
            { key: 'name_cn', label: '中文名' },
            { key: 'name', label: '英文名' },
            { key: 'logo', label: 'Logo' }
        ],
        onAdd: (cb) => showBrandModal(null, cb),
        onEdit: (item, cb) => showBrandModal(item, cb)
    });
}

function showBrandModal(brand, cb) {
    const isEdit = !!brand;
    showModal(isEdit ? '编辑品牌' : '新增品牌', `
        <form id="brandForm" class="space-y-4">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">品牌ID *</label>
                <input type="text" name="brand_id" value="${escapeHtml(brand?.brand_id || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm" ${isEdit ? 'readonly' : ''} required>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">中文名 *</label>
                <input type="text" name="name_cn" value="${escapeHtml(brand?.name_cn || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm" required>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">英文名</label>
                <input type="text" name="name" value="${escapeHtml(brand?.name || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Logo (emoji/图标)</label>
                <input type="text" name="logo" value="${escapeHtml(brand?.logo || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">分类</label>
                <input type="text" name="category" value="${escapeHtml(brand?.category || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
            </div>
        </form>
    `, async (close) => {
        const form = document.getElementById('brandForm');
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        if (!data.brand_id || !data.name_cn) throw new Error('请填写必填项');
        const url = isEdit ? `/brands/${brand.brand_id}` : '/brands';
        const method = isEdit ? 'PUT' : 'POST';
        await api(url, { method, body: JSON.stringify(data) });
        alert(isEdit ? '更新成功' : '创建成功');
        close();
        cb();
    });
}

// ============ 品类管理 ============
function renderCategories() {
    renderListPage({
        key: 'categories',
        itemName: '品类',
        apiPath: 'categories',
        idKey: 'category_id',
        searchPlaceholder: '品类名称',
        columns: [
            { key: 'category_id', label: '品类ID' },
            { key: 'name', label: '名称' },
            { key: 'icon', label: '图标' }
        ],
        onAdd: (cb) => showCategoryModal(null, cb),
        onEdit: (item, cb) => showCategoryModal(item, cb)
    });
}

function showCategoryModal(cat, cb) {
    const isEdit = !!cat;
    showModal(isEdit ? '编辑品类' : '新增品类', `
        <form id="catForm" class="space-y-4">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">品类ID *</label>
                <input type="text" name="category_id" value="${escapeHtml(cat?.category_id || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm" ${isEdit ? 'readonly' : ''} required>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">名称 *</label>
                <input type="text" name="name" value="${escapeHtml(cat?.name || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm" required>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">图标 (emoji)</label>
                <input type="text" name="icon" value="${escapeHtml(cat?.icon || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
            </div>
        </form>
    `, async (close) => {
        const form = document.getElementById('catForm');
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        const url = isEdit ? `/categories/${cat.category_id}` : '/categories';
        const method = isEdit ? 'PUT' : 'POST';
        await api(url, { method, body: JSON.stringify(data) });
        alert(isEdit ? '更新成功' : '创建成功');
        close();
        cb();
    });
}

// ============ 门店管理 ============
function renderStores() {
    renderListPage({
        key: 'stores',
        itemName: '门店',
        apiPath: 'stores',
        idKey: 'store_id',
        searchPlaceholder: '门店名称',
        filters: [
            { key: 'country', label: '国家', options: [
                { value: 'CN', label: '中国' },
                { value: 'JP', label: '日本' },
                { value: 'US', label: '美国' },
                { value: 'FR', label: '法国' },
                { value: 'HK', label: '香港' },
                { value: 'KR', label: '韩国' },
                { value: 'IT', label: '意大利' }
            ]}
        ],
        columns: [
            { key: 'store_id', label: '门店ID' },
            { key: 'name', label: '名称' },
            { key: 'country', label: '国家' },
            { key: 'city', label: '城市' },
            { key: 'type', label: '类型' },
            { key: 'rating', label: '评分' }
        ],
        onAdd: (cb) => showStoreModal(null, cb),
        onEdit: (item, cb) => showStoreModal(item, cb)
    });
}

function showStoreModal(store, cb) {
    const isEdit = !!store;
    showModal(isEdit ? '编辑门店' : '新增门店', `
        <form id="storeForm" class="space-y-4">
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">门店ID *</label>
                    <input type="text" name="store_id" value="${escapeHtml(store?.store_id || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm" ${isEdit ? 'readonly' : ''} required>
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">类型</label>
                    <select name="type" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
                        <option value="mall">商场</option>
                        <option value="street">街区</option>
                        <option value="dutyfree">免税店</option>
                    </select>
                </div>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">名称 *</label>
                <input type="text" name="name" value="${escapeHtml(store?.name || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm" required>
            </div>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">国家 *</label>
                    <input type="text" name="country" value="${escapeHtml(store?.country || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm" required>
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">城市 *</label>
                    <input type="text" name="city" value="${escapeHtml(store?.city || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm" required>
                </div>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">地址</label>
                <input type="text" name="address" value="${escapeHtml(store?.address || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
            </div>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">评分</label>
                    <input type="number" step="0.1" name="rating" value="${store?.rating || 0}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">图片URL</label>
                    <input type="text" name="image" value="${escapeHtml(store?.image || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
                </div>
            </div>
        </form>
    `, async (close) => {
        const form = document.getElementById('storeForm');
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        data.rating = parseFloat(data.rating) || 0;
        const url = isEdit ? `/stores/${store.store_id}` : '/stores';
        const method = isEdit ? 'PUT' : 'POST';
        await api(url, { method, body: JSON.stringify(data) });
        alert(isEdit ? '更新成功' : '创建成功');
        close();
        cb();
    });
}

// ============ 优惠券管理 ============
function renderCoupons() {
    renderListPage({
        key: 'coupons',
        itemName: '优惠券',
        apiPath: 'coupons',
        idKey: 'coupon_id',
        searchPlaceholder: '优惠券标题',
        filters: [
            { key: 'status', label: '状态', options: [
                { value: 'available', label: '可用' },
                { value: 'disabled', label: '已禁用' }
            ]}
        ],
        columns: [
            { key: 'coupon_id', label: 'ID' },
            { key: 'title', label: '标题' },
            { key: 'type', label: '类型' },
            { key: 'discount', label: '优惠值' },
            { key: 'threshold', label: '门槛' },
            { key: 'country', label: '国家' },
            { key: 'expire_date', label: '到期日' },
            { key: 'status', label: '状态', render: (item) => `<span class="px-2 py-0.5 text-xs rounded-full ${item.status === 'available' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}">${item.status === 'available' ? '可用' : '已禁用'}</span>` }
        ],
        onAdd: (cb) => showCouponModal(null, cb),
        onEdit: (item, cb) => showCouponModal(item, cb)
    });
}

function showCouponModal(coupon, cb) {
    const isEdit = !!coupon;
    showModal(isEdit ? '编辑优惠券' : '新增优惠券', `
        <form id="couponForm" class="space-y-4">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">优惠券ID *</label>
                <input type="text" name="coupon_id" value="${escapeHtml(coupon?.coupon_id || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm" ${isEdit ? 'readonly' : ''} required>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">标题 *</label>
                <input type="text" name="title" value="${escapeHtml(coupon?.title || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm" required>
            </div>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">类型</label>
                    <select name="type" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
                        <option value="discount">满减</option>
                        <option value="percent">折扣</option>
                        <option value="cashback">返现</option>
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">状态</label>
                    <select name="status" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
                        <option value="available">可用</option>
                        <option value="disabled">已禁用</option>
                    </select>
                </div>
            </div>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">优惠值</label>
                    <input type="number" step="0.01" name="discount" value="${coupon?.discount || 0}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">使用门槛</label>
                    <input type="number" step="0.01" name="threshold" value="${coupon?.threshold || 0}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
                </div>
            </div>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">国家</label>
                    <input type="text" name="country" value="${escapeHtml(coupon?.country || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">到期日</label>
                    <input type="date" name="expire_date" value="${escapeHtml(coupon?.expire_date || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
                </div>
            </div>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">门店ID</label>
                    <input type="text" name="store_id" value="${escapeHtml(coupon?.store_id || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">门店名称</label>
                    <input type="text" name="store_name" value="${escapeHtml(coupon?.store_name || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
                </div>
            </div>
        </form>
    `, async (close) => {
        const form = document.getElementById('couponForm');
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        data.discount = parseFloat(data.discount) || 0;
        data.threshold = parseFloat(data.threshold) || 0;
        const url = isEdit ? `/coupons/${coupon.coupon_id}` : '/coupons';
        const method = isEdit ? 'PUT' : 'POST';
        await api(url, { method, body: JSON.stringify(data) });
        alert(isEdit ? '更新成功' : '创建成功');
        close();
        cb();
    });
}

// ============ 买手管理 ============
function renderBuyers() {
    renderListPage({
        key: 'buyers',
        itemName: '买手',
        apiPath: 'buyers',
        idKey: 'buyer_id',
        searchPlaceholder: '买手名称',
        filters: [
            { key: 'country', label: '国家', options: [
                { value: 'JP', label: '日本' },
                { value: 'FR', label: '法国' },
                { value: 'KR', label: '韩国' },
                { value: 'IT', label: '意大利' },
                { value: 'HK', label: '香港' },
                { value: 'US', label: '美国' }
            ]}
        ],
        columns: [
            { key: 'buyer_id', label: '买手ID' },
            { key: 'name', label: '名称' },
            { key: 'country', label: '国家' },
            { key: 'city', label: '城市' },
            { key: 'rating', label: '评分' },
            { key: 'orders', label: '订单数' },
            { key: 'fee_rate', label: '费率(%)' },
            { key: 'delivery_days', label: '交付天数' }
        ],
        onAdd: (cb) => showBuyerModal(null, cb),
        onEdit: (item, cb) => showBuyerModal(item, cb)
    });
}

function showBuyerModal(buyer, cb) {
    const isEdit = !!buyer;
    showModal(isEdit ? '编辑买手' : '新增买手', `
        <form id="buyerForm" class="space-y-4">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">买手ID *</label>
                <input type="text" name="buyer_id" value="${escapeHtml(buyer?.buyer_id || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm" ${isEdit ? 'readonly' : ''} required>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">名称 *</label>
                <input type="text" name="name" value="${escapeHtml(buyer?.name || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm" required>
            </div>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">国家</label>
                    <input type="text" name="country" value="${escapeHtml(buyer?.country || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">城市</label>
                    <input type="text" name="city" value="${escapeHtml(buyer?.city || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
                </div>
            </div>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">评分</label>
                    <input type="number" step="0.1" name="rating" value="${buyer?.rating || 5}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">订单数</label>
                    <input type="number" name="orders" value="${buyer?.orders || 0}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
                </div>
            </div>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">费率(%)</label>
                    <input type="number" step="0.1" name="fee_rate" value="${buyer?.fee_rate || 10}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">交付天数</label>
                    <input type="number" name="delivery_days" value="${buyer?.delivery_days || 15}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
                </div>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">头像URL</label>
                <input type="text" name="avatar" value="${escapeHtml(buyer?.avatar || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">简介</label>
                <textarea name="intro" rows="3" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">${escapeHtml(buyer?.intro || '')}</textarea>
            </div>
        </form>
    `, async (close) => {
        const form = document.getElementById('buyerForm');
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        data.rating = parseFloat(data.rating) || 5;
        data.orders = parseInt(data.orders) || 0;
        data.fee_rate = parseFloat(data.fee_rate) || 10;
        data.delivery_days = parseInt(data.delivery_days) || 15;
        const url = isEdit ? `/buyers/${buyer.buyer_id}` : '/buyers';
        const method = isEdit ? 'PUT' : 'POST';
        await api(url, { method, body: JSON.stringify(data) });
        alert(isEdit ? '更新成功' : '创建成功');
        close();
        cb();
    });
}

// ============ 需求管理 ============
function renderDemands() {
    renderListPage({
        key: 'demands',
        itemName: '需求',
        apiPath: 'demands',
        idKey: 'demand_id',
        searchPlaceholder: '商品名称',
        filters: [
            { key: 'status', label: '状态', options: [
                { value: 'bidding', label: '招标中' },
                { value: 'matched', label: '已匹配' },
                { value: 'done', label: '已完成' }
            ]}
        ],
        columns: [
            { key: 'demand_id', label: '需求ID' },
            { key: 'product_name', label: '商品名称' },
            { key: 'user_id', label: '用户ID' },
            { key: 'country', label: '国家' },
            { key: 'budget', label: '预算' },
            { key: 'quantity', label: '数量' },
            { key: 'bids', label: '投标数' },
            { key: 'status', label: '状态', render: (item) => {
                const map = { bidding: ['招标中', 'bg-yellow-100 text-yellow-700'], matched: ['已匹配', 'bg-blue-100 text-blue-700'], done: ['已完成', 'bg-green-100 text-green-700'] };
                const [text, cls] = map[item.status] || [item.status, 'bg-gray-100 text-gray-600'];
                return `<span class="px-2 py-0.5 text-xs rounded-full ${cls}">${text}</span>`;
            }},
            { key: 'created_at', label: '创建时间', render: (item) => formatDate(item.created_at) }
        ],
        onAdd: null,
        onEdit: (item, cb) => showDemandModal(item, cb)
    });
}

function showDemandModal(demand, cb) {
    showModal('编辑需求', `
        <form id="demandForm" class="space-y-4">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">商品名称</label>
                <input type="text" name="product_name" value="${escapeHtml(demand.product_name)}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
            </div>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">状态</label>
                    <select name="status" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
                        <option value="bidding">招标中</option>
                        <option value="matched">已匹配</option>
                        <option value="done">已完成</option>
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">国家</label>
                    <input type="text" name="country" value="${escapeHtml(demand.country || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
                </div>
            </div>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">预算</label>
                    <input type="number" step="0.01" name="budget" value="${demand.budget || 0}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">数量</label>
                    <input type="number" name="quantity" value="${demand.quantity || 1}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
                </div>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">截止日期</label>
                <input type="date" name="deadline" value="${escapeHtml(demand.deadline || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">匹配买手ID</label>
                <input type="text" name="matched_buyer_id" value="${escapeHtml(demand.matched_buyer_id || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">描述</label>
                <textarea name="description" rows="3" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">${escapeHtml(demand.description || '')}</textarea>
            </div>
        </form>
    `, async (close) => {
        const form = document.getElementById('demandForm');
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        data.budget = parseFloat(data.budget) || 0;
        data.quantity = parseInt(data.quantity) || 1;
        await api(`/demands/${demand.demand_id}`, { method: 'PUT', body: JSON.stringify(data) });
        alert('更新成功');
        close();
        cb();
    });
}

// ============ 返点管理 ============
function renderRebates() {
    renderListPage({
        key: 'rebates',
        itemName: '返点活动',
        apiPath: 'rebates',
        idKey: 'rebate_id',
        searchPlaceholder: '活动标题',
        filters: [
            { key: 'status', label: '状态', options: [
                { value: 'available', label: '进行中' },
                { value: 'expired', label: '已过期' }
            ]}
        ],
        columns: [
            { key: 'rebate_id', label: 'ID' },
            { key: 'title', label: '标题' },
            { key: 'country', label: '国家' },
            { key: 'store_name', label: '门店' },
            { key: 'rate', label: '返点率(%)' },
            { key: 'status', label: '状态', render: (item) => `<span class="px-2 py-0.5 text-xs rounded-full ${item.status === 'available' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}">${item.status === 'available' ? '进行中' : '已过期'}</span>` },
            { key: 'start_date', label: '开始日期' },
            { key: 'end_date', label: '结束日期' }
        ],
        onAdd: (cb) => showRebateModal(null, cb),
        onEdit: (item, cb) => showRebateModal(item, cb)
    });
}

function showRebateModal(rebate, cb) {
    const isEdit = !!rebate;
    showModal(isEdit ? '编辑返点活动' : '新增返点活动', `
        <form id="rebateForm" class="space-y-4">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">活动ID *</label>
                <input type="text" name="rebate_id" value="${escapeHtml(rebate?.rebate_id || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm" ${isEdit ? 'readonly' : ''} required>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">标题 *</label>
                <input type="text" name="title" value="${escapeHtml(rebate?.title || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm" required>
            </div>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">国家</label>
                    <input type="text" name="country" value="${escapeHtml(rebate?.country || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">返点率(%) *</label>
                    <input type="number" step="0.1" name="rate" value="${rebate?.rate || 0}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm" required>
                </div>
            </div>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">门店名称</label>
                    <input type="text" name="store_name" value="${escapeHtml(rebate?.store_name || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">状态</label>
                    <select name="status" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
                        <option value="available">进行中</option>
                        <option value="expired">已过期</option>
                    </select>
                </div>
            </div>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">开始日期</label>
                    <input type="date" name="start_date" value="${escapeHtml(rebate?.start_date || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">结束日期</label>
                    <input type="date" name="end_date" value="${escapeHtml(rebate?.end_date || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
                </div>
            </div>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">品牌ID</label>
                    <input type="text" name="brand_id" value="${escapeHtml(rebate?.brand_id || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">品牌名称</label>
                    <input type="text" name="brand_name" value="${escapeHtml(rebate?.brand_name || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
                </div>
            </div>
            <div>
                <label class="flex items-center text-sm">
                    <input type="checkbox" name="is_vip_only" ${rebate?.is_vip_only ? 'checked' : ''} class="mr-2">
                    仅VIP用户
                </label>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">描述</label>
                <textarea name="description" rows="2" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">${escapeHtml(rebate?.description || '')}</textarea>
            </div>
        </form>
    `, async (close) => {
        const form = document.getElementById('rebateForm');
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        data.rate = parseFloat(data.rate) || 0;
        data.is_vip_only = form.querySelector('[name="is_vip_only"]').checked;
        const url = isEdit ? `/rebates/${rebate.rebate_id}` : '/rebates';
        const method = isEdit ? 'PUT' : 'POST';
        await api(url, { method, body: JSON.stringify(data) });
        alert(isEdit ? '更新成功' : '创建成功');
        close();
        cb();
    });
}

// ============ 汇率管理 ============
async function renderExchange() {
    const container = document.getElementById('pageContent');
    container.innerHTML = '<div class="flex items-center justify-center h-64"><i class="ri-loader-4-line text-indigo-500 text-4xl animate-spin"></i></div>';
    try {
        const data = await api('/exchange-rates');
        const rates = data?.rates || {};
        const keys = Object.keys(rates);
        container.innerHTML = `
            <div class="bg-white rounded-xl shadow-sm border border-gray-100">
                <div class="p-5 border-b border-gray-100 flex items-center justify-between">
                    <div>
                        <h3 class="text-lg font-semibold text-gray-800">汇率管理</h3>
                        <p class="text-sm text-gray-500 mt-1">基准货币: ${data?.base || 'CNY'} | 更新时间: ${formatDate(data?.update_time)}</p>
                    </div>
                    <button id="editRatesBtn" class="bg-indigo-500 hover:bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition flex items-center">
                        <i class="ri-edit-line mr-1"></i> 编辑汇率
                    </button>
                </div>
                <div class="p-5">
                    <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-4">
                        ${keys.map(key => `
                            <div class="border border-gray-200 rounded-lg p-4 hover:border-indigo-300 transition">
                                <p class="text-sm text-gray-500">${key}</p>
                                <p class="text-lg font-semibold text-gray-800 mt-1">${rates[key]}</p>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;
        document.getElementById('editRatesBtn').addEventListener('click', () => {
            showRatesModal(data, () => renderExchange());
        });
    } catch (err) {
        container.innerHTML = `<div class="text-red-500">加载失败: ${escapeHtml(err.message)}</div>`;
    }
}

function showRatesModal(data, cb) {
    const rates = data?.rates || {};
    const keys = Object.keys(rates);
    showModal('编辑汇率', `
        <form id="ratesForm" class="space-y-3">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">基准货币</label>
                <input type="text" name="base" value="${escapeHtml(data?.base || 'CNY')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
            </div>
            <div class="grid grid-cols-2 gap-3">
                ${keys.map(key => `
                    <div>
                        <label class="block text-xs font-medium text-gray-600 mb-1">${key}</label>
                        <input type="number" step="0.0001" name="rate_${key}" value="${rates[key]}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
                    </div>
                `).join('')}
            </div>
        </form>
    `, async (close) => {
        const form = document.getElementById('ratesForm');
        const formData = new FormData(form);
        const base = formData.get('base');
        const newRates = {};
        keys.forEach(key => {
            newRates[key] = parseFloat(formData.get(`rate_${key}`)) || 0;
        });
        await api('/exchange-rates', { method: 'PUT', body: JSON.stringify({ base, rates: newRates }) });
        alert('更新成功');
        close();
        cb();
    });
}

// ============ 用户管理 ============
function renderUsers() {
    renderListPage({
        key: 'users',
        itemName: '用户',
        apiPath: 'users',
        idKey: 'user_id',
        searchPlaceholder: '昵称/手机/用户ID',
        columns: [
            { key: 'user_id', label: '用户ID' },
            { key: 'nickname', label: '昵称' },
            { key: 'phone', label: '手机' },
            { key: 'is_vip', label: 'VIP', render: (item) => item.is_vip ? '<span class="text-amber-500"><i class="ri-vip-crown-line"></i> 是</span>' : '否' },
            { key: 'is_admin', label: '管理员', render: (item) => item.is_admin ? '<span class="text-indigo-500"><i class="ri-shield-check-line"></i> 是</span>' : '否' },
            { key: 'status', label: '状态', render: (item) => `<span class="px-2 py-0.5 text-xs rounded-full ${item.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}">${item.status === 'active' ? '正常' : '禁用'}</span>` },
            { key: 'created_at', label: '注册时间', render: (item) => formatDate(item.created_at) }
        ],
        onAdd: null,
        onEdit: (item, cb) => showUserModal(item, cb)
    });
}

function showUserModal(user, cb) {
    showModal('编辑用户', `
        <form id="userForm" class="space-y-4">
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">用户ID</label>
                    <input type="text" name="user_id" value="${escapeHtml(user.user_id)}" class="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-sm" readonly>
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">昵称</label>
                    <input type="text" name="nickname" value="${escapeHtml(user.nickname || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
                </div>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">手机号</label>
                <input type="text" name="phone" value="${escapeHtml(user.phone || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
            </div>
            <div class="grid grid-cols-2 gap-4">
                <label class="flex items-center text-sm">
                    <input type="checkbox" name="is_vip" ${user.is_vip ? 'checked' : ''} class="mr-2">
                    VIP用户
                </label>
                <label class="flex items-center text-sm">
                    <input type="checkbox" name="is_admin" ${user.is_admin ? 'checked' : ''} class="mr-2">
                    管理员
                </label>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">状态</label>
                <select name="status" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
                    <option value="active">正常</option>
                    <option value="disabled">禁用</option>
                </select>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">重置密码 (管理员用)</label>
                <input type="password" name="password" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm" placeholder="留空则不修改">
            </div>
        </form>
    `, async (close) => {
        const form = document.getElementById('userForm');
        const formData = new FormData(form);
        const data = {
            nickname: formData.get('nickname'),
            phone: formData.get('phone'),
            is_vip: form.querySelector('[name="is_vip"]').checked,
            is_admin: form.querySelector('[name="is_admin"]').checked,
            status: formData.get('status')
        };
        const pwd = formData.get('password');
        if (pwd) data.password = pwd;
        await api(`/users/${user.user_id}`, { method: 'PUT', body: JSON.stringify(data) });
        alert('更新成功');
        close();
        cb();
    });
}

// ============ 商品管理 ============
function renderProducts() {
    renderListPage({
        key: 'products',
        itemName: '商品',
        apiPath: 'products',
        idKey: 'spu_id',
        searchPlaceholder: '商品名称/货号',
        columns: [
            { key: 'spu_id', label: 'SPU ID' },
            { key: 'article_no', label: '货号' },
            { key: 'brand_name', label: '品牌' },
            { key: 'name', label: '名称' },
            { key: 'category_id', label: '品类' },
            { key: 'created_at', label: '创建时间', render: (item) => formatDate(item.created_at) }
        ],
        onAdd: (cb) => showProductModal(null, cb),
        onEdit: (item, cb) => showProductModal(item, cb)
    });
}

function showProductModal(product, cb) {
    const isEdit = !!product;
    showModal(isEdit ? '编辑商品' : '新增商品', `
        <form id="productForm" class="space-y-4">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">SPU ID *</label>
                <input type="text" name="spu_id" value="${escapeHtml(product?.spu_id || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm" ${isEdit ? 'readonly' : ''} required>
            </div>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">品牌ID *</label>
                    <input type="text" name="brand_id" value="${escapeHtml(product?.brand_id || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm" required>
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">品牌名 *</label>
                    <input type="text" name="brand_name" value="${escapeHtml(product?.brand_name || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm" required>
                </div>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">商品名称 *</label>
                <input type="text" name="name" value="${escapeHtml(product?.name || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm" required>
            </div>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">英文名</label>
                    <input type="text" name="name_en" value="${escapeHtml(product?.name_en || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">货号</label>
                    <input type="text" name="article_no" value="${escapeHtml(product?.article_no || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
                </div>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">品类ID</label>
                <input type="text" name="category_id" value="${escapeHtml(product?.category_id || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">图片URL</label>
                <input type="text" name="image" value="${escapeHtml(product?.image || '')}" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">描述</label>
                <textarea name="description" rows="3" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm">${escapeHtml(product?.description || '')}</textarea>
            </div>
        </form>
    `, async (close) => {
        const form = document.getElementById('productForm');
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        const url = isEdit ? `/products/${product.spu_id}` : '/products';
        const method = isEdit ? 'PUT' : 'POST';
        await api(url, { method, body: JSON.stringify(data) });
        alert(isEdit ? '更新成功' : '创建成功');
        close();
        cb();
    });
}

// ============ 初始化 ============
render();
