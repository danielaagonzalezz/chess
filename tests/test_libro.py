import json

from chess.bots import MLBot
from chess.bots.libro import RUTA_LIBRO, Libro
from chess.game import Game


def test_el_libro_tiene_la_posicion_inicial_con_jugadas_legales():
    libro = Libro(seed=1)
    jugadas = libro.jugadas(Game())
    assert len(libro) > 100
    assert {str(j) for j, _ in jugadas} >= {"e2e4", "d2d4"}


def test_todas_las_jugadas_del_libro_son_legales_en_su_posicion():
    # Recorremos partidas siguiendo siempre la jugada mas frecuente del libro.
    libro = Libro(seed=3)
    game = Game()
    for _ in range(30):
        opciones = libro.jugadas(game)
        if not opciones:
            break
        game.jugar(max(opciones, key=lambda o: o[1])[0])   # jugar() lanza error si fuera ilegal
    assert len(game.historial) >= 6


def test_elegir_varia_y_respeta_la_frecuencia():
    libro = Libro(seed=5)
    elegidas = [str(libro.elegir(Game())) for _ in range(300)]
    assert set(elegidas) <= {"e2e4", "d2d4", "g1f3", "c2c4"}
    assert elegidas.count("e2e4") > elegidas.count("d2d4")


def test_fuera_del_libro_no_devuelve_nada():
    game = Game.desde_fen("8/5k2/8/8/3K4/8/4P3/8 w - - 0 1")
    assert Libro(seed=1).elegir(game) is None


def test_el_fichero_del_libro_tiene_el_formato_esperado():
    with open(RUTA_LIBRO, encoding="utf-8") as f:
        datos = json.load(f)
    for clave, jugadas in list(datos.items())[:200]:
        assert len(clave.split()) == 3
        assert all(len(texto) in (4, 5) and veces > 0 for texto, veces in jugadas)


def test_el_bot_con_libro_juega_su_apertura_y_luego_piensa():
    bot = MLBot(profundidad=3, libro=True, seed=2)
    game = Game()
    jugada = bot.choose_move(game)
    assert bot.del_libro and jugada in game.jugadas_legales()
    # En una posicion fuera del libro, piensa.
    final = Game.desde_fen("8/5k2/8/8/3K4/8/4P3/8 w - - 0 1")
    bot.choose_move(final)
    assert not bot.del_libro
