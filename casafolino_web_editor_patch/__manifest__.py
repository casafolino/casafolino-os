{
    "name": "CasaFolino — Web Editor Patch",
    "version": "18.0.1.0.1",
    "category": "Customization",
    "summary": "Guard difensivo per widget ImageCrop",
    "description": "Patch OWL di ImageCrop._onCropOptionClick e _save con guard "
                   "su cropper non inizializzato. Evita TypeError quando si clicca "
                   "un'opzione di crop senza immagine target valida.",
    "author": "CasaFolino S.r.l.",
    "depends": ["web_editor"],
    "data": [],
    "assets": {
        "web_editor.backend_assets_wysiwyg": [
            "casafolino_web_editor_patch/static/src/js/image_crop_patch.js",
        ],
    },
    "license": "LGPL-3",
    "installable": True,
    "auto_install": False,
}
