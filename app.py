import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta

st.markdown('<meta http-equiv="refresh" content="45">', unsafe_allow_html=True)
st.set_page_config(page_title="V5.1 TOP3", layout="centered", page_icon="🎯")
st.markdown("<h2 style='text-align:center;'>🎯 V5.1 - TOP 3 RISCO MINIMO</h2>", unsafe_allow_html=True)

AGORA = datetime.utcnow() - timedelta(hours=3)
HORA = AGORA.hour
BLOQUEADO = False
MOTIVO = ""
if HORA >= 23 or HORA < 8:
    BLOQUEADO=True; MOTIVO=f"🌙 MADRUGADA {AGORA.strftime('%H:%M')} - DORME"
if BLOQUEADO:
    st.error(MOTIVO)
else:
    st.success(f"✅ LIBERADO | Hora Brasil {AGORA.strftime('%H:%M')} | Atualiza 45s | Max 2 trades")

MOEDAS = {'BTCBRL':'BTC','ETHBRL':'ETH','SOLBRL':'SOL','BNBBRL':'BNB','XRPBRL':'XRP','DOGEBRL':'DOGE','ADABRL':'ADA','LINKBRL':'LINK','AVAXBRL':'AVAX','LTCBRL':'LTC'}

@st.cache_data(ttl=30)
def pega_dados():
    dados=[]
    for symbol, nome in MOEDAS.items():
        try:
            url = f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}&interval=15m&limit=100"
            r = requests.get(url, timeout=10)
            klines = r.json()
            if not klines or isinstance(klines, dict): continue
            closes = np.array([float(k[4]) for k in klines])
            volumes = np.array([float(k[5]) for k in klines])
            close = pd.Series(closes)
            volume = pd.Series(volumes)
            preco = float(close.iloc[-1])
            preco_96 = float(close.iloc[0]) if len(close)>=96 else preco
            var_btc = (preco-preco_96)/preco_96*100 if nome=='BTC' else 0
            delta = close.diff()
            gain = delta.where(delta>0,0).rolling(14).mean()
            loss = -delta.where(delta<0,0).rolling(14).mean()
            rs = gain/loss.replace(0,np.nan)
            rsi = 100-(100/(1+rs))
            rsi_val = float(rsi.iloc[-1]) if not np.isnan(rsi.iloc[-1]) else 50
            mm9 = float(close.rolling(9).mean().iloc[-1])
            mm21 = float(close.rolling(21).mean().iloc[-1])
            vol_m = float(volume.rolling(20).mean().iloc[-1])
            vol_a = float(volume.iloc[-1])
            vr = vol_a/vol_m if vol_m>0 else 0
            score = 50
            if 45<=rsi_val<=65: score+=25
            elif rsi_val>70 or rsi_val<30: score-=20
            if mm9>mm21: score+=15
            else: score-=15
            if vr>1.2: score+=20
            elif vr<0.8: score-=20
            score=max(0,min(100,int(score)))
            entrada=preco; stop=preco*0.992; parcial=preco*1.008; alvo=preco*1.016
            dados.append({'Moeda':nome,'Preco':round(preco,2),'RSI':round(rsi_val,1),'Score':score,'Vol':vr,'MM9':mm9,'MM21':mm21,'Entrada':round(entrada,2),'Stop':round(stop,2),'Parcial':round(parcial,2),'Alvo':round(alvo,2),'VarBTC':var_btc})
        except: continue
    return pd.DataFrame(dados).sort_values(by='Score', ascending=False) if dados else pd.DataFrame()

df = pega_dados()
if not df.empty:
    btc_row = df[df['Moeda']=='BTC']
    btc_caindo = False
    if not btc_row.empty:
        var = float(btc_row.iloc[0]['VarBTC'])
        if var < -1:
            btc_caindo = True
            st.error(f"🛑 BTC CAINDO {var:.2f}% - MERCADO RUIM, NAO OPERA")
    top3 = df.head(3)
    st.markdown("### 🏆 TOP 3 - SO ENTRA SE FOR MUITO SEGURO")
    for i, (_, row) in enumerate(top3.iterrows(), 1):
        pode = row['Score']>=75 and row['Vol']>1.2 and 45<=row['RSI']<=65 and row['MM9']>row['MM21'] and not BLOQUEADO and not btc_caindo
        if pode:
            cor="#00FF88"; bg="#0a2e1f"; titulo=f"🟢 {i}º COMPRA - {row['Moeda']} - Score {row['Score']}"
        else:
            cor="#FFAA00"; bg="#1a1a1a"; titulo=f"🟡 {i}º AGUARDA - {row['Moeda']} - Score {row['Score']}"
        st.markdown(f"""
        <div style='background:{bg}; padding:15px; border-radius:12px; border:2px solid {cor}; margin-bottom:10px;'>
        <h3>{titulo}</h3>
        <p>RSI {row['RSI']} | Vol {'FORTE' if row['Vol']>1.2 else 'FRACO / MEDIO'}<br><br>
        <b>👉 CAMINHADA:</b><br>
        1️⃣ ENTRA a <b>R$ {row['Entrada']}</b><br>
        2️⃣ Se cair, STOP a <b>R$ {row['Stop']}</b> (-0.8%) - Sai e aceita loss pequeno<br>
        3️⃣ Se subir, VENDE METADE a <b>R$ {row['Parcial']}</b> (+0.8%) - Garante lucro<br>
        4️⃣ Deixa o resto, ALVO FINAL a <b>R$ {row['Alvo']}</b> (+1.6%)</p>
        </div>
        """, unsafe_allow_html=True)
        if pode:
            st.code(f"{row['Moeda']} - ENTRA {row['Entrada']} - STOP {row['Stop']} - VENDE METADE {row['Parcial']} - ALVO {row['Alvo']}", language="text")
    st.caption("Segura o texto e clica em Copiar pra colar na Binance")
    st.markdown("### 📊 TOP 10 - Por Score")
    st.dataframe(df[['Moeda','Preco','RSI','Score','Entrada','Stop','Alvo']], use_container_width=True, hide_index=True)
    if st.button("🔄 ATUALIZAR AGORA", use_container_width=True):
        st.cache_data.clear(); st.rerun()
else:
    st.warning("Carregando... aguarde 45s")
