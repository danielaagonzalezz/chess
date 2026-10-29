"""
Interfaz web para jugar al ajedrez contra un bot (Streamlit).

Para verla en tu ordenador, desde la carpeta del proyecto:

    python -m pip install -e ".[web]"
    python -m streamlit run web/app.py

Como se juega: pulsa una pieza tuya y despues la casilla a la que quieres
moverla. Las casillas a las que puede ir se marcan en color. Despues de tu
jugada, el bot responde solo.
"""

import sys
from pathlib import Path

# Asi la web funciona aunque el paquete no este instalado (por ejemplo en
# Streamlit Cloud): anadimos la carpeta src al camino de busqueda.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import streamlit as st  # noqa: E402

from chess.bots import BOTS  # noqa: E402
from chess.game import Game  # noqa: E402
from chess.pieces import (  # noqa: E402
    BISHOP, BLACK, KNIGHT, QUEEN, ROOK, WHITE, Square, opposite_color,
)

ARCHIVOS = "abcdefgh"

# Piezas a las que puede promocionar un peon, con su nombre en pantalla.
NOMBRES_PROMOCION = {
    "Dama": QUEEN,
    "Torre": ROOK,
    "Alfil": BISHOP,
    "Caballo": KNIGHT,
}

NOMBRES_COLOR = {WHITE: "blancas", BLACK: "negras"}


# =========================================================
# Estado de la sesion
# =========================================================

def nueva_partida():
    """Empieza una partida nueva con las opciones elegidas en la barra lateral."""
    st.session_state.game = Game()
    st.session_state.seleccion = None
    st.session_state.mensaje = ""
    st.session_state.bot = BOTS[st.session_state.get("bot_elegido", list(BOTS)[0])]()


def empezar_partida():
    """Se ejecuta al pulsar "Empezar partida" (antes de redibujar la pagina)."""
    st.session_state.humano = WHITE if st.session_state.color_elegido == "blancas" else BLACK
    nueva_partida()


def iniciar_estado():
    if "game" not in st.session_state:
        st.session_state.humano = WHITE
        nueva_partida()


# =========================================================
# Lo que ocurre al pulsar una casilla
# =========================================================

def pulsar_casilla(texto_casilla):
    """Se ejecuta al pulsar un boton del tablero."""
    game = st.session_state.game
    humano = st.session_state.humano

    if game.esta_terminada() or game.turno != humano:
        return

    casilla = Square(ARCHIVOS.index(texto_casilla[0]), int(texto_casilla[1]) - 1)
    pieza = game.board.get_piece(casilla)
    seleccion = st.session_state.seleccion
    st.session_state.mensaje = ""

    # Primer clic: elegir una pieza propia.
    if seleccion is None:
        if pieza is not None and pieza.color == humano:
            st.session_state.seleccion = casilla
        else:
            st.session_state.mensaje = "Elige primero una pieza tuya."
        return

    # Pulsar la misma casilla otra vez: quitar la seleccion.
    if casilla == seleccion:
        st.session_state.seleccion = None
        return

    # Pulsar otra pieza propia: cambiar la seleccion.
    if pieza is not None and pieza.color == humano:
        st.session_state.seleccion = casilla
        return

    # Segundo clic: intentar mover.
    candidatas = [
        j for j in game.jugadas_legales()
        if j.origen == seleccion and j.destino == casilla
    ]
    if not candidatas:
        st.session_state.mensaje = "Esa jugada no es legal."
        return

    jugada = candidatas[0]
    if len(candidatas) > 1:
        # Es una promocion: hay cuatro jugadas, elegimos la que pide el desplegable.
        pieza_elegida = NOMBRES_PROMOCION[st.session_state.promocion]
        jugada = [j for j in candidatas if j.promocion == pieza_elegida][0]

    game.jugar(jugada)
    st.session_state.seleccion = None


def mover_bot():
    """Si le toca al bot y la partida sigue, el bot juega."""
    game = st.session_state.game
    if game.esta_terminada() or game.turno == st.session_state.humano:
        return
    with st.spinner("El bot está pensando…"):
        jugada = st.session_state.bot.choose_move(game.copy())
    game.jugar(jugada)


# =========================================================
# Dibujo del tablero
# =========================================================

def simbolo(pieza):
    # El ︎ fuerza a mostrar la pieza como texto y no como emoji.
    return pieza.unicode() + "︎"


def dibujar_tablero():
    game = st.session_state.game
    humano = st.session_state.humano
    seleccion = st.session_state.seleccion

    # Casillas a las que puede ir la pieza seleccionada.
    destinos = set()
    if seleccion is not None:
        for j in game.jugadas_legales():
            if j.origen == seleccion:
                destinos.add(j.destino)

    # Las blancas se dibujan abajo si juegas con blancas, y al reves.
    if humano == WHITE:
        filas = range(7, -1, -1)
        columnas = range(8)
    else:
        filas = range(8)
        columnas = range(7, -1, -1)

    for rank in filas:
        celdas = st.columns([0.4] + [1] * 8, gap="small")
        celdas[0].markdown("**" + str(rank + 1) + "**")
        for posicion, file in enumerate(columnas):
            casilla = Square(file, rank)
            pieza = game.board.get_piece(casilla)

            if pieza is not None:
                etiqueta = simbolo(pieza)
            elif casilla in destinos:
                etiqueta = "●"
            else:
                etiqueta = " "

            resaltada = casilla == seleccion or casilla in destinos
            celdas[posicion + 1].button(
                etiqueta,
                key="sq_" + str(casilla),
                type="primary" if resaltada else "secondary",
                use_container_width=True,
                on_click=pulsar_casilla,
                args=(str(casilla),),
            )

    letras = st.columns([0.4] + [1] * 8, gap="small")
    for posicion, file in enumerate(columnas):
        letras[posicion + 1].markdown(
            "<div style='text-align:center'><b>" + ARCHIVOS[file] + "</b></div>",
            unsafe_allow_html=True,
        )


# =========================================================
# Pagina
# =========================================================

def estado_de_la_partida():
    game = st.session_state.game
    humano = st.session_state.humano

    if game.esta_terminada():
        if game.ganador() is None:
            st.info("Tablas por " + game.motivo + ".")
        elif game.ganador() == humano:
            st.success("¡Has ganado por " + game.motivo + "!")
        else:
            st.error("Has perdido por " + game.motivo + ".")
        return

    if game.turno == humano:
        texto = "Tu turno (" + NOMBRES_COLOR[humano] + ")"
        if game.esta_en_jaque():
            texto += " — ¡estás en jaque!"
        st.write(texto)
    else:
        st.write("Turno del bot…")

    if st.session_state.mensaje:
        st.warning(st.session_state.mensaje)


def barra_lateral():
    st.sidebar.header("Partida nueva")
    st.sidebar.selectbox("Rival", list(BOTS), key="bot_elegido")
    st.sidebar.radio("Juegas con", ["blancas", "negras"], key="color_elegido")
    st.sidebar.button(
        "Empezar partida", use_container_width=True, on_click=empezar_partida,
    )

    st.sidebar.divider()
    st.sidebar.selectbox(
        "Si promocionas un peón, elegir", list(NOMBRES_PROMOCION), key="promocion",
    )

    game = st.session_state.game
    with st.sidebar.expander("Jugadas"):
        if game.historial:
            st.write(" ".join(str(j) for j in game.historial))
        else:
            st.write("Todavía no hay jugadas.")
    with st.sidebar.expander("Posición (FEN)"):
        st.code(game.fen())


def main():
    st.set_page_config(page_title="Ajedrez contra bots", page_icon="♞")
    st.title("♞ Ajedrez contra bots")

    iniciar_estado()
    mover_bot()
    barra_lateral()
    dibujar_tablero()
    estado_de_la_partida()


main()
