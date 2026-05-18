/** @odoo-module **/

import { ImageCrop } from "@web_editor/js/wysiwyg/widgets/image_crop";
import { patch } from "@web/core/utils/patch";

patch(ImageCrop.prototype, {
    /**
     * Guard: if cropper not initialized, ignore click silently.
     * Prevents TypeError when crop ratio buttons clicked before
     * cropper.js instance is ready.
     */
    _onCropOptionClick(ev) {
        if (!this.$cropperImage || !this.$cropperImage.length || !this.$cropperImage[0].cropper) {
            console.warn("[CasaFolino] ImageCrop._onCropOptionClick: cropper not ready, ignoring.");
            if (ev && ev.preventDefault) ev.preventDefault();
            if (ev && ev.stopPropagation) ev.stopPropagation();
            return;
        }
        return super._onCropOptionClick(ev);
    },

    /**
     * Guard: if media element missing, force-close state without
     * touching DOM refs. Prevents TypeError on this.media.setAttribute
     * when _closeCropper runs against a destroyed/missing media element.
     */
    _closeCropper() {
        if (this._cropperClosed) return;
        if (!this.media) {
            console.warn("[CasaFolino] ImageCrop._closeCropper: no media element, force-closing state.");
            this._cropperClosed = true;
            if (this.$cropperImage) {
                try { this.$cropperImage.cropper('destroy'); } catch (_e) { /* noop */ }
            }
            this.state.active = false;
            return;
        }
        return super._closeCropper();
    },
});
