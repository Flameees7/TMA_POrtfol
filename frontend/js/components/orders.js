/**
 * Orders Component: My Orders history and "Заказ получен" customer action.
 */

const OrdersComponent = {
    orders: [],
    isLoading: false,

    async loadOrders() {
        const container = document.getElementById('orders-list');
        if (!container) return;

        this.isLoading = true;
        this.renderLoading(container);

        try {
            this.orders = await Api.getMyOrders();
            this.renderOrders(container);
        } catch (error) {
            container.innerHTML = `
                <div class="text-center py-12 px-4">
                    <div class="w-12 h-12 bg-rose-50 text-rose-500 rounded-full flex items-center justify-center mx-auto mb-3">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                    </div>
                    <p class="text-slate-800 font-semibold text-sm mb-1">Не удалось загрузить заказы</p>
                    <p class="text-slate-500 text-xs mb-4">Попробуйте обновить страницу</p>
                    <button onclick="OrdersComponent.loadOrders()" class="px-4 py-2 bg-emerald-600 text-white text-xs font-semibold rounded-xl active:scale-95 transition-all">
                        Обновить
                    </button>
                </div>
            `;
        } finally {
            this.isLoading = false;
        }
    },

    renderLoading(container) {
        let html = '';
        for (let i = 0; i < 3; i++) {
            html += `
                <div class="bg-white rounded-2xl p-4 border border-slate-100 shadow-sm animate-pulse space-y-3 mb-3">
                    <div class="flex justify-between items-center">
                        <div class="h-4 bg-slate-200 rounded w-20"></div>
                        <div class="h-4 bg-slate-200 rounded w-24"></div>
                    </div>
                    <div class="h-5 bg-slate-200 rounded w-3/4"></div>
                    <div class="h-4 bg-slate-100 rounded w-1/2"></div>
                </div>
            `;
        }
        container.innerHTML = html;
    },

    renderOrders(container) {
        if (!this.orders || this.orders.length === 0) {
            container.innerHTML = `
                <div class="text-center py-16 px-4">
                    <div class="w-16 h-16 bg-slate-100 text-slate-400 rounded-full flex items-center justify-center mx-auto mb-4">
                        <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z"></path></svg>
                    </div>
                    <h3 class="text-slate-900 font-bold text-base mb-1">У вас пока нет заказов</h3>
                    <p class="text-slate-500 text-xs mb-5 max-w-xs mx-auto">Выберите понравившийся товар в каталоге и оформите свой первый заказ</p>
                    <button onclick="App.switchTab('catalog')" class="px-6 py-3 bg-emerald-600 text-white text-xs font-bold rounded-xl shadow-md shadow-emerald-500/20 active:scale-95 transition-all">
                        Перейти в каталог
                    </button>
                </div>
            `;
            return;
        }

        let html = '';
        this.orders.forEach(o => {
            // Status styling
            let badgeBg = "bg-amber-50 text-amber-700 border-amber-200";
            let statusIcon = "⏳";

            if (o.status === "assembling") {
                badgeBg = "bg-indigo-50 text-indigo-700 border-indigo-200";
                statusIcon = "📦";
            } else if (o.status === "in_transit") {
                badgeBg = "bg-purple-50 text-purple-700 border-purple-200";
                statusIcon = "🚚";
            } else if (o.status === "completed") {
                badgeBg = "bg-emerald-50 text-emerald-700 border-emerald-200";
                statusIcon = "✅";
            } else if (o.status === "cancelled") {
                badgeBg = "bg-slate-100 text-slate-500 border-slate-200";
                statusIcon = "🚫";
            }

            const photo = (o.product_photos && o.product_photos.length > 0)
                ? o.product_photos[0]
                : 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=300&q=80';

            html += `
                <div class="bg-white rounded-2xl p-4 border border-slate-100 shadow-sm mb-3 space-y-3 animate-fade-in">
                    <!-- Top Bar -->
                    <div class="flex items-center justify-between">
                        <span class="text-xs font-black text-slate-900 font-mono">${o.order_number}</span>
                        <span class="px-2.5 py-1 text-[10px] font-bold rounded-full border ${badgeBg} flex items-center gap-1">
                            <span>${statusIcon}</span>
                            <span>${o.status_label}</span>
                        </span>
                    </div>

                    <!-- Product Snapshot -->
                    <div class="flex items-center gap-3 bg-slate-50 p-2.5 rounded-xl border border-slate-100">
                        <img src="${photo}" alt="" class="w-12 h-12 object-cover rounded-lg bg-slate-200 flex-shrink-0" onerror="this.style.display='none'">
                        <div class="flex-1 min-w-0">
                            <h4 class="text-xs font-bold text-slate-800 truncate">${o.product_title}</h4>
                            <div class="text-xs font-extrabold text-emerald-700 mt-0.5">${Utils.formatPrice(o.product_price)}</div>
                        </div>
                    </div>

                    <!-- Meta Details -->
                    <div class="text-[11px] text-slate-500 space-y-1">
                        <div class="flex justify-between">
                            <span>Способ получения:</span>
                            <span class="font-medium text-slate-700">${o.delivery_type_label} ${o.delivery_provider ? `(${o.delivery_provider})` : ''}</span>
                        </div>
                        <div class="flex justify-between">
                            <span>Оплата:</span>
                            <span class="font-medium text-slate-700">${o.payment_method_label}</span>
                        </div>
                        <div class="flex justify-between">
                            <span>Дата заказа:</span>
                            <span class="font-medium text-slate-700">${Utils.formatDate(o.created_at)}</span>
                        </div>
                    </div>

                    <!-- Customer Action: "Заказ получен" button when status == in_transit -->
                    ${o.status === "in_transit" ? `
                        <div class="pt-2 border-t border-slate-100">
                            <button onclick="OrdersComponent.confirmReceipt(${o.id}, '${o.order_number}')" 
                                    class="w-full py-2.5 px-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow-sm shadow-emerald-500/20 active:scale-95 transition-all flex items-center justify-center gap-1.5">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"></path></svg>
                                <span>Заказ получен</span>
                            </button>
                        </div>
                    ` : ''}
                </div>
            `;
        });

        container.innerHTML = html;
    },

    async confirmReceipt(orderId, orderNumber) {
        TelegramService.haptic('medium');
        if (!confirm(`Подтвердить, что заказ ${orderNumber} получен вами?`)) {
            return;
        }

        try {
            await Api.markOrderReceived(orderId);
            TelegramService.haptic('success');
            Utils.showToast("Спасибо за покупку! Заказ завершен.", "success");
            await this.loadOrders();
        } catch (error) {
            TelegramService.haptic('error');
            Utils.showToast(error.message || "Не удалось обновить статус", "error");
        }
    }
};

window.OrdersComponent = OrdersComponent;
