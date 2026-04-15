/** @odoo-module */
/**
 * Global DOM observer that injects a "Solicitar traslado" button into the
 * ProductInfoPopup whenever it appears. This avoids all OWL lifecycle issues
 * since it works purely at the DOM level.
 */
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
            // Look for the ProductInfoPopup's title section
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

    _openTransferFromProductInfo() {
        this.dialog.add(TransferRequestPopup, {
            close: () => {},
        });
    },
});
