"""Testes automáticos do domínio do No $tress.

Executar:  python -m unittest testes -v
"""

import json
import os
import tempfile
import unittest
from datetime import date, timedelta

from main import (
    Assinatura, AssinaturaAnual, AssinaturaMensal, Categoria,
    GerenciadorAssinaturas, PeriodoTeste, Relatorio,
    formatar_data, formatar_moeda, ler_data, ler_valor, somar_meses,
)

HOJE = date(2026, 11, 5)


def cat(nome="Entretenimento"):
    return Categoria(nome)


def mensal(nome="Netflix", valor=55.90, inicio=date(2026, 11, 7), categoria=None):
    return AssinaturaMensal(nome, valor, inicio, categoria or cat())


def anual(nome="Google One", valor=120.0, inicio=date(2026, 3, 15)):
    return AssinaturaAnual(nome, valor, inicio, cat("Trabalho"))


def teste(nome="Duolingo Super", inicio=date(2026, 11, 1), dias=7, apos=34.90):
    return PeriodoTeste(nome, inicio, cat("Educação"), dias, apos)


class TesteEncapsulamento(unittest.TestCase):
    def test_validacoes_do_construtor(self):
        with self.assertRaises(ValueError):
            AssinaturaMensal("", 10, HOJE, cat())            # nome vazio
        with self.assertRaises(ValueError):
            AssinaturaMensal("X", 10, HOJE, None)            # sem categoria
        with self.assertRaises(ValueError):
            AssinaturaMensal("X", 10, "05/11/2026", cat())   # data não é date
        with self.assertRaises(ValueError):
            AssinaturaMensal("X", 0, HOJE, cat())            # valor zero
        with self.assertRaises(ValueError):
            PeriodoTeste("X", HOJE, cat(), 0, 19.90)         # duração zero
        with self.assertRaises(ValueError):
            PeriodoTeste("X", HOJE, cat(), 7, 0)             # valor após zero

    def test_valor_e_privado(self):
        a = mensal()
        self.assertFalse(hasattr(a, "__valor"))
        self.assertTrue(hasattr(a, "_Assinatura__valor"))
        self.assertEqual(a.get_valor(), 55.90)
        a.set_valor(60)
        self.assertEqual(a.get_valor(), 60.0)

    def test_valor_invalido_e_recusado(self):
        a = mensal()
        for invalido in (-5, 0, "10", None, float("nan")):
            with self.assertRaises(ValueError):
                a.set_valor(invalido)
        self.assertEqual(a.get_valor(), 55.90)  # continua com o valor antigo


class TesteFuncoesAuxiliares(unittest.TestCase):
    def test_ler_data(self):
        self.assertEqual(ler_data("05/11/2026"), date(2026, 11, 5))
        for ruim in ("2026-11-05", "31/02/2026", "abc", ""):
            with self.assertRaises(ValueError):
                ler_data(ruim)

    def test_ler_valor(self):
        self.assertEqual(ler_valor("23,90"), 23.90)
        self.assertEqual(ler_valor("23.90"), 23.90)
        self.assertEqual(ler_valor("1.234,56"), 1234.56)
        for ruim in ("abc", "0", "-1", "", "nan"):
            with self.assertRaises(ValueError):
                ler_valor(ruim)

    def test_somar_meses_e_formato(self):
        self.assertEqual(somar_meses(date(2026, 1, 31), 1), date(2026, 2, 28))
        self.assertEqual(somar_meses(date(2026, 1, 31), 2), date(2026, 3, 31))
        self.assertEqual(somar_meses(date(2026, 12, 15), 1), date(2027, 1, 15))
        self.assertEqual(somar_meses(date(2026, 3, 31), -1), date(2026, 2, 28))
        self.assertEqual(formatar_data(date(2026, 11, 5)), "05/11/2026")
        self.assertEqual(formatar_moeda(3189.38), "R$ 3.189,38")
        self.assertEqual(formatar_moeda(55.9), "R$ 55,90")


class TesteGerenciador(unittest.TestCase):
    def setUp(self):
        self.g = GerenciadorAssinaturas(caminho=os.devnull)

    def test_alertas_dos_proximos_7_dias(self):
        self.g.adicionar(mensal("Netflix", inicio=HOJE + timedelta(days=3)))
        self.g.adicionar(mensal("Spotify", inicio=HOJE + timedelta(days=10)))
        self.g.adicionar(teste("Duolingo", inicio=HOJE - timedelta(days=5), dias=7))
        alertas = self.g.gerar_alertas(HOJE)
        self.assertEqual(len(alertas), 2)
        self.assertEqual([al.assinatura.nome for al in alertas], ["Duolingo", "Netflix"])
        self.assertTrue(alertas[0].titulo.startswith("Fim do período de teste"))
        self.assertTrue(alertas[1].titulo.startswith("Vencimento próximo"))
        self.assertIn("R$ 34,90", alertas[0].mensagem)

    def test_edicao_mantem_historico(self):
        antiga = mensal("Netflix")
        self.g.adicionar(antiga)
        self.g.registrar_pagamento("Netflix", HOJE)
        nova = mensal("Netflix HD", valor=60.0)
        self.g.substituir("Netflix", nova)
        self.assertEqual([a.nome for a in self.g.listar()], ["Netflix HD"])
        self.assertEqual(len(self.g.cobrancas), 1)
        self.assertIs(self.g.cobrancas[0].assinatura, nova)
        self.assertEqual(nova.ultimo_pagamento, date(2026, 11, 7))

    def test_exemplos_nao_duplicam(self):
        self.assertEqual(self.g.carregar_exemplos(HOJE), 6)
        self.assertEqual(self.g.carregar_exemplos(HOJE), 0)
        self.assertEqual(len(self.g.listar()), 6)
        self.assertEqual(len(self.g.gerar_alertas(HOJE)), 2)  # Netflix e Duolingo

    def test_nome_duplicado_e_recusado(self):
        self.g.adicionar(mensal("Netflix"))
        with self.assertRaises(ValueError):
            self.g.adicionar(mensal("netflix"))
        self.assertEqual(len(self.g.listar()), 1)

    def test_registrar_pagamento_cria_cobranca(self):
        self.g.adicionar(mensal("Netflix", 55.90))
        c = self.g.registrar_pagamento("netflix", HOJE)
        self.assertEqual(c.valor, 55.90)
        self.assertEqual(c.data, HOJE)
        self.assertEqual(len(self.g.cobrancas), 1)
        self.g.adicionar(teste("Duolingo"))
        with self.assertRaises(ValueError):  # teste ativo não gera pagamento
            self.g.registrar_pagamento("Duolingo", HOJE)

    def test_remover_apaga_cobrancas(self):
        self.g.adicionar(mensal("Netflix"))
        self.g.adicionar(mensal("Spotify", inicio=date(2026, 11, 14)))
        self.g.registrar_pagamento("Netflix", HOJE)
        self.g.registrar_pagamento("Spotify", HOJE)
        self.g.remover("Netflix")
        self.assertIsNone(self.g.buscar("Netflix"))
        self.assertEqual([c.assinatura.nome for c in self.g.cobrancas], ["Spotify"])


class TestePersistencia(unittest.TestCase):
    def setUp(self):
        self._pasta = tempfile.TemporaryDirectory()
        self.addCleanup(self._pasta.cleanup)
        self.caminho = os.path.join(self._pasta.name, "assinaturas.json")

    def test_arquivo_inexistente_comeca_vazio(self):
        g = GerenciadorAssinaturas(self.caminho)
        self.assertIsNone(g.carregar_json())
        self.assertEqual(g.listar(), [])

    def test_json_ida_e_volta(self):
        g = GerenciadorAssinaturas(self.caminho)
        g.carregar_exemplos(HOJE)
        g.registrar_pagamento("Netflix", HOJE)
        g.salvar_json()

        with open(self.caminho, encoding="utf-8") as arq:
            tipos = {d["nome"]: d["tipo"] for d in json.load(arq)["assinaturas"]}
        self.assertEqual(tipos["Duolingo Super"], "teste")
        self.assertEqual(tipos["Google One"], "anual")

        g2 = GerenciadorAssinaturas(self.caminho)
        self.assertIsNone(g2.carregar_json())
        self.assertEqual([a.nome for a in g2.listar()], [a.nome for a in g.listar()])
        for a, b in zip(g.listar(), g2.listar()):
            self.assertIs(type(a), type(b))
            self.assertEqual(a.get_valor(), b.get_valor())
            self.assertEqual(a.proxima_cobranca(HOJE), b.proxima_cobranca(HOJE))
            self.assertEqual(a.categoria.get_nome(), b.categoria.get_nome())
        self.assertEqual(len(g2.cobrancas), 1)
        self.assertEqual(g2.cobrancas[0].assinatura.nome, "Netflix")
        self.assertEqual(g2.buscar("Duolingo Super").duracao_dias, 7)

    def test_arquivo_corrompido_vira_backup(self):
        with open(self.caminho, "w", encoding="utf-8") as arq:
            arq.write("{ isto nao e json")
        g = GerenciadorAssinaturas(self.caminho)
        aviso = g.carregar_json()
        self.assertIsNotNone(aviso)
        self.assertEqual(g.listar(), [])
        self.assertTrue(os.path.exists(self.caminho + ".bak"))


class TestePolimorfismo(unittest.TestCase):
    def test_assinatura_e_abstrata(self):
        with self.assertRaises(TypeError):
            Assinatura("X", 10, HOJE, cat())

    def test_custo_mensal_de_cada_tipo(self):
        lista = [mensal(valor=55.90), anual(valor=120.0), teste()]
        custos = [a.calcular_custo_mensal(HOJE) for a in lista]  # mesma chamada, 3 tipos
        self.assertEqual(custos, [55.90, 10.0, 0.0])

    def test_teste_passa_a_cobrar_depois_do_fim(self):
        t = teste(inicio=date(2026, 11, 1), dias=7, apos=34.90)
        self.assertEqual(t.calcular_custo_mensal(date(2026, 11, 7)), 0.0)
        self.assertEqual(t.calcular_custo_mensal(date(2026, 11, 8)), 34.90)
        self.assertEqual(t.calcular_custo_mensal(date(2027, 1, 1)), 34.90)


class TesteProximaCobranca(unittest.TestCase):
    def test_mensal_e_ajuste_de_fim_de_mes(self):
        a = mensal(inicio=date(2026, 1, 31))
        self.assertEqual(a.proxima_cobranca(date(2026, 2, 1)), date(2026, 2, 28))
        self.assertEqual(a.proxima_cobranca(date(2026, 3, 1)), date(2026, 3, 31))

    def test_anual(self):
        a = anual(inicio=date(2026, 3, 15))
        self.assertEqual(a.proxima_cobranca(HOJE), date(2027, 3, 15))

    def test_cobranca_hoje_conta_como_proxima(self):
        a = mensal(inicio=HOJE)
        self.assertEqual(a.proxima_cobranca(HOJE), HOJE)

    def test_pagamento_avanca_a_proxima_cobranca(self):
        a = mensal(inicio=date(2026, 11, 7))
        self.assertEqual(a.proxima_cobranca(date(2026, 11, 7)), date(2026, 11, 7))
        a.marcar_pago(date(2026, 11, 7))
        self.assertEqual(a.proxima_cobranca(date(2026, 11, 7)), date(2026, 12, 7))

    def test_pagamento_antecipado_quita_o_vencimento_pendente(self):
        a = mensal(inicio=date(2026, 11, 7))
        a.marcar_pago(HOJE)  # paga dia 05, antes do vencimento do dia 07
        self.assertEqual(a.ultimo_pagamento, date(2026, 11, 7))
        self.assertEqual(a.proxima_cobranca(HOJE), date(2026, 12, 7))
        self.assertEqual(a.proxima_cobranca(date(2026, 11, 7)), date(2026, 12, 7))

    def test_periodo_de_teste(self):
        t = teste(inicio=date(2026, 11, 1), dias=7)
        self.assertEqual(t.fim_do_teste(), date(2026, 11, 8))
        self.assertTrue(t.em_teste(HOJE))
        self.assertFalse(t.em_teste(date(2026, 11, 8)))
        self.assertEqual(t.proxima_cobranca(HOJE), date(2026, 11, 8))
        self.assertEqual(t.proxima_cobranca(date(2026, 11, 9)), date(2026, 12, 8))


class TesteRelatorio(unittest.TestCase):
    def setUp(self):
        self.lista = [
            mensal("Netflix", 55.90),
            mensal("Spotify", 23.90),
            mensal("Academia", 99.00, categoria=cat("Saúde")),
            mensal("Xbox Game Pass", 44.99),
            anual(valor=120.0),
            teste(),
        ]

    def test_total_e_por_categoria(self):
        self.assertEqual(Relatorio.gasto_mensal_total(self.lista, HOJE), 233.79)
        por_categoria = Relatorio.gasto_por_categoria(self.lista, HOJE)
        self.assertEqual(por_categoria, {"Entretenimento": 124.79, "Saúde": 99.0,
                                         "Trabalho": 10.0, "Educação": 0.0})
        self.assertEqual(list(por_categoria)[0], "Entretenimento")  # ordem decrescente

    def test_projecao_anual_simples(self):
        lista = [mensal(valor=50.0), anual(valor=120.0)]
        self.assertEqual(Relatorio.projecao_anual(lista, HOJE), 720.0)  # (50 + 10) * 12

    def test_projecao_considera_fim_do_teste(self):
        # o teste termina em 08/11: o mês atual custa 0 e os outros 11 meses custam 34,90
        self.assertEqual(Relatorio.projecao_anual([teste()], HOJE), round(34.90 * 11, 2))
        self.assertEqual(Relatorio.projecao_anual(self.lista, HOJE), 3189.38)  # Figura 1


if __name__ == "__main__":
    unittest.main()
