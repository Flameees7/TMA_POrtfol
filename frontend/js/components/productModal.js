/**
 * Product Modal Component: Photo Gallery / Slider, Details & Purchase action.
 */

const ProductModalComponent = {
    currentProduct: null,
    currentPhotoIndex: 0,

    async open(productId) {
        TelegramService.haptic('light');
        const modal = document.getElementById('product-modal');
        if (!modal) return;

        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';

        TelegramService.showBackButton(() => {
            this.close();
        });

        this.renderLoading();

        try {
            this.currentProduct = await Api.getProduct(productId);
            this.renderProductDetails();
        } catch (error) {
            Utils.showToast('Не удалось загрузить товар', 'error');
            this.close();
        }
    },

    close() {
        TelegramService.haptic('light');
        const modal = document.getElementById('product-modal');
        if (modal) {
            modal.classList.add('hidden');
        }
        document.body.style.overflow = '';
        TelegramService.hideBackButton();
        this.currentProduct = null;
    },

    renderLoading() {
        const container = document.getElementById('product-modal-content');
        if (!container) return;

        container.innerHTML = `
            <div class="p-6 flex flex-col items-center justify-center min-h-[300px]">
                <div class="w-8 h-8 border-3 border-emerald-600 border-t-transparent rounded-full animate-spin mb-3"></div>
                <p class="text-xs text-slate-400 font-medium">Загрузка информации...</p>
            </div>
        `;
    },

    renderProductDetails() {
        const p = this.currentProduct;
        const container = document.getElementById('product-modal-content');
        if (!p || !container) return;

        const photos = (p.photos && p.photos.length > 0)
            ? p.photos
            : ['https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800&q=80'];

        // Photos slider HTML
        let photosHtml = '';
        photos.forEach((url, idx) => {
            photosHtml += `
                <div class="w-full flex-shrink-0 aspect-square snap-center relative">
                    <img src="${url}" 
                         alt="${p.title}" 
                         class="w-full h-full object-cover rounded-2xl"
                         onerror="this.src='https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800&q=80'">
                </div>
            `;
        });

        // Dots indicator
        let dotsHtml = '';
        if (photos.length > 1) {
            dotsHtml = `
                <div class="flex items-center justify-center gap-1.5 mt-2">
                    ${photos.map((_, i) => `<span id="dot-${i}" class="w-2 h-2 rounded-full transition-all ${i === 0 ? 'bg-emerald-600 w-4' : 'bg-slate-200'}"></span>`).join('')}
                </div>
            `;
        }

        // Status badge
        let badgeColor = "bg-emerald-50 text-emerald-700 border-emerald-200";
        let statusText = "В наличии (Готов к отправке)";
        let isBuyable = p.is_available;

        if (p.stock_status === "reserved") {
            badgeColor = "bg-amber-50 text-amber-700 border-amber-200";
            statusText = "Товар забронирован";
            isBuyable = false;
        } else if (!p.is_available || p.stock_status === "out_of_stock") {
            badgeColor = "bg-slate-100 text-slate-500 border-slate-200";
            statusText = "Нет в наличии";
            isBuyable = false;
        }

        container.innerHTML = `
            <div class="p-4 sm:p-6 pb-24 animate-fade-in max-h-[85vh] overflow-y-auto no-scrollbar">
                <!-- Close Button -->
                <div class="flex justify-end mb-2">
                    <button onclick="ProductModalComponent.close()" class="w-8 h-8 rounded-full bg-slate-100 text-slate-500 flex items-center justify-center active:scale-90 transition-transform">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                    </button>
                </div>

                <!-- Gallery Slider -->
                <div class="relative w-full mb-3">
                    <div id="modal-gallery-slider" 
                         class="w-full flex overflow-x-auto snap-x snap-mandatory no-scrollbar rounded-2xl bg-slate-50">
                        ${photosHtml}
                    </div>
                    ${dotsHtml}
                </div>

                <!-- Product Info -->
                <div class="space-y-3">
                    <div class="flex items-center justify-between">
                        <span class="px-2.5 py-1 text-xs font-semibold rounded-full border ${badgeColor}">
                            ${statusText}
                        </span>
                        <span class="text-xs text-slate-400 font-mono">Арт: ${p.external_id}</span>
                    </div>

                    <h2 class="text-lg font-bold text-slate-900 leading-snug">
                        ${p.title}
                    </h2>

                    <div class="text-2xl font-extrabold text-emerald-600">
                        ${Utils.formatPrice(p.price)}
                    </div>

                    <div class="pt-3 border-t border-slate-100">
                        <h4 class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Описание</h4>
                        <p class="text-sm text-slate-600 leading-relaxed whitespace-pre-line">
                            ${p.description || 'Описание товара скоро будет добавлено.'}
                        </p>
                    </div>

                    <!-- Store Guarantees -->
                    <div class="p-3 bg-slate-50 rounded-xl border border-slate-100 grid grid-cols-2 gap-2 text-xs text-slate-600 mt-4">
                        <div class="flex items-center gap-2">
                            <span class="text-emerald-600">✓</span> Гарантия качества
                        </div>
                        <div class="flex items-center gap-2">
                            <span class="text-emerald-600">✓</span> Быстрая доставка
                        </div>
                        <div class="flex items-center gap-2">
                            <span class="text-emerald-600">✓</span> Оплата при получении
                        </div>
                        <div class="flex items-center gap-2">
                            <span class="text-emerald-600">✓</span> Проверка перед покупкой
                        </div>
                    </div>
                </div>
            </div>

            <!-- Sticky Bottom Action Bar -->
            <div class="fixed bottom-0 left-0 right-0 p-4 bg-white/95 backdrop-blur-md border-t border-slate-100 flex items-center gap-3 z-30 max-w-lg mx-auto">
                <div class="flex-1">
                    <span class="text-[11px] text-slate-400 block font-medium">Итого к оплате</span>
                    <span class="text-lg font-black text-slate-900">${Utils.formatPrice(p.price)}</span>
                </div>
                <button onclick="ProductModalComponent.proceedToCheckout()" 
                        ${!isBuyable ? 'disabled' : ''}
                        class="flex-[2] py-3.5 px-6 rounded-xl font-bold text-sm text-white shadow-md transition-all flex items-center justify-center gap-2 ${isBuyable ? 'bg-emerald-600 hover:bg-emerald-700 active:scale-95 shadow-emerald-500/20' : 'bg-slate-300 cursor-not-allowed shadow-none'}">
                    <span>${isBuyable ? 'Оформить заказ' : 'Недоступен'}</span>
                    ${isBuyable ? '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"></path></svg>' : ''}
                </button>
            </div>
        `;

        // Bind slider scroll listener for dot updates
        const slider = document.getElementById('modal-gallery-slider');
        if (slider && photos.length > 1) {
            slider.addEventListener('scroll', () => {
                const scrollLeft = slider.scrollLeft;
                const width = slider.offsetWidth;
                const activeIndex = Math.round(scrollLeft / width);
                photos.forEach((_, i) => {
                    const dot = document.getElementById(`dot-${i}`);
                    if (dot) {
                        if (i === activeIndex) {
                            dot.className = 'w-4 h-2 rounded-full transition-all bg-emerald-600';
                        } else {
                            dot.className = 'w-2 h-2 rounded-full transition-all bg-slate-200';
                        }
                    }
                });
            });
        }
    },

    proceedToCheckout() {
        if (!this.currentProduct) return;
        TelegramService.haptic('medium');
        const prod = this.currentProduct;
        this.close();
        CheckoutModalComponent.open(prod);
    }
};

window.ProductModalComponent = ProductModalComponent;
