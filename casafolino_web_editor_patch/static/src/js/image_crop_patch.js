/** @odoo-module **/

import { ImageCrop } from "@web_editor/js/wysiwyg/widgets/image_crop";
import { patch } from "@web/core/utils/patch";

patch(ImageCrop.prototype, {
    /**
     * Guard: if cropper not initialized, ignore click silently.
     */
    _onCropOptionClick(ev) {
        if (!this.$cropperImage || !this.$cropperImage.length || !this.$cropperImage[0].cropper) {
            console.warn("[CasaFolino] ImageCrop._onCropOptionClick: cropper not initialized, ignoring click.");
            if (ev && ev.preventDefault) ev.preventDefault();
            if (ev && ev.stopPropagation) ev.stopPropagation();
            return;
        }
        return super._onCropOptionClick(ev);
    },

    /**
     * Guard: if media element missing, abort silently.
     */
    async _save(refreshOptions = true) {
        if (!this.media) {
            console.warn("[CasaFolino] ImageCrop._save: no media element, aborting silently.");
            return;
        }
        if (!this.$cropperImage || !this.$cropperImage.length || !this.$cropperImage[0].cropper) {
            console.warn("[CasaFolino] ImageCrop._save: cropper not initialized, aborting silently.");
            return;
        }
        return super._save(refreshOptions);
    },
});
