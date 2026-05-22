# Practica-6.--Software-Interactivo-para-Visualizar-Automatas-de-Pila

## 👥 Autores

- **Gustavo Sebastián Bonilla Ojeda** — 2025630175  
- **Ximena Velázquez Mendoza** — 2024630176  
- **Yoltic Isaí Velázquez Ramos** — 2025230228  

📍 *ESCOM - Instituto Politécnico Nacional*  
📅 *Fecha: 21 de mayo de 2026*  

# Simulador de Autómata de Pila No Determinista (APND)

Este módulo implementa una interfaz gráfica para **crear, visualizar y simular un Autómata de Pila No Determinista (NPDA/APND)** utilizando **Python y Tkinter**.

Permite definir un autómata de pila personalizado, cargar sus transiciones, visualizar su estructura gráficamente y simular paso a paso el procesamiento de una cadena de entrada.

---

## Características

### Definición completa del APND

El usuario puede configurar:

- **Estados** del autómata
- **Estado inicial**
- **Estados de aceptación**
- **Alfabeto de entrada**
- **Alfabeto de pila**
- **Símbolo de fondo de pila**
- **Condición de aceptación**

### Condiciones de aceptación soportadas

Se puede elegir entre:

- **Por estado final**
- **Por pila vacía**
- **Ambas condiciones**

---

## Entrada de transiciones

Las transiciones se ingresan manualmente, una por línea, usando el formato:

```text
origen, simbolo_entrada, simbolo_pila, destino, cadena_apilar
```

### Ejemplo

```text
q0,a,Z,q1,AZ
q1,b,A,q1,AA
q1,λ,A,q2,λ
```

Donde:

- `λ` representa una transición epsilon (sin consumir símbolo)
- `simbolo_entrada` puede ser `λ`
- `simbolo_pila` indica qué debe encontrarse en la cima
- `cadena_apilar` indica qué símbolos se empujarán a la pila

---

## Funcionalidades disponibles

### 💾 Cargar AP

Valida y carga la definición del autómata.

Verifica:

- Estados válidos
- Transiciones bien formadas
- Estados destino existentes

Después de cargar:

- Calcula automáticamente posiciones para dibujar los estados
- Muestra un mensaje con el número de estados y reglas cargadas

---

### 📋 Ver Tabla

Muestra todas las transiciones cargadas en formato tabular.

Útil para verificar rápidamente la definición del autómata.

---

### 🗺 Dibujar AP

Genera una representación gráfica del autómata:

- Estados normales
- Estado inicial
- Estados de aceptación (doble círculo)
- Transiciones dirigidas
- Loops
- Transiciones bidireccionales curvadas
- Etiquetas con reglas

### Colores utilizados

- **Verde:** estado inicial
- **Dorado:** estado de aceptación
- **Azul claro:** estado normal
- **Rojo:** estado activo durante simulación

---

## Simulación de cadenas

Permite probar si una cadena es aceptada por el APND.

### Pasos:

1. Escribir una cadena
2. Presionar **▶ Simular**

El sistema:

- Ejecuta la simulación no determinista
- Busca un camino aceptante
- Si existe, guarda toda la traza de ejecución

---

## Navegación paso a paso

Después de una simulación exitosa se puede recorrer el proceso usando:

### ⏮ Paso anterior

Retrocede un paso en la simulación.

### ⏭ Paso siguiente

Avanza al siguiente paso.

En cada paso se actualiza:

- Estado actual
- Entrada restante
- Regla aplicada
- Contenido actual de la pila

---

## Visualización de la pila

La pila se muestra gráficamente en un panel lateral.

Características:

- Cada celda representa un símbolo
- La **cima** se resalta en rojo
- Se indica visualmente cuál es el tope de la pila

---

## Ejemplo completo

### Configuración

**Estados**

```text
q0,q1,q2
```

**Inicial**

```text
q0
```

**Aceptación**

```text
q2
```

**Alfabeto entrada**

```text
a,b
```

**Alfabeto pila**

```text
A,Z
```

**Fondo de pila**

```text
Z
```

---

### Transiciones

```text
q0,a,Z,q1,AZ
q1,a,A,q1,AA
q1,b,A,q1,λ
q1,λ,Z,q2,Z
```

### Cadena de prueba

```text
aaabbb
```

---

## Requisitos

- Python 3
- Tkinter
- XML (`ElementTree`)
- JSON
- NetworkX
- Matplotlib

---
