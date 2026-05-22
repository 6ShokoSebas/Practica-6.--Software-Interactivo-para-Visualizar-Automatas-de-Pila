import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import xml.etree.ElementTree as ET
import json
from collections import deque
import re

# Operaciones de lenguaje
def obtener_prefijos(w):
    return list({w[:i] if w[:i] else "λ" for i in range(len(w) + 1)})

def obtener_sufijos(w):
    return list({w[i:] if w[i:] else "λ" for i in range(len(w) + 1)})

def obtener_subcadenas(w):
    return list({w[i:j] if w[i:j] else "λ" for i in range(len(w) + 1) for j in range(i, len(w) + 1)})

def obtener_positiva(alfabeto, max_longitud):
    resultado = set(alfabeto)
    actual = set(alfabeto)
    while True:
        siguiente = {s1 + s2 for s1 in actual for s2 in alfabeto if len(s1 + s2) <= max_longitud}
        if not siguiente:
            break
        resultado.update(siguiente)
        actual = siguiente
    return list(resultado)

def obtener_kleene(alfabeto, max_longitud):
    resultado = set(obtener_positiva(alfabeto, max_longitud))
    resultado.add("λ")
    return list(resultado)

# Clase Automata
class Automata:
    def __init__(self):
        self.estados   = set()
        self.alfabeto  = set()
        self.inicial   = None
        self.aceptacion = set()
        self.transiciones = {}
        self.tipo      = "AFD"
        self.posiciones = {}

    # Obtener transiciones
    def _trans_set(self, estado, simbolo):
        return self.transiciones.get(estado, {}).get(simbolo, set())

    # Calcular clausura lambda
    def lambda_clausura(self, estados):
        clausura = set(estados)
        pila = list(estados)
        while pila:
            s = pila.pop()
            for t in self._trans_set(s, "λ"):
                if t not in clausura:
                    clausura.add(t)
                    pila.append(t)
        return frozenset(clausura)

    # Cargar archivo JFLAP
    def cargar_jff(self, ruta):
        tree = ET.parse(ruta)
        root = tree.getroot()
        automaton = root.find('automaton')

        self.estados.clear(); self.aceptacion.clear()
        self.transiciones.clear(); self.alfabeto.clear()
        self.tipo = "AFD"

        for state in automaton.findall('state'):
            s_id = state.get('id')
            self.estados.add(s_id)
            self.transiciones[s_id] = {}

            x = float(state.find('x').text) if state.find('x') is not None else 100
            y = float(state.find('y').text) if state.find('y') is not None else 100
            self.posiciones[s_id] = (x, y)

            if state.find('initial') is not None:
                self.inicial = s_id
            if state.find('final') is not None:
                self.aceptacion.add(s_id)

        for trans in automaton.findall('transition'):
            origen  = trans.find('from').text
            destino = trans.find('to').text
            sym_node = trans.find('read')
            simbolo  = sym_node.text if (sym_node is not None and sym_node.text) else "λ"

            if simbolo != "λ":
                self.alfabeto.add(simbolo)
            self.transiciones.setdefault(origen, {}).setdefault(simbolo, set()).add(destino)

        self._detectar_tipo()

    # Detectar tipo de autómata
    def _detectar_tipo(self):
        tiene_lambda = any("λ" in t for t in self.transiciones.values())
        no_det = any(len(v) > 1 for t in self.transiciones.values() for v in t.values())
        if tiene_lambda:
            self.tipo = "AFNλ"
        elif no_det:
            self.tipo = "AFND"
        else:
            self.tipo = "AFD"

    # Simulación AFD
    def procesar_cadena_afd(self, cadena):
        if self.inicial is None:
            return False, []
        estado_actual = self.inicial
        traza = [estado_actual]
        for simbolo in cadena:
            destinos = self._trans_set(estado_actual, simbolo)
            if not destinos:
                return False, traza
            estado_actual = next(iter(destinos))
            traza.append(estado_actual)
        return estado_actual in self.aceptacion, traza

    # Wrapper general
    def procesar_cadena(self, cadena):
        aceptada, traza = self.procesar_cadena_afd(cadena)
        return aceptada, traza

    # Simulación AFND
    def procesar_cadena_afnd(self, cadena):
        estados_activos = frozenset({self.inicial})
        pasos = [("INICIO", estados_activos)]
        for simbolo in cadena:
            nuevos = frozenset(d for s in estados_activos for d in self._trans_set(s, simbolo))
            pasos.append((simbolo, nuevos))
            estados_activos = nuevos
            if not estados_activos:
                break
        aceptada = bool(estados_activos & self.aceptacion)
        return aceptada, pasos

    # Simulación AFN-Lambda
    def procesar_cadena_afnl(self, cadena):
        estados_activos = self.lambda_clausura({self.inicial})
        pasos = [("INICIO / λ-clausura", estados_activos)]
        for simbolo in cadena:
            after_sym = frozenset(d for s in estados_activos for d in self._trans_set(s, simbolo))
            after_lc = self.lambda_clausura(after_sym)
            pasos.append((simbolo, after_sym))
            pasos.append(("λ-clausura", after_lc))
            estados_activos = after_lc
            if not estados_activos:
                break
        aceptada = bool(estados_activos & self.aceptacion)
        return aceptada, pasos

    # Conversión AFND a AFD
    def convertir_afnd_a_afd(self):
        afd = Automata()
        afd.alfabeto = set(self.alfabeto)
        afd.tipo = "AFD"
        q0_set = frozenset({self.inicial})
        cola = deque([q0_set])
        visitados = {}
        contador = 0

        visitados[q0_set] = str(contador)
        afd.inicial = str(contador)
        afd.estados.add(str(contador))
        afd.transiciones[str(contador)] = {}
        if q0_set & self.aceptacion:
            afd.aceptacion.add(str(contador))
        contador += 1

        while cola:
            cur_set = cola.popleft()
            cur_id = visitados[cur_set]
            for sym in self.alfabeto:
                dest_set = frozenset(d for s in cur_set for d in self._trans_set(s, sym))
                if not dest_set: continue
                if dest_set not in visitados:
                    visitados[dest_set] = str(contador)
                    afd.estados.add(str(contador))
                    afd.transiciones[str(contador)] = {}
                    if dest_set & self.aceptacion: afd.aceptacion.add(str(contador))
                    cola.append(dest_set)
                    contador += 1
                dest_id = visitados[dest_set]
                afd.transiciones[cur_id][sym] = {dest_id}
        return afd, visitados

    # Conversión AFN-Lambda a AFND
    def convertir_afnl_a_afnd(self):
        afnd = Automata()
        afnd.alfabeto = set(self.alfabeto)
        afnd.tipo = "AFND"
        afnd.estados = set(self.estados)
        afnd.inicial = self.inicial
        afnd.transiciones = {s: {} for s in self.estados}

        for s in self.estados:
            lc = self.lambda_clausura({s})
            if lc & self.aceptacion: afnd.aceptacion.add(s)
            for sym in self.alfabeto:
                destinos = frozenset(d for t in lc for d in self._trans_set(t, sym))
                if destinos:
                    total = self.lambda_clausura(destinos)
                    afnd.transiciones[s][sym] = set(total)
        return afnd

    # Minimizar AFD
    def minimizar_afd(self):
        accesibles = set()
        cola = deque([self.inicial])
        while cola:
            s = cola.popleft()
            if s in accesibles:
                continue
            accesibles.add(s)
            for sym in self.alfabeto:
                for d in self._trans_set(s, sym):
                    if d not in accesibles:
                        cola.append(d)

        estados_util = accesibles
        inaccesibles = self.estados - accesibles

        estados_lista = sorted(estados_util)
        n = len(estados_lista)
        idx = {s: i for i, s in enumerate(estados_lista)}
        distinguible = [[False] * n for _ in range(n)]

        for i in range(n):
            for j in range(i + 1, n):
                si, sj = estados_lista[i], estados_lista[j]
                if (si in self.aceptacion) != (sj in self.aceptacion):
                    distinguible[i][j] = True

        changed = True
        while changed:
            changed = False
            for i in range(n):
                for j in range(i + 1, n):
                    if distinguible[i][j]: continue
                    si, sj = estados_lista[i], estados_lista[j]
                    for sym in self.alfabeto:
                        di_set = self._trans_set(si, sym)
                        dj_set = self._trans_set(sj, sym)
                        di = next(iter(di_set)) if di_set else None
                        dj = next(iter(dj_set)) if dj_set else None
                        if di is None and dj is None: continue
                        if (di is None) != (dj is None):
                            distinguible[i][j] = True
                            changed = True
                            break
                        ii, jj = (idx[di], idx[dj]) if idx[di] < idx[dj] else (idx[dj], idx[di])
                        if distinguible[ii][jj]:
                            distinguible[i][j] = True
                            changed = True
                            break

        padre = {s: s for s in estados_lista}
        def find(x):
            while padre[x] != x:
                padre[x] = padre[padre[x]]
                x = padre[x]
            return x
        def union(x, y):
            padre[find(x)] = find(y)

        for i in range(n):
            for j in range(i + 1, n):
                if not distinguible[i][j]:
                    union(estados_lista[i], estados_lista[j])

        grupos = {}
        for s in estados_lista:
            r = find(s)
            grupos.setdefault(r, set()).add(s)

        afd_min = Automata()
        afd_min.alfabeto = set(self.alfabeto)
        afd_min.tipo = "AFD"
        repr_map = {}
        for rep, grupo in grupos.items():
            for s in grupo: repr_map[s] = rep
            afd_min.estados.add(rep)
            if self.inicial in grupo: afd_min.inicial = rep
            if grupo & self.aceptacion: afd_min.aceptacion.add(rep)
            afd_min.transiciones[rep] = {}

        for rep, grupo in grupos.items():
            s = next(iter(grupo))
            for sym in self.alfabeto:
                destinos = self._trans_set(s, sym)
                if destinos:
                    dest = next(iter(destinos))
                    afd_min.transiciones[rep][sym] = {repr_map[dest]}

        info = {
            "inaccesibles": inaccesibles, "grupos": grupos, "repr_map": repr_map,
            "estados_antes": len(estados_util) + len(inaccesibles),
            "estados_despues": len(afd_min.estados), "estados_util": len(estados_util),
        }
        return afd_min, info
    



    
class AutomataPila:
    """
    Autómata de Pila No Determinista (APND).

    Transiciones almacenadas como:
        self.transiciones[(estado, sim_entrada, sim_pila)] = {(estado_dest, cadena_apilar), ...}

    sim_entrada y sim_pila pueden ser 'λ' (epsilon).
    cadena_apilar es una cadena; el primer carácter queda en la cima.
    Ejemplo: (q0,'a','Z') -> {(q1,'AZ'), (q1,'Z')}

    Condición de aceptación: 'estado_final', 'pila_vacia', o 'ambas'.
    """
    SIMBOLO_FONDO = 'Z'   # símbolo de fondo de pila por defecto

    def __init__(self):
        self.estados      = set()
        self.alfabeto     = set()      # símbolos de entrada
        self.alfa_pila    = set()      # símbolos de pila
        self.inicial      = None
        self.aceptacion   = set()      # estados de aceptación
        self.transiciones = {}         # (est, sim_ent, sim_pila) -> set of (est_dest, cadena)
        self.cond_acep    = 'ambas'    # 'estado_final' | 'pila_vacia' | 'ambas'
        self.posiciones   = {}
        self.simbolo_fondo = self.SIMBOLO_FONDO

    # ── Agregar transición ───────────────────────────────────────────────────
    def agregar_trans(self, orig, sim_ent, sim_pila, dest, apilar):
        key = (orig, sim_ent, sim_pila)
        self.transiciones.setdefault(key, set()).add((dest, apilar))

    # ── Descripción de configuración ─────────────────────────────────────────
    @staticmethod
    def _acepta_config(estado, pila, entrada_restante, estados_ac, cond):
        cadena_consumida = not entrada_restante
        pila_vacia       = not pila
        es_final         = estado in estados_ac
        if cond == 'estado_final':
            return cadena_consumida and es_final
        if cond == 'pila_vacia':
            return cadena_consumida and pila_vacia
        # 'ambas'
        return cadena_consumida and (es_final or pila_vacia)

    # ── Simulación con backtracking (BFS/DFS limitado) ───────────────────────
    def simular(self, cadena, max_configs=50000):
        """
        Devuelve (aceptada, pasos) donde pasos es una lista de dicts:
            {'estado': ..., 'pila': [...], 'entrada': '...', 'regla': '...'}
        Si acepta, pasos es el camino aceptante. Si no, pasos es None.
        """
        if self.inicial is None:
            return False, None

        pila_init = [self.simbolo_fondo]
        # config: (estado, pila_tuple, entrada_restante, historial)
        cola = deque()
        cola.append((self.inicial, tuple(pila_init), cadena, []))
        visitados = set()
        explorados = 0

        while cola and explorados < max_configs:
            estado, pila_t, entrada, hist = cola.popleft()
            explorados += 1

            sig_ent = entrada[0] if entrada else 'λ'
            cima    = pila_t[-1] if pila_t else None

            paso_actual = {
                'estado': estado,
                'pila': list(pila_t),
                'entrada': entrada,
                'regla': ''
            }

            # Verificar aceptación
            if self._acepta_config(estado, pila_t, entrada,
                                    self.aceptacion, self.cond_acep):
                return True, hist + [paso_actual]

            # Expandir transiciones aplicables
            candidatos = []
            for sim_e in ([sig_ent, 'λ'] if entrada else ['λ']):
                for sim_p in ([cima, 'λ'] if cima else ['λ']):
                    key = (estado, sim_e, sim_p)
                    for (dest, apilar) in self.transiciones.get(key, set()):
                        # Calcular nueva pila
                        nueva_pila = list(pila_t)
                        if sim_p != 'λ' and nueva_pila:
                            nueva_pila.pop()    # quitar cima leída
                        if apilar != 'λ':
                            for c in reversed(apilar):  # apilar de derecha a izq
                                nueva_pila.append(c)
                        nueva_entrada = entrada[1:] if sim_e != 'λ' else entrada
                        cfg_id = (dest, tuple(nueva_pila), nueva_entrada)
                        if cfg_id not in visitados:
                            visitados.add(cfg_id)
                            regla = f"δ(q{estado}, {sim_e}, {sim_p}) → (q{dest}, {apilar if apilar!='λ' else 'λ'})"
                            candidatos.append((dest, tuple(nueva_pila), nueva_entrada,
                                               hist + [{**paso_actual, 'regla': regla}]))

            cola.extend(candidatos)

        return False, None

    # ── Tabla de transiciones legible ────────────────────────────────────────
    def tabla_texto(self):
        lineas = ["Transiciones del Autómata de Pila:"]
        lineas.append(f"  Estado inicial : q{self.inicial}")
        lineas.append(f"  Estados finales: {{{', '.join('q'+s for s in sorted(self.aceptacion))}}}")
        lineas.append(f"  Condición acep.: {self.cond_acep}")
        lineas.append(f"  Fondo de pila  : {self.simbolo_fondo}")
        lineas.append("")
        lineas.append(f"  {'Origen':<8} {'Ent':<5} {'Pila':<6} {'Destino':<8} {'Apilar'}")
        lineas.append("  " + "-"*40)
        for (orig, sim_e, sim_p), dests in sorted(self.transiciones.items()):
            for (dest, apilar) in sorted(dests):
                lineas.append(f"  q{orig:<7} {sim_e:<5} {sim_p:<6} q{dest:<7} {apilar}")
        return "\n".join(lineas)

# Interfaz Gráfica
class SimuladorApp:
    COLOR_AFD  = "#d4edda"
    COLOR_AFND = "#d1ecf1"
    COLOR_AFNL = "#fff3cd"

    def __init__(self, root):
        self.root = root
        self.root.title("Simulador ESCOM – Teoría de la Computación (Unificado)")
        self.root.geometry("980x800")
        self.root.resizable(True, True)
        self.automata = Automata()
        self.ap = AutomataPila()          # autómata de pila activo
        self.ap_pasos = []                # pasos de última simulación AP
        self.afd_minimizado = None
        self._build_ui()

        self.estado_seleccionado = None
        self.estado_drag = None
        self.offset_drag = (0, 0)
        self.modo_transicion = False
        self.origen_transicion = None
        self.items_canvas = {}  # map estado -> (circulo, texto)

    # Construir UI
    def _build_ui(self):
        tk.Label(self.root, text="Simulador de Autómatas Finitos y Expresiones Regulares", font=("Arial", 14, "bold"), pady=8).pack()
        self.lbl_tipo = tk.Label(self.root, text="Tipo: —", font=("Arial", 11, "bold"), bg="#eeeeee", relief="groove", padx=10, pady=4)
        self.lbl_tipo.pack(fill=tk.X, padx=20, pady=(0, 4))

        frm_arch = tk.Frame(self.root)
        frm_arch.pack(pady=3)
        tk.Button(frm_arch, text="✏️ Crear Manualmente", command=self.editor_manual, bg="#fffacd", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=4)
        tk.Button(frm_arch, text="📂 Cargar Archivo", command=self.cargar_archivo, bg="lightblue", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=4)
        tk.Button(frm_arch, text="💾 Exportar", command=self.exportar_automata, bg="plum", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=4)

        self.lbl_info = tk.Label(self.root, text="Ningún autómata cargado.", fg="red", justify=tk.CENTER, font=("Arial", 9))
        self.lbl_info.pack(pady=3)

        nb = ttk.Notebook(self.root)
        nb.pack(expand=True, fill=tk.BOTH, padx=10, pady=5)

        tab_sim = tk.Frame(nb); nb.add(tab_sim, text=" Simulación ")
        self._build_tab_simulacion(tab_sim)
        
        tab_lc = tk.Frame(nb); nb.add(tab_lc, text=" λ-Clausura ")
        self._build_tab_lambda(tab_lc)

        tab_conv = tk.Frame(nb); nb.add(tab_conv, text=" Conversiones ")
        self._build_tab_conversiones(tab_conv)

        tab_min = tk.Frame(nb); nb.add(tab_min, text=" Minimización ")
        self._build_tab_minimizacion(tab_min)

        tab_er = tk.Frame(nb); nb.add(tab_er, text=" AFD a ER ")
        self._build_tab_afd_a_er(tab_er)

        tab_prac = tk.Frame(nb); nb.add(tab_prac, text=" Casos Prácticos ")
        self._build_tab_casos_practicos(tab_prac)

        tab_vis = tk.Frame(nb); nb.add(tab_vis, text=" Tablas y Grafos ")
        self._build_tab_visualizacion(tab_vis)
        
        tab_ext = tk.Frame(nb); nb.add(tab_ext, text=" Extras Lenguaje ")
        self._build_tab_extras(tab_ext)

        tab_canvas = tk.Frame(nb)
        nb.add(tab_canvas, text=" Visualizador JFLAP ")
        self._build_tab_canvas(tab_canvas)

        tab_ap = tk.Frame(nb)
        nb.add(tab_ap, text=" Autómata de Pila ")
        self._build_tab_ap(tab_ap)


    # Interfaz Simulación
    def _build_tab_simulacion(self, parent):
        tk.Label(parent, text="Cadena a evaluar:", font=("Arial", 10, "bold")).pack(pady=(12, 2))
        self.txt_cadena = tk.Entry(parent, width=50, font=("Arial", 12))
        self.txt_cadena.pack()
        frm = tk.Frame(parent); frm.pack(pady=8)
        tk.Button(frm, text="Validar Rápido", command=self.validar_cadena, bg="#e2e3e5").pack(side=tk.LEFT, padx=5)
        tk.Button(frm, text="Paso a Paso", command=self.paso_a_paso, bg="lightgreen").pack(side=tk.LEFT, padx=5)
        tk.Button(frm, text="Pruebas Múltiples", command=self.pruebas_multiples, bg="#ffc107").pack(side=tk.LEFT, padx=5)
        self.txt_resultado = tk.Text(parent, height=15, width=80, font=("Consolas", 10), state=tk.DISABLED, bg="#f8f9fa")
        self.txt_resultado.pack(expand=True, fill=tk.BOTH, padx=10, pady=4)

    # Interfaz Clausura Lambda
    def _build_tab_lambda(self, parent):
        tk.Label(parent, text="Cálculo de λ-clausura", font=("Arial", 11, "bold")).pack(pady=12)
        frm = tk.Frame(parent); frm.pack()
        tk.Label(frm, text="Estado(s) separados por coma:").pack(side=tk.LEFT)
        self.entry_lc = tk.Entry(frm, width=20); self.entry_lc.pack(side=tk.LEFT, padx=5)
        tk.Button(frm, text="Calcular", command=self.calcular_lambda_clausura, bg=self.COLOR_AFNL).pack(side=tk.LEFT)
        self.txt_lc = tk.Text(parent, height=20, width=80, font=("Consolas", 10), state=tk.DISABLED, bg="#f8f9fa")
        self.txt_lc.pack(expand=True, fill=tk.BOTH, padx=10, pady=8)

    # Interfaz Conversiones
    def _build_tab_conversiones(self, parent):
        tk.Label(parent, text="Conversiones entre tipos de autómatas", font=("Arial", 11, "bold")).pack(pady=12)
        frm = tk.Frame(parent); frm.pack(pady=6)
        tk.Button(frm, text="AFNλ → AFND  (Eliminar λ)", command=self.convertir_afnl_afnd, bg=self.COLOR_AFNL, width=30, font=("Arial", 10, "bold")).pack(pady=4)
        tk.Button(frm, text="AFND → AFD  (Subconjuntos)", command=self.convertir_afnd_afd, bg=self.COLOR_AFND, width=30, font=("Arial", 10, "bold")).pack(pady=4)
        self.txt_conv = tk.Text(parent, height=18, width=80, font=("Consolas", 9), state=tk.DISABLED, bg="#f8f9fa")
        self.txt_conv.pack(expand=True, fill=tk.BOTH, padx=10, pady=6)

    # Interfaz Minimización
    def _build_tab_minimizacion(self, parent):
        tk.Label(parent, text="Minimización y Comparación de AFD", font=("Arial", 11, "bold")).pack(pady=5)
        frm_btns = tk.Frame(parent); frm_btns.pack()
        tk.Button(frm_btns, text="▶ Minimizar AFD actual", command=self.ejecutar_minimizacion, bg="#d4edda", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Button(frm_btns, text="👁 Ver Comparación Lado a Lado", command=self.mostrar_grafos_lado_a_lado, bg="#ffb6c1", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        frm_equiv = tk.Frame(parent); frm_equiv.pack(pady=10)
        tk.Label(frm_equiv, text="Probar 5 cadenas (separadas por coma):").pack(side=tk.LEFT)
        self.entry_equiv = tk.Entry(frm_equiv, width=40); self.entry_equiv.pack(side=tk.LEFT, padx=5)
        tk.Button(frm_equiv, text="Prueba de Equivalencia", command=self.probar_equivalencia, bg="#ffe4b5").pack(side=tk.LEFT)
        self.txt_min = tk.Text(parent, height=15, width=80, font=("Consolas", 9), state=tk.DISABLED, bg="#f8f9fa")
        self.txt_min.pack(expand=True, fill=tk.BOTH, padx=10, pady=8)

    # Interfaz Conversión AFD a ER
    def _build_tab_afd_a_er(self, parent):
        tk.Label(parent, text="Conversión AFD a Expresión Regular", font=("Arial", 11, "bold")).pack(pady=10)
        tk.Button(parent, text="⚙️ Ejecutar Algoritmo GNFA", command=self.convertir_afd_a_er, bg="#e0b0ff", font=("Arial", 10, "bold")).pack()
        self.txt_er = tk.Text(parent, height=20, width=80, font=("Consolas", 10), state=tk.DISABLED, bg="#f8f9fa")
        self.txt_er.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

    # Interfaz Casos Prácticos
    def _build_tab_casos_practicos(self, parent):
        tk.Label(parent, text="Validadores con Expresiones Regulares", font=("Arial", 11, "bold")).pack(pady=10)
        frm_ctrl = tk.Frame(parent); frm_ctrl.pack()
        tk.Label(frm_ctrl, text="Selecciona un caso:").pack(side=tk.LEFT, padx=5)
        self.combo_casos = ttk.Combobox(frm_ctrl, values=["Correo Electrónico", "Teléfono MX", "Fecha"], width=30)
        self.combo_casos.current(0)
        self.combo_casos.pack(side=tk.LEFT, padx=5)
        self.combo_casos.bind("<<ComboboxSelected>>", self._actualizar_regex_info)
        self.lbl_er_info = tk.Label(parent, text="", font=("Consolas", 10), fg="blue", pady=10)
        self.lbl_er_info.pack()
        frm_in = tk.Frame(parent); frm_in.pack(pady=5)
        tk.Label(frm_in, text="Texto a validar:").pack(side=tk.LEFT)
        self.entry_prac = tk.Entry(frm_in, width=40, font=("Arial", 11)); self.entry_prac.pack(side=tk.LEFT, padx=5)
        tk.Button(frm_in, text="Validar", command=self.validar_caso_practico, bg="#add8e6").pack(side=tk.LEFT)
        tk.Button(frm_in, text="Visualizar AFD Equivalente", command=self.mostrar_afd_practico, bg="#ffb6c1").pack(side=tk.LEFT, padx=10)
        self.lbl_feedback = tk.Label(parent, text="", font=("Arial", 11, "bold"))
        self.lbl_feedback.pack(pady=15)
        self._actualizar_regex_info(None)

    # Interfaz Visualización
    def _build_tab_visualizacion(self, parent):
        tk.Label(parent, text="Visualización del Autómata Actual", font=("Arial", 11, "bold")).pack(pady=12)
        frm = tk.Frame(parent); frm.pack(pady=4)
        tk.Button(frm, text="Ver Tabla de Transiciones", command=self.mostrar_tabla, bg="#f0e68c").pack(side=tk.LEFT, padx=6)
        tk.Button(frm, text="Ver Grafo de NetworkX", command=self.mostrar_grafo_principal, bg="#ffb6c1").pack(side=tk.LEFT, padx=6)

    # Interfaz Extras Lenguaje
    def _build_tab_extras(self, parent):
        tk.Label(parent, text="Operaciones de Lenguaje Formal", font=("Arial", 11, "bold")).pack(pady=12)
        frm = tk.Frame(parent); frm.pack()
        tk.Button(frm, text="Prefijos / Sufijos / Subcadenas", command=self.mostrar_partes_cadena).pack(side=tk.LEFT, padx=5)
        tk.Button(frm, text="Cerradura Kleene (*) y Positiva (+)", command=self.mostrar_kleene).pack(side=tk.LEFT, padx=5)

    def _build_tab_canvas(self, parent):
        self.canvas = tk.Canvas(parent, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        frm = tk.Frame(parent)
        frm.pack()

        tk.Button(frm, text="Agregar Estados", command=lambda: self.set_modo("estado")).pack(side=tk.LEFT)
        tk.Button(frm, text="Agregar Transiciones", command=lambda: self.set_modo("transicion")).pack(side=tk.LEFT)
        tk.Button(frm, text="Borrar", command=lambda: self.set_modo("borrar")).pack(side=tk.LEFT)
        tk.Button(frm, text="Simular", command=self.simular_visual).pack(side=tk.LEFT)
        tk.Button(frm, text="Limpiar", command=lambda: self.canvas.delete("all")).pack(side=tk.LEFT)

        self.canvas.bind("<Button-1>", self.click_canvas)
        self.canvas.bind("<B1-Motion>", self.drag_canvas)
        self.canvas.bind("<ButtonRelease-1>", self.drop_canvas)
        self.canvas.bind("<Button-3>", self.click_derecho)
        self.canvas.bind("<Double-1>", self.editar_estado)

    def set_modo(self, modo):
        self.modo_transicion = modo

    def click_canvas(self, event):
        if self.modo_transicion == "estado":
            s_id = str(len(self.automata.estados))
            self.automata.estados.add(s_id)
            self.automata.transiciones[s_id] = {}
            self.automata.posiciones[s_id] = (event.x, event.y)

            if self.automata.inicial is None:
                self.automata.inicial = s_id

            self.dibujar_automata_canvas()

    def encontrar_estado(self, x, y):
        pos = getattr(self, 'pos_canvas', self.automata.posiciones)
        for s, (sx, sy) in pos.items():
            if (x - sx)**2 + (y - sy)**2 <= 30**2:
                return s
        return None
    
    def encontrar_transicion(self, x, y):
        a = self.automata
        pos = getattr(self, 'pos_canvas', a.posiciones)

        for orig, trans in a.transiciones.items():
            x1, y1 = pos.get(orig, (0, 0))

            for sym, dests in trans.items():
                for dest in dests:
                    x2, y2 = pos.get(dest, (0, 0))

                    mx = (x1 + x2) / 2
                    my = (y1 + y2) / 2

                    if (x - mx)**2 + (y - my)**2 < 20**2:
                        return (orig, sym, dest)

        return None
    
    def borrar_estado(self, s):
        a = self.automata

        # eliminar estado
        a.estados.discard(s)
        a.posiciones.pop(s, None)
        a.aceptacion.discard(s)

        # eliminar transiciones salientes
        a.transiciones.pop(s, None)

        # eliminar transiciones entrantes
        for orig in list(a.transiciones.keys()):
            for sym in list(a.transiciones[orig].keys()):
                a.transiciones[orig][sym].discard(s)
                if not a.transiciones[orig][sym]:
                    del a.transiciones[orig][sym]

        # si era inicial
        if a.inicial == s:
            a.inicial = next(iter(a.estados), None)

    def borrar_transicion(self, orig, sym, dest):
        a = self.automata

        if orig in a.transiciones and sym in a.transiciones[orig]:
            a.transiciones[orig][sym].discard(dest)

            if not a.transiciones[orig][sym]:
                del a.transiciones[orig][sym]
    
    def click_canvas(self, event):
        s = self.encontrar_estado(event.x, event.y)

        # MODO BORRAR
        if self.modo_transicion == "borrar":
            if s:
                if messagebox.askyesno("Borrar estado", f"¿Eliminar estado q{s}?"):
                    self.borrar_estado(s)
                    self.dibujar_automata_canvas()
                return

            t = self.encontrar_transicion(event.x, event.y)
            if t:
                orig, sym, dest = t
                if messagebox.askyesno("Borrar transición", f"{orig} --{sym}--> {dest}"):
                    self.borrar_transicion(orig, sym, dest)
                    self.dibujar_automata_canvas()
                return
        
        if s:
            self.estado_drag = s
            sx, sy = self.automata.posiciones[s]
            self.offset_drag = (event.x - sx, event.y - sy)
        elif self.modo_transicion == "estado":
            s_id = str(len(self.automata.estados))
            self.automata.estados.add(s_id)
            self.automata.transiciones[s_id] = {}
            self.automata.posiciones[s_id] = (event.x, event.y)
            if self.automata.inicial is None:
                self.automata.inicial = s_id
            self.dibujar_automata_canvas()

    def drag_canvas(self, event):
        if self.estado_drag:
            dx, dy = self.offset_drag
            new_x = event.x - dx
            new_y = event.y - dy

            self.automata.posiciones[self.estado_drag] = (new_x, new_y)
            if not hasattr(self, 'pos_canvas'):
                self.pos_canvas = {}
            self.pos_canvas[self.estado_drag] = (new_x, new_y)
            self.dibujar_automata_canvas()
    
    def drop_canvas(self, event):
        self.estado_drag = None

    def click_derecho(self, event):
        s = self.encontrar_estado(event.x, event.y)
        if not s:
            return

        if not self.origen_transicion:
            self.origen_transicion = s
        else:
            destino = s
            simbolo = simpledialog.askstring("Símbolo", "Etiqueta de transición:") or "λ"

            self.automata.transiciones.setdefault(self.origen_transicion, {}).setdefault(simbolo, set()).add(destino)

            self.origen_transicion = None
            self.dibujar_automata_canvas()

    def editar_estado(self, event):
        s = self.encontrar_estado(event.x, event.y)
        if not s:
            return

        if messagebox.askyesno("Final", "¿Es estado de aceptación?"):
            self.automata.aceptacion.add(s)
        else:
            self.automata.aceptacion.discard(s)

        self.dibujar_automata_canvas()

    def simular_visual(self):
        a = self.automata
        cadena = self.txt_cadena.get()

        if a.tipo == "AFD":
            self._simular_afd_visual(cadena)
        elif a.tipo == "AFND":
            self._simular_afnd_visual(cadena)
        else:
            self._simular_afnl_visual(cadena)
        
    def resaltar_estados(self, estados, color="red"):
        pos = getattr(self, 'pos_canvas', self.automata.posiciones)
        for s in estados:
            if s not in pos:
                continue
            x, y = pos[s]
            self.canvas.create_oval(
                x-35, y-35, x+35, y+35,
                outline=color, width=3
            )

    def _simular_afd_visual(self, cadena):
        aceptada, traza = self.automata.procesar_cadena_afd(cadena)

        def animar(i):
            if i >= len(traza):
                return
            s = traza[i]
            es_final = s in self.automata.aceptacion and i == len(traza) - 1
            color = "green" if es_final and aceptada else "red"
            self.dibujar_automata_canvas(estados_resaltados={s}, color_resalte=color)
            self.root.after(800, lambda: animar(i+1))

        animar(0)
        
    def _simular_afnd_visual(self, cadena):
        a = self.automata

        estados_activos = {a.inicial}
        pasos = [("Inicio", estados_activos)]

        for simbolo in cadena:
            nuevos = set()
            for s in estados_activos:
                nuevos |= a.transiciones.get(s, {}).get(simbolo, set())
            pasos.append((simbolo, nuevos))
            estados_activos = nuevos

        def animar(i):
            if i >= len(pasos):
                return

            simbolo, estados = pasos[i]
            aceptados = estados & a.aceptacion
            no_aceptados = estados - aceptados

            self.dibujar_automata_canvas()
            self.resaltar_estados(no_aceptados, "red")
            self.resaltar_estados(aceptados, "green")

            self.canvas.create_text(
                100, 20,
                text=f"Paso {i}: '{simbolo}' → {{{', '.join(sorted(estados))}}}",
                fill="black", font=("Arial", 11, "bold")
            )

            self.root.after(900, lambda: animar(i+1))

        animar(0)

    def _simular_afnl_visual(self, cadena):
        a = self.automata

        estados_activos = set(a.lambda_clausura({a.inicial}))
        pasos = [("λ*", estados_activos)]

        for simbolo in cadena:
            after_sym = set()
            for s in estados_activos:
                after_sym |= a.transiciones.get(s, {}).get(simbolo, set())

            after_lc = set(a.lambda_clausura(after_sym))

            pasos.append((simbolo, after_sym))
            pasos.append(("λ*", after_lc))

            estados_activos = after_lc

        def animar(i):
            if i >= len(pasos):
                return

            self.dibujar_automata_canvas()

            simbolo, estados = pasos[i]

            color = "purple" if simbolo == "λ*" else "red"
            self.resaltar_estados(estados, color)

            aceptados = estados & a.aceptacion
            self.resaltar_estados(aceptados, "green")

            self.canvas.create_text(
                120, 30,
                text=f"{simbolo} → {estados}",
                font=("Arial", 12, "bold")
            )

            self.root.after(900, lambda: animar(i+1))

        animar(0)

    # Archivos: Crear Manualmente
    def editor_manual(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Crear Autómata Manual")
        dlg.geometry("500x540")
        dlg.grab_set()

        tk.Label(dlg, text="Crear Autómata Manual", font=("Arial", 12, "bold")).pack(pady=10)
        frm_tipo = tk.Frame(dlg); frm_tipo.pack(pady=4)
        tk.Label(frm_tipo, text="Tipo de autómata:").pack(side=tk.LEFT)
        tipo_var = tk.StringVar(value="AFD")
        for t in ("AFD", "AFND", "AFNλ"):
            tk.Radiobutton(frm_tipo, text=t, variable=tipo_var, value=t).pack(side=tk.LEFT, padx=3)

        def campo(parent, etiqueta):
            tk.Label(parent, text=etiqueta, font=("Arial", 9)).pack(anchor=tk.W, padx=20)
            e = tk.Entry(parent, width=60, font=("Arial", 10)); e.pack(padx=20, pady=2)
            return e

        e_alf  = campo(dlg, "Alfabeto (separado por comas, ej: 0,1):")
        e_est  = campo(dlg, "Estados (separado por comas, ej: q0,q1,q2):")
        e_ini  = campo(dlg, "Estado inicial:")
        e_acep = campo(dlg, "Estados de aceptación (separado por comas):")

        tk.Label(dlg, text="Transiciones (una por línea: origen,símbolo,destino):", font=("Arial", 9)).pack(anchor=tk.W, padx=20, pady=(8, 0))
        tk.Label(dlg, text="  Para λ escribe: origen,λ,destino  |  AFND: origen,a,dest1,dest2,...", font=("Arial", 8), fg="gray").pack(anchor=tk.W, padx=20)
        txt_trans = tk.Text(dlg, height=8, width=60, font=("Consolas", 9))
        txt_trans.pack(padx=20, pady=4)

        def guardar():
            a = self.automata
            a.tipo = tipo_var.get()
            a.alfabeto   = {x.strip() for x in e_alf.get().split(",") if x.strip()}
            a.estados    = {x.strip() for x in e_est.get().split(",") if x.strip()}
            a.inicial    = e_ini.get().strip()
            a.aceptacion = {x.strip() for x in e_acep.get().split(",") if x.strip() and x.strip() in a.estados}
            a.transiciones = {s: {} for s in a.estados}

            if a.inicial not in a.estados:
                messagebox.showerror("Error", "El estado inicial no está en el conjunto de estados.", parent=dlg)
                return

            for ln in txt_trans.get("1.0", tk.END).strip().splitlines():
                partes = [p.strip() for p in ln.split(",")]
                if len(partes) < 3: continue
                orig, sym = partes[0], partes[1]
                dests = set(partes[2:])
                if orig not in a.estados: continue
                if sym == "λ" or sym in a.alfabeto or a.tipo in ("AFND", "AFNλ"):
                    a.transiciones.setdefault(orig, {}).setdefault(sym, set()).update(dests)

            a._detectar_tipo()
            self.actualizar_info()
            dlg.destroy()

        tk.Button(dlg, text="Guardar Autómata", command=guardar, bg="#d4edda", font=("Arial", 10, "bold")).pack(pady=10)

    # Archivos: Cargar
    def cargar_archivo(self):
        fp = filedialog.askopenfilename(filetypes=[("Soportados", "*.jff *.json *.xml"), ("JFLAP", "*.jff"), ("JSON", "*.json")])
        if not fp: return
        try:
            if fp.endswith('.json'):
                with open(fp, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.automata.alfabeto   = set(data["alfabeto"])
                self.automata.estados    = set(data["estados"])
                self.automata.inicial    = data["inicial"]
                self.automata.aceptacion = set(data["aceptacion"])
                self.automata.transiciones = {}
                for est, trans in data["transiciones"].items():
                    self.automata.transiciones[est] = {}
                    for sym, dest in trans.items():
                        if isinstance(dest, list): self.automata.transiciones[est][sym] = set(dest)
                        elif isinstance(dest, str): self.automata.transiciones[est][sym] = {dest}
                        else: self.automata.transiciones[est][sym] = set(dest)
                self.automata._detectar_tipo()
            else:
                self.automata.cargar_jff(fp)
            self.actualizar_info()
            messagebox.showinfo("Éxito", f"Autómata ({self.automata.tipo}) cargado.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # Archivos: Exportar
    def exportar_automata(self):
        if not self.automata.estados: return messagebox.showwarning("Aviso", "No hay autómata.")
        fp = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json"), ("JFLAP/XML", "*.jff *.xml")])
        if not fp: return
        try:
            if fp.endswith('.json'):
                data = {
                    "tipo": self.automata.tipo,
                    "alfabeto": list(self.automata.alfabeto),
                    "estados": list(self.automata.estados),
                    "inicial": self.automata.inicial,
                    "aceptacion": list(self.automata.aceptacion),
                    "transiciones": {e: {s: list(d) for s, d in t.items()} for e, t in self.automata.transiciones.items()}
                }
                with open(fp, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4, ensure_ascii=False)
            else:
                root_el = ET.Element("structure")
                ET.SubElement(root_el, "type").text = "fa"
                auto_el = ET.SubElement(root_el, "automaton")
                for est in self.automata.estados:
                    s_el = ET.SubElement(auto_el, "state", id=str(est), name=f"q{est}")
                    x, y = self.automata.posiciones.get(est, (100, 100))
                    ET.SubElement(s_el, "x").text = str(x)
                    ET.SubElement(s_el, "y").text = str(y)
                    if str(est) == str(self.automata.inicial): ET.SubElement(s_el, "initial")
                    if str(est) in self.automata.aceptacion: ET.SubElement(s_el, "final")
                for orig, trans in self.automata.transiciones.items():
                    for sym, dests in trans.items():
                        for dest in dests:
                            t_el = ET.SubElement(auto_el, "transition")
                            ET.SubElement(t_el, "from").text = str(orig)
                            ET.SubElement(t_el, "to").text = str(dest)
                            ET.SubElement(t_el, "read").text = "" if sym == "λ" else sym
                tree = ET.ElementTree(root_el)
                tree.write(fp, encoding="utf-8", xml_declaration=True)
            messagebox.showinfo("Éxito", f"Exportado a:\n{fp}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # Lógica: Validar Cadena (Rápida)
    def validar_cadena(self):
        cadena = self.txt_cadena.get()
        if not self.automata.estados: return
        a = self.automata
        if a.tipo == "AFD":
            aceptada, traza = a.procesar_cadena_afd(cadena)
            txt = f"Tipo: AFD\nCadena: '{cadena}'\nResultado: {'✅ ACEPTADA' if aceptada else '❌ RECHAZADA'}\nTraza: " + " → ".join(f"q{s}" for s in traza)
        elif a.tipo == "AFND":
            aceptada, pasos = a.procesar_cadena_afnd(cadena)
            txt = f"Tipo: AFND\nCadena: '{cadena}'\nResultado: {'✅ ACEPTADA' if aceptada else '❌ RECHAZADA'}\n\n"
            for sym, conj in pasos: txt += f"  [{sym}]  →  {{{', '.join(sorted(conj))}}}\n"
        else: 
            aceptada, pasos = a.procesar_cadena_afnl(cadena)
            txt = f"Tipo: AFN-λ\nCadena: '{cadena}'\nResultado: {'✅ ACEPTADA' if aceptada else '❌ RECHAZADA'}\n\n"
            for sym, conj in pasos: txt += f"  [{sym}]  →  {{{', '.join(sorted(conj))}}}\n"
        self._write_text(self.txt_resultado, txt)

    # Lógica: Simulación Paso a Paso
    def paso_a_paso(self):
        cadena = self.txt_cadena.get()
        if not self.automata.estados: return
        a = self.automata
        lineas = [f"━━━ Simulación Paso a Paso ({a.tipo}) ━━━", f"Cadena: '{cadena}'\n"]
        if a.tipo == "AFD":
            aceptada, traza = a.procesar_cadena_afd(cadena)
            lineas.append(f"Estado inicial: q{a.inicial}")
            for i, sym in enumerate(cadena):
                if i + 1 < len(traza): lineas.append(f"Paso {i+1}: δ(q{traza[i]}, '{sym}') = q{traza[i+1]}")
                else:
                    lineas.append(f"Paso {i+1}: ✗ Sin transición con '{sym}'")
                    break
            lineas.append(f"\nResultado: {'✅ ACEPTADA' if aceptada else '❌ RECHAZADA'}")
        elif a.tipo == "AFND":
            aceptada, pasos = a.procesar_cadena_afnd(cadena)
            for sym, conj in pasos: lineas.append(f"  [{sym:^8}]  Estados activos: {{{', '.join(sorted(conj))}}}")
            lineas.append("\nResultado: " + ("✅ ACEPTADA" if aceptada else "❌ RECHAZADA"))
        else:  
            aceptada, pasos = a.procesar_cadena_afnl(cadena)
            for sym, conj in pasos:
                if sym.startswith("λ"): lineas.append(f"  [λ-clausura]  {{{', '.join(sorted(conj))}}}")
                else: lineas.append(f"  [símbolo '{sym}']  →  {{{', '.join(sorted(conj))}}}")
            lineas.append("\nResultado: " + ("✅ ACEPTADA" if aceptada else "❌ RECHAZADA"))
        self._write_text(self.txt_resultado, "\n".join(lineas))

    # Lógica: Pruebas Múltiples (txt)
    def pruebas_multiples(self):
        if not self.automata.estados: return messagebox.showwarning("Aviso", "Carga autómata primero.")
        fp = filedialog.askopenfilename(filetypes=[("Texto", "*.txt"), ("Todos", "*.*")])
        if not fp: return
        with open(fp, 'r', encoding='utf-8') as f: cadenas = [ln.strip() for ln in f if ln.strip()]
        a = self.automata
        lineas = [f"Informe de Pruebas Múltiples ({a.tipo})", "=" * 50]
        ac = rc = 0
        for cad in cadenas:
            ok, _ = a.procesar_cadena_afd(cad) if a.tipo == "AFD" else a.procesar_cadena_afnd(cad) if a.tipo == "AFND" else a.procesar_cadena_afnl(cad)
            lineas.append(f"  '{cad}'  →  {'✅ ACEPTADA' if ok else '❌ RECHAZADA'}")
            if ok: ac += 1 
            else: rc += 1
        lineas += ["", f"Total: {len(cadenas)}  |  Aceptadas: {ac}  |  Rechazadas: {rc}"]
        self._write_text(self.txt_resultado, "\n".join(lineas))

    # Lógica: Cálculo de λ-clausura
    def calcular_lambda_clausura(self):
        a = self.automata
        if not a.estados: return messagebox.showwarning("Aviso", "No hay autómata cargado.")
        raw = self.entry_lc.get().strip()
        est_in = {s.strip() for s in raw.split(",") if s.strip() in a.estados}
        if not est_in: return messagebox.showwarning("Aviso", f"Estado(s) '{raw}' no encontrados.")
        clausura = a.lambda_clausura(est_in)
        lineas = [f"λ-clausura({{{', '.join(sorted(est_in))}}})", "=" * 40, f"Resultado: {{{', '.join(sorted(clausura))}}}\n", "Detalle:"]
        for s in sorted(est_in):
            d = a._trans_set(s, "λ")
            lineas.append(f"  δ(q{s}, λ) = {{{', '.join(sorted(d))} }}" if d else f"  δ(q{s}, λ) = ∅")
        self._write_text(self.txt_lc, "\n".join(lineas))

    # Lógica: Conversión AFNλ a AFND
    def convertir_afnl_afnd(self):
        if self.automata.tipo != "AFNλ": return messagebox.showwarning("Aviso", "No es AFN-λ.")
        afnd = self.automata.convertir_afnl_a_afnd()
        lineas = ["━━━ Conversión: AFN-λ → AFND (Eliminación de λ) ━━━\n", "Tabla de transiciones:"]
        sims = sorted(afnd.alfabeto)
        enc = "Estado".ljust(12) + "  ".join(s.ljust(20) for s in sims)
        lineas.extend([enc, "-" * len(enc)])
        for est in sorted(afnd.estados):
            fila = est.ljust(12)
            for sym in sims:
                dests = afnd.transiciones.get(est, {}).get(sym, set())
                fila += ("{" + ",".join(sorted(dests)) + "}").ljust(22) if dests else "-".ljust(22)
            lineas.append(fila)
        self._write_text(self.txt_conv, "\n".join(lineas))
        if messagebox.askyesno("Cargar", "¿Cargar AFND como activo?"):
            self.automata = afnd; self.actualizar_info()

    # Lógica: Conversión AFND a AFD
    def convertir_afnd_afd(self):
        if self.automata.tipo not in ("AFND", "AFNλ"): return messagebox.showwarning("Aviso", "Ya es AFD.")
        afd, visitados = self.automata.convertir_afnd_a_afd()
        lineas = ["━━━ Conversión: AFND → AFD (Construcción de Subconjuntos) ━━━\n", "Mapeo de conjuntos:"]
        for fs, nid in sorted(visitados.items(), key=lambda x: int(x[1])):
            m = " [INICIAL]" if nid == afd.inicial else ""
            m += " [ACEPTACIÓN]" if nid in afd.aceptacion else ""
            lineas.append(f"  Estado {nid}: {{{', '.join(sorted(fs))}}}{m}")
        lineas += ["\nTabla de transiciones:"]
        sims = sorted(afd.alfabeto)
        enc = "Estado".ljust(10) + "  ".join(s.ljust(10) for s in sims)
        lineas.extend([enc, "-" * len(enc)])
        for est in sorted(afd.estados, key=lambda x: int(x)):
            fila = est.ljust(10)
            for sym in sims:
                dests = afd.transiciones.get(est, {}).get(sym, set())
                fila += (next(iter(dests)) if dests else "-").ljust(12)
            lineas.append(fila)
        self._write_text(self.txt_conv, "\n".join(lineas))
        if messagebox.askyesno("Cargar", "¿Cargar AFD como activo?"):
            self.automata = afd; self.actualizar_info()

    # Lógica: Ejecutar Minimización
    def ejecutar_minimizacion(self):
        if self.automata.tipo != "AFD" or not self.automata.estados: return messagebox.showwarning("Aviso", "Requiere AFD válido.")
        self.afd_minimizado, info = self.automata.minimizar_afd()
        lineas = ["━━━ Minimización Completa ━━━"]
        lineas.append(f"Estados eliminados: {info['estados_antes'] - info['estados_despues']}")
        lineas.append("Grupos equivalentes:")
        for rep, grupo in info['grupos'].items(): lineas.append(f"  Representante {rep} <- {{{', '.join(sorted(grupo))}}}")
        self._write_text(self.txt_min, "\n".join(lineas))
        messagebox.showinfo("Éxito", "Minimización completada. Usa los botones para comparar.")

    # Visualización: Comparación de Grafos
    def mostrar_grafos_lado_a_lado(self):
        if not self.automata.estados or not self.afd_minimizado: return messagebox.showwarning("Aviso", "Minimiza primero.")
        try:
            import matplotlib.pyplot as plt
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
            self._dibujar_grafo_ax(self.automata, ax1, "AFD Original")
            self._dibujar_grafo_ax(self.afd_minimizado, ax2, "AFD Minimizado")
            plt.tight_layout()
            plt.show()
        except ImportError:
            messagebox.showerror("Error", "Faltan librerías: networkx matplotlib")

    # Lógica: Evaluar Equivalencia
    def probar_equivalencia(self):
        if not self.afd_minimizado: return messagebox.showwarning("Aviso", "Minimiza primero.")
        cadenas = [c.strip() for c in self.entry_equiv.get().split(",") if c.strip()]
        if not cadenas: return messagebox.showwarning("Aviso", "Ingresa cadena(s).")
        lineas = ["━━━ Prueba de Equivalencia Automática ━━━\n"]
        todas_iguales = True
        for cad in cadenas:
            ok_orig, _ = self.automata.procesar_cadena_afd(cad)
            ok_min, _ = self.afd_minimizado.procesar_cadena_afd(cad)
            match = "✅" if ok_orig == ok_min else "❌ DIFERENCIA"
            if ok_orig != ok_min: todas_iguales = False
            lineas.append(f"Cadena '{cad}':\n  ├─ Original:   {'Aceptada' if ok_orig else 'Rechazada'}\n  └─ Minimizado: {'Aceptada' if ok_min else 'Rechazada'}  {match}")
        lineas.append(f"\nCONCLUSIÓN: {'Ambos son equivalentes.' if todas_iguales else 'NO son equivalentes.'}")
        self._write_text(self.txt_min, "\n".join(lineas))

    # Lógica: Algoritmo GNFA AFD a ER
    def convertir_afd_a_er(self):
        if self.automata.tipo != "AFD" or not self.automata.estados: return messagebox.showwarning("Aviso", "Requiere AFD.")
        a = self.automata
        lineas = ["━━━ Algoritmo de Eliminación de Estados ━━━\n"]
        
        gnfa = {s: {} for s in a.estados}
        for u in a.estados:
            for sym, dests in a.transiciones.get(u, {}).items():
                v = next(iter(dests))
                gnfa[u][v] = sym if v not in gnfa[u] else f"({gnfa[u][v]}+{sym})"
        gnfa['START'] = {a.inicial: 'λ'}
        for s in a.estados: gnfa[s]['END'] = 'λ' if s in a.aceptacion else None
        for s in a.estados: gnfa[s] = {k: v for k, v in gnfa[s].items() if v}
        
        def format_regex(r1, r2, r3):
            r2_star = f"({r2})*" if len(r2)>1 else f"{r2}*"
            if r2 == 'λ': r2_star = ""
            res = f"{r1 if r1!='λ' else ''}{r2_star}{r3 if r3!='λ' else ''}"
            return res if res else 'λ'

        for q in list(a.estados):
            lineas.append(f"[*] Eliminando estado q{q}...")
            entradas = [p for p in gnfa if q in gnfa.get(p, {}) and p != q]
            salidas = [r for r, regex in gnfa.get(q, {}).items() if r != q]
            bucle_q = gnfa.get(q, {}).get(q, 'λ')

            for p in entradas:
                for r in salidas:
                    pq = gnfa[p][q]; qr = gnfa[q][r]
                    nueva_ruta = format_regex(pq, bucle_q, qr)
                    if r in gnfa.get(p, {}): gnfa[p][r] = f"({gnfa[p][r]}+{nueva_ruta})"
                    else: gnfa[p][r] = nueva_ruta
            
            del gnfa[q]
            for p in gnfa: 
                if q in gnfa[p]: del gnfa[p][q]
            lineas.append(f"    -> Estado actualizado.\n")

        er_final = gnfa['START'].get('END', '∅')
        lineas.append(f"Expresión Regular: {er_final}")
        self._write_text(self.txt_er, "\n".join(lineas))

    # Lógica: Actualizar Información ER Práctica
    def _actualizar_regex_info(self, event):
        sel = self.combo_casos.get()
        if "Correo" in sel: self.lbl_er_info.config(text="ER: ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$")
        elif "Teléfono" in sel: self.lbl_er_info.config(text="ER: ^\\d{10}$")
        elif "Fecha" in sel: self.lbl_er_info.config(text="ER: ^(0[1-9]|[12][0-9]|3[01])/(0[1-9]|1[012])/\\d{4}$")

    # Lógica: Validar Casos Prácticos
    def validar_caso_practico(self):
        sel = self.combo_casos.get()
        txt = self.entry_prac.get().strip()
        if "Correo" in sel: patron = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        elif "Teléfono" in sel: patron = r"^\d{10}$"
        elif "Fecha" in sel: patron = r"^(0[1-9]|[12][0-9]|3[01])/(0[1-9]|1[012])/\d{4}$"
        
        if re.fullmatch(patron, txt): self.lbl_feedback.config(text="✅ Válido.", fg="green")
        else: self.lbl_feedback.config(text="❌ Inválido.", fg="red")

    # Lógica: Mostrar AFD Práctico
    def mostrar_afd_practico(self):
        sel = self.combo_casos.get()
        a_prac = Automata()
        a_prac.tipo = "AFD"
        
        if "Teléfono" in sel:
            a_prac.estados = {str(i) for i in range(11)}; a_prac.inicial = "0"; a_prac.aceptacion = {"10"}; a_prac.alfabeto = {"d"}
            for i in range(10): a_prac.transiciones[str(i)] = {"d": {str(i+1)}}
        elif "Correo" in sel:
            a_prac.estados = {"0", "1", "2", "3", "4"}; a_prac.inicial = "0"; a_prac.aceptacion = {"4"}; a_prac.alfabeto = {"char", "@", "."}
            a_prac.transiciones = {"0": {"char": {"0"}, "@": {"1"}}, "1": {"char": {"2"}}, "2": {"char": {"2"}, ".": {"3"}}, "3": {"char": {"4"}}, "4": {"char": {"4"}}}
        elif "Fecha" in sel:
            a_prac.estados = {"0","1","2","3","4","5"}; a_prac.inicial = "0"; a_prac.aceptacion = {"5"}; a_prac.alfabeto = {"DD", "MM", "YYYY", "/"}
            a_prac.transiciones = {"0": {"DD": {"1"}}, "1": {"/": {"2"}}, "2": {"MM": {"3"}}, "3": {"/": {"4"}}, "4": {"YYYY": {"5"}}}

        try:
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(8, 4))
            self._dibujar_grafo_ax(a_prac, ax, f"AFD: {sel}")
            plt.tight_layout()
            plt.show()
        except ImportError: messagebox.showerror("Error", "Faltan librerías matplotlib/networkx")

    # Visualización: Mostrar Tabla
    def mostrar_tabla(self):
        if not self.automata.estados: return messagebox.showwarning("Aviso", "No hay autómata cargado.")
        top = tk.Toplevel(self.root)
        top.title(f"Tabla de Transiciones ({self.automata.tipo})")
        top.geometry("560x360")
        sims = sorted(self.automata.alfabeto) + (["λ"] if self.automata.tipo == "AFNλ" else [])
        cols = ["Estado"] + sims
        tree = ttk.Treeview(top, columns=cols, show="headings")
        for c in cols: tree.heading(c, text=c); tree.column(c, anchor=tk.CENTER, width=90)
        for est in sorted(self.automata.estados):
            pref = "→ " if str(est) == str(self.automata.inicial) else "  "
            pref += "* " if str(est) in self.automata.aceptacion else "  "
            fila = [f"{pref}q{est}"]
            for sym in sims:
                dests = self.automata.transiciones.get(str(est), {}).get(sym, set())
                fila.append("{" + ",".join(f"q{d}" for d in sorted(dests)) + "}" if dests else "-")
            tree.insert("", tk.END, values=fila)
        sb = ttk.Scrollbar(top, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=6, pady=6)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

    # Visualización: Mostrar Grafo Principal
    def mostrar_grafo_principal(self):
        if not self.automata.estados: return
        try:
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(8, 6))
            self._dibujar_grafo_ax(self.automata, ax, f"Grafo Principal ({self.automata.tipo})")
            plt.show()
        except ImportError: messagebox.showerror("Error", "Faltan librerías: networkx matplotlib")

    # Helper: Dibujar Grafo en un Axes
    def _dibujar_grafo_ax(self, a, ax, titulo):
        import networkx as nx
        G = nx.MultiDiGraph()
        for orig, trans in a.transiciones.items():
            for sym, dests in trans.items():
                for dest in dests:
                    if G.has_edge(f"q{orig}", f"q{dest}"):
                        for _, d in G[f"q{orig}"][f"q{dest}"].items(): d['label'] += f",{sym}"; break
                    else:
                        G.add_edge(f"q{orig}", f"q{dest}", label=sym, style='dashed' if sym == "λ" else 'solid')
        pos = nx.spring_layout(G, seed=42)
        colors = ["#90EE90" if n.replace("q","") == str(a.inicial) else "#FFD700" if n.replace("q","") in a.aceptacion else "#ADD8E6" for n in G.nodes()]
        nx.draw_networkx_nodes(G, pos, node_color=colors, node_size=1500, ax=ax)
        nx.draw_networkx_labels(G, pos, font_size=9, font_weight="bold", ax=ax)
        nx.draw_networkx_edges(G, pos, edgelist=[e for e in G.edges(data=True) if e[2]['style']!='dashed'], connectionstyle='arc3,rad=0.2', arrowsize=15, ax=ax)
        nx.draw_networkx_edges(G, pos, edgelist=[e for e in G.edges(data=True) if e[2]['style']=='dashed'], connectionstyle='arc3,rad=0.2', arrowsize=15, ax=ax, style='dashed', edge_color='purple')
        edge_labels = {(u, v): d['label'] for u, v, d in G.edges(data=True)}
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_color="red", ax=ax)
        ax.set_title(titulo)
        ax.axis('off')

    # Extras: Lenguaje
    def mostrar_partes_cadena(self):
        cadena = self.txt_cadena.get() if hasattr(self, 'txt_cadena') else ""
        if not cadena: cadena = simpledialog.askstring("Cadena", "Ingresa una cadena:") or ""
        if not cadena: return
        msg  = f"Cadena: '{cadena}'\n\nPREFIJOS:\n{sorted(obtener_prefijos(cadena), key=len)}\n\nSUFIJOS:\n{sorted(obtener_sufijos(cadena), key=len)}\n\nSUBCADENAS:\n{sorted(obtener_subcadenas(cadena), key=len)}"
        self._crear_ventana_resultados("Subcadenas, Prefijos y Sufijos", msg)

    def mostrar_kleene(self):
        if not self.automata.alfabeto: return messagebox.showwarning("Aviso", "Carga un autómata primero.")
        n = simpledialog.askinteger("Cerradura", "Longitud máxima (n):", minvalue=1, maxvalue=8)
        if n:
            msg = f"Alfabeto: {sorted(self.automata.alfabeto)}\n\nCERRADURA POSITIVA (+):\n{sorted(obtener_positiva(self.automata.alfabeto, n), key=len)}\n\nCERRADURA DE KLEENE (*):\n{sorted(obtener_kleene(self.automata.alfabeto, n), key=len)}"
            self._crear_ventana_resultados("Cerraduras", msg)

    def _crear_ventana_resultados(self, titulo, contenido):
        top = tk.Toplevel(self.root)
        top.title(titulo)
        top.geometry("520x420")
        txt = tk.Text(top, wrap=tk.WORD, font=("Consolas", 10))
        txt.insert(tk.END, contenido)
        txt.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        tk.Button(top, text="Guardar en .txt", command=lambda: self._guardar_txt(contenido), bg="lightgray").pack(pady=5)

    def _guardar_txt(self, contenido):
        fp = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Texto", "*.txt")])
        if fp:
            with open(fp, 'w', encoding='utf-8') as f: f.write(contenido)
            messagebox.showinfo("Éxito", "Archivo guardado.")

    # UI Helpers
    def _write_text(self, widget, texto):
        widget.config(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, texto)
        widget.config(state=tk.DISABLED)

    def actualizar_info(self):
        a = self.automata
        tipos_color = {"AFD": self.COLOR_AFD, "AFND": self.COLOR_AFND, "AFNλ": self.COLOR_AFNL}
        self.lbl_tipo.config(text=f"Tipo actual: {a.tipo}", bg=tipos_color.get(a.tipo, "#eee"))
        self.lbl_info.config(text=f"Estados: {len(a.estados)} | Inicial: q{a.inicial} | Finales: {len(a.aceptacion)}", fg="green")
    
    # Visulizador JFLAP (dibujado)
    def dibujar_automata_canvas(self, estados_resaltados=None, color_resalte="red"):
        import math
        a = self.automata
        self.canvas.delete("all")

        if not a.estados:
            return

        R = 30  # radio del estado

        if a.posiciones:
            xs = [p[0] for p in a.posiciones.values()]
            ys = [p[1] for p in a.posiciones.values()]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            span_x = max(max_x - min_x, 1)
            span_y = max(max_y - min_y, 1)

            W = self.canvas.winfo_width()  or 800
            H = self.canvas.winfo_height() or 500
            margin = 80
            scale = min((W - 2*margin) / span_x, (H - 2*margin) / span_y, 3.0)

            def _pos(s):
                ox, oy = a.posiciones.get(s, (min_x, min_y))
                return margin + (ox - min_x) * scale, margin + (oy - min_y) * scale
        else:
            def _pos(s):
                return a.posiciones.get(s, (100, 100))

        self.pos_canvas = {s: _pos(s) for s in a.estados}

        pares = {}
        for orig, trans in a.transiciones.items():
            for sym, dests in trans.items():
                for dest in dests:
                    pares.setdefault((orig, dest), []).append(sym)

        bidi = {(o, d) for (o, d) in pares if o != d and (d, o) in pares}

        for s in a.estados:
            x, y = self.pos_canvas[s]
            fill_color = "#90EE90" if s == a.inicial else                          "#FFD700" if s in a.aceptacion else "#ADD8E6"
            self.canvas.create_oval(x-R, y-R, x+R, y+R,
                                    fill=fill_color, outline="black", width=2)
            if s in a.aceptacion:
                self.canvas.create_oval(x-R+5, y-R+5, x+R-5, y+R-5,
                                        outline="black", width=2)
            self.canvas.create_text(x, y, text=f"q{s}",
                                    font=("Arial", 9, "bold"))
            if s == a.inicial:
                self.canvas.create_line(x - R - 30, y, x - R, y,
                                        arrow=tk.LAST, width=2)

        for (orig, dest), syms in pares.items():
            label = ", ".join(sorted(syms))
            x1, y1 = self.pos_canvas[orig]
            x2, y2 = self.pos_canvas[dest]

            if orig == dest:

                loop_w = R * 1.4
                loop_h = R * 1.2
                bx0 = x1 - loop_w
                by0 = y1 - R - loop_h * 2
                bx1 = x1 + loop_w
                by1 = y1 - R
                self.canvas.create_arc(bx0, by0, bx1, by1,
                                       start=20, extent=300,
                                       style=tk.ARC, width=2)
                angle_arrow = math.radians(320)
                cx_arc = (bx0 + bx1) / 2
                cy_arc = (by0 + by1) / 2
                rx_arc = (bx1 - bx0) / 2
                ry_arc = (by1 - by0) / 2
                tip_x = cx_arc + rx_arc * math.cos(angle_arrow)
                tip_y = cy_arc - ry_arc * math.sin(angle_arrow)
                # Dirección tangente en ese punto
                tang_x = -rx_arc * math.sin(angle_arrow)
                tang_y =  ry_arc * math.cos(angle_arrow)
                tang_len = math.hypot(tang_x, tang_y) or 1
                tang_x /= tang_len; tang_y /= tang_len
                arr = 8
                self.canvas.create_line(
                    tip_x - tang_x * arr, tip_y + tang_y * arr,
                    tip_x, tip_y,
                    arrow=tk.LAST, width=2
                )
                # Etiqueta centrada sobre el bucle
                self.canvas.create_text(
                    x1, by0 - 8,
                    text=label, font=("Arial", 9, "bold"), fill="blue"
                )

            else:
                dx = x2 - x1
                dy = y2 - y1
                dist = math.hypot(dx, dy) or 1
                ux, uy = dx / dist, dy / dist    # unitario
                nx, ny = -uy, ux                  # normal

                # Puntos de borde del círculo
                sx = x1 + ux * R
                sy = y1 + uy * R
                ex = x2 - ux * R
                ey = y2 - uy * R

                if (orig, dest) in bidi:
                    # Curva desplazada lateralmente para flechas de vuelta
                    offset = 24
                    # Punto de control único en el centro desplazado
                    mid_x = (sx + ex) / 2 + nx * offset
                    mid_y = (sy + ey) / 2 + ny * offset
                    self.canvas.create_line(
                        sx + nx * 6, sy + ny * 6,
                        mid_x, mid_y,
                        ex + nx * 6, ey + ny * 6,
                        smooth=True, arrow=tk.LAST, width=2
                    )
                    lbl_x = mid_x + nx * 14
                    lbl_y = mid_y + ny * 14
                else:
                    self.canvas.create_line(sx, sy, ex, ey,
                                            arrow=tk.LAST, width=2)
                    lbl_x = (sx + ex) / 2 + nx * 16
                    lbl_y = (sy + ey) / 2 + ny * 16

                self.canvas.create_text(lbl_x, lbl_y, text=label,
                                        font=("Arial", 9, "bold"), fill="blue")

        if estados_resaltados:
            for s in estados_resaltados:
                if s in self.pos_canvas:
                    x, y = self.pos_canvas[s]
                    self.canvas.create_oval(x-R-5, y-R-5, x+R+5, y+R+5,
                                            outline=color_resalte, width=3)
                    
       #  Pestaña Automata de Pila
    def _build_tab_ap(self, parent):
        import math
        COLOR_AP = "#e8d5f5"

        frm_top = tk.Frame(parent, bg=COLOR_AP); frm_top.pack(fill=tk.X, padx=8, pady=6)
        tk.Label(frm_top, text="Autómata de Pila No Determinista", bg=COLOR_AP,
                 font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=6, pady=4)

        def lbl(txt, r, c):
            tk.Label(frm_top, text=txt, bg=COLOR_AP, font=("Arial", 9)).grid(
                row=r, column=c, sticky="w", padx=4)
        def ent(r, c, w=18):
            e = tk.Entry(frm_top, width=w, font=("Arial", 9))
            e.grid(row=r, column=c, padx=4, pady=2); return e

        lbl("Estados (q0,q1,...):", 1, 0); self.ap_e_estados  = ent(1, 1)
        lbl("Inicial:",             1, 2); self.ap_e_inicial   = ent(1, 3, 6)
        lbl("Aceptación:",          1, 4); self.ap_e_acep      = ent(1, 5)
        lbl("Alfabeto entrada:",    2, 0); self.ap_e_alfa       = ent(2, 1)
        lbl("Alfabeto pila:",       2, 2); self.ap_e_alfa_pila  = ent(2, 3)
        lbl("Fondo de pila:",       2, 4); self.ap_e_fondo      = ent(2, 5, 4)
        self.ap_e_fondo.insert(0, "Z")

        lbl("Condición de aceptación:", 3, 0)
        self.ap_cond_var = tk.StringVar(value="ambas")
        frm_cond = tk.Frame(frm_top, bg=COLOR_AP); frm_cond.grid(row=3, column=1, columnspan=3, sticky="w")
        for val, txt in [("estado_final","Por estado final"),
                          ("pila_vacia", "Por pila vacía"),
                          ("ambas",      "Ambas")]:
            tk.Radiobutton(frm_cond, text=txt, variable=self.ap_cond_var,
                           value=val, bg=COLOR_AP).pack(side=tk.LEFT, padx=4)

        frm_tr = tk.LabelFrame(parent, text="Transiciones  (orig, sim_entrada, sim_pila, dest, cadena_apilar)",
                                font=("Arial", 9)); frm_tr.pack(fill=tk.X, padx=8, pady=2)
        tk.Label(frm_tr, text="Una por línea.  Use λ para epsilon.  Ejemplo:  q0,a,Z,q1,AZ",
                 font=("Arial", 8), fg="gray").pack(anchor="w", padx=6)
        self.ap_txt_trans = tk.Text(frm_tr, height=7, width=80, font=("Consolas", 9))
        self.ap_txt_trans.pack(padx=6, pady=4)

        frm_btns = tk.Frame(parent); frm_btns.pack(pady=4)
        tk.Button(frm_btns, text="💾 Cargar AP",        bg="#c8e6c9",
                  command=self.ap_cargar,        font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=4)
        tk.Button(frm_btns, text="📋 Ver Tabla",        bg="#fff9c4",
                  command=self.ap_ver_tabla,     font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=4)
        tk.Button(frm_btns, text="🗺 Dibujar AP",       bg="#b3e5fc",
                  command=self.ap_dibujar,       font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=4)

        frm_sim = tk.LabelFrame(parent, text="Simulación", font=("Arial", 9)); frm_sim.pack(fill=tk.X, padx=8, pady=4)
        frm_s2 = tk.Frame(frm_sim); frm_s2.pack(pady=4)
        tk.Label(frm_s2, text="Cadena:").pack(side=tk.LEFT)
        self.ap_entry_cadena = tk.Entry(frm_s2, width=30, font=("Arial", 11)); self.ap_entry_cadena.pack(side=tk.LEFT, padx=6)
        tk.Button(frm_s2, text="▶ Simular", bg="#ce93d8",
                  command=self.ap_simular, font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=4)
        tk.Button(frm_s2, text="⏮ Paso anterior", command=self.ap_paso_ant,
                  font=("Arial", 9)).pack(side=tk.LEFT, padx=2)
        tk.Button(frm_s2, text="⏭ Paso siguiente", command=self.ap_paso_sig,
                  font=("Arial", 9)).pack(side=tk.LEFT, padx=2)
        self.ap_lbl_paso = tk.Label(frm_sim, text="", font=("Arial", 10, "bold"), fg="#6a1b9a")
        self.ap_lbl_paso.pack(pady=2)

        frm_viz = tk.Frame(parent); frm_viz.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        self.ap_canvas = tk.Canvas(frm_viz, bg="white", width=560)
        self.ap_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        frm_pila = tk.Frame(frm_viz, bg="#fce4ec", width=130, relief="groove", bd=2)
        frm_pila.pack(side=tk.LEFT, fill=tk.Y, padx=(6, 0))
        tk.Label(frm_pila, text="PILA", bg="#fce4ec",
                 font=("Arial", 10, "bold")).pack(pady=4)
        self.ap_pila_canvas = tk.Canvas(frm_pila, bg="#fce4ec", width=120)
        self.ap_pila_canvas.pack(fill=tk.BOTH, expand=True)

        self.ap_paso_idx = 0
        self.ap_pasos    = []

    def ap_cargar(self):
        ap = self.ap
        ap.__init__()

        ap.estados    = {x.strip() for x in self.ap_e_estados.get().split(",") if x.strip()}
        ap.inicial    = self.ap_e_inicial.get().strip()
        ap.aceptacion = {x.strip() for x in self.ap_e_acep.get().split(",") if x.strip()}
        ap.alfabeto   = {x.strip() for x in self.ap_e_alfa.get().split(",") if x.strip()}
        ap.alfa_pila  = {x.strip() for x in self.ap_e_alfa_pila.get().split(",") if x.strip()}
        ap.simbolo_fondo = self.ap_e_fondo.get().strip() or "Z"
        ap.cond_acep  = self.ap_cond_var.get()

        errores = []
        for ln in self.ap_txt_trans.get("1.0", tk.END).strip().splitlines():
            partes = [p.strip() for p in ln.split(",")]
            if len(partes) != 5:
                errores.append(f"Línea inválida (necesita 5 campos): {ln}")
                continue
            orig, sim_e, sim_p, dest, apilar = partes
            if orig not in ap.estados:
                errores.append(f"Estado origen desconocido: {orig}")
            elif dest not in ap.estados:
                errores.append(f"Estado destino desconocido: {dest}")
            else:
                ap.agregar_trans(orig, sim_e, sim_p, dest, apilar)

        if errores:
            messagebox.showwarning("Errores al cargar", "\n".join(errores))
            return

        import math
        n = len(ap.estados)
        cx, cy, r = 280, 200, 150
        for i, s in enumerate(sorted(ap.estados)):
            ang = 2 * math.pi * i / max(n, 1) - math.pi / 2
            ap.posiciones[s] = (cx + r * math.cos(ang), cy + r * math.sin(ang))

        self.ap_dibujar()
        messagebox.showinfo("AP cargado", f"Autómata de Pila cargado con {len(ap.estados)} estados y {len(ap.transiciones)} reglas.")

    def ap_ver_tabla(self):
        dlg = tk.Toplevel(self.root); dlg.title("Tabla de Transiciones – AP")
        dlg.geometry("600x400")
        txt = tk.Text(dlg, font=("Consolas", 10), state=tk.DISABLED)
        txt.pack(expand=True, fill=tk.BOTH, padx=8, pady=8)
        txt.config(state=tk.NORMAL)
        txt.insert(tk.END, self.ap.tabla_texto())
        txt.config(state=tk.DISABLED)

    def ap_dibujar(self, paso=None):
        import math
        ap = self.ap
        self.ap_canvas.delete("all")
        if not ap.estados:
            return

        R = 28
        pos = ap.posiciones

        if pos:
            xs = [p[0] for p in pos.values()]
            ys = [p[1] for p in pos.values()]
            mnx, mxx = min(xs), max(xs)
            mny, mxy = min(ys), max(ys)
            W = self.ap_canvas.winfo_width()  or 560
            H = self.ap_canvas.winfo_height() or 340
            mg = 70
            sc = min((W-2*mg)/max(mxx-mnx,1), (H-2*mg)/max(mxy-mny,1), 3.0)
            def _p(s):
                ox, oy = pos.get(s, (mnx, mny))
                return mg+(ox-mnx)*sc, mg+(oy-mny)*sc
        else:
            def _p(s): return pos.get(s, (100,100))

        self.ap_pos_canvas = {s: _p(s) for s in ap.estados}

        estado_activo = paso["estado"] if paso else None

        pares = {}
        for (orig, sim_e, sim_p), dests in ap.transiciones.items():
            for (dest, apilar) in dests:
                lbl = f"{sim_e},{sim_p}/{apilar}"
                pares.setdefault((orig, dest), []).append(lbl)

        bidi = {(o,d) for (o,d) in pares if o!=d and (d,o) in pares}

        for (orig, dest), labels in pares.items():
            label = "\n".join(labels)
            x1,y1 = self.ap_pos_canvas[orig]
            x2,y2 = self.ap_pos_canvas[dest]

            if orig == dest:
                lw = R*1.4; lh = R*1.2
                bx0=x1-lw; by0=y1-R-lh*2; bx1=x1+lw; by1=y1-R
                self.ap_canvas.create_arc(bx0,by0,bx1,by1, start=20,extent=300,
                                          style=tk.ARC,width=2)
                self.ap_canvas.create_text(x1, by0-8, text=label,
                                           font=("Arial",7,"bold"), fill="blue")
            else:
                dx=x2-x1; dy=y2-y1
                dist=math.hypot(dx,dy) or 1
                ux,uy=dx/dist,dy/dist; nx,ny=-uy,ux
                sx=x1+ux*R; sy=y1+uy*R; ex=x2-ux*R; ey=y2-uy*R
                if (orig,dest) in bidi:
                    off=22
                    mx=(sx+ex)/2+nx*off; my=(sy+ey)/2+ny*off
                    self.ap_canvas.create_line(sx+nx*6,sy+ny*6, mx,my,
                                               ex+nx*6,ey+ny*6,
                                               smooth=True,arrow=tk.LAST,width=2)
                    lx=mx+nx*14; ly=my+ny*14
                else:
                    self.ap_canvas.create_line(sx,sy,ex,ey,arrow=tk.LAST,width=2)
                    lx=(sx+ex)/2+nx*16; ly=(sy+ey)/2+ny*16
                self.ap_canvas.create_text(lx,ly, text=label,
                                           font=("Arial",7,"bold"), fill="blue")

        for s in ap.estados:
            x,y = self.ap_pos_canvas[s]
            fill = "#90EE90" if s == ap.inicial else                    "#FFD700" if s in ap.aceptacion else "#ADD8E6"
            if s == estado_activo:
                fill = "#FF6B6B"
            self.ap_canvas.create_oval(x-R,y-R,x+R,y+R,
                                       fill=fill,outline="black",width=2)
            if s in ap.aceptacion:
                self.ap_canvas.create_oval(x-R+4,y-R+4,x+R-4,y+R-4,
                                           outline="black",width=2)
            self.ap_canvas.create_text(x,y, text=f"q{s}",
                                       font=("Arial",9,"bold"))
            if s == ap.inicial:
                self.ap_canvas.create_line(x-R-28,y,x-R,y,arrow=tk.LAST,width=2)

    def ap_dibujar_pila(self, pila):
        self.ap_pila_canvas.delete("all")
        H = self.ap_pila_canvas.winfo_height() or 300
        W = self.ap_pila_canvas.winfo_width()  or 120
        celd_h = 32; celd_w = 70; x0 = (W - celd_w) // 2

        if not pila:
            self.ap_pila_canvas.create_text(W//2, H//2, text="(vacía)",
                                            font=("Arial",9), fill="gray")
            return

        n = len(pila)
        y_base = H - 10
        for i, sym in enumerate(pila):        
            y1 = y_base - (i+1)*celd_h
            y2 = y_base - i*celd_h
            # cima en rojo
            color = "#ff8a80" if i == n-1 else "#f8bbd0"
            self.ap_pila_canvas.create_rectangle(x0, y1, x0+celd_w, y2,
                                                  fill=color, outline="black")
            self.ap_pila_canvas.create_text(x0+celd_w//2, (y1+y2)//2,
                                             text=sym, font=("Arial",10,"bold"))
        cima_y = y_base - n*celd_h - 2
        self.ap_pila_canvas.create_text(x0+celd_w//2, cima_y-10,
                                         text="▲ cima", font=("Arial",8), fill="#6a1b9a")

    def ap_simular(self):
        cadena = self.ap_entry_cadena.get().strip()
        aceptada, pasos = self.ap.simular(cadena)

        if aceptada and pasos:
            self.ap_pasos   = pasos
            self.ap_paso_idx = 0
            self._ap_mostrar_paso()
            messagebox.showinfo("Resultado",
                f"Cadena '{cadena}' ACEPTADA\n"
                f"Pasos en el camino aceptante: {len(pasos)}\n"
                f"Use ⏮ / ⏭ para recorrer la traza.")
        else:
            self.ap_pasos    = []
            self.ap_paso_idx = 0
            self.ap_dibujar()
            self.ap_dibujar_pila([])
            self.ap_lbl_paso.config(text=f"Cadena '{cadena}' RECHAZADA (o límite de configuraciones alcanzado)")

    def _ap_mostrar_paso(self):
        if not self.ap_pasos:
            return
        idx  = self.ap_paso_idx
        paso = self.ap_pasos[idx]
        self.ap_dibujar(paso=paso)
        self.ap_dibujar_pila(paso["pila"])
        entrada_rest = paso["entrada"] if paso["entrada"] else "λ"
        regla = paso.get("regla", "—")
        self.ap_lbl_paso.config(
            text=f"Paso {idx+1}/{len(self.ap_pasos)}  |  "
                 f"Estado: q{paso['estado']}  |  "
                 f"Entrada restante: {entrada_rest}\n"
                 f"Regla: {regla}"
        )

    def ap_paso_ant(self):
        if self.ap_pasos and self.ap_paso_idx > 0:
            self.ap_paso_idx -= 1
            self._ap_mostrar_paso()

    def ap_paso_sig(self):
        if self.ap_pasos and self.ap_paso_idx < len(self.ap_pasos) - 1:
            self.ap_paso_idx += 1
            self._ap_mostrar_paso()

# Punto de entrada
if __name__ == "__main__":
    root = tk.Tk()
    app = SimuladorApp(root)
    root.mainloop()