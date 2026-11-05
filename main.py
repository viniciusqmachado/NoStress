"""No $tress - controle de assinaturas e contas recorrentes.

Projeto final de Programação Orientada a Objetos - Universidade La Salle.
Autor: Vinícius Quevedo Machado

Estrutura do arquivo:
  1. Funções auxiliares (datas, valores, formatação)
  2. Classes de domínio (9): Categoria, Assinatura, AssinaturaMensal,
     AssinaturaAnual, PeriodoTeste, Cobranca, Alerta, Relatorio,
     GerenciadorAssinaturas
  3. Classes de interface (6): JanelaPrincipal, TelaBase, TelaLista,
     TelaCadastro, TelaAlertas, TelaRelatorio
  4. Programa principal (main)

Como executar:  python main.py   (o gráfico precisa de: pip install matplotlib)
"""

import calendar
import json
import math
import os
import shutil
import tkinter as tk
from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta
from tkinter import messagebox, ttk

try:  # o gráfico é opcional: sem matplotlib o programa funciona sem ele
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    TEM_MATPLOTLIB = True
except Exception:  # ImportError ou problema de backend
    TEM_MATPLOTLIB = False

CAMINHO_PADRAO = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "assinaturas.json"
)
NOMES_CATEGORIAS = ["Entretenimento", "Trabalho", "Saúde", "Educação", "Outros"]
JANELA_ALERTA_DIAS = 7  # valor fixo no código

MSG_VALOR = "Informe um valor numérico maior que zero."
MSG_DATA = "Data inválida. Use dd/mm/aaaa."
MSG_DURACAO = "A duração deve ser um número inteiro maior que zero."
MSG_VALOR_APOS = "Informe o valor cobrado após o teste."
MSG_DUPLICADO = "Já existe uma assinatura com esse nome."


# ----------------------------------------------------------------------
# 1. Funções auxiliares
# ----------------------------------------------------------------------
def somar_meses(data, meses):
    """Soma meses a uma data ajustando o dia no fim do mês (31/01 + 1 = 28/02)."""
    total = data.year * 12 + (data.month - 1) + meses
    ano, mes0 = divmod(total, 12)
    mes = mes0 + 1
    dia = min(data.day, calendar.monthrange(ano, mes)[1])
    return date(ano, mes, dia)


def formatar_data(data):
    return data.strftime("%d/%m/%Y")


def formatar_numero(valor):
    """1234.5 -> '1.234,50' (padrão brasileiro)."""
    texto = f"{valor:,.2f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_moeda(valor):
    return "R$ " + formatar_numero(valor)


def ler_data(texto):
    """Converte 'dd/mm/aaaa' em date ou levanta ValueError."""
    try:
        return datetime.strptime(str(texto).strip(), "%d/%m/%Y").date()
    except ValueError:
        raise ValueError(MSG_DATA) from None


def ler_valor(texto):
    """Converte texto em número maior que zero (aceita vírgula ou ponto)."""
    try:
        t = str(texto).replace("R$", "").strip()
        if "," in t:  # '1.234,56' -> '1234.56'
            t = t.replace(".", "").replace(",", ".")
        valor = float(t)
    except ValueError:
        raise ValueError(MSG_VALOR) from None
    if not math.isfinite(valor) or valor <= 0:
        raise ValueError(MSG_VALOR)
    return valor


def _texto_faltam(dias):
    if dias <= 0:
        return "é hoje"
    if dias == 1:
        return "falta 1 dia"
    return f"faltam {dias} dias"


def _texto_em(dias):
    if dias <= 0:
        return "hoje"
    if dias == 1:
        return "em 1 dia"
    return f"em {dias} dias"


# ----------------------------------------------------------------------
# 2. Classes de domínio
# ----------------------------------------------------------------------
class Categoria:
    """Agrupa assinaturas (Entretenimento, Trabalho, Saúde...)."""

    def __init__(self, nome):
        self.nome = nome

    def get_nome(self):
        return self.nome


class Assinatura(ABC):
    """Classe base abstrata: não existe assinatura 'genérica'."""

    tipo = ""      # texto gravado no JSON
    rotulo = ""    # texto mostrado na tela
    _aceita_valor_zero = False
    _passo_meses = 1  # de quantos em quantos meses a cobrança se repete

    def __init__(self, nome, valor, data_inicio, categoria, ultimo_pagamento=None):
        nome = nome.strip() if isinstance(nome, str) else ""
        if not nome:
            raise ValueError("Informe um nome.")
        if not isinstance(categoria, Categoria):
            raise ValueError("Escolha uma categoria.")
        if not self.__validar_data(data_inicio):
            raise ValueError(MSG_DATA)
        self.nome = nome
        self.__valor = 0.0
        self.set_valor(valor)
        self.data_inicio = data_inicio
        self.categoria = categoria
        self.ultimo_pagamento = ultimo_pagamento  # último vencimento já pago

    # --- encapsulamento do valor ---
    def get_valor(self):
        return self.__valor

    def set_valor(self, novo):
        invalido = (
            isinstance(novo, bool)
            or not isinstance(novo, (int, float))
            or not math.isfinite(novo)
            or novo < 0
            or (novo == 0 and not self._aceita_valor_zero)
        )
        if invalido:
            raise ValueError(MSG_VALOR)
        self.__valor = float(novo)

    # --- polimorfismo ---
    @abstractmethod
    def calcular_custo_mensal(self, data_ref=None):
        """Custo mensal equivalente; cada subclasse calcula do seu jeito."""

    def valor_cobranca(self):
        """Valor que será cobrado no próximo vencimento."""
        return self.get_valor()

    # --- próxima cobrança ---
    def _primeiro_vencimento(self):
        return self.data_inicio

    def proxima_cobranca(self, data_ref=None):
        return self.__calcular_proxima_cobranca(data_ref or date.today())

    def marcar_pago(self, data):
        """Quita o vencimento pendente (mesmo que o pagamento seja antecipado)."""
        self.ultimo_pagamento = self.proxima_cobranca(data)

    # --- métodos privados ---
    def __validar_data(self, data):
        return isinstance(data, date)

    def __calcular_proxima_cobranca(self, ref):
        primeiro = self._primeiro_vencimento()
        passo = self._passo_meses
        dif = (ref.year - primeiro.year) * 12 + (ref.month - primeiro.month)
        k = max(0, dif // passo - 1)
        while True:
            venc = somar_meses(primeiro, k * passo)
            if venc >= ref and (
                self.ultimo_pagamento is None or venc > self.ultimo_pagamento
            ):
                return venc
            k += 1

    # --- persistência ---
    def to_dict(self):
        return {
            "tipo": self.tipo,
            "nome": self.nome,
            "valor": self.get_valor(),
            "categoria": self.categoria.get_nome(),
            "data_inicio": self.data_inicio.isoformat(),
            "ultimo_pagamento": (
                self.ultimo_pagamento.isoformat() if self.ultimo_pagamento else None
            ),
        }


class AssinaturaMensal(Assinatura):
    tipo = "mensal"
    rotulo = "Mensal"

    def calcular_custo_mensal(self, data_ref=None):
        return self.get_valor()


class AssinaturaAnual(Assinatura):
    tipo = "anual"
    rotulo = "Anual"
    _passo_meses = 12

    def calcular_custo_mensal(self, data_ref=None):
        return self.get_valor() / 12


class PeriodoTeste(Assinatura):
    """Teste gratuito que depois vira cobrança mensal (o objeto não troca de classe)."""

    tipo = "teste"
    rotulo = "Período de teste"
    _aceita_valor_zero = True

    def __init__(self, nome, data_inicio, categoria, duracao_dias,
                 valor_apos_teste, ultimo_pagamento=None):
        if (isinstance(duracao_dias, bool) or not isinstance(duracao_dias, int)
                or duracao_dias <= 0):
            raise ValueError(MSG_DURACAO)
        if (isinstance(valor_apos_teste, bool)
                or not isinstance(valor_apos_teste, (int, float))
                or not math.isfinite(valor_apos_teste) or valor_apos_teste <= 0):
            raise ValueError(MSG_VALOR_APOS)
        super().__init__(nome, 0.0, data_inicio, categoria, ultimo_pagamento)
        self.duracao_dias = duracao_dias
        self.valor_apos_teste = float(valor_apos_teste)

    def fim_do_teste(self):
        return self.data_inicio + timedelta(days=self.duracao_dias)

    def em_teste(self, data_ref=None):
        return self.__teste_ativo(data_ref or date.today())

    def __teste_ativo(self, data_ref):
        return data_ref < self.fim_do_teste()

    def calcular_custo_mensal(self, data_ref=None):
        data_ref = data_ref or date.today()
        return 0.0 if self.__teste_ativo(data_ref) else self.valor_apos_teste

    def valor_cobranca(self):
        return self.valor_apos_teste

    def _primeiro_vencimento(self):
        return self.fim_do_teste()  # a primeira cobrança é no fim do teste

    def to_dict(self):
        dados = super().to_dict()
        dados["duracao_dias"] = self.duracao_dias
        dados["valor_apos_teste"] = self.valor_apos_teste
        return dados


def criar_assinatura(tipo, nome, valor, data_inicio, categoria,
                     duracao_dias=None, valor_apos_teste=None,
                     ultimo_pagamento=None):
    """Fábrica: cria a subclasse certa a partir do campo 'tipo'."""
    if tipo == "mensal":
        return AssinaturaMensal(nome, valor, data_inicio, categoria, ultimo_pagamento)
    if tipo == "anual":
        return AssinaturaAnual(nome, valor, data_inicio, categoria, ultimo_pagamento)
    if tipo == "teste":
        return PeriodoTeste(nome, data_inicio, categoria, duracao_dias,
                            valor_apos_teste, ultimo_pagamento)
    raise ValueError(f"Tipo de assinatura desconhecido: {tipo!r}")


class Cobranca:
    """Registro de um pagamento feito pelo usuário."""

    def __init__(self, data, valor, assinatura):
        self.data = data
        self.valor = valor
        self.assinatura = assinatura

    def to_dict(self):
        return {
            "assinatura": self.assinatura.nome,
            "data": self.data.isoformat(),
            "valor": self.valor,
        }


class Alerta:
    """Aviso de vencimento próximo ou de fim de período de teste."""

    def __init__(self, assinatura, titulo, mensagem, data_aviso):
        self.assinatura = assinatura
        self.titulo = titulo
        self.mensagem = mensagem
        self.data_aviso = data_aviso


class Relatorio:
    """Cálculos de gasto. Chama calcular_custo_mensal() sem saber o tipo (polimorfismo)."""

    @staticmethod
    def gasto_mensal_total(lista, data_ref=None):
        data_ref = data_ref or date.today()
        return round(sum(a.calcular_custo_mensal(data_ref) for a in lista), 2)

    @staticmethod
    def gasto_por_categoria(lista, data_ref=None):
        data_ref = data_ref or date.today()
        totais = {}
        for a in lista:
            nome = a.categoria.get_nome()
            totais[nome] = totais.get(nome, 0.0) + a.calcular_custo_mensal(data_ref)
        ordenado = sorted(totais.items(), key=lambda item: item[1], reverse=True)
        return {nome: round(valor, 2) for nome, valor in ordenado}

    @staticmethod
    def projecao_anual(lista, data_ref=None):
        """Soma os próximos 12 meses, um a um (testes que terminam passam a pesar)."""
        data_ref = data_ref or date.today()
        total = 0.0
        for i in range(12):
            ref = somar_meses(data_ref, i)
            total += sum(a.calcular_custo_mensal(ref) for a in lista)
        return round(total, 2)


class GerenciadorAssinaturas:
    """Mantém as assinaturas, as cobranças e coordena as operações do sistema."""

    def __init__(self, caminho=CAMINHO_PADRAO):
        self.caminho = caminho
        self.assinaturas = []
        self.cobrancas = []
        self.categorias = [Categoria(n) for n in NOMES_CATEGORIAS]

    # --- categorias ---
    def buscar_categoria(self, nome):
        for c in self.categorias:
            if c.get_nome().lower() == str(nome).strip().lower():
                return c
        raise ValueError("Escolha uma categoria.")

    # --- CRUD ---
    def listar(self):
        return list(self.assinaturas)

    def buscar(self, nome):
        chave = str(nome).strip().lower()
        for a in self.assinaturas:
            if a.nome.lower() == chave:
                return a
        return None

    def adicionar(self, assinatura):
        if self.buscar(assinatura.nome) is not None:
            raise ValueError(MSG_DUPLICADO)
        self.assinaturas.append(assinatura)

    def substituir(self, nome, nova):
        """Edição: troca a assinatura mantendo o histórico de pagamentos."""
        antiga = self.buscar(nome)
        if antiga is None:
            raise ValueError("Assinatura não encontrada.")
        outra = self.buscar(nova.nome)
        if outra is not None and outra is not antiga:
            raise ValueError(MSG_DUPLICADO)
        if nova.ultimo_pagamento is None:
            nova.ultimo_pagamento = antiga.ultimo_pagamento
        self.assinaturas[self.assinaturas.index(antiga)] = nova
        for c in self.cobrancas:
            if c.assinatura is antiga:
                c.assinatura = nova

    def remover(self, nome):
        a = self.buscar(nome)
        if a is None:
            raise ValueError("Assinatura não encontrada.")
        self.assinaturas.remove(a)
        self.cobrancas = [c for c in self.cobrancas if c.assinatura is not a]

    def registrar_pagamento(self, nome, data=None):
        a = self.buscar(nome)
        if a is None:
            raise ValueError("Assinatura não encontrada.")
        data = data or date.today()
        if isinstance(a, PeriodoTeste) and a.em_teste(data):
            raise ValueError("Não é possível registrar pagamento durante o período de teste.")
        cobranca = Cobranca(data, a.valor_cobranca(), a)
        a.marcar_pago(data)
        self.cobrancas.append(cobranca)
        return cobranca

    def listar_cobrancas(self, nome=None):
        if nome is None:
            return list(self.cobrancas)
        return [c for c in self.cobrancas if c.assinatura.nome.lower() == nome.lower()]

    # --- alertas ---
    def gerar_alertas(self, data_ref=None, dias=JANELA_ALERTA_DIAS):
        data_ref = data_ref or date.today()
        alertas = []
        for a in self.assinaturas:
            prox = a.proxima_cobranca(data_ref)
            faltam = (prox - data_ref).days
            if not 0 <= faltam <= dias:
                continue
            if isinstance(a, PeriodoTeste) and a.em_teste(data_ref):
                titulo = f"Fim do período de teste: {a.nome}"
                msg = (f"O teste termina {_texto_em(faltam)} ({formatar_data(prox)}); "
                       f"depois passa a cobrar {formatar_moeda(a.valor_apos_teste)} por mês.")
            else:
                titulo = f"Vencimento próximo: {a.nome}"
                msg = (f"Cobrança de {formatar_moeda(a.valor_cobranca())} em "
                       f"{formatar_data(prox)} ({_texto_faltam(faltam)}).")
            alertas.append(Alerta(a, titulo, msg, prox))
        alertas.sort(key=lambda al: al.data_aviso)
        return alertas

    # --- exemplos de demonstração ---
    def carregar_exemplos(self, hoje=None):
        """Cadastra 6 assinaturas de demonstração (só com a lista vazia)."""
        if self.assinaturas:
            return 0
        hoje = hoje or date.today()
        cat = self.buscar_categoria

        def inicio(dias, meses):  # início tal que o próximo vencimento caia em hoje+dias
            return somar_meses(hoje + timedelta(days=dias), -meses)

        modelos = [
            criar_assinatura("mensal", "Netflix", 55.90, inicio(2, 6), cat("Entretenimento")),
            criar_assinatura("mensal", "Spotify", 23.90, inicio(9, 6), cat("Entretenimento")),
            criar_assinatura("mensal", "Academia", 99.00, inicio(14, 6), cat("Saúde")),
            criar_assinatura("mensal", "Xbox Game Pass", 44.99, inicio(21, 6), cat("Entretenimento")),
            criar_assinatura("anual", "Google One", 120.00, inicio(130, 12), cat("Trabalho")),
            criar_assinatura("teste", "Duolingo Super", 0.0, hoje - timedelta(days=4),
                             cat("Educação"), 7, 34.90),
        ]
        for m in modelos:
            self.adicionar(m)
        return len(modelos)

    # --- persistência ---
    def salvar_json(self, caminho=None):
        caminho = caminho or self.caminho
        dados = {
            "assinaturas": [a.to_dict() for a in self.assinaturas],
            "cobrancas": [c.to_dict() for c in self.cobrancas],
        }
        temporario = caminho + ".tmp"  # grava num temporário para não perder dados
        with open(temporario, "w", encoding="utf-8") as arq:
            json.dump(dados, arq, ensure_ascii=False, indent=2)
        os.replace(temporario, caminho)

    def carregar_json(self, caminho=None):
        """Carrega o JSON. Retorna None se deu certo ou uma mensagem de aviso.

        Arquivo inexistente: começa vazio. Arquivo corrompido: guarda uma
        cópia (.bak), avisa e começa vazio.
        """
        caminho = caminho or self.caminho
        self.assinaturas = []
        self.cobrancas = []
        if not os.path.exists(caminho):
            return None
        try:
            with open(caminho, "r", encoding="utf-8") as arq:
                dados = json.load(arq)
            assinaturas = []
            for d in dados["assinaturas"]:
                categoria = self.buscar_categoria(d["categoria"])
                a = criar_assinatura(
                    d["tipo"], d["nome"], float(d["valor"]),
                    date.fromisoformat(d["data_inicio"]), categoria,
                    d.get("duracao_dias"), d.get("valor_apos_teste"),
                    date.fromisoformat(d["ultimo_pagamento"]) if d.get("ultimo_pagamento") else None,
                )
                if any(x.nome.lower() == a.nome.lower() for x in assinaturas):
                    raise ValueError("nome repetido no arquivo")
                assinaturas.append(a)
            por_nome = {a.nome.lower(): a for a in assinaturas}
            cobrancas = [
                Cobranca(date.fromisoformat(c["data"]), float(c["valor"]),
                         por_nome[c["assinatura"].lower()])
                for c in dados["cobrancas"]
            ]
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            backup = caminho + ".bak"
            try:
                shutil.copyfile(caminho, backup)
            except OSError:
                pass
            return ("O arquivo de dados está corrompido. Uma cópia foi guardada em "
                    f"'{os.path.basename(backup)}' e o programa começou vazio.")
        self.assinaturas = assinaturas
        self.cobrancas = cobrancas
        return None


# ----------------------------------------------------------------------
# 3. Classes de interface (Tkinter)
# ----------------------------------------------------------------------
VERDE = "#1F7A5A"
VERDE_CLARO = "#E8F3EE"
AMARELO = "#FFF4CC"
VERMELHO = "#B3261E"
PALETA = ["#1F7A5A", "#E0A030", "#3A7CA5", "#8E6BBF", "#9AA5A0"]


def criar_cartao(pai, titulo, variavel):
    """Pequeno cartão com título e valor em destaque."""
    cartao = tk.Frame(pai, bg=VERDE_CLARO, highlightbackground=VERDE,
                      highlightthickness=1, padx=10, pady=6)
    tk.Label(cartao, text=titulo, bg=VERDE_CLARO, anchor="w",
             font=("Helvetica", 9)).pack(fill="x")
    tk.Label(cartao, textvariable=variavel, bg=VERDE_CLARO, anchor="w",
             fg=VERDE, font=("Helvetica", 14, "bold")).pack(fill="x")
    return cartao


class TelaBase(ttk.Frame, ABC):
    """Tela abstrata: cada tela implementa atualizar() à sua maneira."""

    def __init__(self, master, gerenciador):
        super().__init__(master, padding=12)
        self.gerenciador = gerenciador

    @property
    def janela(self):
        return self.winfo_toplevel()

    @abstractmethod
    def atualizar(self):
        """Redesenha a tela com os dados atuais."""


class TelaLista(TelaBase):
    """Tela principal: totais, tabela de assinaturas e botões de ação."""

    COLUNAS = [
        ("nome", "Nome", 190, "w"),
        ("categoria", "Categoria", 130, "w"),
        ("tipo", "Tipo", 130, "w"),
        ("custo", "Custo/mês (R$)", 120, "e"),
        ("proxima", "Próx. cobrança", 120, "center"),
    ]

    def __init__(self, master, gerenciador):
        super().__init__(master, gerenciador)
        self.v_total = tk.StringVar()
        self.v_proj = tk.StringVar()
        self.v_qtd = tk.StringVar()
        self.v_status = tk.StringVar()
        self.__ordem = []  # nomes na ordem em que aparecem na tabela

        topo = ttk.Frame(self)
        topo.pack(fill="x")
        for titulo, var in (("Custo mensal total", self.v_total),
                            ("Projeção anual", self.v_proj),
                            ("Assinaturas", self.v_qtd)):
            criar_cartao(topo, titulo, var).pack(side="left", expand=True,
                                                 fill="x", padx=(0, 8))

        meio = ttk.Frame(self)
        meio.pack(fill="both", expand=True, pady=8)
        self.tabela = ttk.Treeview(meio, columns=[c[0] for c in self.COLUNAS],
                                   show="headings", selectmode="browse")
        for chave, titulo, largura, ancora in self.COLUNAS:
            self.tabela.heading(chave, text=titulo)
            self.tabela.column(chave, width=largura, anchor=ancora)
        self.tabela.tag_configure("vence", background=AMARELO)
        barra = ttk.Scrollbar(meio, orient="vertical", command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=barra.set)
        self.tabela.grid(row=0, column=0, sticky="nsew")
        barra.grid(row=0, column=1, sticky="ns")
        meio.rowconfigure(0, weight=1)
        meio.columnconfigure(0, weight=1)
        self.tabela.bind("<<TreeviewSelect>>", lambda e: self.__ao_selecionar())

        botoes = ttk.Frame(self)
        botoes.pack(fill="x")
        ttk.Button(botoes, text="Nova assinatura",
                   command=lambda: self.janela.nova_assinatura()).pack(side="left", padx=(0, 6))
        ttk.Button(botoes, text="Editar", command=self.__editar).pack(side="left", padx=6)
        ttk.Button(botoes, text="Remover", command=self.__remover).pack(side="left", padx=6)
        self.botao_pagar = ttk.Button(botoes, text="Registrar pagamento",
                                      command=self.__pagar)
        self.botao_pagar.pack(side="left", padx=6)
        self.botao_exemplos = ttk.Button(botoes, text="Carregar exemplos",
                                         command=self.__exemplos)
        self.botao_exemplos.pack(side="right")

        ttk.Label(self, textvariable=self.v_status).pack(anchor="w", pady=(8, 0))

    def definir_status(self, texto):
        self.v_status.set(texto)

    def __selecionado(self, avisar=True):
        sel = self.tabela.selection()
        if not sel:
            if avisar:
                messagebox.showinfo("Selecione uma assinatura",
                                    "Clique em uma linha da tabela primeiro.")
            return None
        return self.__ordem[int(sel[0])]

    def __ao_selecionar(self):
        nome = self.__selecionado(avisar=False)
        a = self.gerenciador.buscar(nome) if nome else None
        em_teste = isinstance(a, PeriodoTeste) and a.em_teste(self.janela.hoje())
        self.botao_pagar.state(["disabled"] if em_teste else ["!disabled"])

    def __editar(self):
        nome = self.__selecionado()
        if nome:
            self.janela.editar_assinatura(nome)

    def __remover(self):
        nome = self.__selecionado()
        if not nome:
            return
        if messagebox.askyesno("Remover assinatura",
                               f"Remover '{nome}' e as cobranças dela?"):
            self.gerenciador.remover(nome)
            self.janela.salvar_dados()
            self.janela.atualizar_abas()
            self.atualizar()
            self.definir_status(f"'{nome}' removida.")

    def __pagar(self):
        nome = self.__selecionado()
        if not nome:
            return
        try:
            c = self.gerenciador.registrar_pagamento(nome, self.janela.hoje())
        except ValueError as erro:
            messagebox.showwarning("Registrar pagamento", str(erro))
            return
        self.janela.salvar_dados()
        self.janela.atualizar_abas()
        self.atualizar()
        self.definir_status(f"Pagamento de {formatar_moeda(c.valor)} registrado em '{nome}'.")

    def __exemplos(self):
        qtd = self.gerenciador.carregar_exemplos(self.janela.hoje())
        self.janela.salvar_dados()
        self.janela.atualizar_abas()
        self.atualizar()
        self.definir_status(f"{qtd} assinaturas de exemplo carregadas.")

    def atualizar(self):
        hoje = self.janela.hoje()
        lista = self.gerenciador.listar()
        self.v_total.set(formatar_moeda(Relatorio.gasto_mensal_total(lista, hoje)))
        self.v_proj.set(formatar_moeda(Relatorio.projecao_anual(lista, hoje)))
        self.v_qtd.set(str(len(lista)))

        anterior = self.__selecionado(avisar=False)
        self.tabela.delete(*self.tabela.get_children())
        self.__ordem = [a.nome for a in lista]
        for i, a in enumerate(lista):
            prox = a.proxima_cobranca(hoje)
            tags = ("vence",) if 0 <= (prox - hoje).days <= JANELA_ALERTA_DIAS else ()
            self.tabela.insert("", "end", iid=str(i), tags=tags, values=(
                a.nome, a.categoria.get_nome(), a.rotulo,
                formatar_numero(a.calcular_custo_mensal(hoje)), formatar_data(prox)))
        if anterior in self.__ordem:
            self.tabela.selection_set(str(self.__ordem.index(anterior)))
        self.botao_exemplos.state(["!disabled"] if not lista else ["disabled"])
        self.__ao_selecionar()


class TelaCadastro(TelaBase):
    """Formulário de nova assinatura / edição."""

    def __init__(self, master, gerenciador):
        super().__init__(master, gerenciador)
        self.campos = {n: tk.StringVar() for n in
                       ("nome", "valor", "categoria", "tipo", "data_inicio",
                        "duracao", "valor_apos")}
        self.campos["tipo"].set("mensal")
        self.v_titulo = tk.StringVar(value="Nova assinatura")
        self.v_erro = tk.StringVar()
        self.__editando = None  # nome original, quando está editando

        ttk.Label(self, textvariable=self.v_titulo,
                  style="Titulo.TLabel").grid(row=0, column=0, columnspan=2,
                                              sticky="w", pady=(0, 10))
        linhas = [
            (1, "Nome"), (2, "Valor (R$)"), (3, "Categoria"), (4, "Tipo"),
            (5, "Data de início (1ª cobrança)"), (6, "Duração do teste (dias)"),
            (7, "Valor após o teste (R$)"),
        ]
        rotulos = {}
        for linha, texto in linhas:
            rotulos[linha] = ttk.Label(self, text=texto)
            rotulos[linha].grid(row=linha, column=0, sticky="w", pady=4, padx=(0, 16))

        self.entrada_nome = ttk.Entry(self, textvariable=self.campos["nome"], width=40)
        self.entrada_valor = ttk.Entry(self, textvariable=self.campos["valor"], width=40)
        self.combo = ttk.Combobox(self, textvariable=self.campos["categoria"],
                                  state="readonly", width=38)
        tipos = ttk.Frame(self)
        for texto, valor in (("Mensal", "mensal"), ("Anual", "anual"),
                             ("Período de teste", "teste")):
            ttk.Radiobutton(tipos, text=texto, value=valor,
                            variable=self.campos["tipo"],
                            command=self.__ao_mudar_tipo).pack(side="left", padx=(0, 12))
        self.entrada_data = ttk.Entry(self, textvariable=self.campos["data_inicio"], width=40)
        self.entrada_duracao = ttk.Entry(self, textvariable=self.campos["duracao"], width=40)
        self.entrada_apos = ttk.Entry(self, textvariable=self.campos["valor_apos"], width=40)

        for linha, widget in ((1, self.entrada_nome), (2, self.entrada_valor),
                              (3, self.combo), (4, tipos), (5, self.entrada_data),
                              (6, self.entrada_duracao), (7, self.entrada_apos)):
            widget.grid(row=linha, column=1, sticky="w", pady=4)
        # linhas exibidas só para o tipo "Período de teste"
        self.__linhas_teste = [(rotulos[6], self.entrada_duracao),
                               (rotulos[7], self.entrada_apos)]

        tk.Label(self, textvariable=self.v_erro, fg=VERMELHO, anchor="w").grid(
            row=8, column=0, columnspan=2, sticky="w", pady=(10, 4))
        botoes = ttk.Frame(self)
        botoes.grid(row=9, column=0, columnspan=2, sticky="w", pady=6)
        ttk.Button(botoes, text="Salvar", command=self.__salvar).pack(side="left", padx=(0, 8))
        ttk.Button(botoes, text="Cancelar",
                   command=lambda: self.janela.mostrar_tela("lista")).pack(side="left")
        self.__ao_mudar_tipo()

    def atualizar(self):
        self.combo.configure(values=[c.get_nome() for c in self.gerenciador.categorias])

    def preparar_novo(self):
        self.__editando = None
        self.v_titulo.set("Nova assinatura")
        self.v_erro.set("")
        for nome in ("nome", "valor", "categoria", "duracao", "valor_apos"):
            self.campos[nome].set("")
        self.campos["tipo"].set("mensal")
        self.campos["data_inicio"].set(formatar_data(self.janela.hoje()))
        self.atualizar()
        self.__ao_mudar_tipo()

    def preparar_edicao(self, a):
        self.__editando = a.nome
        self.v_titulo.set(f"Editar assinatura: {a.nome}")
        self.v_erro.set("")
        self.atualizar()
        self.campos["nome"].set(a.nome)
        self.campos["categoria"].set(a.categoria.get_nome())
        self.campos["tipo"].set(a.tipo)
        self.campos["data_inicio"].set(formatar_data(a.data_inicio))
        self.campos["valor"].set(formatar_numero(a.get_valor()))
        if isinstance(a, PeriodoTeste):
            self.campos["duracao"].set(str(a.duracao_dias))
            self.campos["valor_apos"].set(formatar_numero(a.valor_apos_teste))
        else:
            self.campos["duracao"].set("")
            self.campos["valor_apos"].set("")
        self.__ao_mudar_tipo()

    def __ao_mudar_tipo(self):
        if self.campos["tipo"].get() == "teste":
            self.campos["valor"].set("0,00")
            self.entrada_valor.state(["disabled"])
            for rotulo, entrada in self.__linhas_teste:
                rotulo.grid()
                entrada.grid()
        else:
            if self.campos["valor"].get() == "0,00":
                self.campos["valor"].set("")
            self.entrada_valor.state(["!disabled"])
            for rotulo, entrada in self.__linhas_teste:
                rotulo.grid_remove()
                entrada.grid_remove()

    def __montar(self):
        """Valida os campos e devolve a Assinatura do tipo escolhido."""
        nome = self.campos["nome"].get().strip()
        if not nome:
            raise ValueError("Informe um nome.")
        tipo = self.campos["tipo"].get()
        valor = 0.0 if tipo == "teste" else ler_valor(self.campos["valor"].get())
        nome_categoria = self.campos["categoria"].get()
        if not nome_categoria:
            raise ValueError("Escolha uma categoria.")
        categoria = self.gerenciador.buscar_categoria(nome_categoria)
        inicio = ler_data(self.campos["data_inicio"].get())
        duracao = apos = None
        if tipo == "teste":
            try:
                duracao = int(self.campos["duracao"].get().strip())
            except ValueError:
                raise ValueError(MSG_DURACAO) from None
            if duracao <= 0:
                raise ValueError(MSG_DURACAO)
            try:
                apos = ler_valor(self.campos["valor_apos"].get())
            except ValueError:
                raise ValueError(MSG_VALOR_APOS) from None
        return criar_assinatura(tipo, nome, valor, inicio, categoria, duracao, apos)

    def __salvar(self):
        try:
            nova = self.__montar()
            if self.__editando is None:
                self.gerenciador.adicionar(nova)
                status = f"'{nova.nome}' cadastrada."
            else:
                self.gerenciador.substituir(self.__editando, nova)
                status = f"'{nova.nome}' atualizada."
        except ValueError as erro:
            self.v_erro.set(str(erro))  # mostra a mensagem e mantém o formulário
            return
        self.v_erro.set("")
        self.janela.salvar_dados()
        self.janela.atualizar_abas()
        self.janela.mostrar_tela("lista")
        self.janela.telas["lista"].definir_status(status)


class TelaAlertas(TelaBase):
    """Vencimentos e fins de teste dos próximos 7 dias."""

    def __init__(self, master, gerenciador):
        super().__init__(master, gerenciador)
        self.v_titulo = tk.StringVar()
        ttk.Label(self, textvariable=self.v_titulo,
                  style="Titulo.TLabel").pack(anchor="w", pady=(0, 10))
        self.lista = ttk.Frame(self)
        self.lista.pack(fill="both", expand=True)

    def atualizar(self):
        for w in self.lista.winfo_children():
            w.destroy()
        hoje = self.janela.hoje()
        self.v_titulo.set(f"Avisos para os próximos {JANELA_ALERTA_DIAS} dias "
                          f"(hoje: {formatar_data(hoje)})")
        alertas = self.gerenciador.gerar_alertas(hoje)
        for al in alertas:
            caixa = tk.Frame(self.lista, bg=AMARELO,
                             highlightbackground="#E0B84A", highlightthickness=1)
            caixa.pack(fill="x", pady=4)
            tk.Label(caixa, text=al.titulo, bg=AMARELO, anchor="w",
                     font=("Helvetica", 10, "bold")).pack(fill="x", padx=8, pady=(6, 0))
            tk.Label(caixa, text=al.mensagem, bg=AMARELO, anchor="w", justify="left",
                     wraplength=780).pack(fill="x", padx=8, pady=(0, 6))
        if not alertas:
            ttk.Label(self.lista, text="Nenhum alerta para os próximos "
                                       f"{JANELA_ALERTA_DIAS} dias.").pack(anchor="w")


class TelaRelatorio(TelaBase):
    """Totais, gasto por categoria e gráfico de pizza (matplotlib)."""

    def __init__(self, master, gerenciador):
        super().__init__(master, gerenciador)
        self.v_total = tk.StringVar()
        self.v_proj = tk.StringVar()

        esquerda = ttk.Frame(self)
        esquerda.grid(row=0, column=0, sticky="n", padx=(0, 16))
        ttk.Label(esquerda, text="Relatório de gastos",
                  style="Titulo.TLabel").pack(anchor="w", pady=(0, 8))
        criar_cartao(esquerda, "Custo mensal total", self.v_total).pack(fill="x", pady=4)
        criar_cartao(esquerda, "Projeção anual", self.v_proj).pack(fill="x", pady=4)
        self.tabela = ttk.Treeview(esquerda, columns=("categoria", "valor", "pct"),
                                   show="headings", height=6, selectmode="none")
        for chave, titulo, largura, ancora in (("categoria", "Categoria", 120, "w"),
                                               ("valor", "R$/mês", 80, "e"),
                                               ("pct", "%", 60, "e")):
            self.tabela.heading(chave, text=titulo)
            self.tabela.column(chave, width=largura, anchor=ancora)
        self.tabela.pack(fill="x", pady=8)
        ttk.Button(esquerda, text="Atualizar", command=self.atualizar).pack()

        if TEM_MATPLOTLIB:
            self.figura = Figure(figsize=(5.2, 4), dpi=100)
            self.canvas = FigureCanvasTkAgg(self.figura, master=self)
            self.canvas.get_tk_widget().grid(row=0, column=1, sticky="nsew")
        else:
            self.figura = None
            ttk.Label(self, text="Gráfico indisponível.\nInstale com: pip install matplotlib",
                      justify="center").grid(row=0, column=1, sticky="nsew")
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

    def atualizar(self):
        hoje = self.janela.hoje()
        lista = self.gerenciador.listar()
        total = Relatorio.gasto_mensal_total(lista, hoje)
        dados = Relatorio.gasto_por_categoria(lista, hoje)
        self.v_total.set(formatar_moeda(total))
        self.v_proj.set(formatar_moeda(Relatorio.projecao_anual(lista, hoje)))
        self.tabela.delete(*self.tabela.get_children())
        for nome, valor in dados.items():
            pct = (valor / total * 100) if total else 0.0
            self.tabela.insert("", "end", values=(
                nome, formatar_numero(valor), f"{pct:.1f}".replace(".", ",")))
        self.__desenhar_grafico(dados)

    def __desenhar_grafico(self, dados):
        if not TEM_MATPLOTLIB:
            return
        self.figura.clear()
        ax = self.figura.add_subplot(111)
        itens = [(n, v) for n, v in dados.items() if v > 0]
        if itens:
            ax.pie([v for _, v in itens], labels=[n for n, _ in itens],
                   autopct="%1.1f%%", startangle=90,
                   colors=PALETA[:len(itens)])
            ax.set_title("Gasto mensal por categoria")
        else:
            ax.text(0.5, 0.5, "Sem gastos para exibir", ha="center", va="center")
            ax.axis("off")
        self.canvas.draw()


class JanelaPrincipal(tk.Tk):
    """Janela com a barra de abas e as quatro telas."""

    ABAS = [("lista", "Assinaturas"), ("cadastro", "Nova assinatura"),
            ("alertas", "Alertas"), ("relatorio", "Relatórios")]

    def __init__(self, gerenciador):
        super().__init__()
        self.gerenciador = gerenciador
        self.telas = {}
        self.botoes_abas = {}
        self.title("No $tress – Controle de Assinaturas")
        self.geometry("960x620")
        self.minsize(820, 540)

        self.__criar_abas()
        self.__criar_telas()

        aviso = self.gerenciador.carregar_json()
        if aviso:
            messagebox.showwarning("No $tress", aviso)
        self.mostrar_tela("lista")

    def hoje(self):
        return date.today()

    def __criar_abas(self):
        estilo = ttk.Style(self)
        estilo.theme_use("clam")
        estilo.configure("Titulo.TLabel", font=("Helvetica", 13, "bold"), foreground=VERDE)
        estilo.configure("Aba.TButton", background=VERDE_CLARO, foreground="black",
                         padding=(14, 6))
        estilo.map("Aba.TButton", background=[("active", "#D3E9DF")])
        estilo.configure("AbaAtiva.TButton", background=VERDE, foreground="white",
                         padding=(14, 6))
        estilo.map("AbaAtiva.TButton", background=[("active", VERDE)])
        estilo.configure("TButton", padding=(10, 4))
        # correção conhecida: sem isto as cores das linhas do Treeview não aparecem
        for opcao in ("foreground", "background"):
            atual = [e for e in estilo.map("Treeview", query_opt=opcao)
                     if e[:2] != ("!disabled", "!selected")]
            estilo.map("Treeview", **{opcao: atual})

        barra = ttk.Frame(self, padding=(12, 10, 12, 0))
        barra.pack(fill="x")
        for chave, texto in self.ABAS:
            if chave == "cadastro":
                comando = self.nova_assinatura
            else:
                comando = lambda c=chave: self.mostrar_tela(c)
            botao = ttk.Button(barra, text=texto, style="Aba.TButton", command=comando)
            botao.pack(side="left", padx=(0, 6))
            self.botoes_abas[chave] = botao

        self.area = ttk.Frame(self)
        self.area.pack(fill="both", expand=True)
        self.area.rowconfigure(0, weight=1)
        self.area.columnconfigure(0, weight=1)

    def __criar_telas(self):
        classes = {"lista": TelaLista, "cadastro": TelaCadastro,
                   "alertas": TelaAlertas, "relatorio": TelaRelatorio}
        for chave, classe in classes.items():
            tela = classe(self.area, self.gerenciador)
            tela.grid(row=0, column=0, sticky="nsew")
            self.telas[chave] = tela

    def mostrar_tela(self, nome):
        tela = self.telas[nome]
        tela.atualizar()
        tela.tkraise()
        for chave, botao in self.botoes_abas.items():
            botao.configure(style="AbaAtiva.TButton" if chave == nome else "Aba.TButton")
        self.atualizar_abas()

    def nova_assinatura(self):
        self.telas["cadastro"].preparar_novo()
        self.mostrar_tela("cadastro")

    def editar_assinatura(self, nome):
        a = self.gerenciador.buscar(nome)
        if a is None:
            return
        self.telas["cadastro"].preparar_edicao(a)
        self.mostrar_tela("cadastro")

    def atualizar_abas(self):
        qtd = len(self.gerenciador.gerar_alertas(self.hoje()))
        self.botoes_abas["alertas"].configure(text=f"Alertas ({qtd})")

    def salvar_dados(self):
        try:
            self.gerenciador.salvar_json()
        except OSError as erro:
            messagebox.showerror("No $tress", f"Não foi possível salvar os dados:\n{erro}")

    def iniciar(self):
        self.mainloop()


# ----------------------------------------------------------------------
# 4. Programa principal
# ----------------------------------------------------------------------
def main():
    gerenciador = GerenciadorAssinaturas()   # objeto 1
    janela = JanelaPrincipal(gerenciador)    # objeto 2 (cria as telas)
    janela.iniciar()


if __name__ == "__main__":
    main()
