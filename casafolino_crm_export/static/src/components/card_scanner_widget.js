/** @odoo-module */
import { Component, useState, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

class CardScannerWidget extends Component {
    static template = "casafolino_crm_export.CardScannerWidget";
    static props = ["*"];

    setup() {
        this.state = useState({
            step: "capture",
            imageData: null,
            imagePreview: null,
            formData: {
                first_name: "",
                last_name: "",
                email: "",
                phone: "",
                mobile: "",
                company: "",
                job_title: "",
                country: "",
                city: "",
                address: "",
                website: "",
                country_code: "",
            },
            language: "en_US",
            error: null,
            leadId: null,
            leadName: null,
            emailSent: false,
        });
        this.fileInputRef = useRef("fileInput");
        this.notification = useService("notification");
        this.action = useService("action");
    }

    onCaptureClick() {
        this.fileInputRef.el.click();
    }

    onFileChange(ev) {
        const file = ev.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = async (e) => {
            const dataUrl = e.target.result;
            this.state.imagePreview = dataUrl;
            const base64 = dataUrl.split(",")[1];
            this.state.imageData = base64;
            this.state.step = "loading";
            this.state.error = null;

            try {
                const result = await rpc("/casafolino/crm/card-scan", {
                    image_data: base64,
                });
                if (result.error) {
                    this.state.error = result.error;
                    this.state.step = "preview";
                    return;
                }
                const data = result.data || {};
                Object.keys(this.state.formData).forEach((key) => {
                    if (data[key] !== undefined && data[key] !== null) {
                        this.state.formData[key] = data[key];
                    }
                });
                if (data.suggested_lang) {
                    this.state.language = data.suggested_lang;
                }
                this.state.step = "preview";
            } catch (err) {
                this.state.error = "Errore di connessione. Compila manualmente.";
                this.state.step = "preview";
            }
        };
        reader.readAsDataURL(file);
    }

    onFieldInput(ev) {
        const field = ev.target.dataset.field;
        if (field) {
            this.state.formData[field] = ev.target.value;
        }
    }

    onLanguageChange(ev) {
        this.state.language = ev.target.value;
    }

    async onConfirmSend() {
        await this._submitCard(true);
    }

    async onSaveOnly() {
        await this._submitCard(false);
    }

    async _submitCard(sendEmail) {
        this.state.step = "submitting";
        this.state.error = null;
        try {
            const result = await rpc("/casafolino/crm/card-confirm", {
                form_data: this.state.formData,
                image_data: this.state.imageData,
                language: this.state.language,
                send_email: sendEmail,
            });
            if (result.success) {
                this.state.leadId = result.lead_id;
                this.state.leadName = result.lead_name;
                this.state.emailSent = result.email_sent;
                this.state.step = "done";
                this.notification.add(
                    sendEmail ? "Lead creato e email inviata!" : "Lead salvato!",
                    { type: "success" }
                );
            } else {
                this.state.error = result.error || "Errore nella creazione del lead.";
                this.state.step = "preview";
            }
        } catch (err) {
            this.state.error = "Errore di connessione. Riprova.";
            this.state.step = "preview";
        }
    }

    onOpenLead() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "crm.lead",
            res_id: this.state.leadId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    onScanAnother() {
        this.state.step = "capture";
        this.state.imageData = null;
        this.state.imagePreview = null;
        this.state.error = null;
        this.state.leadId = null;
        this.state.leadName = null;
        this.state.emailSent = false;
        Object.keys(this.state.formData).forEach((key) => {
            this.state.formData[key] = "";
        });
        this.state.language = "en_US";
        if (this.fileInputRef.el) {
            this.fileInputRef.el.value = "";
        }
    }
}

registry.category("actions").add("casafolino_card_scanner", CardScannerWidget);
