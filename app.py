import streamlit as st
import pandas as pd
from datetime import date, datetime
from fpdf import FPDF
from io import BytesIO
import pdfplumber
from ofxparse import OfxParser
import re

# ==============================================================================
# CONFIGURAÇÃO INICIAL
# ==============================================================================
st.set_page_config(page_title="Tesouraria Centro Espírita", layout="wide", page_icon="🕊️")

# Seu WhatsApp configurado no sistema
WHATSAPP_TESOUREIRO = "5595981136537"

# Estilos CSS
st.markdown("""
<style>
    .big-font {font-size:20px !important; color: #2E7D32;}
    .stButton>button {width: 100%;}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# ESTADO DA APLICAÇÃO (BANCO DE DADOS EM MEMÓRIA)
# ==============================================================================
def init_session():
    if 'financeiro' not in st.session_state:
        st.session_state['financeiro'] = pd.DataFrame(columns=[
            "ID", "Data", "Tipo", "Categoria", "Centro_Custo", "Descrição", "Valor", "Socio", "Conciliado"
        ])

    if 'socios' not in st.session_state:
        st.session_state['socios'] = pd.DataFrame({
            "Nome": ["Joel Silva", "Maria Oliveira", "Doador Anônimo"],
            "Telefone": [WHATSAPP_TESOUREIRO, "95988888888", ""],
            "Status": ["Ativo", "Ativo", "N/A"],
            "Email": ["joel@email.com", "maria@email.com", ""]
        })

    # Configurações Financeiras Padrão
    if 'config_categorias_receita' not in st.session_state:
        st.session_state['config_categorias_receita'] = pd.DataFrame({"Nome": ["Doação Anônima", "Mensalidade", "Cantina", "Bazar", "Livros", "Eventos"]})
    
    if 'config_categorias_despesa' not in st.session_state:
        st.session_state['config_categorias_despesa'] = pd.DataFrame({"Nome": ["Energia", "Água", "Manutenção Predial", "Assistência Social", "Internet", "Material de Limpeza"]})

    if 'config_centros_custo' not in st.session_state:
        st.session_state['config_centros_custo'] = pd.DataFrame({"Nome": ["Geral", "Departamento Doutrinário", "Assistência Social", "Administrativo"]})

init_session()

# ==============================================================================
# FUNÇÕES DE RELATÓRIO PDF
# ==============================================================================
class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'Centro Espírita - Relatório Financeiro', 0, 1, 'C')
        self.set_font('Arial', '', 10)
        self.cell(0, 10, f'Gerado em: {datetime.now().strftime("%d/%m/%Y")}', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Tesouraria - Contato: +{WHATSAPP_TESOUREIRO} | Página ' + str(self.page_no()), 0, 0, 'C')

def gerar_relatorio_pdf(df, titulo):
    pdf = PDFReport()
    pdf.add_page()
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, titulo, 0, 1, 'L')
    pdf.ln(5)
    
    # Cabeçalho da Tabela
    pdf.set_font("Arial", "B", 10)
    pdf.cell(25, 8, "Data", 1)
    pdf.cell(50, 8, "Categoria", 1)
    pdf.cell(80, 8, "Descrição", 1)
    pdf.cell(35, 8, "Valor (R$)", 1)
    pdf.ln()
    
    # Dados
    pdf.set_font("Arial", "", 9)
    total = 0
    for index, row in df.iterrows():
        pdf.cell(25, 8, str(row['Data']), 1)
        pdf.cell(50, 8, str(row['Categoria'])[:25], 1) # Corta texto longo
        pdf.cell(80, 8, str(row['Descrição'])[:40], 1)
        pdf.cell(35, 8, f"{row['Valor']:.2f}", 1)
        pdf.ln()
        total += row['Valor']
        
    pdf.set_font("Arial", "B", 10)
    pdf.cell(155, 10, "TOTAL:", 1, 0, 'R')
    pdf.cell(35, 10, f"R$ {total:.2f}", 1, 1, 'C')
    
    return pdf.output(dest='S').encode('latin-1')

def gerar_historico_socio_pdf(nome_socio, df_socio):
    pdf = PDFReport()
    pdf.add_page()
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"Histórico de Contribuições: {nome_socio}", 0, 1)
    pdf.ln(5)
    
    # Tabela simples
    pdf.set_font("Arial", "B", 10)
    pdf.cell(30, 8, "Data", 1)
    pdf.cell(40, 8, "Categoria", 1)
    pdf.cell(90, 8, "Descrição", 1)
    pdf.cell(30, 8, "Valor", 1)
    pdf.ln()
    
    pdf.set_font("Arial", "", 10)
    for i, row in df_socio.iterrows():
        pdf.cell(30, 8, str(row['Data']), 1)
        pdf.cell(40, 8, row['Categoria'], 1)
        pdf.cell(90, 8, row['Descrição'], 1)
        pdf.cell(30, 8, f"{row['Valor']:.2f}", 1)
        pdf.ln()
        
    return pdf.output(dest='S').encode('latin-1')

# ==============================================================================
# FUNÇÕES DE PARSE (EXTRATO)
# ==============================================================================
def parse_ofx(file):
    ofx = OfxParser.parse(file)
    transactions = []
    for account in ofx.accounts:
        for trans in account.statement.transactions:
            transactions.append({
                "Data": trans.date.date(),
                "Valor": float(trans.amount),
                "Descrição": trans.memo,
                "ID_Banco": trans.id
            })
    return pd.DataFrame(transactions)

def parse_pdf_extrato(file):
    # Esta é uma função genérica. Extratos bancários em PDF variam muito.
    # Tenta extrair linhas que pareçam transações (Data dd/mm + Valor)
    transactions = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            for line in text.split('\n'):
                # Regex simples para tentar achar data (dd/mm) e valor monetário
                # Exemplo: 12/01 Pix Recebido 100,00
                match = re.search(r'(\d{2}/\d{2})\s+(.+?)\s+(-?[\d\.,]+)$', line)
                if match:
                    try:
                        # Tenta limpar o valor
                        val_str = match.group(3).replace('.', '').replace(',', '.')
                        transactions.append({
                            "Data": match.group(1) + f"/{date.today().year}", # Assume ano atual
                            "Descrição": match.group(2),
                            "Valor": float(val_str)
                        })
                    except:
                        pass
    return pd.DataFrame(transactions)

# ==============================================================================
# INTERFACE PRINCIPAL
# ==============================================================================

st.sidebar.title("🕊️ Tesouraria")
menu = st.sidebar.radio("Navegação", 
    ["Dashboard", "Lançamentos", "Sócios & Histórico", "Conciliação Bancária", "Relatórios", "Configurações"]
)

# --- DASHBOARD ---
if menu == "Dashboard":
    st.title("Visão Geral")
    df = st.session_state['financeiro']
    if not df.empty:
        receita = df[df['Tipo']=='Entrada']['Valor'].sum()
        despesa = df[df['Tipo']=='Saída']['Valor'].sum()
        saldo = receita - despesa
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Receitas", f"R$ {receita:,.2f}")
        c2.metric("Despesas", f"R$ {despesa:,.2f}")
        c3.metric("Saldo", f"R$ {saldo:,.2f}")
    else:
        st.info("Bem-vindo, Joel. Comece fazendo lançamentos ou configurações.")

# --- LANÇAMENTOS ---
elif menu == "Lançamentos":
    st.title("Novo Lançamento")
    with st.form("form_lanc"):
        c1, c2, c3 = st.columns(3)
        dt = c1.date_input("Data", date.today())
        tipo = c2.selectbox("Tipo", ["Entrada", "Saída"])
        
        # Listas Dinâmicas baseadas na Configuração
        if tipo == "Entrada":
            lista_cats = st.session_state['config_categorias_receita']['Nome'].tolist()
        else:
            lista_cats = st.session_state['config_categorias_despesa']['Nome'].tolist()
            
        lista_cc = st.session_state['config_centros_custo']['Nome'].tolist()
        
        cat = c3.selectbox("Categoria", lista_cats)
        
        c4, c5 = st.columns(2)
        cc = c4.selectbox("Centro de Custo", lista_cc)
        val = c5.number_input("Valor", min_value=0.01)
        
        desc = st.text_input("Descrição")
        socio = st.selectbox("Sócio Vinculado", ["Não Identificado"] + st.session_state['socios']['Nome'].tolist())
        
        if st.form_submit_button("Salvar"):
            novo = {
                "ID": len(st.session_state['financeiro']) + 1,
                "Data": dt, "Tipo": tipo, "Categoria": cat, "Centro_Custo": cc,
                "Descrição": desc, "Valor": val, "Socio": socio, "Conciliado": "Manual"
            }
            st.session_state['financeiro'] = pd.concat([st.session_state['financeiro'], pd.DataFrame([novo])], ignore_index=True)
            st.success("Salvo!")

# --- SÓCIOS E HISTÓRICO ---
elif menu == "Sócios & Histórico":
    st.title("Gestão de Sócios")
    
    tab1, tab2 = st.tabs(["Cadastro (Editar/Excluir)", "Histórico de Pagamentos"])
    
    with tab1:
        st.info("Edite os dados diretamente na tabela abaixo.")
        # Data Editor permite adicionar, alterar e excluir
        df_editado = st.data_editor(
            st.session_state['socios'], 
            num_rows="dynamic", 
            key="editor_socios",
            use_container_width=True
        )
        # Atualiza o estado se houver mudança
        if not df_editado.equals(st.session_state['socios']):
            st.session_state['socios'] = df_editado
            st.rerun() # Recarrega a página para atualizar listas
            
    with tab2:
        st.subheader("Consultar Histórico")
        socio_selecionado = st.selectbox("Selecione o Sócio", st.session_state['socios']['Nome'].unique())
        
        df_fin = st.session_state['financeiro']
        historico = df_fin[df_fin['Socio'] == socio_selecionado]
        
        if not historico.empty:
            st.dataframe(historico[['Data', 'Categoria', 'Descrição', 'Valor']], use_container_width=True)
            
            # Botão PDF Histórico
            pdf_hist = gerar_historico_socio_pdf(socio_selecionado, historico)
            st.download_button("📥 Baixar Histórico (PDF)", data=pdf_hist, file_name=f"historico_{socio_selecionado}.pdf", mime="application/pdf")
        else:
            st.warning("Nenhum lançamento encontrado para este sócio.")

# --- CONCILIAÇÃO BANCÁRIA ---
elif menu == "Conciliação Bancária":
    st.title("Conciliação Bancária")
    st.markdown("Suporta **OFX, PDF, Excel e CSV**.")
    
    uploaded_file = st.file_uploader("Upload Extrato", type=['ofx', 'pdf', 'xlsx', 'csv'])
    
    df_importado = pd.DataFrame()
    
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.ofx'):
                df_importado = parse_ofx(uploaded_file)
                st.success("Arquivo OFX processado!")
            elif uploaded_file.name.endswith('.pdf'):
                df_importado = parse_pdf_extrato(uploaded_file)
                st.warning("Atenção: A leitura de PDF pode ser imprecisa dependendo do layout do banco. Verifique os valores.")
            elif uploaded_file.name.endswith('.xlsx'):
                df_importado = pd.read_excel(uploaded_file)
            elif uploaded_file.name.endswith('.csv'):
                df_importado = pd.read_csv(uploaded_file)
                
            if not df_importado.empty:
                st.divider()
                st.subheader("Classificar Lançamentos")
                
                # Exibição para conciliação
                with st.form("form_concilia"):
                    lancamentos_finais = []
                    # Limita a 10 para o exemplo
                    for index, row in df_importado.head(10).iterrows():
                        cols = st.columns([1, 2, 2, 2])
                        val = row.get('Valor', 0)
                        desc_banco = row.get('Descrição', 'Sem desc')
                        dt_banco = row.get('Data', date.today())
                        
                        cols[0].write(f"**R$ {val}**")
                        cols[1].caption(f"{dt_banco} | {desc_banco}")
                        
                        tipo_sugrido = "Entrada" if float(val) > 0 else "Saída"
                        cat_list = st.session_state['config_categorias_receita']['Nome'].tolist() if tipo_sugrido == "Entrada" else st.session_state['config_categorias_despesa']['Nome'].tolist()
                        
                        cat_sel = cols[2].selectbox("Categoria", ["Ignorar"] + cat_list, key=f"cat_{index}")
                        soc_sel = cols[3].selectbox("Sócio", ["Não Identificado"] + st.session_state['socios']['Nome'].tolist(), key=f"soc_{index}")
                        
                        lancamentos_finais.append({
                            "Data": dt_banco, "Tipo": tipo_sugrido, "Valor": abs(float(val)),
                            "Categoria": cat_sel, "Socio": soc_sel, "Descrição": desc_banco
                        })
                        st.markdown("---")
                    
                    if st.form_submit_button("Processar Conciliação"):
                        for l in lancamentos_finais:
                            if l['Categoria'] != "Ignorar":
                                novo = {
                                    "ID": len(st.session_state['financeiro']) + 1,
                                    "Data": l['Data'], "Tipo": l['Tipo'],
                                    "Categoria": l['Categoria'], "Centro_Custo": "Geral",
                                    "Descrição": l['Descrição'], "Valor": l['Valor'],
                                    "Socio": l['Socio'], "Conciliado": "Auto"
                                }
                                st.session_state['financeiro'] = pd.concat([st.session_state['financeiro'], pd.DataFrame([novo])], ignore_index=True)
                        st.success("Lançamentos importados com sucesso!")
                        
        except Exception as e:
            st.error(f"Erro ao processar arquivo: {e}")

# --- RELATÓRIOS ---
elif menu == "Relatórios":
    st.title("Central de Relatórios")
    
    col1, col2 = st.columns(2)
    dt_inicio = col1.date_input("Data Início", date(date.today().year, 1, 1))
    dt_fim = col2.date_input("Data Fim", date.today())
    
    tipo_relatorio = st.selectbox("Tipo de Relatório", ["Fluxo de Caixa (Completo)", "Apenas Receitas", "Apenas Despesas"])
    agrupar_por = st.checkbox("Agrupar por Categoria (Resumo)")
    
    if st.button("Gerar Relatório"):
        df = st.session_state['financeiro']
        # Filtros
        mask = (df['Data'] >= dt_inicio) & (df['Data'] <= dt_fim)
        df_filtrado = df.loc[mask]
        
        if tipo_relatorio == "Apenas Receitas":
            df_filtrado = df_filtrado[df_filtrado['Tipo'] == "Entrada"]
        elif tipo_relatorio == "Apenas Despesas":
            df_filtrado = df_filtrado[df_filtrado['Tipo'] == "Saída"]
            
        if not df_filtrado.empty:
            st.write(f"Encontrados {len(df_filtrado)} registros.")
            st.dataframe(df_filtrado)
            
            # Geração do PDF
            pdf_bytes = gerar_relatorio_pdf(df_filtrado, f"Relatório: {tipo_relatorio} ({dt_inicio} a {dt_fim})")
            
            st.download_button(
                label="📥 Baixar PDF do Relatório",
                data=pdf_bytes,
                file_name="relatorio_financeiro.pdf",
                mime="application/pdf"
            )
        else:
            st.warning("Nenhum dado encontrado no período.")

# --- CONFIGURAÇÕES ---
elif menu == "Configurações":
    st.title("⚙️ Parâmetros do Sistema")
    st.info("Aqui você define as categorias que aparecem nos menus.")
    
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.subheader("Receitas")
        st.data_editor(st.session_state['config_categorias_receita'], num_rows="dynamic", key="conf_rec")
        
    with c2:
        st.subheader("Despesas")
        st.data_editor(st.session_state['config_categorias_despesa'], num_rows="dynamic", key="conf_desp")
        
    with c3:
        st.subheader("Centros de Custo")
        st.data_editor(st.session_state['config_centros_custo'], num_rows="dynamic", key="conf_cc")
