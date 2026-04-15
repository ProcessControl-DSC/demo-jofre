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

        onMounted(() => {
            // Find the modal footer (where Añadir/Descartar buttons are)
            const footer = document.querySelector('.modal-footer');
            if (!footer) return;
            if (footer.querySelector('.transfer-main-btn')) return;

            const btn = document.createElement('button');
            btn.className = 'btn btn-outline-primary transfer-main-btn';
            btn.innerHTML = '<i class="fa fa-exchange me-1"></i>Solicitar traslado';
            btn.addEventListener('click', (ev) => {
                ev.stopPropagation();
                this._openTransferRequest();
            });
            footer.prepend(btn);
        });

        onWillUnmount(() => {});
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

        this.dialogService.add(TransferRequestPopup, {
            productTemplate: productTemplate,
            productId: productId,
            warehouseName: '',
            availableQty: 0,
            availableWarehouses: [],
            close: () => {},
        });
    },
});
