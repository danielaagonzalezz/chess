"""
Tests del torneo.

Lo importante: un bot que falla, se cuelga o hace una jugada ilegal pierde
su partida, pero no rompe el torneo. Los bots defectuosos estan definidos
a nivel de modulo porque cada bot juega en su propio proceso y hay que
poder enviarlos a el.
"""

import json
import time

import pytest

from chess.bots import BOTS, Bot, RandomBot
from chess.move import Move
from chess.pieces import square_from_algebraic as sq
from chess.torneo import (
    LIMITE_JUGADAS, a_html, a_markdown, calcular_elo, guardar, jugar_partida,
    jugar_torneo, main,
)

RAPIDO = dict(tiempo_maximo=5, max_jugadas=40)


# ---------- Bots defectuosos (a nivel de modulo, ver arriba) ----------

class Normal(Bot):
    name = "normal"

    def __init__(self):
        self._bot = RandomBot(seed=1)

    def choose_move(self, game):
        return self._bot.choose_move(game)


def crear_normal():
    return Normal()


class Roto(Bot):
    name = "roto"

    def choose_move(self, game):
        raise RuntimeError("boom")


class Tramposo(Bot):
    name = "tramposo"

    def choose_move(self, game):
        return Move(sq("a1"), sq("a8"))


class Texto(Bot):
    name = "texto"

    def choose_move(self, game):
        return "e2e4"


class Colgado(Bot):
    name = "colgado"

    def choose_move(self, game):
        while True:
            time.sleep(0.05)


class Suicida(Bot):
    """Muere sin avisar: el proceso termina de golpe."""

    name = "suicida"

    def choose_move(self, game):
        import os
        os._exit(1)


class NoArranca(Bot):
    name = "no-arranca"

    def __init__(self):
        raise ValueError("no puedo crearme")

    def choose_move(self, game):  # pragma: no cover
        raise NotImplementedError


def blancas(clase):
    return (clase.name, clase)


# ---------- Una partida ----------

def test_una_partida_normal_termina_con_resultado():
    p = jugar_partida(("aleatorio", None), ("1-paso", None), semilla=1, **RAPIDO)
    assert p["resultado"] in ("1-0", "0-1", "1/2-1/2")
    assert p["blancas"] == "aleatorio" and p["negras"] == "1-paso"
    assert p["fallo"] is None
    assert p["medias_jugadas"] == len(p["jugadas"].split())


def test_si_se_pasa_del_maximo_de_jugadas_son_tablas():
    p = jugar_partida(("aleatorio", None), ("aleatorio", None), semilla=1,
                      tiempo_maximo=5, max_jugadas=6)
    assert p["resultado"] == "1/2-1/2"
    assert p["motivo"] == LIMITE_JUGADAS
    assert p["medias_jugadas"] == 6


@pytest.mark.parametrize("clase, motivo", [
    (Roto, "excepcion"),
    (Tramposo, "ilegal"),
    (Texto, "ilegal"),
    (Suicida, "caida"),
])
def test_un_bot_defectuoso_con_blancas_pierde(clase, motivo):
    p = jugar_partida(blancas(clase), ("normal", crear_normal), semilla=3, **RAPIDO)
    assert p["resultado"] == "0-1"
    assert p["motivo"].startswith(motivo)
    assert p["fallo"] == {"blancas": motivo}


def test_un_bot_defectuoso_con_negras_pierde():
    p = jugar_partida(("normal", crear_normal), blancas(Roto), semilla=3, **RAPIDO)
    assert p["resultado"] == "1-0"
    assert p["fallo"] == {"negras": "excepcion"}


def test_un_bot_colgado_pierde_por_tiempo_y_no_cuelga_el_torneo():
    inicio = time.time()
    p = jugar_partida(blancas(Colgado), ("normal", crear_normal), semilla=3,
                      tiempo_maximo=1, max_jugadas=40)
    assert p["resultado"] == "0-1"
    assert p["fallo"] == {"blancas": "tiempo"}
    assert time.time() - inicio < 30


def test_un_bot_que_no_arranca_pierde():
    p = jugar_partida(blancas(NoArranca), ("normal", crear_normal), semilla=3, **RAPIDO)
    assert p["resultado"] == "0-1"
    assert p["fallo"] == {"blancas": "arranque"}


def test_si_los_dos_fallan_al_arrancar_son_tablas():
    p = jugar_partida(blancas(NoArranca), ("otro", NoArranca), semilla=3, **RAPIDO)
    assert p["resultado"] == "1/2-1/2"


# ---------- El torneo ----------

def test_el_torneo_sobrevive_a_bots_defectuosos():
    bots = {
        "normal": crear_normal, "roto": Roto, "tramposo": Tramposo,
        "texto": Texto, "colgado": Colgado, "suicida": Suicida,
    }
    torneo = jugar_torneo(bots, partidas_por_pareja=2, tiempo_maximo=1,
                          max_jugadas=30, paralelo=2)
    # 6 bots -> 15 parejas -> 30 partidas, todas terminadas.
    assert len(torneo["partidas"]) == 30
    tabla = {f["bot"]: f for f in torneo["clasificacion"]}
    assert set(tabla) == set(bots)
    # El unico bot que juega bien gana todo lo que puede.
    assert tabla["normal"]["posicion"] == 1
    # Los defectuosos cuentan sus fallos y pierden contra el que juega bien.
    for nombre in ("roto", "tramposo", "texto", "colgado", "suicida"):
        assert tabla[nombre]["fallos"] >= 1
    # Ningun defectuoso le gana nunca al que juega bien.
    contra_normal = [p for p in torneo["partidas"] if "normal" in (p["blancas"], p["negras"])]
    assert len(contra_normal) == 10
    for p in contra_normal:
        ganador = p["blancas"] if p["resultado"] == "1-0" else p["negras"]
        assert ganador == "normal", p
    # Todas las partidas reparten un punto en total.
    assert sum(f["puntos"] for f in tabla.values()) == 30


def test_el_torneo_del_catalogo_rapido_clasifica_por_nivel():
    elegidos = {n: BOTS[n] for n in ("aleatorio", "1-paso", "minimax-2")}
    torneo = jugar_torneo(elegidos, partidas_por_pareja=2, max_jugadas=80,
                          tiempo_maximo=10, paralelo=2)
    orden = [f["bot"] for f in torneo["clasificacion"]]
    assert orden[0] == "minimax-2"
    assert orden[-1] == "aleatorio"
    assert [f["posicion"] for f in torneo["clasificacion"]] == [1, 2, 3]
    elos = [f["elo"] for f in torneo["clasificacion"]]
    assert elos == sorted(elos, reverse=True)


def test_cada_pareja_juega_con_los_dos_colores_y_la_misma_apertura():
    elegidos = {n: BOTS[n] for n in ("aleatorio", "1-paso")}
    torneo = jugar_torneo(elegidos, partidas_por_pareja=2, max_jugadas=10)
    a, b = torneo["partidas"]
    assert (a["blancas"], a["negras"]) == (b["negras"], b["blancas"])
    assert a["apertura"] == b["apertura"]


def test_validaciones_de_los_parametros():
    with pytest.raises(ValueError):
        jugar_torneo({"a": crear_normal})
    with pytest.raises(ValueError):
        jugar_torneo({"a": crear_normal, "b": crear_normal}, partidas_por_pareja=3)
    with pytest.raises(ValueError):
        jugar_torneo({"a": crear_normal, "b": crear_normal}, partidas_por_pareja=0)


# ---------- Elo ----------

def _partida(blancas, negras, resultado):
    return {"blancas": blancas, "negras": negras, "resultado": resultado, "fallo": None}


def test_el_elo_ordena_por_resultados_y_la_media_es_1000():
    partidas = [
        _partida("a", "b", "1-0"), _partida("b", "a", "0-1"),
        _partida("a", "c", "1-0"), _partida("c", "a", "0-1"),
        _partida("b", "c", "1-0"), _partida("c", "b", "0-1"),
    ]
    elo = calcular_elo(["a", "b", "c"], partidas)
    assert elo["a"] > elo["b"] > elo["c"]
    assert abs(sum(elo.values()) / 3 - 1000) <= 1


def test_el_elo_de_bots_igualados_es_igual_y_no_es_infinito():
    partidas = [_partida("a", "b", "1/2-1/2"), _partida("b", "a", "1/2-1/2")]
    assert calcular_elo(["a", "b"], partidas) == {"a": 1000, "b": 1000}
    # Un bot que lo gana todo tiene un Elo alto pero finito.
    barrido = [_partida("a", "b", "1-0"), _partida("b", "a", "0-1")] * 5
    elo = calcular_elo(["a", "b"], barrido)
    assert 1000 < elo["a"] < 3000


# ---------- Salidas ----------

@pytest.fixture(scope="module")
def torneo_pequeno():
    elegidos = {n: BOTS[n] for n in ("aleatorio", "1-paso")}
    return jugar_torneo(elegidos, partidas_por_pareja=2, max_jugadas=10)


def test_el_markdown_tiene_una_fila_por_bot(torneo_pequeno):
    texto = a_markdown(torneo_pequeno)
    assert "`aleatorio`" in texto and "`1-paso`" in texto
    assert texto.count("\n| ") >= 2


def test_el_html_es_una_pagina_con_la_clasificacion(torneo_pequeno):
    pagina = a_html(torneo_pequeno)
    assert pagina.startswith("<!doctype html>")
    assert "aleatorio" in pagina and "1-paso" in pagina
    assert "clasificacion.json" in pagina


def test_el_html_escapa_los_nombres_de_los_bots():
    torneo = {
        "generado": "hoy", "duracion_segundos": 1,
        "configuracion": {"partidas_por_pareja": 2, "max_jugadas": 10},
        "clasificacion": [{
            "posicion": 1, "bot": "<script>x</script>", "elo": 1000, "puntos": 1.0,
            "partidas": 2, "victorias": 1, "tablas": 0, "derrotas": 1, "fallos": 0,
        }],
        "cruces": {"<script>x</script>": {}},
        "partidas": [],
    }
    assert "<script>" not in a_html(torneo)


def test_guardar_escribe_los_tres_ficheros(tmp_path, torneo_pequeno):
    guardar(torneo_pequeno, tmp_path / "salida")
    for nombre in ("clasificacion.json", "clasificacion.md", "clasificacion.html"):
        assert (tmp_path / "salida" / nombre).is_file()
    datos = json.loads((tmp_path / "salida" / "clasificacion.json").read_text(encoding="utf-8"))
    assert len(datos["clasificacion"]) == 2


def test_la_linea_de_comandos(tmp_path, capsys):
    codigo = main(["--bots", "aleatorio,1-paso", "--partidas", "2",
                   "--max-jugadas", "10", "--salida", str(tmp_path)])
    assert codigo == 0
    assert (tmp_path / "clasificacion.html").is_file()
    assert "Clasificación de bots" in capsys.readouterr().out


def test_la_linea_de_comandos_rechaza_bots_desconocidos():
    with pytest.raises(SystemExit):
        main(["--bots", "aleatorio,no-existe"])
