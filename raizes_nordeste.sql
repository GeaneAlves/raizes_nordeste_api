CREATE DATABASE IF NOT EXISTS raizes_nordeste;
USE raizes_nordeste;

CREATE TABLE unidades (
    id_unidade INT AUTO_INCREMENT PRIMARY KEY,
    nome_fantasia VARCHAR(100) NOT NULL,
    cnpj VARCHAR(18) UNIQUE NOT NULL,
    cidade VARCHAR(100) NOT NULL,
    estado CHAR(2) NOT NULL,
    tipo_cozinha VARCHAR(30) NOT NULL CHECK (tipo_cozinha IN ('COMPLETA', 'REDUZIDA')),
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE produtos (
    id_produto INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    descricao TEXT,
    categoria VARCHAR(50) NOT NULL,
    preco_base DECIMAL(10, 2) NOT NULL,
    sazonal BOOLEAN DEFAULT FALSE,
    periodo_sazonal VARCHAR(50),
    ativo BOOLEAN DEFAULT TRUE
);

CREATE TABLE estoque_unidade (
    id_estoque INT AUTO_INCREMENT PRIMARY KEY,
    id_unidade INT NOT NULL,
    id_produto INT NOT NULL,
    quantidade_atual INT NOT NULL DEFAULT 0,
    preco_local DECIMAL(10, 2) NOT NULL,
    disponivel_cardapio BOOLEAN DEFAULT TRUE,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE (id_unidade, id_produto),
    FOREIGN KEY (id_unidade) REFERENCES unidades(id_unidade) ON DELETE CASCADE,
    FOREIGN KEY (id_produto) REFERENCES produtos(id_produto) ON DELETE CASCADE
);

CREATE TABLE clientes (
    id_cliente INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    cpf VARCHAR(14) UNIQUE,
    email VARCHAR(150) UNIQUE,
    telefone VARCHAR(20),
    data_nascimento DATE,
    pontos_fidelidade INT DEFAULT 0,
    consentimento_lgpd BOOLEAN NOT NULL DEFAULT FALSE,
    data_consentimento TIMESTAMP NULL,
    anonimizado BOOLEAN DEFAULT FALSE,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE funcionarios (
    id_funcionario INT AUTO_INCREMENT PRIMARY KEY,
    id_unidade INT NOT NULL,
    nome VARCHAR(150) NOT NULL,
    cargo VARCHAR(50) NOT NULL CHECK (cargo IN ('ATENDENTE', 'COZINHEIRO', 'GERENTE', 'ADMIN_MATRIZ')),
    matricula VARCHAR(30) UNIQUE NOT NULL,
    ativo BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (id_unidade) REFERENCES unidades(id_unidade)
);

CREATE TABLE logs_auditoria (
    id_log INT AUTO_INCREMENT PRIMARY KEY,
    id_unidade INT NOT NULL,
    id_funcionario INT NOT NULL,
    acao VARCHAR(100) NOT NULL,
    tabela_afetada VARCHAR(50) NOT NULL,
    id_registro_afetado INT NOT NULL,
    detalhes JSON,
    data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_unidade) REFERENCES unidades(id_unidade),
    FOREIGN KEY (id_funcionario) REFERENCES funcionarios(id_funcionario)
);

CREATE TABLE pedidos (
    id_pedido INT AUTO_INCREMENT PRIMARY KEY,
    id_unidade INT NOT NULL,
    id_cliente INT NULL,
    id_funcionario INT NULL,
    canal_venda VARCHAR(30) NOT NULL CHECK (canal_venda IN ('APP', 'TOTEM', 'BALCAO', 'PICKUP')),
    status_pedido VARCHAR(30) NOT NULL DEFAULT 'AGUARDANDO_PAGAMENTO' 
        CHECK (status_pedido IN ('AGUARDANDO_PAGAMENTO', 'PAGO', 'EM_PREPARO', 'PRONTO', 'ENTREGUE', 'CANCELADO')),
    valor_total DECIMAL(10, 2) NOT NULL,
    desconto_aplicado DECIMAL(10, 2) DEFAULT 0.00,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_unidade) REFERENCES unidades(id_unidade),
    FOREIGN KEY (id_cliente) REFERENCES clientes(id_cliente),
    FOREIGN KEY (id_funcionario) REFERENCES funcionarios(id_funcionario)
);

CREATE TABLE itens_pedido (
    id_item INT AUTO_INCREMENT PRIMARY KEY,
    id_pedido INT NOT NULL,
    id_produto INT NOT NULL,
    quantidade INT NOT NULL CHECK (quantidade > 0),
    preco_unitario DECIMAL(10, 2) NOT NULL,
    subtotal DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (id_pedido) REFERENCES pedidos(id_pedido) ON DELETE CASCADE,
    FOREIGN KEY (id_produto) REFERENCES produtos(id_produto)
);

CREATE TABLE transacoes_pagamento (
    id_transacao INT AUTO_INCREMENT PRIMARY KEY,
    id_pedido INT NOT NULL,
    gateway_externo VARCHAR(50) NOT NULL,
    id_transacao_externa VARCHAR(150) UNIQUE,
    metodo_pagamento VARCHAR(30) NOT NULL CHECK (metodo_pagamento IN ('PIX', 'CREDITO', 'DEBITO', 'VALE_REFEICAO')),
    valor DECIMAL(10, 2) NOT NULL,
    status_pagamento VARCHAR(30) NOT NULL DEFAULT 'PENDENTE'
        CHECK (status_pagamento IN ('PENDENTE', 'APROVADO', 'RECUSADO', 'FALHA_COMUNICACAO')),
    payload_retorno JSON,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (id_pedido) REFERENCES pedidos(id_pedido)
);