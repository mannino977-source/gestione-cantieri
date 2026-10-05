import os
import re
import streamlit as st
from datetime import datetime
from PIL import Image
import pytesseract
from pypdf import PdfReader

# Configurazione della pagina
st.set_page_config(
    page_title="Gestione Costi Cantiere",
    page_icon="🏗️",
    layout="centered"
)

# --- 1. CONFIGURAZIONE DEI DATI E DEI TOKEN ---
database_aziende = {
    "rossi_srl_secret": {
        "nome_impresa": "Impresa Edile Rossi SRL",
        "cantieri": [
            "Cantiere Via Roma, 14",
            "Ristrutturazione Appartamento Centro"
        ]
    },
    "bianchi_figli_secret": {
        "nome_impresa": "Costruzioni Bianchi & Figli",
        "cantieri": [
            "Nuova Villetta Via dei Pini",
            "Manutenzione Facciata Condominio Sole"
        ]
    }
}

# --- 2. LETTURA DEL TOKEN DALL'INDIRIZZO WEB ---
query_params = st.query_params
token_inserito = query_params.get("token", None)

# --- 3. CONTROLLO DI ACCESSO (BLINDATURA) ---
if not token_inserito or token_inserito not in database_aziende:
    st.error("🚫 Accesso non autorizzato o link non valido.")
    st.info("💡 Utilizza il link personale fornito dall'amministratore della piattaforma.")
    st.stop()

dati_azienda = database_aziende[token_inserito]
nome_impresa = dati_azienda["nome_impresa"]
cantieri_disponibili = dati_azienda["cantieri"]

# --- 4. INTERFACCIA RISERVATA ALL'IMPRESA ---
st.title(f"🏗️ {nome_impresa}")
st.write("Registrazione rapida e scansione intelligente delle spese di cantiere.")
st.divider()

# Selezione del cantiere
cantiere_scelto = st.selectbox(
    "Seleziona il Cantiere", 
    ["Seleziona cantiere..."] + cantieri_disponibili
)

if cantiere_scelto != "Seleziona cantiere...":
    
    tipo_caricamento = st.radio("Come vuoi inserire il documento?", ["Scatta foto", "Carica file (Immagine o PDF)"], horizontal=True)
    
    file_caricato = None
    if tipo_caricamento == "Scatta foto":
        file_caricato = st.camera_input("Fotografa lo scontrino o il DDT")
    else:
        file_caricato = st.file_uploader("Carica il file", type=["jpg", "jpeg", "png", "pdf"])

    if file_caricato is not None:
        st.divider()
        st.info("🔍 Scansione e ricerca P.IVA / Codice Fiscale in corso...")
        
        testo_estratto = ""
        nome_file_originale = file_caricato.name.lower()
        
        try:
            if nome_file_originale.endswith('.pdf'):
                reader = PdfReader(file_caricato)
                for pagina in reader.pages:
                    testo_estratto += pagina.extract_text() or ""
                st.success("✅ Testo estratto correttamente dal PDF!")
            else:
                immagine = Image.open(file_caricato)
                testo_estratto = pytesseract.image_to_string(immagine, lang='ita')
                st.success("✅ Immagine scansionata con successo!")
        except Exception as e:
            st.warning("⚠️ Impossibile analizzare automaticamente il testo.")

        # Mostra il testo grezzo in un expander per debug
        with st.expander("🔎 Mostra testo grezzo letto dal documento (per debug)"):
            st.text(testo_estratto if testo_estratto else "Nessun testo rilevato.")

        # --- ESTRAZIONE INTELLIGENTE CON REGEX (P.IVA o Codice Fiscale) ---
        piva_trovata = ""
        
        # Cerca pattern di Partita IVA (11 cifre, eventualmente precedute da IT o P.IVA)
        match_piva = re.search(r'(?:p\.?\s*iva|it)?\s*([0-9]{11})', testo_estratto, re.IGNORECASE)
        if match_piva:
            piva_trovata = match_piva.group(1)
        else:
            # Fallback: cerca qualsiasi sequenza di 11 cifre nel testo
            match_11cifre = re.search(r'\b[0-9]{11}\b', testo_estratto)
            if match_11cifre:
                piva_trovata = match_11cifre.group(0)

        # Pulizia delle righe per estrarre una descrizione di base
        righe = [r.strip() for r in testo_estratto.split('\n') if r.strip()]
        descrizione_suggerita = righe[1] if len(righe) > 1 else "Spesa_Cantiere"

        # Campi modificabili dall'utente per la verifica
        st.write("Verifica i dati estratti dal documento:")
        fornitore_input = st.text_input("Fornitore / P.IVA o Codice Fiscale", value=piva_trovata if piva_trovata else "Fornitore_Generico")
        descrizione_input = st.text_input("Descrizione dell'acquisto", value=descrizione_suggerita)

        st.divider()
        
        # --- OPZIONI DI PAGAMENTO ---
        st.subheader("💳 Dettagli di Pagamento")
        pagato = st.checkbox("La spesa è già stata saldata?")
        
        metodo_pagamento = "Non_Specificato"
        if pagato:
            metodo_pagamento = st.selectbox(
                "Metodo di pagamento utilizzato",
                ["Bonifico", "Carta di pagamento", "Contanti"]
            )

        # --- 5. SALVATAGGIO E ARCHIVIAZIONE ---
        if st.button("Conferma e Archivia 🚀", type="primary"):
            if not fornitore_input or not descrizione_input:
                st.error("⚠️ Inserisci sia il fornitore/P.IVA che la descrizione per procedere.")
            else:
                # Pulizia delle stringhe per i nomi dei file
                fornitore_pulito = "".join(c for c in fornitore_input if c.isalnum() or c in (' ', '_')).strip().replace(" ", "_")
                descrizione_pulita = "".join(c for c in descrizione_input if c.isalnum() or c in (' ', '_')).strip().replace(" ", "_")
                pagamento_pulito = metodo_pagamento.replace(" ", "_")
                
                # Creazione struttura cartelle sul Mac
                cartella_base = "archivio_aziende"
                nome_impresa_pulito = nome_impresa.replace(" ", "_").replace("&", "e")
                nome_cantiere_pulito = cantiere_scelto.replace(" ", "_").replace(",", "")
                
                percorso_cartella = os.path.join(cartella_base, nome_impresa_pulito, nome_cantiere_pulito)
                os.makedirs(percorso_cartella, exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                estensione = file_caricato.name.split('.')[-1]
                
                # COMPOSIZIONE NOME FILE CON P.IVA / IDENTIFICATIVO
                nome_file_ordinato = f"{fornitore_pulito}_{descrizione_pulita}_{pagamento_pulito}_{timestamp}.{estensione}"
                percorso_file_completo = os.path.join(percorso_cartella, nome_file_ordinato)
                
                if hasattr(file_caricato, 'seek'):
                    file_caricato.seek(0)
                    
                with open(percorso_file_completo, "wb") as f:
                    f.write(file_caricato.getbuffer())
                    
                st.success("✅ Spesa registrata e archiviata correttamente!")
                st.info(f"📁 File salvato come: `{nome_file_ordinato}`")
                st.balloons()