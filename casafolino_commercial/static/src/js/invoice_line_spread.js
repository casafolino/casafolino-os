/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { Record } from "@web/model/relational_model/record";
import { StaticList } from "@web/model/relational_model/static_list";

const SPREAD_FIELDS = {
    account_id: _t("conto"),
    discount: _t("sconto"),
};

let isSpreadingInvoiceLineValues = false;

function getInvoiceLineSiblings(record) {
    const parent = record?._parentRecord;
    const invoiceLines = parent?.data?.invoice_line_ids;
    if (parent?.resModel !== "account.move" || invoiceLines?.resModel !== "account.move.line") {
        return [];
    }
    return invoiceLines.records.filter(
        (line) =>
            line !== record && line.resModel === "account.move.line" && !line.data.display_type
    );
}

function shouldSpreadFromLine(record) {
    return (
        !isSpreadingInvoiceLineValues &&
        record?.resModel === "account.move.line" &&
        !record.data.display_type &&
        record._parentRecord?.resModel === "account.move"
    );
}

function confirmSpread(labels) {
    const fieldText = labels.join(", ");
    return window.confirm(
        _t("Vuoi estendere %s a tutte le altre righe della fattura?", fieldText)
    );
}

async function spreadRecordFields(sourceRecord, changes) {
    const targetRecords = getInvoiceLineSiblings(sourceRecord);
    if (!targetRecords.length) {
        return;
    }
    const spreadChanges = {};
    const labels = [];
    for (const fieldName of Object.keys(SPREAD_FIELDS)) {
        if (fieldName in changes && fieldName in sourceRecord.fields) {
            spreadChanges[fieldName] = changes[fieldName];
            labels.push(SPREAD_FIELDS[fieldName]);
        }
    }
    if (!labels.length || !confirmSpread(labels)) {
        return;
    }
    isSpreadingInvoiceLineValues = true;
    try {
        await Promise.all(targetRecords.map((record) => record.update(spreadChanges)));
    } finally {
        isSpreadingInvoiceLineValues = false;
    }
}

function getTaxListOwner(list) {
    const lineRecord = list?._parent;
    if (
        list?.resModel !== "account.tax" ||
        lineRecord?.resModel !== "account.move.line" ||
        lineRecord.data.tax_ids !== list
    ) {
        return null;
    }
    return lineRecord;
}

async function spreadTaxes(sourceTaxList) {
    const sourceLine = getTaxListOwner(sourceTaxList);
    if (!shouldSpreadFromLine(sourceLine)) {
        return;
    }
    const targetRecords = getInvoiceLineSiblings(sourceLine).filter((line) => line.data.tax_ids);
    if (!targetRecords.length || !confirmSpread([_t("imposte")])) {
        return;
    }
    const sourceIds = sourceTaxList.currentIds.filter((id) => typeof id === "number");
    isSpreadingInvoiceLineValues = true;
    try {
        await Promise.all(
            targetRecords.map((record) => {
                const taxList = record.data.tax_ids;
                const currentIds = taxList.currentIds.filter((id) => typeof id === "number");
                return taxList.addAndRemove({
                    add: sourceIds.filter((id) => !currentIds.includes(id)),
                    remove: currentIds.filter((id) => !sourceIds.includes(id)),
                });
            })
        );
    } finally {
        isSpreadingInvoiceLineValues = false;
    }
}

patch(Record.prototype, {
    async update(changes, options) {
        const result = await super.update(changes, options);
        if (shouldSpreadFromLine(this)) {
            await spreadRecordFields(this, changes);
        }
        return result;
    },
});

patch(StaticList.prototype, {
    async addAndRemove(params) {
        const result = await super.addAndRemove(params);
        await spreadTaxes(this);
        return result;
    },

    async forget(record) {
        const result = await super.forget(record);
        await spreadTaxes(this);
        return result;
    },
});
