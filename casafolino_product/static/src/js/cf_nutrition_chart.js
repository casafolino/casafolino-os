/** @odoo-module **/

import { Component, useRef, onMounted, onPatched } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const COLORS = {
    fat: "#e8821e",
    carbs: "#5A6E3A",
    protein: "#4a90d9",
    fiber: "#85bb2f",
};

const FALLBACK_LABELS = {
    fat: "Grassi",
    carbs: "Carboidrati",
    protein: "Proteine",
    fiber: "Fibre",
};

class CfNutritionChart extends Component {
    static template = "casafolino_nutrition.CfNutritionChart";
    static props = { ...standardFieldProps };

    setup() {
        this.canvasRef = useRef("canvas");
        onMounted(() => this._draw());
        onPatched(() => this._draw());
    }

    get _parsed() {
        try {
            const raw = this.props.record.data[this.props.name];
            return raw ? JSON.parse(raw) : {};
        } catch {
            return {};
        }
    }

    get hasData() {
        const d = this._parsed;
        return Object.keys(d).some((k) => k !== "labels" && d[k] > 0);
    }

    get legendItems() {
        const d = this._parsed;
        const labels = d.labels || FALLBACK_LABELS;
        return Object.keys(COLORS)
            .filter((k) => d[k] > 0)
            .map((k) => ({ key: k, color: COLORS[k], label: labels[k] || k, pct: d[k] }));
    }

    _draw() {
        const canvas = this.canvasRef.el;
        if (!canvas) return;
        const d = this._parsed;
        if (!this.hasData) return;

        const ctx = canvas.getContext("2d");
        const w = canvas.width;
        const h = canvas.height;
        const cx = w / 2;
        const cy = h / 2;
        const outer = Math.min(cx, cy) - 6;
        const inner = outer * 0.52;

        ctx.clearRect(0, 0, w, h);

        const segments = Object.keys(COLORS).filter((k) => d[k] > 0);
        let startAngle = -Math.PI / 2;

        for (const key of segments) {
            const angle = (d[key] / 100) * 2 * Math.PI;
            ctx.beginPath();
            ctx.moveTo(cx, cy);
            ctx.arc(cx, cy, outer, startAngle, startAngle + angle);
            ctx.closePath();
            ctx.fillStyle = COLORS[key];
            ctx.fill();
            startAngle += angle;
        }

        // inner hole
        ctx.beginPath();
        ctx.arc(cx, cy, inner, 0, 2 * Math.PI);
        ctx.fillStyle = "#fff";
        ctx.fill();

        // centre text
        ctx.fillStyle = "#495057";
        ctx.font = "bold 11px Arial, sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText("Macro", cx, cy - 7);
        ctx.font = "10px Arial, sans-serif";
        ctx.fillText("% g/100g", cx, cy + 7);
    }
}

registry.category("fields").add("cf_nutrition_chart", {
    component: CfNutritionChart,
    supportedTypes: ["char"],
});
