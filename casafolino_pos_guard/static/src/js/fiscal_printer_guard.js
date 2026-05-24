/** @odoo-module **/

const isFiscalPrinterSerialError = (reason) => {
    const message = reason?.message || "";
    const stack = reason?.stack || "";
    return (
        message.includes("Failed to fetch") &&
        (stack.includes("getPrinterSerialNumber") ||
            stack.includes("directIO") ||
            stack.includes("sendCommand"))
    );
};

window.addEventListener(
    "unhandledrejection",
    (event) => {
        if (!isFiscalPrinterSerialError(event.reason)) {
            return;
        }
        console.warn(
            "[CasaFolino POS] Stampante fiscale non raggiungibile durante il controllo seriale; apertura POS mantenuta.",
            event.reason
        );
        event.preventDefault();
    },
    true
);
