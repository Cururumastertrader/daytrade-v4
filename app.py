import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="V4 MOBILE", layout="centered", page_icon="🎯")
st.markdown("<h2 style='text-align:center;'>🎯 V4 MOBILE</h2>", unsafe_allow_html=True)

with st.expander("💰 MINHA BANCA - CLICA AQUI", expanded=True):
    banca = st.number_input("Banca R$", value=1000, step=100)
    risco_pct = st.slider("Risco %", 0.5, 2.0, 1.0)
    loss_hoje = st.number_input("Ja perdi hoje R$", value=0.0, step=10.0)
    trades_hoje = st.number_input("Trades hoje", value=0, step=1)
    loss_seq = st.number_input("Loss seguidos", value=0, step=1)

risco_reais = banca * (risco_pct/100)
max_loss = banca * 0.02
HORA = datetime.now().hour
BLOQUEADO = False
MOTIVO = ""
if HORA >= 23 or HORA < 8:
    BLOQUEADO=True; MOTIVO=f"🌙 MADRUGADA {datetime.now().strftime('%H:%M')} - DORME"
elif loss_hoje >= max_loss:
    BLOQUEADO=True; MOTIVO="🛑 LOSS -2% ATINGIDO - PAROU"
elif loss_seq >= 2:
    BLOQUEADO=True; MOTIVO="🧠 TILT - 2 LOSSES - PARA 1h"
elif trades_hoje >= 4:
    BLOQUEADO=True; MOTIVO="✅ 4 TRADES FEITOS"

if BLOQUEADO:
    st.error(MOTIVO)
else:
    st.success(f"✅ LIBERADO - Faltam {4-trades_hoje} trades | Pode perder R$ {max_loss-loss_hoje:.2f}")

@st.cache_data(ttl=30)
def pega_dolar():
    try:
        df = yf.download("USD-BRL=X", period="1d", interval="1m", progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        return float(df['Close'].iloc[-1])
    except: return 5.40
DOLAR = pega_dolar()
st.write(f"Dolar R$ {DOLAR:.2f} | Banca R$ {banca:.2f}")

MOEDAS = {'BTC-USD':'BTC','ETH-USD':'ETH','SOL-USD':'SOL','BNB-USD':'BNB','XRP-USD':'XRP','DOGE-USD':'DOGE','ADA-USD':'ADA','LINK-USD':'LINK','AVAX-USD':'AVAX','LTC-USD':'LTC'}

@st.cache_data(ttl=20)
def pega_dados():
    dados=[]
    for ticker, nome in MOEDAS.items():
        try:
            df = yf.download(ticker, period="5d", interval="15m", progress=False, auto_adjust=True)
            if df.empty: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            close=df['Close']; volume=df['Volume']
            preco_usd=float(close.iloc[-1]); preco=preco_usd*DOLAR
            abertura=float(close.iloc[-20])*DOLAR
            delta=close.diff(); gain=delta.where(delta>0,0).rolling(14).mean(); loss=-delta.where(delta<0,0).rolling(14).mean()
            rs=gain/loss.replace(0,np.nan); rsi=100-(100/(1+rs)); rsi_val=float(rsi.iloc[-1]) if not np.isnan(rsi.iloc[-1]) else 50
            mm9=float(close.rolling(9).mean().iloc[-1]); mm21=float(close.rolling(21).mean().iloc[-1])
            vol_m=float(volume.rolling(20).mean().iloc[-1]); vol_a=float(volume.iloc[-1]); vr=vol_a/vol_m if vol_m>0 else 0
            score=50
            if 45<=rsi_val<=65: score+=20
            elif 30<=rsi_val<45: score+=10
            elif rsi_val>70: score-=10
            if mm9>mm21: score+=15
            else: score-=10
            if vr>1.2: score+=15
            elif vr<0.8: score-=15
            score=max(0,min(100,int(score)))
            entrada=preco; stop=preco*0.992; alvo=preco*1.016; parcial=preco*1.008
            qtd=(risco_reais/(entrada-stop)) if entrada-stop>0 else 0
            sinal="🟢 COMPRA" if score>=70 and not BLOQUEADO else "🔴 ESPERA" if BLOQUEADO else "🟡 AGUARDA"
            dados.append({'Moeda':nome,'Preco':round(preco,2),'RSI':round(rsi_val,1),'Score':score,'Sinal':sinal,'Entrada':round(entrada,2),'Stop':round(stop,2),'Parcial':round(parcial,2),'Alvo':round(alvo,2),'Qtd':round(qtd,3),'Vol':"FORTE" if vr>1.2 else "FRACO" if vr<0.8 else "MEDIO"})
        except: continue
    return pd.DataFrame(dados).sort_values(by='Score', ascending=False) if dados else pd.DataFrame()

df = pega_dados()
if not df.empty:
    melhor = df.iloc[0]
    st.markdown(f"""
    <div style='background:#0a2e1f; padding:15px; border-radius:12px; border:2px solid #00FF88; text-align:center;'>
    <h3>🏆 {melhor['Moeda']} - Score {melhor['Score']}</h3>
    <p>{melhor['Sinal']}<br>
    Entrada R$ {melhor['Entrada']}<br>
    Stop R$ {melhor['Stop']} | Parcial R$ {melhor['Parcial']} | Alvo R$ {melhor['Alvo']}<br>
    Qtd {melhor['Qtd']} = R$ {melhor['Qtd']*melhor['Entrada']:.2f}</p>
    </div>
    """, unsafe_allow_html=True)
    st.code(f"{melhor['Moeda']} - Entrada {melhor['Entrada']} - SL {melhor['Stop']} - TP {melhor['Alvo']} - Parcial {melhor['Parcial']} - Qtd {melhor['Qtd']}", language="text")
    st.caption("Segura o texto e clica em Copiar pra colar na Binance")
    st.markdown("### 📊 TOP 10")
    st.dataframe(df[['Moeda','Preco','RSI','Score','Vol','Sinal','Entrada','Stop','Alvo']], use_container_width=True, hide_index=True)
    if st.button("🔄 ATUALIZAR AGORA", use_container_width=True):
        st.cache_data.clear(); st.rerun()
else:
    st.warning("Carregando...")

st.caption("V4 Mobile - So em Reais - Max 4 trades - Loss -2% para")
