/**
 * Main Application Orchestrator: Routing, Tab switching, and State.
 */

const App = {
    currentTab: 'catalog',

    init() {
        // 1. Initialize Telegram WebApp
        TelegramService.init();

        // 2. Set user display
        const user = TelegramService.getUser();
        const userGreetingEl = document.getElementById('user-greeting');
        if (userGreetingEl) {
            userGreetingEl.textContent = user.first_name ? `Привет, ${user.first_name}!` : 'Добро пожаловать!';
        }

        // 3. Initialize Catalog
        CatalogComponent.init();

        // 4. Handle initial hash routing
        if (window.location.hash === '#orders') {
            this.switchTab('orders');
        }

        // 5. Listen to popstate / hash changes
        window.addEventListener('hashchange', () => {
            if (window.location.hash === '#orders') {
                this.switchTab('orders', false);
            } else {
                this.switchTab('catalog', false);
            }
        });
    },

    switchTab(tabName, updateHash = true) {
        if (this.currentTab === tabName && tabName === 'catalog') return;

        TelegramService.haptic('selection');
        this.currentTab = tabName;

        if (updateHash) {
            window.location.hash = tabName === 'orders' ? '#orders' : '';
        }

        const catalogSection = document.getElementById('tab-catalog');
        const ordersSection = document.getElementById('tab-orders');
        const navCatalogBtn = document.getElementById('nav-catalog');
        const navOrdersBtn = document.getElementById('nav-orders');

        if (tabName === 'catalog') {
            if (catalogSection) catalogSection.classList.remove('hidden');
            if (ordersSection) ordersSection.classList.add('hidden');

            if (navCatalogBtn) {
                navCatalogBtn.className = "flex flex-col items-center justify-center flex-1 py-1 text-emerald-600 font-bold transition-all";
                navCatalogBtn.querySelector('.nav-icon-bg').className = "nav-icon-bg w-10 h-7 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mb-0.5 transition-colors";
            }
            if (navOrdersBtn) {
                navOrdersBtn.className = "flex flex-col items-center justify-center flex-1 py-1 text-slate-400 font-medium transition-all";
                navOrdersBtn.querySelector('.nav-icon-bg').className = "nav-icon-bg w-10 h-7 rounded-full bg-transparent text-slate-400 flex items-center justify-center mb-0.5 transition-colors";
            }
        } else if (tabName === 'orders') {
            if (catalogSection) catalogSection.classList.add('hidden');
            if (ordersSection) ordersSection.classList.remove('hidden');

            if (navOrdersBtn) {
                navOrdersBtn.className = "flex flex-col items-center justify-center flex-1 py-1 text-emerald-600 font-bold transition-all";
                navOrdersBtn.querySelector('.nav-icon-bg').className = "nav-icon-bg w-10 h-7 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mb-0.5 transition-colors";
            }
            if (navCatalogBtn) {
                navCatalogBtn.className = "flex flex-col items-center justify-center flex-1 py-1 text-slate-400 font-medium transition-all";
                navCatalogBtn.querySelector('.nav-icon-bg').className = "nav-icon-bg w-10 h-7 rounded-full bg-transparent text-slate-400 flex items-center justify-center mb-0.5 transition-colors";
            }

            OrdersComponent.loadOrders();
        }

        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
};

window.App = App;

// Bootstrap on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    App.init();
});
