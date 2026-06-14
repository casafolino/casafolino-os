/** @odoo-module **/
import { Component, useState, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

export class FolderSidebar extends Component {
    static template = "casafolino_mail.FolderSidebar";
    static props = ["*"];

    setup() {
        this.state = useState({
            folders: [],
            loading: false,
            selectedFolderId: null,
            createMode: false,
            newFolderName: '',
            newFolderAccountId: null,
            renameId: null,
            renameName: '',
            contextMenuId: null,
        });

        onWillStart(async () => {
            await this.loadFolders();
        });
    }

    async loadFolders() {
        this.state.loading = true;
        try {
            const res = await rpc('/cf/mail/v3/folders/list');
            this.state.folders = res.folders || [];
        } catch (e) {
            console.error('[folders] loadFolders error:', e);
        }
        this.state.loading = false;
    }

    get accountGroups() {
        const groups = {};
        for (const f of this.state.folders) {
            if (!groups[f.account_id]) {
                groups[f.account_id] = {
                    account_id: f.account_id,
                    account_name: f.account_name,
                    system: [],
                    custom: [],
                };
            }
            if (f.is_system) {
                groups[f.account_id].system.push(f);
            } else {
                groups[f.account_id].custom.push(f);
            }
        }
        // Filter by selected account if any
        const selectedIds = this.props.selectedAccountIds;
        if (selectedIds && selectedIds.length === 1) {
            const id = selectedIds[0];
            if (groups[id]) {
                return [groups[id]];
            }
            return [];
        }
        return Object.values(groups);
    }

    selectFolder(folderId, accountId) {
        this.state.selectedFolderId = folderId;
        this.state.contextMenuId = null;
        if (this.props.onFolderSelect) {
            this.props.onFolderSelect(folderId, accountId);
        }
    }

    clearFolderFilter() {
        this.state.selectedFolderId = null;
        if (this.props.onFolderSelect) {
            this.props.onFolderSelect(null, null);
        }
    }

    // ── Create folder ──

    startCreate(accountId) {
        this.state.createMode = true;
        this.state.newFolderName = '';
        this.state.newFolderAccountId = accountId;
    }

    cancelCreate() {
        this.state.createMode = false;
        this.state.newFolderName = '';
    }

    onNewFolderInput(ev) {
        this.state.newFolderName = ev.target.value;
    }

    async onNewFolderKeydown(ev) {
        if (ev.key === 'Enter' && this.state.newFolderName.trim()) {
            await this.createFolder();
        } else if (ev.key === 'Escape') {
            this.cancelCreate();
        }
    }

    async createFolder() {
        const name = this.state.newFolderName.trim();
        if (!name) return;
        try {
            await rpc('/cf/mail/v3/folder/create', {
                name: name,
                account_id: this.state.newFolderAccountId,
            });
            this.state.createMode = false;
            this.state.newFolderName = '';
            await this.loadFolders();
        } catch (e) {
            console.error('[folders] create error:', e);
        }
    }

    // ── Context menu ──

    onFolderContextMenu(ev, folderId) {
        ev.preventDefault();
        const folder = this.state.folders.find(f => f.id === folderId);
        if (folder && !folder.is_system) {
            this.state.contextMenuId = folderId;
        }
    }

    closeContextMenu() {
        this.state.contextMenuId = null;
    }

    // ── Rename ──

    startRename(folderId) {
        const folder = this.state.folders.find(f => f.id === folderId);
        if (!folder) return;
        this.state.renameId = folderId;
        this.state.renameName = folder.name;
        this.state.contextMenuId = null;
    }

    onRenameInput(ev) {
        this.state.renameName = ev.target.value;
    }

    async onRenameKeydown(ev) {
        if (ev.key === 'Enter' && this.state.renameName.trim()) {
            await this.renameFolder();
        } else if (ev.key === 'Escape') {
            this.state.renameId = null;
        }
    }

    async renameFolder() {
        try {
            await rpc('/cf/mail/v3/folder/rename', {
                folder_id: this.state.renameId,
                name: this.state.renameName.trim(),
            });
            this.state.renameId = null;
            await this.loadFolders();
        } catch (e) {
            console.error('[folders] rename error:', e);
        }
    }

    // ── Delete ──

    async deleteFolder(folderId) {
        this.state.contextMenuId = null;
        if (!confirm('Eliminare questa cartella? I messaggi verranno spostati in Inbox.')) {
            return;
        }
        try {
            await rpc('/cf/mail/v3/folder/delete', {
                folder_id: folderId,
            });
            if (this.state.selectedFolderId === folderId) {
                this.clearFolderFilter();
            }
            await this.loadFolders();
        } catch (e) {
            console.error('[folders] delete error:', e);
        }
    }

    // ── Manage rules ──

    openRules() {
        if (this.props.onOpenRules) {
            this.props.onOpenRules();
        }
    }
}
