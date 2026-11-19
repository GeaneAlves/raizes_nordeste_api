# Guia de Execução e Testes — API Raízes do Nordeste

## 1. Instalar dependências e iniciar o servidor
No terminal do VS Code / Codespaces, execute os comandos abaixo na ordem:

```bash
pip install -r requirements.txt
uvicorn main:app --reload


Bash
pip install -r requirements.txt
uvicorn main:app --reload


Assim que aparecer a mensagem Application startup complete, o próprio VS Code vai mostrar uma notificação no canto inferior direito: "Your application running on port 8000 is available" com um botão azul Open in Browser.

Clique nele, adicione /docs ao final da URL que abrir no navegador (ex: [https://seu-codespace-8000.app.github.dev/docs](https://seu-codespace-8000.app.github.dev/docs)) e você terá o painel completo da API pronto para executar os testes e tirar os prints para o Tópico 6 do seu trabalho!

Por fim, não se esqueça de ir na aba Source Control (ícone de ramificação no menu esquerdo do VS Code), digitar uma mensagem de commit (ex: feat: implementa API backend Raizes do Nordeste) e clicar em Commit & Sync para salvar tudo no seu repositório público do GitHub. Me avise quando estiver rodando para montarmos os cenários de teste e prints!