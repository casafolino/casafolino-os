/** @odoo-module **/

document.addEventListener("change", (event) => {
    const input = event.target.closest(".cf-qty");
    if (!input) {
        return;
    }
    const step = Number(input.step || 1);
    const min = Number(input.min || step);
    let value = Number(input.value || min);
    value = Math.max(value, min);
    if (step > 1 && value % step) {
        value = Math.ceil(value / step) * step;
    }
    input.value = value;
});
