# NostraWhatsApp - Envío Masivo de WhatsApp desde Excel

Este proyecto permite enviar mensajes personalizados de WhatsApp a una lista de contactos extraída desde un archivo Excel, usando una interfaz gráfica desarrollada en PyQt5. Incluye dos versiones principales:

- **main.py + src/**: Versión refactorizada y modular, con buenas prácticas, separación en módulos y uso de base de datos interna SQLite.
- **nostrawhatsapp.py**: Versión monolítica (código espagueti), todo en un solo archivo.

---

## Estructura del proyecto

```
Whatsapp mensajeria desde un excell/
│
├── main.py                  # Lanzador de la versión refactorizada
├── nostrawhatsapp.py        # Versión monolítica (todo en uno)
├── requirements.txt         # Dependencias del proyecto
├── nostra_whatsapp.db       # Base de datos SQLite (se crea automáticamente)
├── src/
│   ├── controllers/
│   │   └── whatsapp_sender.py
│   ├── models/
│   │   ├── database.py
│   │   └── pandas_model.py
│   ├── utils/
│   │   └── constants.py
│   └── views/
│       ├── main_window.py
│       └── history_window.py
│
├── build/, dist/            # Carpetas generadas por PyInstaller
├── .gitignore
├── README.md
```

---

## Requisitos

- Python 3.8+
- Google Chrome instalado
- WhatsApp Web (debes iniciar sesión manualmente)

Instala las dependencias con:
```bash
pip install -r requirements.txt
```

---

## Uso de la versión refactorizada (recomendada)

1. **Ejecuta la app:**
   ```bash
   python main.py
   ```
2. **Importa tu archivo Excel** con los contactos (usa el botón en la interfaz).
3. **Personaliza el mensaje** usando variables como `[Nombre contacto]`, `[Ciudad]`, etc.
4. **Filtra por ciudad, comuna o giro** (solo un filtro activo a la vez).
5. **Haz clic en "Iniciar Envío"**. Debes tener WhatsApp Web abierto y logueado en Chrome.
6. **Consulta el historial** de envíos desde la interfaz.

**Notas:**
- El historial de envíos se guarda en `nostra_whatsapp.db`.
- No se reenvía el mismo mensaje al mismo contacto si activas la opción correspondiente.
- Puedes usar modo prueba para enviar solo al primer contacto.

---

## Uso de la versión monolítica (`nostrawhatsapp.py`)

1. **Ejecuta el archivo directamente:**
   ```bash
   python nostrawhatsapp.py
   ```
2. El flujo es similar, pero todo el código está en un solo archivo y es menos mantenible.

---

## Empaquetar como ejecutable (.exe)

1. Instala PyInstaller:
   ```bash
   pip install pyinstaller
   ```
2. Genera el ejecutable:
   ```bash
   pyinstaller --onefile --windowed main.py
   ```
   El ejecutable estará en la carpeta `dist/`.

---

## Notas técnicas

- **Refactorización:**
  - `main.py` solo lanza la app y la interfaz está en `src/views/main_window.py`.
  - La lógica de base de datos está en `src/models/database.py`.
  - El envío de WhatsApp se maneja en un hilo aparte en `src/controllers/whatsapp_sender.py`.
  - El historial se muestra con `src/views/history_window.py`.
- **Código espagueti:**
  - `nostrawhatsapp.py` contiene todo (modelo, vista, controlador, lógica de envío, etc.) en un solo archivo.

---

## Comandos útiles

- Instalar dependencias:
  ```bash
  pip install -r requirements.txt
  ```
- Ejecutar versión modular:
  ```bash
  python main.py
  ```
- Ejecutar versión monolítica:
  ```bash
  python nostrawhatsapp.py
  ```
- Empaquetar para Windows:
  ```bash
  pyinstaller --onefile --windowed main.py
  ```

---

## Autor

**Camilo Zavala - C1ZC**  
Portafolio: [https://c1zc.github.io/CamiloZavala/](https://c1zc.github.io/CamiloZavala/)

---

## Licencia

Este proyecto está bajo la licencia MIT. Consulta el archivo `LICENSE` para más detalles.
