# test_run.py — Script temporaneo da eseguire in Odoo Shell
# Utilizzato per verificare l'integrazione di Gemini e Telegram in Stage.

import logging
_logger = logging.getLogger('odoo.tests.gemini')

print("=========================================")
print("🧪 Odoo Shell: Test Gemini & Telegram")
print("=========================================")

# Cerca l'ultimo messaggio email inbound ricevuto
msg = env['casafolino.mail.message'].search([('direction', '=', 'inbound')], limit=1)

if msg:
    print(f"📬 Trovato messaggio di test: ID {msg.id}")
    print(f"   • Oggetto: '{msg.subject}'")
    print(f"   • Mittente: {msg.sender_name} <{msg.sender_email}>")

    # 1. Reset campi AI
    print("\n🔄 Reset campi AI in corso...")
    msg.write({
        'ai_classified_at': False,
        'ai_category': False,
        'ai_urgency': False,
        'ai_error': False
    })
    env.cr.commit()
    print("   ✅ Campi resettati.")

    # 2. Esecuzione Classificazione Gemini
    print("\n🧠 Avvio Classificazione Gemini...")
    try:
        msg._classify_with_gemini()
        env.cr.commit()
        
        # Rileggi valori
        msg.invalidate_recordset()
        print(f"   ✅ Classificazione completata!")
        print(f"   • Categoria AI: {msg.ai_category}")
        print(f"   • Urgenza AI: {msg.ai_urgency}")
        print(f"   • AI Errore: {msg.ai_error}")
        print(f"   • Sintesi Gemini: {msg.snippet}")
    except Exception as e:
        print(f"   ❌ Errore durante la classificazione: {e}")

    # 3. Test Invio Notifica Telegram
    print("\n💬 Avvio Test Notifica Telegram...")
    try:
        # Abilita temporaneamente per il test se disabilitato
        ICP = env['ir.config_parameter'].sudo()
        original_enabled = ICP.get_param('casafolino.telegram_enabled', '0')
        if original_enabled != '1':
            print("   ⚠️ casafolino.telegram_enabled era disattivato. Lo attivo per il test.")
            ICP.set_param('casafolino.telegram_enabled', '1')
            env.cr.commit()

        # Invia
        res = msg.action_send_telegram_notification()
        
        # Ripristina valore originale
        if original_enabled != '1':
            ICP.set_param('casafolino.telegram_enabled', original_enabled)
            env.cr.commit()

        if res:
            print("   🚀 Notifica Telegram inviata con successo! Controlla il cellulare.")
        else:
            print("   ❌ Invio notifica fallito. Controlla che i parametri casafolino.telegram_bot_token e casafolino.telegram_chat_id siano corretti.")
    except Exception as e:
        print(f"   ❌ Errore durante l'invio Telegram: {e}")

else:
    print("❌ Nessun messaggio email in ingresso trovato nel database per eseguire il test.")

print("=========================================")
print("🏁 Fine Test")
print("=========================================")
