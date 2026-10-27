# Sistema de Biblioteca — Empréstimo e Devolução de Livros

Projeto prático de Informática para a Internet desenvolvido com **Python, Flask e SQLite**. Inclui cadastro de livros e usuários, empréstimos, devoluções, cálculo simples de multas por atraso, pesquisa no acervo e relatórios.

## Funcionalidades

- Login com permissões de administrador e leitor.
- Painel inicial com resumo do acervo e dos empréstimos.
- Cadastro, edição, pesquisa e consulta de livros.
- Cadastro de usuários/leitores.
- Registro de empréstimos com prazo de 14 dias.
- Limite de 3 empréstimos ativos por leitor.
- Registro de devolução e multa de R$ 1,00 por dia de atraso.
- Histórico de empréstimos do leitor e visão geral do bibliotecário.
- Relatório de empréstimos, atrasos e livros mais emprestados.
- Banco SQLite criado automaticamente na primeira execução.

## Requisitos

- Python 3.10 ou mais recente
- pip
- Navegador web

## Executar localmente

1. Descompacte a pasta do projeto e abra um terminal dentro dela.
2. Crie um ambiente virtual:

   **Windows (PowerShell):**
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   **Linux/macOS:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Inicie o sistema:
   ```bash
   python app.py
   ```
5. Abra `http://127.0.0.1:5000` no navegador.

### Primeiro acesso

- Usuário/matrícula: `admin`
- Senha: `admin123`

Troque a senha e a chave secreta antes de usar com dados reais. O banco local `biblioteca.db` é criado automaticamente.

## Publicar no GitHub

1. Crie um repositório novo no GitHub, por exemplo `sistema-biblioteca`.
2. Extraia os arquivos desta pasta para uma pasta local.
3. No terminal, dentro da pasta, execute:

   ```bash
   git init
   git add .
   git commit -m "Cria sistema de biblioteca"
   git branch -M main
   git remote add origin https://github.com/SEU-USUARIO/sistema-biblioteca.git
   git push -u origin main
   ```

   Substitua `SEU-USUARIO` pelo seu nome de usuário do GitHub. Não envie senhas reais nem o arquivo do banco de dados.

## Estrutura

```text
sistema-biblioteca/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── biblioteca.db       # criado ao executar; ignorado pelo Git
├── static/
│   └── style.css
└── templates/
    ├── base.html
    ├── login.html
    ├── dashboard.html
    ├── books.html
    ├── book_form.html
    ├── users.html
    ├── user_form.html
    ├── loans.html
    ├── loan_form.html
    └── reports.html
```

## Regras de negócio do protótipo

- Cada empréstimo dura 14 dias.
- Um leitor pode ter até 3 empréstimos ativos.
- O livro só pode ser emprestado se houver exemplar disponível.
- A multa é calculada a R$ 1,00 por dia de atraso no momento da devolução.
- O protótipo não processa pagamentos de multas.

## Observações para apresentação

Este é um protótipo acadêmico para execução local. Antes de disponibilizar publicamente, configure `SECRET_KEY` por variável de ambiente, desative o modo debug, use HTTPS, implemente recuperação de senha e revise as medidas de segurança e privacidade.
