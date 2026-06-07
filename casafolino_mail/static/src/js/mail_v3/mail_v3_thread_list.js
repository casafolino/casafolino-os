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

    get groupedItems() {
        const buckets = [
            { key: 'today', label: 'Oggi', threads: [] },
            { key: 'this_week', label: 'Questa settimana', threads: [] },
            { key: 'last_week', label: 'Scorsa settimana', threads: [] },
            { key: 'older', label: 'Il resto', threads: [] },
        ];
        const bucketByKey = Object.fromEntries(buckets.map((bucket) => [bucket.key, bucket]));

        for (const thread of this.props.threads || []) {
            bucketByKey[this._getDateBucketKey(thread)].threads.push(thread);
        }

        const items = [];
        for (const bucket of buckets) {
            if (!bucket.threads.length) {
                continue;
            }
            items.push({
                type: 'header',
                key: 'header-' + bucket.key,
                label: bucket.label,
                count: bucket.threads.length,
            });
            for (const thread of bucket.threads) {
                items.push({ type: 'thread', key: 'thread-' + thread.id, thread });
            }
        }
        return items;
    }

    _getThreadDate(thread) {
        const raw = thread.last_message_date || thread.email_date || thread.date || '';
        if (!raw) {
            return null;
        }
        const normalized = raw.includes('T') ? raw : raw.replace(' ', 'T');
        const date = new Date(normalized);
        return Number.isNaN(date.getTime()) ? null : date;
    }

    _getDateBucketKey(thread) {
        const date = this._getThreadDate(thread);
        if (!date) {
            return 'older';
        }

        const now = new Date();
        const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        const weekStart = new Date(todayStart);
        const day = weekStart.getDay() || 7;
        weekStart.setDate(weekStart.getDate() - day + 1);

        const lastWeekStart = new Date(weekStart);
        lastWeekStart.setDate(lastWeekStart.getDate() - 7);

        if (date >= todayStart) {
            return 'today';
        }
        if (date >= weekStart) {
            return 'this_week';
        }
        if (date >= lastWeekStart) {
            return 'last_week';
        }
        return 'older';
    }

    formatThreadDate(thread) {
        const date = this._getThreadDate(thread);
        if (!date) {
            return '';
        }
        const bucket = this._getDateBucketKey(thread);
        if (bucket === 'today') {
            return new Intl.DateTimeFormat('it-IT', {
                hour: '2-digit',
                minute: '2-digit',
            }).format(date);
        }
        if (bucket === 'this_week' || bucket === 'last_week') {
            return new Intl.DateTimeFormat('it-IT', {
                weekday: 'short',
                day: 'numeric',
                month: 'short',
            }).format(date);
        }
        return new Intl.DateTimeFormat('it-IT', {
            day: 'numeric',
            month: 'short',
            year: 'numeric',
        }).format(date);
    }

    getAccountColor(accountId) {
        const colors = ['#5A6E3A', '#2980B9', '#8E44AD'];
        const accounts = this.props.accounts || [];
        const idx = accounts.findIndex(a => a.id === accountId);
        return colors[idx >= 0 ? idx % colors.length : 0];
    }
}
