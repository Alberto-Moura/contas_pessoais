import pdfplumber
import re
import json
from pathlib import Path

def local_transacao(prox_linha):
    '''Analisa se é um local de transação ou não'''

    padrao_local = r"^(\d{2}/\d{2}\S+)"
    match_local = re.search(padrao_local, prox_linha)
    if match_local:
        return match_local
    return None


def analisa_parada(linha):
    '''Analisa se o texto da linha contém a palavra "Saldos por Período" e retorna TRUE para parada da execução'''

    parada = r"(?s)^(.*?)(Saldos por Período)(.*?)$"
    match_parada = re.search(parada, linha)

    if match_parada:
        return True
    return None


def indentifica_transacao(linha):
    '''Analisa se é a uma transação e retorna o valor encontrado.'''

    # Padrão para identificar a transação usando regx (exemplo do dado buscado: "COMPRACARTAODEBMC 594461 10,50-")
    padrao_transacao = r"^(.+?)\s+(\d+|-)\s+(-?\d{1,3}(?:\.\d{3})*,\d{2}-?)"
    match_transacao = re.search(padrao_transacao, linha)

    if match_transacao:
        return match_transacao

    return None


def extrair_transacoes(pdf_path, pagina_inicial=0):
    '''Função responsável por abrir o extrato PDF e buscar as informações das transações'''
    
    pagina_final = len(pdfplumber.open(pdf_path).pages)
    nome_arquivo_lido = converter_data(pdf_path.name[:-4])
    transacoes = []

    # Abre o PDF com pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        for i in range(pagina_inicial, pagina_final):
            pagina = pdf.pages[i]
            texto = pagina.extract_text()
            linhas = texto.split("\n")
            cancelar_looping = False

            # Usando um loop com índice para tratar linhas alternadas
            idx = 0
            while idx < len(linhas):
                linha = linhas[idx]

                cancelar_looping = analisa_parada(linha)
                
                if cancelar_looping:
                    break
                
                match_transacao = indentifica_transacao(linha)

                if match_transacao:

                    checar_loja = True # gatilho para analisar o nome da loja
                    
                    descricao = match_transacao.group(1).strip()
                    documento = match_transacao.group(2)
                    valor_str = match_transacao.group(3)

                    # Se o valor termina com '-', move-se para o ínicio (negativo)
                    if valor_str.endswith("-"):
                        valor_str = "-" + valor_str[:-1]

                    # Conversão do valor encontrado para float
                    valor = float(valor_str.replace(".", "").replace(",", "."))
                    
                    # Definindo os tipos de transações mais comuns
                    if "PIX" in descricao.upper():
                        tipo = "pix"
                    elif "CARTAO" in descricao.upper() or "CARTÃO" in descricao.upper():
                        tipo = "cartão"
                    elif "BOLETO" in descricao.upper():
                        tipo = "boleto"
                    elif "SALARIO" in descricao.upper() or "CRÉDITO DE SALARIO" in descricao.upper():
                        tipo = "salário"
                    elif "RESG" in descricao.upper():
                        tipo = "resgate"
                    elif "REMUNERA" in descricao.upper():
                        tipo = "remuneração"
                        checar_loja = False
                    elif "TRANSFERENCIA" in descricao.upper():
                        tipo = "transferência"
                    else:
                        tipo = "outro"
                    
                    # Inicializa o campo de local com vazio
                    loja = ""
                    
                    # Verifica se a próxima linha contém o local. (exemplo deo dado buscado: "12/12CANTINA")
                    if idx + 1 < len(linhas):
                        prox_linha = linhas[idx + 1]
                        match_local = local_transacao(prox_linha)
                        if match_local:
                            loja = match_local.group(1)
                            idx += 1  # Pula a linha de local, já que ela foi consumida
                        elif checar_loja == False:
                            idx += 1 # Pula a linha de local, já que ela foi consumida
                            loja = ""
                        else:
                            idx += 1 # Pula a linha de local, já que ela foi consumida
                            transacao = indentifica_transacao(prox_linha)
                            if transacao:
                                loja = ""
                            else:
                                loja = prox_linha

                    transacoes.append({
                        "mês/ano": nome_arquivo_lido,
                        "descricao": descricao,
                        "tipo": tipo,
                        "documento": documento,
                        "valor": valor,
                        "Local": loja
                    })
                idx += 1
            if cancelar_looping:
                break

    return transacoes


def list_arquivos():
    '''Função para iterar dentro da pasta dos PDF e listá-los'''

    arquivos = []
    nome_arquivos = []

    for arquivo in PASTA_ORIGINAIS.iterdir():
        if arquivo.is_file():
            if arquivo.name not in arquivos_analisados_set:
                arquivos.append(arquivo)
                nome_arquivos.append(arquivo.name)
            else:
                print(f"Arquivo {arquivo.name} já analisado.")
    return nome_arquivos, arquivos


def converter_data(data_str):
    ''' Mapeamento de abreviações de meses para números (minúsculas) '''

    meses = {
        "jan": "01",
        "fev": "02",
        "mar": "03",
        "abr": "04",
        "mai": "05",
        "jun": "06",
        "jul": "07",
        "ago": "08",
        "set": "09",
        "out": "10",
        "nov": "11",
        "dez": "12"
    }
    
    parte_mes = data_str[:3]
    parte_ano = data_str[3:]
    mes_num = meses[parte_mes.lower()]
    return f"{mes_num}/{parte_ano}"


def carregar_bd():
    import json
    import sqlite3

    # Carrega os dados do arquivo JSON
    with open("extrato.json", "r", encoding="utf-8") as f:
        dados = json.load(f)

    # Conecta (ou cria) o banco de dados SQLite
    conn = sqlite3.connect("extrato.db")
    cursor = conn.cursor()

    # Cria a tabela se ela não existir
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS movimentacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mesano TEXT,
        descricao TEXT,
        tipo TEXT,
        documento TEXT,
        valor REAL,
        Local TEXT
    )
    """)

    # Insere os dados no banco
    for transacao in dados["movimentacoes"]:
        cursor.execute("""
        INSERT INTO movimentacoes (mesano, descricao, tipo, documento, valor, Local)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            transacao.get("mês/ano", ""),
            transacao.get("descricao", ""),
            transacao.get("tipo", ""),
            transacao.get("documento", ""),
            transacao.get("valor", 0),
            transacao.get("Local", "")
        ))

    conn.commit()
    conn.close()

    print("Dados enviados para Banco de dados com sucesso!")


if __name__ == "__main__":
    PASTA_ROOT = Path(__file__).parent
    PASTA_ORIGINAIS = PASTA_ROOT / 'pdf_originais'

    try:
        with open("arquivos_analisados.json", "r", encoding="utf-8") as f:
            arquivos_analisados = json.load(f)
            arquivos_analisados_set = set(arquivos_analisados.get("analisados", []))
    except (FileNotFoundError, json.JSONDecodeError):
        arquivos_analisados_set = set()

    # Dicionários para armazenar todas as movimentações e arquivos analisados
    resultado = {"movimentacoes": []}

    nome_arquivos, list_extratos = list_arquivos()
    arquivos_analisados_set.update(nome_arquivos)

    for extrato in list_extratos:
        pdf_file = extrato

        print(f"Analisando o arquivo {pdf_file.name}...")
        transacoes = extrair_transacoes(pdf_file)
        resultado["movimentacoes"].extend(transacoes)
    
    with open("arquivos_analisados.json", "w", encoding="utf-8") as f:
        json.dump({"analisados": sorted(str(item) for item in arquivos_analisados_set)}, f, indent=2, ensure_ascii=False)

    with open("extrato.json", "w", encoding="utf-8") as f:
            json.dump(resultado, f, indent=2, ensure_ascii=False)
    
    print("Arquivo extrato.json gerado com sucesso!")

    carregar_bd()
