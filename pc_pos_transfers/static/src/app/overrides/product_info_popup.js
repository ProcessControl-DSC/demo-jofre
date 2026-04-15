/** @odoo-module */
import { ProductInfoPopup } from "@point_of_sale/app/components/popups/product_info_popup/product_info_popup";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onWillUnmount } from "@odoo/owl";
import { TransferRequestPopup } from "@pc_pos_transfers/app/transfer_request/transfer_request_popup";

patch(ProductInfoPopup.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialogService = useService("dialog");
        this._observer = null;

        onMounted(() => {
            // Watch for accordion content appearing (when user clicks "Inventario")
            this._observer = new MutationObserver(() => {
                this._injectTransferButtons();
            });
            // Observe the entire modal for changes (accordion expand/collapse)
            const modal = document.querySelector('.modal-body');
            if (modal) {
                this._observer.observe(modal, { childList: true, subtree: true, attributes: true });
            }
            // Also try immediately in case accordion is already open
            this._injectTransferButtons();
        });

        onWillUnmount(() => {
            if (this._observer) {
                this._observer.disconnect();
                this._observer = null;
            }
        });
    },

    _injectTransferButtons() {
        const container = document.querySelector('.accordion-content .border-start');
        if (!container) return;
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
