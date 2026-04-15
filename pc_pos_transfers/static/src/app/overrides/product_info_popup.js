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
            this._injectTransferButton();
            // Observer in case the title section renders late
            this._observer = new MutationObserver(() => this._injectTransferButton());
            const modal = document.querySelector('.modal-body');
            if (modal) {
                this._observer.observe(modal, { childList: true, subtree: true });
            }
        });

        onWillUnmount(() => {
            if (this._observer) {
                this._observer.disconnect();
                this._observer = null;
            }
        });
    },

    _injectTransferButton() {
        // Find the title section with "Disponible: X Unidades"
        const titleSection = document.querySelector('.section-product-info-title');
        if (!titleSection) return;
        if (titleSection.querySelector('.transfer-main-btn')) return;

        const btn = document.createElement('button');
        btn.className = 'btn btn-sm btn-outline-primary transfer-main-btn mt-2';
        btn.innerHTML = '<i class="fa fa-exchange me-1"></i>Solicitar traslado de otra tienda';
        btn.addEventListener('click', (ev) => {
            ev.stopPropagation();
            this._openTransferRequest();
        });
        titleSection.appendChild(btn);
    },

    _openTransferRequest() {
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

        // Get warehouse info from accordion if available
        const warehouses = [];
        const rows = document.querySelectorAll('.accordion-content .border-start > .d-flex.gap-2');
        rows.forEach((row) => {
            const divs = row.querySelectorAll(':scope > div');
            if (divs.length < 2) return;
            const whName = divs[0].textContent.replace(':', '').trim();
            const qtyText = divs[1].querySelector('.fw-bolder')?.textContent?.trim();
            const qty = parseFloat(qtyText) || 0;
            if (qty > 0) {
                warehouses.push({ name: whName, qty: qty });
            }
        });

        this.dialogService.add(TransferRequestPopup, {
            productTemplate: productTemplate,
            productId: productId,
            warehouseName: warehouses.length > 0 ? warehouses[0].name : '',
            availableQty: warehouses.length > 0 ? warehouses[0].qty : 0,
            availableWarehouses: warehouses,
            close: () => {},
        });
    },
});
