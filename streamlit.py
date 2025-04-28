import streamlit as st
import pandas as pd
import plotly.express as px
import json

# Configuração da página
st.set_page_config(page_title="Dashboard Financeiro", layout="wide")

st.title("📊 Dashboard Financeiro")

# Upload do arquivo JSON
st.sidebar.header("📂 Carregar Arquivo JSON")
arquivo = st.sidebar.file_uploader("Selecione um arquivo JSON", type=["json"])

if arquivo:
    # Carregar JSON
    dados = json.load(arquivo)
    
    # Criar DataFrame
    df = pd.DataFrame(dados["movimentacoes"])

    # Converter a coluna de valor para numérico
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")

    # Converter datas para datetime (se necessário)
    df["data Completa"] = pd.to_datetime(df["mês/ano"], format="%m/%y", errors="coerce").dt.date
    df["ano"] = pd.to_datetime(df["data Completa"], format="%d/%m/%y", errors="coerce").dt.year
    df["mês"] = pd.to_datetime(df["data Completa"], format="%d/%m/%y", errors="coerce").dt.month
    
    df.drop("documento", axis=1, inplace=True)

    df = df[["data Completa", "mês", "ano", "tipo", "descricao", "Local", "valor"]]

    # Filtros na barra lateral
    anos_disponiveis = sorted(df["ano"].dropna().unique(), reverse=True)  # Lista ordenada de anos
    anos_selecionados = st.sidebar.multiselect("Filtrar por Ano", anos_disponiveis, default=anos_disponiveis)
    if anos_selecionados:
        df = df[df["ano"].isin(anos_selecionados)]


    tipo_selecionado = st.sidebar.multiselect("Filtrar por Tipo", df["tipo"].unique())
    if tipo_selecionado:
        df = df[df["tipo"].isin(tipo_selecionado)]

    st.sidebar.write(f"Total de transações: {len(df)}")
    st.sidebar.write(f"Saldo total: R$ {df['valor'].sum():,.2f}")

    # Somar valores positivos (Receitas)
    total_receitas = df[df["valor"] > 0]["valor"].sum()
    # Somar valores negativos (Despesas)
    total_despesas = df[df["valor"] < 0]["valor"].sum()
    total_transacoes = len(df)

    col1, col2, col3 = st.columns(3)  # Criando colunas para organizar os cards

    # Card 1: Total da Receita
    with col1:
        st.metric(label="💰 Total da Receita", value=f"R$ {total_receitas:,.2f}")

    # Card 2: Total da Despesa
    with col2:
        st.metric(label="📉 Total Despesas", value=f"R$ {total_despesas:,.2f}")

    # Card 3: Total de Transações
    with col3:
        st.metric(label="📊 Total de Transações", value=total_transacoes)

    # Exibir DataFrame
    st.subheader("📋 Movimentações")
    st.dataframe(df, use_container_width=True)

    # Gráfico de Gastos por Tipo de Transação
    st.subheader("💰 Gastos por Tipo de Transação")
    gastos_tipo = df.groupby("tipo")["valor"].sum().reset_index()
    fig1 = px.bar(gastos_tipo, x="tipo", y="valor", title="Total por Tipo", text_auto=".2s")
    st.plotly_chart(fig1, use_container_width=True)

    # Gráfico de Evolução dos Gastos ao longo do tempo
    st.subheader("📉 Evolução dos Gastos")
    df_agg = df.groupby("data Completa")["valor"].sum().reset_index()
    fig2 = px.line(df_agg, x="data Completa", y="valor", title="Gastos ao Longo do Tempo", markers=True)
    st.plotly_chart(fig2, use_container_width=True)
