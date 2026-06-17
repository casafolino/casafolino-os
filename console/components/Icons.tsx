// Sprite SVG (dal riferimento v4). Incluso una volta nel layout; usato con <Icon name="home"/>.
export function IconSprite() {
  return (
    <svg width="0" height="0" style={{ position: "absolute" }} aria-hidden="true">
      <symbol id="i-home" viewBox="0 0 24 24"><path d="M3 10l9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z" /></symbol>
      <symbol id="i-inbox" viewBox="0 0 24 24"><path d="M4 4h16v16H4z" /><path d="M4 13h4l2 3h4l2-3h4" /></symbol>
      <symbol id="i-kanban" viewBox="0 0 24 24"><path d="M4 4h4v16H4zM10 4h4v10h-4zM16 4h4v7h-4z" /></symbol>
      <symbol id="i-clock" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></symbol>
      <symbol id="i-fair" viewBox="0 0 24 24"><path d="M4 9l1-5h14l1 5M4 9h16M5 9v11h14V9M9 20v-6h6v6" /></symbol>
      <symbol id="i-folders" viewBox="0 0 24 24"><path d="M4 7h5l2 2h9v9H4zM4 7V5h4l2 2" /></symbol>
      <symbol id="i-reply" viewBox="0 0 24 24"><path d="M9 14L4 9l5-5M4 9h11a5 5 0 0 1 5 5v3" /></symbol>
      <symbol id="i-ai" viewBox="0 0 24 24"><path d="M12 3l1.8 4.2L18 9l-4.2 1.8L12 15l-1.8-4.2L6 9l4.2-1.8zM18 15l.9 2.1L21 18l-2.1.9L18 21l-.9-2.1L15 18l2.1-.9z" /></symbol>
      <symbol id="i-link" viewBox="0 0 24 24"><path d="M10 13a5 5 0 0 0 7 0l2-2a5 5 0 0 0-7-7l-1 1M14 11a5 5 0 0 0-7 0l-2 2a5 5 0 0 0 7 7l1-1" /></symbol>
      <symbol id="i-check" viewBox="0 0 24 24"><path d="M5 12l5 5 9-11" /></symbol>
      <symbol id="i-alert" viewBox="0 0 24 24"><path d="M12 3l9 16H3zM12 10v4M12 17h.01" /></symbol>
    </svg>
  );
}

export function Icon({ name, size = 18, color }: { name: string; size?: number; color?: string }) {
  return (
    <svg className="ic" width={size} height={size} style={color ? { color } : undefined}>
      <use href={`#i-${name}`} />
    </svg>
  );
}
