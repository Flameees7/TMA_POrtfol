/**
 * Catalog Component: Product Grid, Search, and Filtering.
 */

const CatalogComponent = {
    products: [],
    searchQuery: '',
    inStockOnly: false,
    isLoading: false,

    init() {
        this.bindEvents();
        this.loadProducts();
    },

    bindEvents() {
        const searchInput = document.getElementById('search-input');
        const clearSearchBtn = document.getElementById('clear-search-btn');
        const filterAllBtn = document.getElementById('filter-all');
        const filterStockBtn = document.getElementById('filter-stock');

        if (searchInput) {
            let debounceTimer;
            searchInput.addEventListener('input', (e) => {
                this.searchQuery = e.target.value.trim();
                if (clearSearchBtn) {
                    clearSearchBtn.style.display = this.searchQuery ? 'block' : 'none';
                }
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => this.loadProducts(), 300);
            });
        }

        if (clearSearchBtn) {
            clearSearchBtn.addEventListener('click', () => {
                if (searchInput) {
                    searchInput.value = '';
                    this.searchQuery = '';
                    clearSearchBtn.style.display = 'none';
                    this.loadProducts();
                }
            });
        }

        if (filterAllBtn && filterStockBtn) {
            filterAllBtn.addEventListener('click', () => {
                TelegramService.haptic('selection');
                this.inStockOnly = false;
                filterAllBtn.className = "px-3.5 py-1.5 rounded-full text-xs font-semibold bg-emerald-600 text-white shadow-sm transition-all";
                filterStockBtn.className = "px-3.5 py-1.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600 hover:bg-slate-200 transition-all";
                this.loadProducts();
            });

            filterStockBtn.addEventListener('click', () => {
                TelegramService.haptic('selection');
                this.inStockOnly = true;
                filterStockBtn.className = "px-3.5 py-1.5 rounded-full text-xs font-semibold bg-emerald-600 text-white shadow-sm transition-all";
                filterAllBtn.className = "px-3.5 py-1.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600 hover:bg-slate-200 transition-all";
                this.loadProducts();
            });
        }
    },

    async loadProducts() {
        const container = document.getElementById('products-grid');
        if (!container) return;

        this.isLoading = true;
        this.renderSkeletons(container);

        try {
            this.products = await Api.getProducts(this.searchQuery, this.inStockOnly);
            this.renderProducts(container);
        } catch (error) {
            container.innerHTML = `
                <div class="col-span-2 text-center py-12 px-4">
                    <div class="w-12 h-12 bg-rose-50 text-rose-500 rounded-full flex items-center justify-center mx-auto mb-3">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                    </div>
                    <p class="text-slate-800 font-semibold mb-1">Не удалось загрузить товары</p>
                    <p class="text-slate-500 text-xs mb-4">Проверьте подключение к сети</p>
                    <button onclick="CatalogComponent.loadProducts()" class="px-4 py-2 bg-emerald-600 text-white text-xs font-semibold rounded-xl active:scale-95 transition-all">
                        Повторить попытку
                    </button>
                </div>
            `;
        } finally {
            this.isLoading = false;
        }
    },

    renderSkeletons(container) {
        let html = '';
        for (let i = 0; i < 4; i++) {
            html += `
                <div class="bg-white rounded-2xl p-3 border border-slate-100 shadow-sm animate-pulse flex flex-col justify-between">
                    <div class="w-full aspect-square bg-slate-200 rounded-xl mb-3"></div>
                    <div class="h-4 bg-slate-200 rounded w-3/4 mb-2"></div>
                    <div class="h-3 bg-slate-100 rounded w-1/2 mb-3"></div>
                    <div class="h-5 bg-slate-200 rounded w-1/3"></div>
                </div>
            `;
        }
        container.innerHTML = html;
    },

    renderProducts(container) {
        if (!this.products || this.products.length === 0) {
            container.innerHTML = `
                <div class="col-span-2 text-center py-12 px-4">
                    <div class="w-14 h-14 bg-slate-100 text-slate-400 rounded-full flex items-center justify-center mx-auto mb-3">
                        <svg class="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"></path></svg>
                    </div>
                    <h3 class="text-slate-800 font-bold text-sm mb-1">Товары не найдены</h3>
                    <p class="text-slate-500 text-xs">Попробуйте изменить поисковый запрос или фильтры</p>
                </div>
            `;
            return;
        }

        let html = '';
        this.products.forEach(p => {
            const mainPhoto = (p.photos && p.photos.length > 0)
                ? p.photos[0]
                : 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600&q=80';

            // Stock Badge
            let badgeClass = "bg-emerald-50 text-emerald-700 border-emerald-200";
            let badgeText = "В наличии";

            if (p.stock_status === "reserved") {
                badgeClass = "bg-amber-50 text-amber-700 border-amber-200";
                badgeText = "Резерв";
            } else if (!p.is_available || p.stock_status === "out_of_stock") {
                badgeClass = "bg-slate-100 text-slate-500 border-slate-200";
                badgeText = "Нет в наличии";
            } else if (p.stock_status === "preorder") {
                badgeClass = "bg-blue-50 text-blue-700 border-blue-200";
                badgeText = "Под заказ";
            }

            html += `
                <div class="bg-white rounded-2xl p-2.5 border border-slate-100 shadow-sm hover:shadow-md transition-all flex flex-col justify-between cursor-pointer touch-scale group"
                     onclick="ProductModalComponent.open(${p.id})">
                    <div>
                        <div class="relative w-full aspect-square rounded-xl overflow-hidden bg-slate-100 mb-2.5">
                            <img src="${mainPhoto}" 
                                 alt="${p.title}" 
                                 class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                                 loading="lazy"
                                 onerror="this.src='https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600&q=80'">
                            <span class="absolute top-2 left-2 px-2 py-0.5 text-[10px] font-semibold rounded-full border ${badgeClass} backdrop-blur-sm shadow-xs">
                                ${badgeText}
                            </span>
                        </div>
                        <h3 class="text-xs font-bold text-slate-800 line-clamp-2 leading-snug mb-1">
                            ${p.title}
                        </h3>
                    </div>
                    <div class="mt-2 pt-2 border-t border-slate-50 flex items-center justify-between">
                        <span class="text-sm font-extrabold text-slate-900">
                            ${Utils.formatPrice(p.price)}
                        </span>
                        <div class="w-7 h-7 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center group-hover:bg-emerald-600 group-hover:text-white transition-colors">
                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 4v16m8-8H4"></path></svg>
                        </div>
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;
    }
};

window.CatalogComponent = CatalogComponent;
