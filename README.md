# Rede "Raízes do Nordeste" — API Back-end

Solução de arquitetura e desenvolvimento Back-end projetada para o estudo de caso **Rede Raízes do Nordeste** (Projeto Multidisciplinar - UNINTER).

## Arquitetura e Tecnologias
- **Linguagem / Framework:** Python 3 + FastAPI
- **Banco de Dados:** Modelagem relacional compatível com MySQL 8.0 (`database/raizes_nordeste.sql`) e SQLite para execução portátil em nuvem.
- **Padrão de Integração:** API RESTful com documentação interativa OpenAPI (Swagger UI) e processamento assíncrono de pagamentos via Webhooks.

## Funcionalidades Implementadas
1. **Omnicanalidade:** Registro de pedidos unificados para canais `APP`, `TOTEM`, `BALCAO` e `PICKUP`.
2. **Gestão de Franquias:** Cardápio dinâmico por unidade (`COMPLETA` ou `REDUZIDA`), controle de estoque local e itens sazonais.
3. **Fidelidade e LGPD:** Trava de consentimento explícito no cadastro e endpoint dedicado para anonimização de dados pessoais.
4. **Pagamentos Desacoplados:** Solicitação externa e atualização de status via Webhook sem armazenamento de dados sensíveis de cartão.
5. **Auditoria e Matriz:** Rastreabilidade de ajustes manuais de estoque e consolidação de faturamento por unidade.

## Como Executar Localmente ou no Codespaces
```bash
pip install -r requirements.txt
uvicorn main:app --reload