/**
 * API Client for TMA Backend endpoints.
 */

const Api = {
    baseUrl: '/api',

    getHeaders() {
        const headers = {
            'Content-Type': 'application/json'
        };
        const initData = TelegramService.getInitData();
        if (initData) {
            headers['X-Telegram-Init-Data'] = initData;
        }
        return headers;
    },

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            ...options,
            headers: {
                ...this.getHeaders(),
                ...(options.headers || {})
            }
        };

        try {
            const response = await fetch(url, config);
            const data = await response.json();

            if (!response.ok) {
                const errorMsg = data.detail || 'Произошла непредвиденная ошибка';
                throw new Error(errorMsg);
            }

            return data;
        } catch (error) {
            console.error(`API Error on [${url}]:`, error);
            throw error;
        }
    },

    // Products
    async getProducts(search = '', inStockOnly = false) {
        const params = new URLSearchParams();
        if (search) params.append('search', search);
        if (inStockOnly) params.append('in_stock_only', 'true');
        
        const query = params.toString() ? `?${params.toString()}` : '';
        return await this.request(`/products${query}`);
    },

    async getProduct(productId) {
        return await this.request(`/products/${productId}`);
    },

    // Store Info & Requisites
    async getStoreInfo() {
        return await this.request('/store/info');
    },

    // Orders
    async createOrder(orderData) {
        return await this.request('/orders', {
            method: 'POST',
            body: JSON.stringify(orderData)
        });
    },

    async getMyOrders() {
        return await this.request('/orders/my');
    },

    async markOrderReceived(orderId) {
        return await this.request(`/orders/${orderId}/received`, {
            method: 'PATCH'
        });
    }
};

window.Api = Api;
