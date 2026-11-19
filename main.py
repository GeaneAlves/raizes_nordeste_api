from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import sqlite3
import json
import uuid

app = FastAPI(
    title="API Rede Raízes do Nordeste",
    description="Sistema integrado de pedidos omnichannel, gestão de franquias, fidelidade (LGPD) e pagamentos desacoplados.",
    version="1.0.0"
)

DB_PATH = "raizes_nordeste.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Cria as tabelas espelhando o modelo relacional e insere dados iniciais para testes."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS unidades (
        id_unidade INTEGER PRIMARY KEY AUTOINCREMENT,
        nome_fantasia TEXT NOT NULL,
        cnpj TEXT UNIQUE NOT NULL,
        cidade TEXT NOT NULL,
        estado TEXT NOT NULL,
        tipo_cozinha TEXT NOT NULL,
        ativo BOOLEAN DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS produtos (
        id_produto INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        descricao TEXT,
        categoria TEXT NOT NULL,
        preco_base REAL NOT NULL,
        sazonal BOOLEAN DEFAULT 0,
        periodo_sazonal TEXT
    );

    CREATE TABLE IF NOT EXISTS estoque_unidade (
        id_estoque INTEGER PRIMARY KEY AUTOINCREMENT,
        id_unidade INTEGER NOT NULL,
        id_produto INTEGER NOT NULL,
        quantidade_atual INTEGER NOT NULL DEFAULT 0,
        preco_local REAL NOT NULL,
        disponivel_cardapio BOOLEAN DEFAULT 1,
        FOREIGN KEY (id_unidade) REFERENCES unidades(id_unidade),
        FOREIGN KEY (id_produto) REFERENCES produtos(id_produto)
    );

    CREATE TABLE IF NOT EXISTS clientes (
        id_cliente INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        cpf TEXT UNIQUE,
        email TEXT UNIQUE,
        telefone TEXT,
        data_nascimento TEXT,
        pontos_fidelidade INTEGER DEFAULT 0,
        consentimento_lgpd BOOLEAN NOT NULL DEFAULT 0,
        data_consentimento TEXT,
        anonimizado BOOLEAN DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS funcionarios (
        id_funcionario INTEGER PRIMARY KEY AUTOINCREMENT,
        id_unidade INTEGER NOT NULL,
        nome TEXT NOT NULL,
        cargo TEXT NOT NULL,
        matricula TEXT UNIQUE NOT NULL
    );

    CREATE TABLE IF NOT EXISTS logs_auditoria (
        id_log INTEGER PRIMARY KEY AUTOINCREMENT,
        id_unidade INTEGER NOT NULL,
        id_funcionario INTEGER NOT NULL,
        acao TEXT NOT NULL,
        tabela_afetada TEXT NOT NULL,
        id_registro_afetado INTEGER NOT NULL,
        detalhes TEXT,
        data_hora TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS pedidos (
        id_pedido INTEGER PRIMARY KEY AUTOINCREMENT,
        id_unidade INTEGER NOT NULL,
        id_cliente INTEGER,
        id_funcionario INTEGER,
        canal_venda TEXT NOT NULL,
        status_pedido TEXT NOT NULL DEFAULT 'AGUARDANDO_PAGAMENTO',
        valor_total REAL NOT NULL,
        criado_em TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS itens_pedido (
        id_item INTEGER PRIMARY KEY AUTOINCREMENT,
        id_pedido INTEGER NOT NULL,
        id_produto INTEGER NOT NULL,
        quantidade INTEGER NOT NULL,
        preco_unitario REAL NOT NULL,
        subtotal REAL NOT NULL
    );

    CREATE TABLE IF NOT EXISTS transacoes_pagamento (
        id_transacao INTEGER PRIMARY KEY AUTOINCREMENT,
        id_pedido INTEGER NOT NULL,
        gateway_externo TEXT NOT NULL,
        id_transacao_externa TEXT UNIQUE,
        metodo_pagamento TEXT NOT NULL,
        valor REAL NOT NULL,
        status_pagamento TEXT NOT NULL DEFAULT 'PENDENTE',
        payload_retorno TEXT
    );
    """)

    # Popula dados iniciais se o banco estiver vazio
    cursor.execute("SELECT COUNT(*) FROM unidades")
    if cursor.fetchone()[0] == 0:
        cursor.executescript("""
        INSERT INTO unidades (nome_fantasia, cnpj, cidade, estado, tipo_cozinha) VALUES
        ('Raízes do Nordeste - Recife Matriz', '11.111.111/0001-01', 'Recife', 'PE', 'COMPLETA'),
        ('Raízes do Nordeste - Caruaru Express', '11.111.111/0002-02', 'Caruaru', 'PE', 'REDUZIDA');

        INSERT INTO produtos (nome, descricao, categoria, preco_base, sazonal, periodo_sazonal) VALUES
        ('Cuscuz Recheado Carne de Sol', 'Cuscuz nordestino com carne de sol na nata e queijo coalho', 'Cuscuz', 22.90, 0, NULL),
        ('Tapioca de Coco com Queijo', 'Goma fresca hidratada com coco ralado e coalho assado', 'Tapiocas', 14.50, 0, NULL),
        ('Canjica Nordestina Tradicional', 'Receita especial servida com canela', 'Sobremesas', 12.00, 1, 'JUNINO');

        INSERT INTO estoque_unidade (id_unidade, id_produto, quantidade_atual, preco_local, disponivel_cardapio) VALUES
        (1, 1, 50, 22.90, 1),
        (1, 2, 40, 14.50, 1),
        (1, 3, 30, 12.00, 1),
        (2, 2, 25, 13.90, 1);

        INSERT INTO funcionarios (id_unidade, nome, cargo, matricula) VALUES
        (1, 'Dona Francisca', 'GERENTE', 'MAT-001'),
        (1, 'Carlos Silva', 'ATENDENTE', 'MAT-002');
        """)
    conn.commit()
    conn.close()

@app.on_event("startup")
def startup_event():
    init_db()

# =========================================================================
# SCHEMAS (PYDANTIC)
# =========================================================================
class ClienteCreate(BaseModel):
    nome: str
    cpf: str
    email: str
    telefone: str
    data_nascimento: str
    consentimento_lgpd: bool = Field(..., description="Deve ser true para conformidade com a LGPD")

class ItemPedidoInput(BaseModel):
    id_produto: int
    quantidade: int = Field(..., gt=0)

class PedidoCreate(BaseModel):
    id_unidade: int
    id_cliente: Optional[int] = None
    id_funcionario: Optional[int] = None
    canal_venda: str = Field(..., pattern="^(APP|TOTEM|BALCAO|PICKUP)$")
    itens: List[ItemPedidoInput]

class PagamentoSolicitacao(BaseModel):
    id_pedido: int
    gateway_externo: str = "MERCADOPAGO"
    metodo_pagamento: str = Field(..., pattern="^(PIX|CREDITO|DEBITO|VALE_REFEICAO)$")

class WebhookPagamento(BaseModel):
    id_transacao_externa: str
    status: str = Field(..., pattern="^(APROVADO|RECUSADO|FALHA_COMUNICACAO)$")

class AjusteEstoqueInput(BaseModel):
    id_unidade: int
    id_produto: int
    nova_quantidade: int = Field(..., ge=0)
    id_funcionario: int
    motivo: str

# =========================================================================
# ENDPOINTS DA API
# =========================================================================

@app.get("/", tags=["Status"])
def health_check():
    return {"sistema": "Rede Raízes do Nordeste API", "status": "OPERACIONAL"}

@app.get("/api/v1/unidades/{id_unidade}/cardapio", tags=["Cardápio e Unidades"])
def listar_cardapio_unidade(id_unidade: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.id_produto, p.nome, p.descricao, p.categoria, e.preco_local, 
               e.quantidade_atual, p.sazonal, p.periodo_sazonal
        FROM estoque_unidade e
        JOIN produtos p ON e.id_produto = p.id_produto
        WHERE e.id_unidade = ? AND e.disponivel_cardapio = 1 AND e.quantidade_atual > 0
    """, (id_unidade,))
    itens = [dict(row) for row in cursor.fetchall()]
    conn.close()
    if not itens:
        raise HTTPException(status_code=404, detail="Nenhum item disponível encontrado para esta unidade.")
    return {"id_unidade": id_unidade, "cardapio": itens}

@app.post("/api/v1/clientes", status_code=status.HTTP_201_CREATED, tags=["Fidelidade e LGPD"])
def cadastrar_cliente(cliente: ClienteCreate):
    if not cliente.consentimento_lgpd:
        raise HTTPException(
            status_code=400,
            detail="Violação LGPD: O consentimento explícito (consentimento_lgpd=true) é obrigatório."
        )
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO clientes (nome, cpf, email, telefone, data_nascimento, consentimento_lgpd, data_consentimento)
            VALUES (?, ?, ?, ?, ?, 1, ?)
        """, (cliente.nome, cliente.cpf, cliente.email, cliente.telefone, cliente.data_nascimento, datetime.now().isoformat()))
        conn.commit()
        novo_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=409, detail="CPF ou E-mail já cadastrado.")
    conn.close()
    return {"id_cliente": novo_id, "mensagem": "Cliente cadastrado no programa de fidelidade com sucesso."}

@app.patch("/api/v1/clientes/{id_cliente}/anonimizar", tags=["Fidelidade e LGPD"])
def anonimizar_cliente(id_cliente: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id_cliente FROM clientes WHERE id_cliente = ?", (id_cliente,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    
    cursor.execute("""
        UPDATE clientes 
        SET nome = 'TITULAR ANONIMIZADO (LGPD)', cpf = NULL, email = NULL, telefone = NULL, anonimizado = 1
        WHERE id_cliente = ?
    """, (id_cliente,))
    conn.commit()
    conn.close()
    return {"id_cliente": id_cliente, "status": "Dados pessoais anonimizados conforme Art. 18 da LGPD."}

@app.post("/api/v1/pedidos", status_code=status.HTTP_201_CREATED, tags=["Pedidos Omnichannel"])
def criar_pedido(pedido: PedidoCreate):
    conn = get_db()
    cursor = conn.cursor()
    valor_total = 0.0
    itens_processados = []

    for item in pedido.itens:
        cursor.execute("""
            SELECT quantidade_atual, preco_local FROM estoque_unidade 
            WHERE id_unidade = ? AND id_produto = ? AND disponivel_cardapio = 1
        """, (pedido.id_unidade, item.id_produto))
        estoque = cursor.fetchone()
        if not estoque or estoque["quantidade_atual"] < item.quantidade:
            conn.close()
            raise HTTPException(status_code=400, detail=f"Estoque insuficiente para o produto ID {item.id_produto}.")
        
        subtotal = round(estoque["preco_local"] * item.quantidade, 2)
        valor_total += subtotal
        itens_processados.append((item.id_produto, item.quantidade, estoque["preco_local"], subtotal))

    cursor.execute("""
        INSERT INTO pedidos (id_unidade, id_cliente, id_funcionario, canal_venda, status_pedido, valor_total)
        VALUES (?, ?, ?, ?, 'AGUARDANDO_PAGAMENTO', ?)
    """, (pedido.id_unidade, pedido.id_cliente, pedido.id_funcionario, pedido.canal_venda, round(valor_total, 2)))
    id_pedido = cursor.lastrowid

    for id_prod, qtd, preco_unit, sub in itens_processados:
        cursor.execute("""
            INSERT INTO itens_pedido (id_pedido, id_produto, quantidade, preco_unitario, subtotal)
            VALUES (?, ?, ?, ?, ?)
        """, (id_pedido, id_prod, qtd, preco_unit, sub))
        cursor.execute("""
            UPDATE estoque_unidade SET quantidade_atual = quantidade_atual - ?
            WHERE id_unidade = ? AND id_produto = ?
        """, (qtd, pedido.id_unidade, id_prod))

    conn.commit()
    conn.close()
    return {
        "id_pedido": id_pedido,
        "canal": pedido.canal_venda,
        "status": "AGUARDANDO_PAGAMENTO",
        "valor_total": round(valor_total, 2)
    }

@app.get("/api/v1/pedidos/{id_pedido}", tags=["Pedidos Omnichannel"])
def consultar_pedido(id_pedido: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pedidos WHERE id_pedido = ?", (id_pedido,))
    pedido = cursor.fetchone()
    if not pedido:
        conn.close()
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")
    conn.close()
    return dict(pedido)

@app.post("/api/v1/pagamentos/solicitar", tags=["Pagamentos Desacoplados"])
def solicitar_pagamento(dados: PagamentoSolicitacao):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT valor_total, status_pedido FROM pedidos WHERE id_pedido = ?", (dados.id_pedido,))
    pedido = cursor.fetchone()
    if not pedido:
        conn.close()
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")

    tx_externa = f"GW-{uuid.uuid4().hex[:12].upper()}"
    cursor.execute("""
        INSERT INTO transacoes_pagamento (id_pedido, gateway_externo, id_transacao_externa, metodo_pagamento, valor, status_pagamento)
        VALUES (?, ?, ?, ?, ?, 'PENDENTE')
    """, (dados.id_pedido, dados.gateway_externo, tx_externa, dados.metodo_pagamento, pedido["valor_total"]))
    conn.commit()
    conn.close()
    return {
        "id_pedido": dados.id_pedido,
        "gateway": dados.gateway_externo,
        "id_transacao_externa": tx_externa,
        "status_pagamento": "PENDENTE",
        "mensagem": "Requisição enviada ao gateway externo. Aguardando webhook."
    }

@app.post("/api/v1/pagamentos/webhook", tags=["Pagamentos Desacoplados"])
def receber_webhook_pagamento(webhook: WebhookPagamento):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transacoes_pagamento WHERE id_transacao_externa = ?", (webhook.id_transacao_externa,))
    tx = cursor.fetchone()
    if not tx:
        conn.close()
        raise HTTPException(status_code=404, detail="Transação externa não localizada.")

    cursor.execute("""
        UPDATE transacoes_pagamento SET status_pagamento = ?, payload_retorno = ?
        WHERE id_transacao_externa = ?
    """, (webhook.status, json.dumps(webhook.dict()), webhook.id_transacao_externa))

    if webhook.status == "APROVADO":
        cursor.execute("UPDATE pedidos SET status_pedido = 'PAGO' WHERE id_pedido = ?", (tx["id_pedido"],))
        cursor.execute("SELECT id_cliente, valor_total FROM pedidos WHERE id_pedido = ?", (tx["id_pedido"],))
        ped = cursor.fetchone()
        if ped and ped["id_cliente"]:
            pontos = int(ped["valor_total"])
            cursor.execute("UPDATE clientes SET pontos_fidelidade = pontos_fidelidade + ? WHERE id_cliente = ?", (pontos, ped["id_cliente"]))

    conn.commit()
    conn.close()
    return {"id_transacao_externa": webhook.id_transacao_externa, "novo_status": webhook.status}

@app.post("/api/v1/auditoria/ajuste-estoque", tags=["Auditoria e Matriz"])
def ajustar_estoque_com_auditoria(ajuste: AjusteEstoqueInput):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id_estoque, quantidade_atual FROM estoque_unidade WHERE id_unidade = ? AND id_produto = ?",
                   (ajuste.id_unidade, ajuste.id_produto))
    est = cursor.fetchone()
    if not est:
        conn.close()
        raise HTTPException(status_code=404, detail="Registro de estoque não encontrado.")

    qtd_anterior = est["quantidade_atual"]
    cursor.execute("UPDATE estoque_unidade SET quantidade_atual = ? WHERE id_estoque = ?",
                   (ajuste.nova_quantidade, est["id_estoque"]))

    detalhes_log = json.dumps({
        "quantidade_anterior": qtd_anterior,
        "quantidade_nova": ajuste.nova_quantidade,
        "motivo": ajuste.motivo
    })
    cursor.execute("""
        INSERT INTO logs_auditoria (id_unidade, id_funcionario, acao, tabela_afetada, id_registro_afetado, detalhes)
        VALUES (?, ?, 'AJUSTE_MANUAL_ESTOQUE', 'estoque_unidade', ?, ?)
    """, (ajuste.id_unidade, ajuste.id_funcionario, est["id_estoque"], detalhes_log))

    conn.commit()
    conn.close()
    return {"mensagem": "Estoque atualizado e operação registrada na auditoria.", "auditoria": json.loads(detalhes_log)}

@app.get("/api/v1/matriz/relatorios/vendas", tags=["Auditoria e Matriz"])
def relatorio_consolidado_matriz():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.id_unidade, u.nome_fantasia, u.cidade, u.estado,
               COUNT(p.id_pedido) AS total_pedidos,
               COALESCE(SUM(CASE WHEN p.status_pedido = 'PAGO' THEN p.valor_total ELSE 0 END), 0) AS faturamento_aprovado
        FROM unidades u
        LEFT JOIN pedidos p ON u.id_unidade = p.id_unidade
        GROUP BY u.id_unidade
    """)
    relatorio = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"relatorio_consolidado": relatorio}