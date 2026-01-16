import streamlit as st
import pandas as pd
from datetime import date, datetime
from fpdf import FPDF
from io import BytesIO
import base64

# ==============================================================================
# CONFIGURAÇÃO INICIAL E ESTILO
# ==============================================================================
st.set_page_config(page_title="Tesouraria Centro Espírita", layout="wide", page_icon="🕊️")

# Estilo CSS para esconder menus padrão e dar aparência profissional
st.markdown("""
<style>
    .main-header {font-size: 24px; color: #4CAF50; font-weight: bold;}
    .sub-header {font-size: 18px; color: #555;}
    .metric-card {background-color: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid #4CAF50;}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# BANCO DE DADOS SIMULADO (SESSION STATE)
# ==============================================================================
# Na versão final, substituiremos isso pela conexão com Google Sheets
if 'financeiro' not in st.session_state:
    st.session_state['financeiro'] = pd.DataFrame(columns=[
        "ID", "Data", "Tipo", "Categoria", "Descrição", "Valor", "Socio", "Conciliado"
    ])

if 'socios' not in st.session_state:
    # Dados fictícios para teste
    st.session_state['socios'] = pd.DataFrame({
        "Nome": ["Joel Silva", "Maria Oliveira", "Doador Anônimo"],
        "Telefone": ["95999999999", "95988888888", ""],
        "Status": ["Ativo", "Ativo", "N/A"]
    })

# ==============================================================================
# FUNÇÕES UTILITÁRIAS (PDF e WHATSAPP)
# ==============================================================================

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Centro Espírita - Recibo de Tesouraria', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def gerar_recibo_unico(dados_recibo):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Corpo do Recibo
    texto = f"""
    RECIBO Nº {dados_recibo['ID']}
    
    Data: {dados_recibo['Data']}
    Valor: R$ {float(dados_recibo['Valor']):.2f}
    
    Recebemos de: {dados_recibo['Socio']}
    A quantia referente a: {dados_recibo['Categoria']} - {dados_recibo['Descrição']}
    
    
    __________________________________________
    Assinatura do Tesoureiro
    """
    pdf.multi_cell(0, 10, texto)
    return pdf.output(dest='S').encode('latin-1')

def gerar_pdf_unificado(df_selecionado):
    pdf = PDF()
    for index, row in df_selecionado.iterrows():
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        texto = f"""
        RECIBO DE CONTROLE INTERNO - {row['ID']}
        Data: {row['Data']} | Valor: R$ {row['Valor']:.2f}
        Sócio: {row['Socio']} | Categoria: {row['Categoria']}
        Desc: {row['Descrição']}
        ---------------------------------------------------------
        """
        pdf.multi_cell(0, 10, texto)
    return pdf.output(dest='S').encode('latin-1')

def link_whatsapp(telefone):
    if not telefone or len(str(telefone)) < 8:
        return None
    # Remove caracteres não numéricos
    tel_limpo = ''.join(filter(str.isdigit, str(telefone)))
    return f"https://wa.me/55{tel_limpo}?text=Olá, segue seu recibo do Centro Espírita."

# ==============================================================================
# INTERFACE PRINCIPAL
# ==============================================================================

st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2910/2910756.png", width=100)
st.sidebar.title("Menu Tesouraria")
menu = st.sidebar.radio("Navegação", ["Dashboard", "Lançamentos", "Sócios", "Conciliação Bancária", "Emitir Recibos"])

# --- MÓDULO 1: DASHBOARD ---
if menu == "Dashboard":
    st.title("🕊️ Visão Geral da Tesouraria")
    st.markdown("---")
    
    df = st.session_state['financeiro']
    
    if not df.empty:
        receitas = df[df['Tipo'] == "Entrada"]['Valor'].sum()
        despesas = df[df['Tipo'] == "Saída"]['Valor'].sum()
        saldo = receitas - despesas
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Receitas", f"R$ {receitas:,.2f}")
        c2.metric("Despesas", f"R$ {despesas:,.2f}")
        c3.metric("Saldo em Caixa", f"R$ {saldo:,.2f}", delta_color="normal")
        
        st.subheader("Últimas Movimentações")
        st.dataframe(df.tail(5), use_container_width=True)
    else:
        st.info("Nenhum dado lançado ainda.")

# --- MÓDULO 2: LANÇAMENTOS ---
elif menu == "Lançamentos":
    st.title("📝 Novo Lançamento")
    
    with st.form("form_lancamento"):
        col1, col2 = st.columns(2)
        data = col1.date_input("Data", date.today())
        tipo = col2.selectbox("Tipo", ["Entrada", "Saída"])
        
        col3, col4 = st.columns(2)
        if tipo == "Entrada":
            cat_list = ["Doação Anônima", "Mensalidade", "Cantina", "Bazar", "Livros"]
        else:
            cat_list = ["Luz/Água", "Manutenção", "Materiais", "Caridade", "Outros"]
        
        categoria = col3.selectbox("Categoria", cat_list)
        valor = col4.number_input("Valor R$", min_value=0.01, format="%.2f")
        
        # Seleção de Sócio (Carrega da lista de sócios)
        lista_socios = ["Não Identificado"] + st.session_state['socios']['Nome'].tolist()
        socio = st.selectbox("Vinculado ao Sócio/Doador", lista_socios)
        
        descricao = st.text_input("Descrição Detalhada")
        
        submitted = st.form_submit_button("Salvar Movimentação")
        
        if submitted:
            novo_id = len(st.session_state['financeiro']) + 1
            novo_lancamento = {
                "ID": novo_id,
                "Data": data,
                "Tipo": tipo,
                "Categoria": categoria,
                "Descrição": descricao,
                "Valor": valor,
                "Socio": socio,
                "Conciliado": "Manual"
            }
            st.session_state['financeiro'] = pd.concat([st.session_state['financeiro'], pd.DataFrame([novo_lancamento])], ignore_index=True)
            st.success("Lançamento salvo com sucesso!")

# --- MÓDULO 3: SÓCIOS ---
elif menu == "Sócios":
    st.title("👥 Gestão de Sócios")
    
    tab1, tab2 = st.tabs(["Lista de Sócios", "Importar Excel"])
    
    with tab1:
        st.dataframe(st.session_state['socios'], use_container_width=True)
        
    with tab2:
        st.write("Faça upload de uma lista de sócios (Excel) para atualizar o cadastro.")
        uploaded_file = st.file_uploader("Arquivo Excel (.xlsx)", type="xlsx")
        
        if uploaded_file:
            try:
                df_upload = pd.read_excel(uploaded_file)
                st.write("Prévia dos dados:")
                st.dataframe(df_upload.head())
                
                if st.button("Confirmar Importação"):
                    # Aqui você pode adicionar lógica para mesclar e não duplicar
                    st.session_state['socios'] = pd.concat([st.session_state['socios'], df_upload], ignore_index=True)
                    st.success(f"{len(df_upload)} sócios importados com sucesso!")
            except Exception as e:
                st.error(f"Erro ao ler arquivo: {e}")

# --- MÓDULO 4: CONCILIAÇÃO BANCÁRIA ---
elif menu == "Conciliação Bancária":
    st.title("🏦 Importação de Extrato")
    st.markdown("Faça o upload do extrato bancário para gerar lançamentos em lote.")
    
    extrato = st.file_uploader("Extrato Bancário (.csv ou .xlsx)", type=["csv", "xlsx"])
    
    if extrato:
        if extrato.name.endswith('.csv'):
            df_banco = pd.read_csv(extrato)
        else:
            df_banco = pd.read_excel(extrato)
            
        st.info(f"O arquivo contém {len(df_banco)} linhas. Classifique abaixo:")
        
        with st.form("conciliacao_form"):
            lancamentos_conciliados = []
            
            # Mostra as primeiras 5 linhas como exemplo
            for i, row in df_banco.head(5).iterrows():
                st.markdown(f"**Item {i+1}:** R$ {row.get('Valor', 0)} | {row.get('Descrição', 'Sem desc')}")
                
                col_a, col_b = st.columns(2)
                cat_sel = col_a.selectbox(f"Categoria {i}", ["Mensalidade", "Doação", "Despesa Bancária", "Ignorar"], key=f"cat_{i}")
                socio_sel = col_b.selectbox(f"Sócio {i}", ["Não Identificado"] + st.session_state['socios']['Nome'].tolist(), key=f"soc_{i}")
                st.divider()
                
                lancamentos_conciliados.append({
                    "Valor": row.get('Valor', 0),
                    "Categoria": cat_sel,
                    "Socio": socio_sel,
                    "Descricao": row.get('Descrição', '')
                })
            
            if st.form_submit_button("Processar e Lançar"):
                # Lógica simplificada de inserção
                for l in lancamentos_conciliados:
                    if l['Categoria'] != "Ignorar":
                        novo_mov = {
                            "ID": len(st.session_state['financeiro']) + 1,
                            "Data": date.today(),
                            "Tipo": "Entrada" if float(l['Valor']) > 0 else "Saída",
                            "Categoria": l['Categoria'],
                            "Descrição": l['Descricao'],
                            "Valor": abs(float(l['Valor'])),
                            "Socio": l['Socio'],
                            "Conciliado": "Auto-Banco"
                        }
                        st.session_state['financeiro'] = pd.concat([st.session_state['financeiro'], pd.DataFrame([novo_mov])], ignore_index=True)
                st.success("Conciliação realizada!")

# --- MÓDULO 5: EMISSÃO DE RECIBOS ---
elif menu == "Emitir Recibos":
    st.title("🖨️ Central de Recibos")
    
    df = st.session_state['financeiro']
    # Filtra apenas entradas para emitir recibo
    df_entradas = df[df['Tipo'] == "Entrada"]
    
    if not df_entradas.empty:
        st.subheader("Selecione os recibos para gerar")
        
        # Checkbox para selecionar quais recibos imprimir
        # Truque do Streamlit para seleção em tabela
        df_display = df_entradas.copy()
        df_display['Selecionar'] = False
        
        edited_df = st.data_editor(
            df_display,
            column_config={"Selecionar": st.column_config.CheckboxColumn(required=True)},
            disabled=["ID", "Data", "Valor", "Socio"],
            hide_index=True,
        )
        
        recibos_selecionados = edited_df[edited_df['Selecionar'] == True]
        
        col1, col2 = st.columns(2)
        
        # Botão 1: PDF Unificado (Estilo Extrato)
        with col1:
            if not recibos_selecionados.empty:
                pdf_unificado = gerar_pdf_unificado(recibos_selecionados)
                st.download_button(
                    "📂 Baixar PDF Unificado (Todos)",
                    data=pdf_unificado,
                    file_name="recibos_unificados.pdf",
                    mime="application/pdf"
                )
        
        # Lista individual com opção de WhatsApp
        st.markdown("---")
        st.subheader("Envio Individual via WhatsApp")
        
        for index, row in recibos_selecionados.iterrows():
            col_a, col_b, col_c = st.columns([3, 1, 1])
            col_a.write(f"**{row['Socio']}** - R$ {row['Valor']}")
            
            # Gerar PDF individual na memória
            pdf_bytes = gerar_recibo_unico(row)
            
            # Botão Download Individual
            col_b.download_button(
                "⬇️ PDF",
                data=pdf_bytes,
                file_name=f"recibo_{row['ID']}.pdf",
                mime="application/pdf",
                key=f"btn_{row['ID']}"
            )
            
            # Botão WhatsApp
            # Tenta achar o telefone do sócio
            tel_socio = st.session_state['socios'].loc[
                st.session_state['socios']['Nome'] == row['Socio'], 'Telefone'
            ]
            
            if not tel_socio.empty:
                link = link_whatsapp(tel_socio.values[0])
                if link:
                    col_c.markdown(f"[📲 Enviar Zap]({link})", unsafe_allow_html=True)
                else:
                    col_c.caption("Sem Tel")
            else:
                col_c.caption("Não Cadastrado")
            
            st.divider()

    else:
        st.info("Não há entradas registradas para gerar recibos.")
