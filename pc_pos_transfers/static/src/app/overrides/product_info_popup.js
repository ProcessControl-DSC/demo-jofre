/** @odoo-module */
import { ProductInfoPopup } from "@point_of_sale/app/components/popups/product_info_popup/product_info_popup";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onPatched } from "@odoo/owl";
import { TransferRequestPopup } from "@pc_pos_transfers/app/transfer_request/transfer_request_popup";

patch(ProductInfoPopup.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialogService = useService("dialog");

        const injectButtons = () => {
            // Small delay to ensure DOM is ready after dialog renders
            setTimeout(() => this._injectTransferButtons(), 100);
        };
        onMounted(injectButtons);
        onPatched(injectButtons);
    },

    _injectTransferButtons() {
        // Use document.querySelector since Dialog components don't have this.el
        const container = document.querySelector('.accordion-content .border-start');
        if (!container) return;

        // Already injected?
        if (container.querySelector('.transfer-request-btn')) return;

        const rows = container.querySelectorAll(':scope > .d-flex.gap-2');
        rows.forEach((row) => {
            const divs = row.querySelectorAll(':scope > div');
            if (divs.length < 2) return;

            const whName = divs[0].textContent.replace(':', '').trim();
            const qtyText = divs[1].querySelector('.fw-bolder')?.textContent?.trim();
            const qty = parseFloat(qtyText) || 0;

            if (qty > 0) {
                const btnDiv = document.createElement('div');
                btnDiv.className = 'ms-auto';
                btnDiv.innerHTML = '<button class="btn btn-sm btn-outline-primary py-0 px-2 transfer-request-btn"><i class="fa fa-arrow-right me-1"></i>Solicitar</button>';
                btnDiv.querySelector('button').addEventListener('click', (ev) => {
                    ev.stopPropagation();
                    this._openTransferRequest(whName, qty);
                });
                row.classList.add('align-items-center');
                row.appendChild(btnDiv);
            }
        });
    },

    _openTransferRequest(warehouseName, availableQty) {
        const productTemplate = this.props.productTemplate;

        let productId = false;
        const variants = productTemplate?.product_variant_ids;
        if (variants) {
            if (Array.isArray(variants) && variants.length > 0) {
                const first = variants[0];
                productId = typeof first === 'object' ? (first.id || false) : first;
            } else if (typeof variants === 'object' && typeof variants[Symbol.iterator] === 'function') {
                for (const v of variants) {
                    productId = typeof v === 'object' ? (v.id || false) : v;
                    break;
                }
            }
        }

        this.dialogService.add(TransferRequestPopup, {
            productTemplate: productTemplate,
            productId: productId,
            warehouseName: warehouseName,
            availableQty: availableQty,
            close: () => {},
        });
    },
});
