/** @odoo-module */
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";
import { TransferRequestPopup } from "@pc_pos_transfers/app/transfer_request/transfer_request_popup";

let globalObserver = null;

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this._startProductInfoObserver();
    },

    _startProductInfoObserver() {
        if (globalObserver) return;
        const self = this;

        globalObserver = new MutationObserver(() => {
            const titleSection = document.querySelector('.section-product-info-title');
            if (!titleSection) return;
            if (titleSection.querySelector('.transfer-main-btn')) return;

            const btn = document.createElement('button');
            btn.className = 'btn btn-sm btn-outline-primary transfer-main-btn mt-2';
            btn.style.cssText = 'font-size: 14px; padding: 6px 16px;';
            btn.innerHTML = '<i class="fa fa-exchange me-2"></i>Solicitar traslado de otra tienda';
            btn.addEventListener('click', (ev) => {
                ev.stopPropagation();
                ev.preventDefault();
                self._openTransferFromProductInfo();
            });
            titleSection.appendChild(btn);
        });

        globalObserver.observe(document.body, {
            childList: true,
            subtree: true,
        });
    },

    _extractWarehousesFromPopup() {
        const warehouses = [];
        const rows = document.querySelectorAll('.accordion-content .border-start > .d-flex.gap-2');
        rows.forEach((row) => {
            const divs = row.querySelectorAll(':scope > div');
            if (divs.length < 2) return;
            const whName = divs[0].textContent.replace(':', '').trim();
            const qtyText = divs[1].querySelector('.fw-bolder')?.textContent?.trim();
            const qty = parseFloat(qtyText) || 0;
            warehouses.push({ name: whName, qty: qty });
        });
        return warehouses;
    },

    _extractProductNameFromPopup() {
        
        
        const h4 = document.querySelector('.modal-header');
        if (h4) {
            const text = h4.textContent || '';
            return text.split('|')[0].trim();
        }
        return '';
    },

    _openTransferFromProductInfo() {
        const warehouses = this._extractWarehousesFromPopup();
        const productName = this._extractProductNameFromPopup();
        const withStock = warehouses.filter(w => w.qty > 0);

        this.dialog.add(TransferRequestPopup, {
            productName: productName,
            availableWarehouses: withStock,
            warehouseName: withStock.length > 0 ? withStock[0].name : '',
            availableQty: withStock.length > 0 ? withStock[0].qty : 0,
            close: () => {},
        });
    },
});
