#!/usr/bin/env python3
"""
Test Script: Verifica Integrazione Gemini & Telegram su Odoo 18 Stage.
Questo script si collega all'istanza Odoo Stage tramite XML-RPC ed esegue i test
di classificazione Gemini e invio notifica Telegram su un'email esistente.
"""

import xmlrpc.client
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="Test Odoo Gemini & Telegram Integration")
    parser.add_argument("--url", default="http://51.44.170.55:4589", help="Odoo Base URL")
    parser.add_argument("--db", default="folinofood_stage", help="Odoo Database name")
    parser.add_argument("--user", default="antonio@casafolino.com", help="Odoo Login Email")
    parser.add_argument("--password", required=True, help="Odoo User Password")
    parser.add_argument("--msg-id", type=int, help="ID di un record casafolino.mail.message da testare")
    args = parser.parse_args()

    print(f"🔗 Connessione a Odoo in corso ({args.url})...")
    try:
        common = xmlrpc.client.ServerProxy(f"{args.url}/xmlrpc/2/common")
        uid = common.authenticate(args.db, args.user, args.password, {})
        if not uid:
            print("❌ Autenticazione fallita! Verifica email e password.")
            sys.exit(1)
        print(f"✅ Autenticato con successo! User ID: {uid}")

        models = xmlrpc.client.ServerProxy(f"{args.url}/xmlrpc/2/object")

        # 1. Verifica chiavi di configurazione ir.config_parameter
        print("\n🔍 Verifica parametri di configurazione in Odoo:")
        params = [
            'casafolino.gemini_api_key',
            'casafolino.telegram_enabled',
            'casafolino.telegram_bot_token',
            'casafolino.telegram_chat_id',
            'casafolino.telegram_bridge_token',
            'casafolino_mail.ai_classifier_enabled'
        ]
        
        for p in params:
            val = models.execute_kw(args.db, uid, args.password,
                'ir.config_parameter', 'get_param', [p])
            status = "✅ Configurato" if val else "⚠️ Non configurato"
            masked_val = val[:8] + "..." if val and len(val) > 8 else val
            print(f"   • {p}: {status} ({masked_val})")

        # 2. Test modulo di classificazione Gemini se msg-id è specificato
        if args.msg_id:
            print(f"\n🧪 Test Classificazione Gemini su casafolino.mail.message (ID: {args.msg_id})...")
            
            # Reset dei campi AI per forzare una nuova classificazione
            models.execute_kw(args.db, uid, args.password,
                'casafolino.mail.message', 'write',
                [[args.msg_id], {
                    'ai_classified_at': False,
                    'ai_category': False,
                    'ai_urgency': False,
                    'ai_error': False
                }]
            )
            print("   • Campi AI azzerati sul record.")

            # Esegui la classificazione Gemini
            print("   • Chiamata a _classify_with_gemini() in corso...")
            models.execute_kw(args.db, uid, args.password,
                'casafolino.mail.message', '_classify_with_gemini',
                [[args.msg_id]]
            )

            # Leggi i risultati
            msg = models.execute_kw(args.db, uid, args.password,
                'casafolino.mail.message', 'read',
                [[args.msg_id], ['subject', 'ai_category', 'ai_urgency', 'ai_error', 'snippet']]
            )[0]

            print(f"\n📊 Risultati Classificazione Gemini:")
            print(f"   • Oggetto: {msg['subject']}")
            print(f"   • Categoria AI: {msg['ai_category']}")
            print(f"   • Urgenza AI: {msg['ai_urgency']}")
            print(f"   • Errore AI: {msg['ai_error']}")
            print(f"   • Sintesi / Snippet: {msg['snippet']}")

            # 3. Test invio notifica Telegram manuale
            print(f"\n💬 Test invio Notifica Telegram per il messaggio ID {args.msg_id}...")
            res = models.execute_kw(args.db, uid, args.password,
                'casafolino.mail.message', 'action_send_telegram_notification',
                [[args.msg_id]]
            )
            if res:
                print("   🚀 Notifica Telegram inviata con successo! Controlla il tuo cellulare.")
            else:
                print("   ❌ Invio notifica fallito. Verifica se 'casafolino.telegram_enabled' è impostato a '1'.")

        else:
            print("\n💡 Suggerimento: Per eseguire il test di classificazione e invio notifica su un record specifico,")
            print("               aggiungi il parametro '--msg-id <ID>' all'avvio dello script.")

    except Exception as e:
        print(f"❌ Errore durante l'esecuzione del test: {e}")

if __name__ == "__main__":
    main()
