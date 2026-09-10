/**
 * Checkout Modal Component: Multi-option Delivery, Requisites, Crypto/SBP Copy, and Order Creation.
 */

const CheckoutModalComponent = {
    product: null,
    storeInfo: null,
    deliveryType: 'delivery', // 'pickup' | 'delivery'
    deliveryProvider: 'СДЭК',  // 'СДЭК' | 'Почта России'
    paymentMethod: 'sbp',     // 'cash' | 'sbp' | 'usdt_ton' | 'usdt_trc20' | 'ton'
    cryptoNetwork: 'usdt_ton',
    isSubmitting: false,

    async open(product) {
        TelegramService.haptic('light');
        this.product = product;
        const modal = document.getElementById('checkout-modal');
        if (!modal) return;

        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';

        TelegramService.showBackButton(() => {
            this.close();
        });

        // Prefill default delivery and payment
        this.deliveryType = 'delivery';
        this.deliveryProvider = 'СДЭК';
        this.paymentMethod = 'sbp';

        // Load store info / requisites if not loaded
        if (!this.storeInfo) {
            try {
                this.storeInfo = await Api.getStoreInfo();
            } catch (e) {
                console.error("Could not load store info:", e);
            }
        }

        this.render();
    },

    close() {
        TelegramService.haptic('light');
        const modal = document.getElementById('checkout-modal');
        if (modal) {
            modal.classList.add('hidden');
        }
        document.body.style.overflow = '';
        TelegramService.hideBackButton();
        this.product = null;
    },

    setDeliveryType(type) {
        TelegramService.haptic('selection');
        this.deliveryType = type;
        // If switched to delivery and cash was selected, fallback to SBP
        if (type === 'delivery' && this.paymentMethod === 'cash') {
            this.paymentMethod = 'sbp';
        }
        this.render();
    },

    setDeliveryProvider(provider) {
        TelegramService.haptic('selection');
        this.deliveryProvider = provider;
        this.render();
    },

    setPaymentMethod(method) {
        TelegramService.haptic('selection');
        this.paymentMethod = method;
        this.render();
    },

    setCryptoNetwork(network) {
        TelegramService.haptic('selection');
        this.cryptoNetwork = network;
        this.paymentMethod = network; // maps to usdt_ton, usdt_trc20, ton
        this.render();
    },

    render() {
        const container = document.getElementById('checkout-modal-content');
        const p = this.product;
        if (!container || !p) return;

        const tgUser = TelegramService.getUser();
        const info = this.storeInfo || {
            sbp_phone: "+7 (999) 000-00-00",
            sbp_bank: "Т-Банк",
            sbp_receiver_name: "Иван И.",
            crypto_ton_wallet: "EQD1234567890abcdef1234567890abcdef1234567890abc",
            crypto_usdt_ton_wallet: "EQD1234567890abcdef1234567890abcdef1234567890abc",
            crypto_usdt_trc20_wallet: "TXYZ1234567890abcdef1234567890abcdef123",
            pickup_address: "г. Москва, ул. Примерная, д. 10, оф. 205",
            pickup_working_hours: "Пн-Пт: 10:00 - 20:00, Сб-Вс: 11:00 - 18:00",
            pickup_instructions: "Для входа наберите на домофоне 205 или позвоните менеджеру."
        };

        // Determine active crypto address
        let activeCryptoWallet = info.crypto_usdt_ton_wallet;
        if (this.paymentMethod === 'usdt_trc20') {
            activeCryptoWallet = info.crypto_usdt_trc20_wallet;
        } else if (this.paymentMethod === 'ton') {
            activeCryptoWallet = info.crypto_ton_wallet;
        }

        container.innerHTML = `
            <div class="p-4 sm:p-6 pb-28 animate-fade-in max-h-[85vh] overflow-y-auto no-scrollbar">
                <!-- Header -->
                <div class="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
                    <div>
                        <h2 class="text-base font-bold text-slate-900">Оформление заказа</h2>
                        <p class="text-xs text-slate-500">${p.title}</p>
                    </div>
                    <button onclick="CheckoutModalComponent.close()" class="w-8 h-8 rounded-full bg-slate-100 text-slate-500 flex items-center justify-center active:scale-90 transition-transform">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                    </button>
                </div>

                <form id="checkout-form" onsubmit="CheckoutModalComponent.submitOrder(event)" class="space-y-4">
                    <!-- 1. SPOSOB POLUCHENIYA -->
                    <div>
                        <label class="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">1. Способ получения</label>
                        <div class="grid grid-cols-2 gap-2 bg-slate-100 p-1 rounded-xl">
                            <button type="button" 
                                    onclick="CheckoutModalComponent.setDeliveryType('delivery')"
                                    class="py-2.5 rounded-lg text-xs font-bold transition-all ${this.deliveryType === 'delivery' ? 'bg-white text-emerald-700 shadow-xs' : 'text-slate-600'}">
                                🚚 Доставка
                            </button>
                            <button type="button" 
                                    onclick="CheckoutModalComponent.setDeliveryType('pickup')"
                                    class="py-2.5 rounded-lg text-xs font-bold transition-all ${this.deliveryType === 'pickup' ? 'bg-white text-emerald-700 shadow-xs' : 'text-slate-600'}">
                                🚶‍♂️ Самовывоз
                            </button>
                        </div>
                    </div>

                    <!-- Pickup info or Delivery Fields -->
                    ${this.deliveryType === 'pickup' ? `
                        <div class="p-3.5 bg-emerald-50/60 rounded-2xl border border-emerald-100 text-xs space-y-2 text-slate-700">
                            <div>
                                <span class="font-bold text-emerald-800 block">📍 Адрес пункта выдачи:</span>
                                <span>${info.pickup_address}</span>
                            </div>
                            <div>
                                <span class="font-bold text-emerald-800 block">⏰ Часы работы:</span>
                                <span>${info.pickup_working_hours}</span>
                            </div>
                            <div>
                                <span class="font-bold text-emerald-800 block">ℹ️ Правила визита:</span>
                                <span>${info.pickup_instructions}</span>
                            </div>
                        </div>
                    ` : `
                        <!-- Delivery Provider Selection -->
                        <div>
                            <label class="block text-[11px] font-semibold text-slate-600 mb-1.5">Служба доставки:</label>
                            <div class="grid grid-cols-2 gap-2">
                                <button type="button" 
                                        onclick="CheckoutModalComponent.setDeliveryProvider('СДЭК')"
                                        class="p-2.5 rounded-xl border text-xs font-semibold flex items-center justify-center gap-2 transition-all ${this.deliveryProvider === 'СДЭК' ? 'border-emerald-500 bg-emerald-50/50 text-emerald-800 font-bold ring-1 ring-emerald-500' : 'border-slate-200 bg-white text-slate-700'}">
                                    📦 СДЭК (ПВЗ)
                                </button>
                                <button type="button" 
                                        onclick="CheckoutModalComponent.setDeliveryProvider('Почта России')"
                                        class="p-2.5 rounded-xl border text-xs font-semibold flex items-center justify-center gap-2 transition-all ${this.deliveryProvider === 'Почта России' ? 'border-emerald-500 bg-emerald-50/50 text-emerald-800 font-bold ring-1 ring-emerald-500' : 'border-slate-200 bg-white text-slate-700'}">
                                    📮 Почта России
                                </button>
                            </div>
                        </div>

                        <!-- Address input -->
                        <div>
                            <label class="block text-[11px] font-semibold text-slate-600 mb-1">Город и адрес ПВЗ / доставки *</label>
                            <input type="text" id="inp-address" required
                                   placeholder="г. Москва, ул. Тверская 12, ПВЗ №10"
                                   class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-xs focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 bg-white text-slate-800">
                        </div>
                    `}

                    <!-- Contact Details -->
                    <div class="space-y-3 pt-1">
                        <div>
                            <label class="block text-[11px] font-semibold text-slate-600 mb-1">ФИО получателя *</label>
                            <input type="text" id="inp-name" required
                                   value="${tgUser.first_name || ''} ${tgUser.last_name || ''}".trim()
                                   placeholder="Иванов Иван Иванович"
                                   class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-xs focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 bg-white text-slate-800">
                        </div>
                        <div>
                            <label class="block text-[11px] font-semibold text-slate-600 mb-1">Телефон для связи *</label>
                            <input type="tel" id="inp-phone" required
                                   placeholder="+7 (999) 000-00-00"
                                   class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-xs focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 bg-white text-slate-800">
                        </div>
                    </div>

                    <!-- 2. SPOSOB OPLATY -->
                    <div class="pt-2">
                        <label class="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">2. Способ оплаты</label>
                        <div class="grid grid-cols-3 gap-1.5">
                            <!-- SBP -->
                            <button type="button" 
                                    onclick="CheckoutModalComponent.setPaymentMethod('sbp')"
                                    class="p-2 rounded-xl border text-center text-xs font-semibold transition-all ${this.paymentMethod === 'sbp' ? 'border-emerald-500 bg-emerald-50/50 text-emerald-800 ring-1 ring-emerald-500' : 'border-slate-200 bg-white text-slate-700'}">
                                📱 СБП
                            </button>

                            <!-- Crypto -->
                            <button type="button" 
                                    onclick="CheckoutModalComponent.setPaymentMethod(CheckoutModalComponent.cryptoNetwork)"
                                    class="p-2 rounded-xl border text-center text-xs font-semibold transition-all ${['usdt_ton', 'usdt_trc20', 'ton'].includes(this.paymentMethod) ? 'border-emerald-500 bg-emerald-50/50 text-emerald-800 ring-1 ring-emerald-500' : 'border-slate-200 bg-white text-slate-700'}">
                                💎 Криптовалюта
                            </button>

                            <!-- Cash (Only for pickup) -->
                            <button type="button" 
                                    ${this.deliveryType !== 'pickup' ? 'disabled' : ''}
                                    onclick="CheckoutModalComponent.setPaymentMethod('cash')"
                                    class="p-2 rounded-xl border text-center text-xs font-semibold transition-all ${this.deliveryType !== 'pickup' ? 'opacity-40 bg-slate-50 border-slate-200 cursor-not-allowed' : (this.paymentMethod === 'cash' ? 'border-emerald-500 bg-emerald-50/50 text-emerald-800 ring-1 ring-emerald-500' : 'border-slate-200 bg-white text-slate-700')}">
                                💵 Наличные
                            </button>
                        </div>
                        ${this.deliveryType !== 'pickup' ? '<p class="text-[10px] text-slate-400 mt-1">* Оплата наличными доступна только при самовывозе</p>' : ''}
                    </div>

                    <!-- REQUISITES CARD -->
                    ${this.paymentMethod === 'sbp' ? `
                        <div class="p-3.5 bg-slate-50 rounded-2xl border border-slate-200/80 space-y-2.5">
                            <div class="flex items-center justify-between">
                                <span class="text-[11px] font-bold text-slate-500 uppercase">Реквизиты СБП</span>
                                <span class="text-[11px] font-semibold text-emerald-700 bg-emerald-100/60 px-2 py-0.5 rounded-full">${info.sbp_bank}</span>
                            </div>
                            <div class="flex items-center justify-between bg-white p-2.5 rounded-xl border border-slate-100">
                                <div>
                                    <div class="text-[11px] text-slate-400 font-medium">Номер телефона</div>
                                    <div class="text-xs font-extrabold text-slate-800">${info.sbp_phone}</div>
                                    <div class="text-[10px] text-slate-500">Получатель: ${info.sbp_receiver_name}</div>
                                </div>
                                <button type="button" onclick="Utils.copyToClipboard('${info.sbp_phone}', 'Номер телефона скопирован')" class="px-3 py-1.5 bg-emerald-50 text-emerald-700 rounded-lg text-xs font-bold hover:bg-emerald-100 active:scale-95 transition-all">
                                    Скопировать
                                </button>
                            </div>
                            <p class="text-[10px] text-slate-500 leading-tight">Переведите точную сумму <b>${Utils.formatPrice(p.price)}</b> по СБП и нажмите кнопку «Оформить заказ» ниже.</p>
                        </div>
                    ` : ''}

                    ${['usdt_ton', 'usdt_trc20', 'ton'].includes(this.paymentMethod) ? `
                        <div class="p-3.5 bg-slate-50 rounded-2xl border border-slate-200/80 space-y-2.5">
                            <div class="flex items-center justify-between">
                                <span class="text-[11px] font-bold text-slate-500 uppercase">Сеть криптовалюты:</span>
                                <div class="flex gap-1">
                                    <button type="button" onclick="CheckoutModalComponent.setCryptoNetwork('usdt_ton')" class="px-2 py-0.5 text-[10px] rounded-md font-bold ${this.paymentMethod === 'usdt_ton' ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-600'}">USDT TON</button>
                                    <button type="button" onclick="CheckoutModalComponent.setCryptoNetwork('usdt_trc20')" class="px-2 py-0.5 text-[10px] rounded-md font-bold ${this.paymentMethod === 'usdt_trc20' ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-600'}">USDT TRC20</button>
                                    <button type="button" onclick="CheckoutModalComponent.setCryptoNetwork('ton')" class="px-2 py-0.5 text-[10px] rounded-md font-bold ${this.paymentMethod === 'ton' ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-600'}">TON</button>
                                </div>
                            </div>
                            <div class="bg-white p-2.5 rounded-xl border border-slate-100 space-y-2">
                                <div class="text-[10px] text-slate-400 font-medium">Адрес кошелька (${this.paymentMethod.toUpperCase().replace('_', ' ')}):</div>
                                <div class="text-[11px] font-mono font-bold text-slate-800 break-all bg-slate-50 p-2 rounded-lg">
                                    ${activeCryptoWallet}
                                </div>
                                <div class="flex justify-end">
                                    <button type="button" onclick="Utils.copyToClipboard('${activeCryptoWallet}', 'Адрес кошелька скопирован')" class="px-3 py-1.5 bg-emerald-50 text-emerald-700 rounded-lg text-xs font-bold hover:bg-emerald-100 active:scale-95 transition-all">
                                        Скопировать адрес
                                    </button>
                                </div>
                            </div>
                            <div>
                                <label class="block text-[10px] text-slate-500 font-medium mb-1">Хеш транзакции (TxID) — опционально:</label>
                                <input type="text" id="inp-txid" placeholder="Вставьте TxID перевода для быстрой сверки" class="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs bg-white text-slate-800 focus:outline-none focus:border-emerald-500">
                            </div>
                        </div>
                    ` : ''}

                    ${this.paymentMethod === 'cash' ? `
                        <div class="p-3 bg-emerald-50/60 rounded-xl border border-emerald-100 text-xs text-slate-700">
                            💵 Оплата наличными производится сотруднику при получении товара в пункте самовывоза.
                        </div>
                    ` : ''}
                </form>
            </div>

            <!-- Sticky Bottom Confirmation Bar -->
            <div class="fixed bottom-0 left-0 right-0 p-4 bg-white/95 backdrop-blur-md border-t border-slate-100 flex items-center gap-3 z-30 max-w-lg mx-auto">
                <div class="flex-1">
                    <span class="text-[11px] text-slate-400 block font-medium">К оплате:</span>
                    <span class="text-base font-black text-slate-900">${Utils.formatPrice(p.price)}</span>
                </div>
                <button type="button" 
                        id="submit-order-btn"
                        onclick="CheckoutModalComponent.triggerFormSubmit()"
                        class="flex-[2] py-3.5 px-6 rounded-xl font-bold text-sm text-white bg-emerald-600 hover:bg-emerald-700 active:scale-95 shadow-md shadow-emerald-500/20 transition-all flex items-center justify-center gap-2">
                    <span>Подтвердить заказ</span>
                </button>
            </div>
        `;
    },

    triggerFormSubmit() {
        const form = document.getElementById('checkout-form');
        if (form) {
            form.requestSubmit();
        }
    },

    async submitOrder(event) {
        event.preventDefault();
        if (this.isSubmitting || !this.product) return;

        const nameInp = document.getElementById('inp-name');
        const phoneInp = document.getElementById('inp-phone');
        const addressInp = document.getElementById('inp-address');
        const txIdInp = document.getElementById('inp-txid');

        const customerName = nameInp ? nameInp.value.trim() : '';
        const customerPhone = phoneInp ? phoneInp.value.trim() : '';
        const deliveryAddress = this.deliveryType === 'pickup' 
            ? (this.storeInfo?.pickup_address || "Самовывоз из магазина")
            : (addressInp ? addressInp.value.trim() : '');
        const cryptoTxId = txIdInp ? txIdInp.value.trim() : null;

        if (!customerName || !customerPhone) {
            Utils.showToast("Пожалуйста, заполните контактные данные", "error");
            return;
        }

        if (this.deliveryType === 'delivery' && !deliveryAddress) {
            Utils.showToast("Укажите адрес доставки или номер ПВЗ", "error");
            return;
        }

        this.isSubmitting = true;
        const submitBtn = document.getElementById('submit-order-btn');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = `
                <div class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                <span>Оформление...</span>
            `;
        }

        try {
            const orderPayload = {
                product_id: this.product.id,
                delivery_type: this.deliveryType,
                delivery_provider: this.deliveryType === 'delivery' ? this.deliveryProvider : null,
                delivery_address: deliveryAddress,
                customer_name: customerName,
                customer_phone: customerPhone,
                payment_method: this.paymentMethod,
                crypto_tx_id: cryptoTxId
            };

            const createdOrder = await Api.createOrder(orderPayload);
            TelegramService.haptic('success');
            this.showSuccessConfirmation(createdOrder);
        } catch (error) {
            TelegramService.haptic('error');
            Utils.showToast(error.message || "Ошибка при создании заказа", "error");
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = `<span>Подтвердить заказ</span>`;
            }
        } finally {
            this.isSubmitting = false;
        }
    },

    showSuccessConfirmation(order) {
        const container = document.getElementById('checkout-modal-content');
        if (!container) return;

        container.innerHTML = `
            <div class="p-6 text-center animate-fade-in py-10 space-y-4">
                <div class="w-16 h-16 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto shadow-sm">
                    <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"></path></svg>
                </div>

                <div>
                    <h2 class="text-xl font-extrabold text-slate-900">Заказ успешно оформлен!</h2>
                    <p class="text-sm font-bold text-emerald-600 mt-1">Номер вашего заказа: ${order.order_number}</p>
                </div>

                <div class="p-4 bg-slate-50 rounded-2xl border border-slate-100 text-left text-xs space-y-2 text-slate-600">
                    <div><b>Товар:</b> ${order.product_title}</div>
                    <div><b>Сумма:</b> ${Utils.formatPrice(order.product_price)}</div>
                    <div><b>Способ получения:</b> ${order.delivery_type_label}</div>
                    <div><b>Статус:</b> ⏳ ${order.status_label}</div>
                </div>

                <p class="text-xs text-slate-500 leading-relaxed">
                    Мы уже отправили уведомление менеджеру. Вы можете отслеживать статус заказа во вкладке <b>«Мои заказы»</b>.
                </p>

                <div class="pt-2">
                    <button onclick="CheckoutModalComponent.finishAndGoToOrders()" 
                            class="w-full py-3.5 px-6 rounded-xl font-bold text-sm text-white bg-emerald-600 hover:bg-emerald-700 active:scale-95 shadow-md shadow-emerald-500/20 transition-all">
                        Перейти в «Мои заказы»
                    </button>
                </div>
            </div>
        `;
    },

    finishAndGoToOrders() {
        this.close();
        App.switchTab('orders');
    }
};

window.CheckoutModalComponent = CheckoutModalComponent;
