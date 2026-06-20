"use client";
// Login Console — credenziali Odoo dell'umano. Verifica (identità + allowlist Console
// Operator) server-side via server action (basePath-proof sotto /console).
import { Suspense } from "react";
import { useActionState } from "react";
import { useSearchParams } from "next/navigation";
import { authenticate } from "./actions";

function LoginForm() {
  const params = useSearchParams();
  const callbackUrl = params.get("callbackUrl") || "/";
  const [error, formAction, pending] = useActionState(authenticate, undefined);

  return (
    <main
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        background: "#f5f5f0",
        fontFamily: "system-ui, sans-serif",
      }}
    >
      <form
        action={formAction}
        style={{
          width: 340,
          padding: 32,
          background: "#fff",
          borderRadius: 12,
          boxShadow: "0 4px 24px rgba(0,0,0,0.08)",
          display: "flex",
          flexDirection: "column",
          gap: 14,
        }}
      >
        <h1 style={{ margin: 0, fontSize: 20, color: "#3d4d28" }}>Console CasaFolino</h1>
        <p style={{ margin: 0, fontSize: 13, color: "#666" }}>Accedi con le tue credenziali Odoo.</p>
        <input type="hidden" name="callbackUrl" value={callbackUrl} />
        <input
          type="email"
          name="email"
          placeholder="email@casafolino.com"
          autoComplete="username"
          required
          style={inputStyle}
        />
        <input
          type="password"
          name="password"
          placeholder="password"
          autoComplete="current-password"
          required
          style={inputStyle}
        />
        {error && <div style={{ color: "#b00020", fontSize: 13 }}>{error}</div>}
        <button
          type="submit"
          disabled={pending}
          style={{
            padding: "10px 14px",
            border: "none",
            borderRadius: 8,
            background: pending ? "#9aa886" : "#5A6E3A",
            color: "#fff",
            fontWeight: 600,
            cursor: pending ? "default" : "pointer",
          }}
        >
          {pending ? "Verifica…" : "Entra"}
        </button>
      </form>
    </main>
  );
}

const inputStyle: React.CSSProperties = {
  padding: "10px 12px",
  border: "1px solid #d6d6cc",
  borderRadius: 8,
  fontSize: 14,
};

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
