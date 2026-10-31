import pytest

from chess.bots import BOTS, GreedyBot, MinimaxBot, RandomBot
from chess.bots.evaluacion import evaluar
from chess.game import Game
from chess.move import Move
from chess.pieces import square_from_algebraic, WHITE


def sq(texto):
    return square_from_algebraic(texto)


def jugada(texto):
    return Move(sq(texto[:2]), sq(texto[2:4]))


def tablero(fen):
    return Game.desde_fen(fen).board


# ---------- Evaluacion ----------

def test_posicion_inicial_esta_igualada():
    assert evaluar(Game().board) == 0


def test_una_dama_de_mas_es_ventaja_para_las_blancas():
    assert evaluar(tablero("4k3/8/8/8/8/8/8/3QK3 w - - 0 1")) > 800


def test_una_dama_de_mas_es_ventaja_para_las_negras():
    assert evaluar(tablero("3qk3/8/8/8/8/8/8/4K3 w - - 0 1")) < -800


def test_la_evaluacion_es_simetrica_entre_colores():
    # La misma posicion con los colores cambiados y el tablero dado la
    # vuelta debe valer exactamente lo contrario.
    blancas = tablero("4k3/8/8/8/8/8/3QP3/4K3 w - - 0 1")
    negras = tablero("4k3/3qp3/8/8/8/8/8/4K3 w - - 0 1")
    assert evaluar(blancas) == -evaluar(negras)


def test_un_caballo_en_el_centro_vale_mas_que_en_la_esquina():
    centro = evaluar(tablero("4k3/8/8/8/3N4/8/8/4K3 w - - 0 1"))
    esquina = evaluar(tablero("4k3/8/8/8/8/8/8/N3K3 w - - 0 1"))
    assert centro > esquina


def test_en_un_final_ganado_conviene_arrinconar_al_rey_rival():
    rey_en_centro = evaluar(tablero("8/8/8/3k4/8/8/8/3QK3 w - - 0 1"))
    rey_en_esquina = evaluar(tablero("7k/8/8/8/8/8/8/3QK3 w - - 0 1"))
    assert rey_en_esquina > rey_en_centro


# ---------- GreedyBot ----------

def test_codicioso_da_mate_en_una():
    game = Game.desde_fen("7k/8/6K1/8/8/8/8/R7 w - - 0 1")
    assert GreedyBot(seed=1).choose_move(game) == jugada("a1a8")


def test_codicioso_captura_una_pieza_gratis():
    game = Game.desde_fen("4k3/8/8/3q4/8/8/8/3QK3 w - - 0 1")
    assert GreedyBot(seed=1).choose_move(game) == jugada("d1d5")


def test_codicioso_cae_en_la_trampa_de_capturar_un_peon_defendido():
    # Qxd5 gana un peon, pero el peon de c6 recaptura la dama.
    game = Game.desde_fen("4k3/8/2p5/3p4/8/8/3Q4/4K3 w - - 0 1")
    assert GreedyBot(seed=1).choose_move(game) == jugada("d2d5")


# ---------- MinimaxBot ----------

def test_minimax_da_mate_en_una():
    game = Game.desde_fen("7k/8/6K1/8/8/8/8/R7 w - - 0 1")
    assert MinimaxBot(2, seed=1).choose_move(game) == jugada("a1a8")


def test_minimax_encuentra_un_mate_en_dos():
    # Dos torres en escalera: 1.Tb7 (el rey solo puede ir a g8) 2.Ta8#.
    game = Game.desde_fen("7k/8/8/8/8/8/R7/1R4K1 w - - 0 1")
    primera = MinimaxBot(3, seed=1).choose_move(game.copy())
    game.jugar(primera)
    for respuesta in game.jugadas_legales():
        variante = game.copy()
        variante.jugar(respuesta)
        variante.jugar(MinimaxBot(3, seed=2).choose_move(variante.copy()))
        assert variante.resultado == "1-0"


def test_minimax_no_cae_en_la_trampa_del_peon_defendido():
    game = Game.desde_fen("4k3/8/2p5/3p4/8/8/3Q4/4K3 w - - 0 1")
    assert MinimaxBot(2, seed=1).choose_move(game) != jugada("d2d5")


def test_minimax_captura_una_dama_gratis():
    game = Game.desde_fen("4k3/8/8/3q4/8/8/8/3QK3 w - - 0 1")
    assert MinimaxBot(2, seed=1).choose_move(game) == jugada("d1d5")


def test_minimax_con_negras_tambien_juega_bien():
    # Mate en una para las negras: Ta1#.
    game = Game.desde_fen("r7/8/8/8/8/6k1/8/7K b - - 0 1")
    jugada_elegida = MinimaxBot(2, seed=1).choose_move(game)
    game.jugar(jugada_elegida)
    assert game.esta_terminada()
    assert game.ganador() == "black"


def test_minimax_no_modifica_la_partida_y_cuenta_nodos():
    game = Game()
    fen = game.fen()
    bot = MinimaxBot(2, seed=1)
    bot.choose_move(game)
    assert game.fen() == fen
    assert bot.nodos > 0


def test_minimax_con_la_misma_semilla_juega_igual():
    a = MinimaxBot(2, seed=7).choose_move(Game())
    b = MinimaxBot(2, seed=7).choose_move(Game())
    assert a == b


def test_mas_profundidad_mira_mas_posiciones():
    n2, n3 = MinimaxBot(2, seed=1), MinimaxBot(3, seed=1)
    n2.choose_move(Game())
    n3.choose_move(Game())
    assert n3.nodos > n2.nodos


def test_minimax_se_puede_renombrar():
    assert MinimaxBot(2, name="mi-bot").name == "mi-bot"


# ---------- Partidas ----------

def jugar_hasta(game, blancas, negras, max_jugadas):
    while not game.esta_terminada() and len(game.historial) < max_jugadas:
        bot = blancas if game.turno == WHITE else negras
        game.jugar(bot.choose_move(game.copy()))
    return game


def test_minimax_gana_a_un_bot_aleatorio():
    game = jugar_hasta(Game(), MinimaxBot(2, seed=2), RandomBot(seed=2), 60)
    assert game.resultado == "1-0"


def test_minimax_da_mate_con_rey_y_dama_contra_rey():
    game = Game.desde_fen("4k3/8/8/8/8/8/8/3QK3 w - - 0 1")
    game = jugar_hasta(game, MinimaxBot(3, seed=1), RandomBot(seed=1), 80)
    assert game.resultado == "1-0"
    assert game.motivo == "jaque mate"


# ---------- Catalogo ----------

def test_el_catalogo_incluye_los_bots_de_menor_a_mayor_nivel():
    assert list(BOTS) == [
        "aleatorio", "1-paso", "minimax-2", "minimax-3", "minimax-4",
        "ml-2", "ml-4", "ml-6", "ml-3s",
    ]


@pytest.mark.parametrize("nombre", list(BOTS))
def test_cada_bot_del_catalogo_juega_una_jugada_legal(nombre):
    bot = BOTS[nombre]()
    assert bot.name == nombre
    game = Game()
    assert bot.choose_move(game.copy()) in game.jugadas_legales()


# ---------- Profundizacion iterativa y limite de tiempo ----------

def test_sin_limite_de_tiempo_llega_a_la_profundidad_pedida():
    bot = MinimaxBot(3, seed=1)
    bot.choose_move(Game())
    assert bot.profundidad_alcanzada == 3


def test_con_un_limite_de_tiempo_diminuto_sigue_devolviendo_una_jugada_legal():
    game = Game.desde_fen("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1")
    bot = MinimaxBot(6, seed=1, tiempo=0.01)
    jugada_elegida = bot.choose_move(game.copy())
    assert jugada_elegida in game.jugadas_legales()
    assert bot.profundidad_alcanzada < 6


def test_el_limite_de_tiempo_se_respeta():
    import time
    game = Game.desde_fen("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1")
    bot = MinimaxBot(8, seed=1, tiempo=0.5)
    inicio = time.perf_counter()
    bot.choose_move(game.copy())
    assert time.perf_counter() - inicio < 2.0


def test_con_tiempo_de_sobra_se_para_al_encontrar_un_mate():
    game = Game.desde_fen("7k/8/6K1/8/8/8/8/R7 w - - 0 1")
    bot = MinimaxBot(6, seed=1, tiempo=30)
    assert bot.choose_move(game) == jugada("a1a8")
    assert bot.profundidad_alcanzada < 6


def test_la_clave_de_posicion_distingue_posiciones_y_reconoce_repetidas():
    a, b = Game(), Game()
    assert a.clave_posicion() == b.clave_posicion()
    a.jugar("e2e4")
    assert a.clave_posicion() != b.clave_posicion()
    # Mismo tablero por otro orden de jugadas: misma posicion.
    uno, dos = Game(), Game()
    for m in ["g1f3", "g8f6", "b1c3", "b8c6"]:
        uno.jugar(m)
    for m in ["b1c3", "b8c6", "g1f3", "g8f6"]:
        dos.jugar(m)
    assert uno.clave_posicion() == dos.clave_posicion()

