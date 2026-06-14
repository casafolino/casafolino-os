/** @odoo-module **/
import { Component, onMounted, onWillUnmount, useRef } from "@odoo/owl";

export class ThreadList extends Component {
    static template = "casafolino_mail.ThreadList";
    static props = ["*"];

    setup() {
        this.listRef = useRef("threadListContainer");
        this._onScroll = this._onScroll.bind(this);

        onMounted(() => {
            const el = this.listRef.el;
            if (el) {
                el.addEventListener('scroll', this._onScroll);
            }
        });

        onWillUnmount(() => {
            const el = this.listRef.el;
            if (el) {
                el.removeEventListener('scroll', this._onScroll);
            }
        });
    }

    _onScroll() {
        const el = this.listRef.el;
        if (!el) return;
        if (el.scrollTop + el.clientHeight >= el.scrollHeight - 200) {
            if (this.props.hasMore && !this.props.loadingMore && this.props.onLoadMore) {
                this.props.onLoadMore();
            }
        }
    }

    selectThread(threadId) {
        this.props.onSelect(threadId);
    }

    toggleSelect(threadId) {
        if (this.props.onToggleSelect) {
            this.props.onToggleSelect(threadId);
        }
    }

    onSelectAll() {
        if (this.props.onSelectAll) {
            this.props.onSelectAll();
        }
    }

    isSelected(threadId) {
        const ids = this.props.selectedThreadIds || [];
        return ids.includes(threadId);
    }

    getAccountColor(accountId) {
        const colors = ['#5A6E3A', '#2980B9', '#8E44AD'];
        const accounts = this.props.accounts || [];
        const idx = accounts.findIndex(a => a.id === accountId);
        return colors[idx >= 0 ? idx % colors.length : 0];
    }
}
