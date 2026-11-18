import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta

st.markdown('<meta http-equiv="refresh" content="60">', unsafe_allow_html=True)
st.set_page_config(page_title="V5.2 MEIO-TERMO", layout="centered", page_icon="🎯")
st.markdown("<h2 style='text-align:center;'>🎯 V5.2 - MEIO-TERMO</h2>", unsafe_allow_html=True)

AGORA = datetime.utcnow() - timedelta(hours=3)
HORA = AGORA.hour
MIN = AGORA.minute
BLOQUEADO = False
MOTIVO = ""
if HORA >= 23 or HORA < 8:
    BLOQUEADO=True; MOTIVO=f"🌙 MADRUGADA {AGORA.strftime('%H:%M')} - DORME"
if BLOQUEADO:
    st.error(MOTIVO)
else:
    st.success(f"✅ LIBERADO | Hora Brasil {AGORA.strftime('%H:%M')} | Atualiza 60s | Max 2 trades")

# AVISO NOTICIA - NAO BLOQUEIA
EM_NOTICIA = (HORA==14 and MIN>=30) or (HORA==15) or (HORA==16 and MIN==0)
if EM_NOTICIA:
    st.warning("⚠️ 14h30-16h - DADOS EUA / NOTICIA - Mercado pode virar cassino. Entra so se for MUITO seguro.")

MOEDAS = {'BTCBRL':'BTC','ETHBRL':'ETH','SOLBRL':'SOL','BNBBRL':'BNB','XRPBRL':'XRP','DOGEBRL':'DOGE','ADABRL':'ADA','LINKBRL':'LINK','AVAXBRL':'AVAX','LTCBRL':'LTC'}

@st.cache_data(ttl=60)
def pega_1h(symbol):
    try:
        url = f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}&interval=1h&limit=50"
        r = requests.get(url, timeout=10)
        kl = r.json()
        if not kl or isinstance(kl, dict): return True
        c = pd.Series([float(k[4]) for k in kl])
        mm9 = float(c.rolling(9).mean().iloc[-1])
        mm21 = float(c.rolling(21).mean().iloc[-1])
        return mm9 > mm21  # True = 1h subindo
    except: return True

@st.cache_data(ttl=60)
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
            highs = np.array([float(k[2]) for k in klines])
            lows = np.array([float(k[3]) for k in klines])
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
            # ATR - STOP DINAMICO
            tr = pd.DataFrame({'h':highs,'l':lows,'c_prev':pd.Series(closes).shift(1)})
            tr['tr1'] = tr['h']-tr['l']
            tr['tr2'] = abs(tr['h']-tr['c_prev'])
            tr['tr3'] = abs(tr['l']-tr['c_prev'])
            tr['tr'] = tr[['tr1','tr2','tr3']].max(axis=1)
            atr = float(tr['tr'].rolling(14).mean().iloc[-1])
            atr_pct = atr/preco if preco>0 else 0.008
            stop_pct = max(0.005, min(0.012, atr_pct*1.5))  # 0.5% a 1.2%
            score = 50
            if 45<=rsi_val<=65: score+=25
            elif rsi_val>70 or rsi_val<30: score-=20
            if mm9>mm21: score+=15
            else: score-=15
            if vr>1.2: score+=20
            elif vr<0.8: score-=20
            score=max(0,min(100,int(score)))
            h1_subindo = pega_1h(symbol)
            # MEIO-TERMO: se 1h contra, exige 85+
            score_min = 75 if h1_subindo else 85
            entrada=preco; stop=preco*(1-stop_pct); parcial=preco*(1+stop_pct); alvo=preco*(1+stop_pct*2)
            dados.append({'Moeda':nome,'Preco':round(preco,2),'RSI':round(rsi_val,1),'Score':score,'ScoreMin':score_min,'Vol':vr,'MM9':mm9,'MM21':mm21,'Entrada':round(entrada,2),'Stop':round(stop,2),'Parcial':round(parcial,2),'Alvo':round(alvo,2),'VarBTC':var_btc,'StopPct':round(stop_pct*100,2),'H1':h1_subindo})
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
    st.markdown("### 🏆 TOP 3 - MEIO-TERMO")
    for i, (_, row) in enumerate(top3.iterrows(), 1):
        pode = row['Score']>=row['ScoreMin'] and row['Vol']>1.2 and 45<=row['RSI']<=65 and row['MM9']>row['MM21'] and not BLOQUEADO and not btc_caindo
        if pode:
            cor="#00FF88"; bg="#0a2e1f"; titulo=f"🟢 {i}º COMPRA - {row['Moeda']} - Score {row['Score']}"
        else:
            cor="#FFAA00"; bg="#1a1a1a"; titulo=f"🟡 {i}º AGUARDA - {row['Moeda']} - Score {row['Score']}"
        h1_txt = "1h ✅ SUBINDO" if row['H1'] else f"1h ⚠️ CAINDO - Exige {row['ScoreMin']}+"
        st.markdown(f"""
        <div style='background:{bg}; padding:15px; border-radius:12px; border:2px solid {cor}; margin-bottom:10px;'>
        <h3>{titulo}</h3>
        <p>RSI {row['RSI']} | Vol {'FORTE' if row['Vol']>1.2 else 'FRACO / MEDIO'} | {h1_txt}<br>
        Stop dinamico ATR: {row['StopPct']}%<br><br>
        <b>👉 CAMINHADA:</b><br>
        1️⃣ ENTRA a <b>R$ {row['Entrada']}</b><br>
        2️⃣ Se cair, STOP a <b>R$ {row['Stop']}</b> (-{row['StopPct']}%)<br>
        3️⃣ Se subir, VENDE METADE a <b>R$ {row['Parcial']}</b> (+{row['StopPct']}%)<br>
        4️⃣ ALVO FINAL a <b>R$ {row['Alvo']}</b> (+{round(row['StopPct']*2,2)}%)</p>
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
    st.warning("Carregando... aguarde 60s")
