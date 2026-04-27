/** @odoo-module **/
/**
 * Mail V3 Browser Notifications — polling + HTML5 Notification API.
 *
 * Usage: instantiate from MailV3Client.setup(), call start()/stop().
 * Respects user preference (mv3_notifications_enabled).
 */
import { rpc } from "@web/core/network/rpc";

const POLL_INTERVAL_MS = 60000; // 60 seconds
const ORIGINAL_TITLE = document.title;

export class MailV3Notifications {
    constructor({ onNewMail } = {}) {
        this._timer = null;
        this._lastCheck = null;
        this._enabled = false;
        this._permissionGranted = false;
        this._onNewMail = onNewMail || (() => {});
    }

    get isActive() {
        return this._enabled && this._timer !== null;
    }

    /**
     * Start polling. Checks permission state, begins interval.
     */
    start() {
        if (this._timer) return;
        this._enabled = true;
        this._permissionGranted = (Notification.permission === 'granted');
        this._lastCheck = new Date().toISOString().replace('T', ' ').slice(0, 19);
        this._poll(); // immediate first check
        this._timer = setInterval(() => this._poll(), POLL_INTERVAL_MS);
        // Pause polling when tab hidden, resume when visible
        this._visibilityHandler = () => {
            if (document.hidden) {
                if (this._timer) { clearInterval(this._timer); this._timer = null; }
            } else if (this._enabled && !this._timer) {
                this._poll();
                this._timer = setInterval(() => this._poll(), POLL_INTERVAL_MS);
            }
        };
        document.addEventListener('visibilitychange', this._visibilityHandler);
    }

    stop() {
        this._enabled = false;
        if (this._timer) {
            clearInterval(this._timer);
            this._timer = null;
        }
        if (this._visibilityHandler) {
            document.removeEventListener('visibilitychange', this._visibilityHandler);
            this._visibilityHandler = null;
        }
        // Restore original tab title
        document.title = ORIGINAL_TITLE;
    }

    /**
     * Request browser notification permission. Returns true if granted.
     */
    async requestPermission() {
        if (!('Notification' in window)) return false;
        if (Notification.permission === 'granted') {
            this._permissionGranted = true;
            return true;
        }
        if (Notification.permission === 'denied') return false;
        try {
            const result = await Notification.requestPermission();
            this._permissionGranted = (result === 'granted');
            return this._permissionGranted;
        } catch (e) {
            console.warn('[mail v3 notif] Permission request failed:', e);
            return false;
        }
    }

    /**
     * Update tab title badge with unread count.
     */
    updateTabBadge(count) {
        if (count > 0) {
            document.title = `(${count}) Mail CRM`;
        } else {
            document.title = ORIGINAL_TITLE;
        }
    }

    async _poll() {
        if (!this._enabled) return;
        try {
            const res = await rpc('/cf/mail/v3/poll/unread', {
                last_check: this._lastCheck || '',
            });

            const unread = res.unread_count || 0;
            const newSince = res.new_since_last_poll || 0;

            // Update tab badge
            this.updateTabBadge(unread);

            // Fire HTML5 notification for new messages
            if (newSince > 0 && this._permissionGranted) {
                this._showNotification(newSince);
            }

            // Callback for UI updates (e.g. sidebar badge)
            this._onNewMail({ unread_count: unread, new_count: newSince });

            // Update last check from server time
            if (res.server_time) {
                this._lastCheck = res.server_time;
            }
        } catch (e) {
            // Silent fail — don't break UI on network errors
            console.warn('[mail v3 notif] poll error:', e);
        }
    }

    _showNotification(count) {
        try {
            const body = count === 1
                ? 'Hai 1 nuova email'
                : `Hai ${count} nuove email`;
            const notif = new Notification('Mail CRM — CasaFolino', {
                body: body,
                icon: '/casafolino_mail/static/description/icon.png',
                tag: 'cf-mail-new', // replace previous notification
            });
            notif.onclick = () => {
                window.focus();
                notif.close();
            };
            // Auto-close after 8 seconds
            setTimeout(() => notif.close(), 8000);
        } catch (e) {
            console.warn('[mail v3 notif] notification error:', e);
        }
    }
}
