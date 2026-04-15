/** @odoo-module */
import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { AlterationReceipt } from "@pc_pos_alterations/app/alteration_receipt/alteration_receipt";

export class AlterationPopup extends Component {
    static template = "pc_pos_alterations.AlterationPopup";
    static components = { Dialog };
    static props = {
        orderline: { type: Object, optional: true },
        order: { type: Object, optional: true },
        close: Function,
    };

    setup() {
        this.pos = usePos();
        this.printer = useService("printer");
        const alterationTypes = this.pos.models["alteration.type"].getAll();
        const defaultType = alterationTypes.length > 0 ? alterationTypes[0] : null;
        const defaultDays = defaultType ? defaultType.default_duration_days : 3;
        const defaultCost = defaultType && defaultType.product_id
            ? defaultType.product_id.list_price
            : 0;

        const today = new Date();
        today.setDate(today.getDate() + defaultDays);
        const defaultDate = today.toISOString().split("T")[0];

        this.state = useState({
            alterationTypeId: defaultType ? defaultType.id : false,
            description: "",
            datePromised: defaultDate,
            deliveryMethod: "pickup_store",
            cost: defaultCost,
            tailorId: false,
        });

        this.alterationTypes = alterationTypes;
    }

    get productName() {
        if (this.props.orderline && this.props.orderline.product_id) {
            return this.props.orderline.product_id.display_name;
        }
        return "";
    }

    get partnerName() {
        const order = this.props.order || this.pos.getOrder();
        if (order && order.partner_id) {
            return order.partner_id.name;
        }
        return _t("Sin cliente");
    }

    onTypeChange(ev) {
        const typeId = parseInt(ev.target.value);
        this.state.alterationTypeId = typeId;
        const altType = this.alterationTypes.find((t) => t.id === typeId);
        if (altType) {
            const days = altType.default_duration_days || 3;
            const today = new Date();
            today.setDate(today.getDate() + days);
            this.state.datePromised = today.toISOString().split("T")[0];
            this.state.cost = altType.product_id ? altType.product_id.list_price : 0;
        }
    }

    onDescriptionChange(ev) {
        this.state.description = ev.target.value;
    }

    onDateChange(ev) {
        this.state.datePromised = ev.target.value;
    }

    onDeliveryMethodChange(ev) {
        this.state.deliveryMethod = ev.target.value;
    }

    async onClickConfirm() {
        if (!this.state.alterationTypeId) {
            return;
        }

        // 1. Buscar el tipo de arreglo y su producto asociado
        const altType = this.alterationTypes.find(
            (t) => t.id === this.state.alterationTypeId
        );
        if (!altType || !altType.product_id) {
            return;
        }

        // 2. Obtener el registro del producto desde los datos del POS
        const product = this.pos.models["product.product"].get(altType.product_id.id);
        if (!product) {
            console.error("Producto de arreglo no encontrado en el POS:", altType.product_id.id);
            return;
        }

        // 3. Añadir el producto de arreglo como nueva línea al pedido actual
        const order = this.props.order || this.pos.getOrder();
        const orderline = this.props.orderline;

        await this.pos.addLineToCurrentOrder(
            {
                product_tmpl_id: product.product_tmpl_id,
                price_unit: altType.product_id.list_price,
            },
            {},
            false
        );

        // 4. Configurar la línea recién añadida con nota y referencia a la prenda
        const newLine = order.getSelectedOrderline();
        if (newLine) {
            // Almacenar datos del arreglo en customer_note con formato parseable:
            // "descripción|fecha_prometida|método_entrega"
            const garmentName = orderline?.product_id?.display_name || "";
            const noteDesc = this.state.description
                ? `Arreglo para: ${garmentName}. ${this.state.description}`
                : `Arreglo para: ${garmentName}`;
            const noteData = `${noteDesc}|${this.state.datePromised}|${this.state.deliveryMethod}`;
            newLine.setCustomerNote(noteData);

            // Vincular la línea de arreglo a la línea de la prenda original
            if (orderline) {
                newLine.alteration_for_line_id = orderline;
            }
        }

        // 5. Imprimir ticket del arreglo en la impresora de recibos
        await this._printAlterationReceipt(altType, orderline, order);

        // 6. Cerrar el popup
        this.props.close();
    }

    /**
     * Construye los datos del arreglo e imprime el ticket en la impresora
     * de recibos del TPV (IoT o web fallback).
     */
    async _printAlterationReceipt(altType, orderline, order) {
        try {
            // Datos de la tienda
            const company = this.pos.company;
            const config = this.pos.config;
            let storeName = "";
            let storeAddress = "";

            // Intentar obtener nombre de la tienda desde el picking_type (almacén)
            if (config.picking_type_id && config.picking_type_id.warehouse_id) {
                storeName = config.picking_type_id.warehouse_id.name || "";
            }
            if (!storeName && company) {
                storeName = company.name || "";
            }

            // Construir dirección de la tienda desde la compañía
            if (company) {
                const addressParts = [];
                if (company.street) {
                    addressParts.push(company.street);
                }
                if (company.city) {
                    addressParts.push(company.city);
                }
                if (company.zip) {
                    addressParts.push(company.zip);
                }
                storeAddress = addressParts.join(", ");
            }

            // Datos del cliente
            const partner = order.partner_id;
            const partnerName = partner ? partner.name : "Sin identificar";
            const partnerPhone = partner ? (partner.phone || partner.mobile || "") : "";

            // Datos del producto (la prenda)
            const product = orderline ? orderline.product_id : null;
            const productName = product ? product.display_name : "N/A";
            const productRef = product ? (product.barcode || product.default_code || "") : "";

            // Referencia del pedido
            const orderRef = order.name || "";

            // Logo de la empresa (base64)
            const companyLogo = company ? company.logo : false;

            const alterationData = {
                company_logo: companyLogo,
                store_name: storeName,
                store_address: storeAddress,
                date: new Date().toLocaleString("es-ES"),
                partner_name: partnerName,
                partner_phone: partnerPhone,
                product_name: productName,
                product_ref: productRef,
                alteration_type: altType.name || "",
                description: this.state.description || "",
                date_promised: this.state.datePromised || "",
                delivery_method: this.state.deliveryMethod || "",
                order_ref: orderRef,
            };

            await this.printer.print(
                AlterationReceipt,
                { alteration: alterationData },
                { webPrintFallback: true }
            );
        } catch (e) {
            console.warn("No se pudo imprimir el ticket de arreglo:", e);
        }
    }

    onClickCancel() {
        this.props.close();
    }
}
