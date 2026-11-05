# No $tress

> *"Pra onde foi meu salário?"*

**No $tress** é um sistema desktop, feito em **Python orientado a objetos**, que centraliza as assinaturas e contas recorrentes de uma pessoa (streaming, jogos, nuvem, academia, softwares). Ele calcula o custo mensal e a projeção anual, avisa sobre vencimentos e fins de período de teste gratuito e gera relatórios e gráficos de gastos por categoria.

Projeto final da disciplina de **Programação Orientada a Objetos** — Universidade La Salle.

---

## O problema

Muitas pessoas pagam assinaturas e perdem o controle de quais possuem, quando vencem, quando um teste gratuito vira cobrança e quanto tudo isso pesa no mês. O resultado são cobranças esquecidas e um gasto que ninguém enxerga. O No $tress foi pensado para estudantes e jovens profissionais que hoje controlam isso de cabeça ou em uma planilha confusa.

## Funcionalidades

- Cadastrar, editar e remover assinaturas (CRUD completo)
- Três tipos de assinatura: **mensal**, **anual** e **período de teste**
- Custo mensal total e **projeção anual** (soma os próximos 12 meses, um a um)
- **Alertas** de vencimento e de fim de teste para os próximos 7 dias
- Registro manual de pagamentos, que avança a próxima cobrança
- **Relatório** de gastos por categoria, em tabela e em gráfico de pizza
- Persistência em JSON: nada se perde ao fechar o programa
- Proteção contra arquivo corrompido (guarda uma cópia `.bak` e começa vazio)
- Botão "Carregar exemplos" para demonstração

## Tecnologias

| Ferramenta | Uso |
|---|---|
| Python 3 | Linguagem do projeto |
| Tkinter / ttk | Interface gráfica (já vem com o Python) |
| matplotlib | Gráfico de pizza embutido na janela |
| unittest | Testes automáticos do domínio |

## Como executar

**Requisitos:** Python 3.8 ou superior com Tkinter.
No Linux, se faltar o Tkinter: `sudo apt install python3-tk`.

```bash
# 1. Clonar o repositório
git clone https://github.com/viniciusqmachado/NoStress.git
cd NoStress

# 2. Instalar a biblioteca do gráfico
pip install matplotlib

# 3. Abrir o programa
python main.py
```

> Sem o matplotlib o programa funciona normalmente, apenas sem o gráfico.
> O arquivo `assinaturas.json` é criado sozinho na primeira vez que os dados são salvos.

### Testes

```bash
python -m unittest testes -v
```

São 27 testes automáticos cobrindo polimorfismo, encapsulamento, próxima cobrança (incluindo fim de mês e pagamento antecipado), gerenciador, alertas, relatório, persistência em JSON e funções auxiliares.

## Estrutura do projeto

```
NoStress/
├── main.py      # domínio, interface gráfica e programa principal
├── testes.py    # testes automáticos
└── README.md
```

O `assinaturas.json` é gerado em tempo de execução.

## Arquitetura

O sistema tem **15 classes**, com o domínio separado da interface. A interface só conversa com o `GerenciadorAssinaturas`.

### Domínio (9 classes)

| Classe | Responsabilidade |
|---|---|
| `Assinatura` *(abstrata)* | Base com nome, valor privado (`__valor`), data de início, categoria e último pagamento |
| `AssinaturaMensal` | Custo mensal = valor |
| `AssinaturaAnual` | Custo mensal = valor ÷ 12 |
| `PeriodoTeste` | Custo zero durante o teste; depois passa a cobrar `valor_apos_teste` |
| `Categoria` | Agrupa assinaturas (Entretenimento, Trabalho, Saúde, Educação, Outros) |
| `Cobranca` | Registro de um pagamento (data, valor, assinatura) |
| `Alerta` | Aviso de vencimento próximo ou de fim de teste |
| `Relatorio` | Gasto mensal, gasto por categoria e projeção anual |
| `GerenciadorAssinaturas` | Coleção de assinaturas e cobranças, alertas e persistência |

### Interface (6 classes)

`JanelaPrincipal` (herda de `tk.Tk`), `TelaBase` (abstrata, herda de `ttk.Frame`) e as telas `TelaLista`, `TelaCadastro`, `TelaAlertas` e `TelaRelatorio`.

### Conceitos de POO aplicados

- **Herança:** `AssinaturaMensal`, `AssinaturaAnual` e `PeriodoTeste` herdam de `Assinatura`
- **Polimorfismo:** `calcular_custo_mensal()` é sobrescrito em cada subclasse e chamado de forma uniforme pelo `Relatorio`; as telas também implementam `atualizar()` à sua maneira
- **Encapsulamento:** atributo privado `__valor` (com getter e setter validado) e métodos privados como `__validar_data()`, `__calcular_proxima_cobranca()` e `__teste_ativo()`
- **Abstração:** `Assinatura` e `TelaBase` não podem ser instanciadas diretamente
- **Associação:** `Assinatura`–`Categoria`, `Cobranca`–`Assinatura`, `Alerta`–`Assinatura`

## CRUD

| Operação | Na interface | No código |
|---|---|---|
| Create | Nova assinatura → Salvar; Registrar pagamento | `adicionar()`, `registrar_pagamento()` |
| Read | Telas principal, Alertas e Relatórios | `listar()`, `buscar()`, `gerar_alertas()`, `Relatorio` |
| Update | Editar → Salvar | `substituir()` (mantém o histórico de pagamentos) |
| Delete | Remover (com confirmação) | `remover()` (apaga também as cobranças) |

## Telas

<!-- Adicione os prints na pasta docs/ e descomente as linhas abaixo -->
<!--
![Tela principal](docs/tela-principal.png)
![Cadastro](docs/cadastro.png)
![Alertas](docs/alertas.png)
![Relatório](docs/relatorio.png)
-->

- **Assinaturas:** totais no topo, tabela com categoria, tipo, custo no mês e próxima cobrança (linhas em amarelo vencem em até 7 dias)
- **Nova assinatura / Editar:** formulário com validação; ao escolher "Período de teste" aparecem os campos de duração e valor após o teste
- **Alertas:** vencimentos e fins de teste dos próximos 7 dias
- **Relatórios:** totais, gasto por categoria em tabela e gráfico de pizza

## Limitações conhecidas

- Atrasos não são controlados: se um vencimento passa sem pagamento registrado, o sistema considera o próximo ciclo
- Cobranças são manuais: o sistema calcula a próxima data, mas só cria a cobrança quando o usuário clica em "Registrar pagamento"
- Alertas só aparecem com o programa aberto, e a janela é fixa em 7 dias
- A projeção anual é por competência, não fluxo de caixa (uma assinatura anual entra como 1/12 por mês)
- Categorias fixas, sem cadastro de novas pelo programa
- Sem controle de usuários nem de moedas; os dados ficam em um arquivo local, sem senha
- Os testes automáticos cobrem só o domínio; a interface foi testada de forma manual

## Próximos passos

- [ ] Controle de atrasos
- [ ] Categorias editáveis
- [ ] Exportação do relatório
- [ ] Testar a instalação em outros computadores

## Autor

**Vinícius Quevedo Machado**
Ciências da Computação — Universidade La Salle
