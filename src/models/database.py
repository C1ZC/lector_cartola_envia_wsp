import sqlite3
import pandas as pd

class DatabaseManager:
    def __init__(self, db_file="nostra_whatsapp.db"):
        self.db_file = db_file
        self.create_tables()

    def get_connection(self):
        return sqlite3.connect(self.db_file)

    def create_tables(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            razon_social TEXT,
            rut TEXT,
            giro TEXT,
            direccion TEXT,
            comuna TEXT,
            ciudad TEXT,
            nombre_contacto TEXT,
            telefono TEXT
        )
        ''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS historial_envios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            razon_social TEXT,
            telefono TEXT,
            ciudad TEXT,
            resultado TEXT
        )
        ''')
        conn.commit()
        conn.close()

    def import_excel_to_db(self, excel_file):
        try:
            df = pd.read_excel(excel_file)
            required_columns = [
                'Razón social', 'RUT', 'Giro', 'Dirección', 'Comuna',
                'Ciudad', 'Nombre contacto', 'Teléfono'
            ]
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return False, f"Columnas faltantes: {', '.join(missing_columns)}"
            df = df.fillna("")
            for col in required_columns:
                df[col] = df[col].astype(str)
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM clientes")
            for _, row in df.iterrows():
                cursor.execute('''
                INSERT INTO clientes (razon_social, rut, giro, direccion, comuna, ciudad, nombre_contacto, telefono)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['Razón social'],
                    row['RUT'],
                    row['Giro'],
                    row['Dirección'],
                    row['Comuna'],
                    row['Ciudad'],
                    row['Nombre contacto'],
                    row['Teléfono']
                ))
            conn.commit()
            conn.close()
            return True, f"Se importaron {len(df)} registros."
        except Exception as e:
            return False, f"Error al importar: {str(e)}"

    def get_all_clients(self):
        conn = self.get_connection()
        query = '''
        SELECT razon_social as 'Razón social',
               rut as 'RUT',
               giro as 'Giro',
               direccion as 'Dirección',
               comuna as 'Comuna',
               ciudad as 'Ciudad',
               nombre_contacto as 'Nombre contacto',
               telefono as 'Teléfono'
        FROM clientes
        '''
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df

    def get_filtered_clients(self, city=None, commune=None, giro=None):
        conn = self.get_connection()
        query = '''
        SELECT razon_social as 'Razón social',
               rut as 'RUT',
               giro as 'Giro',
               direccion as 'Dirección',
               comuna as 'Comuna',
               ciudad as 'Ciudad',
               nombre_contacto as 'Nombre contacto',
               telefono as 'Teléfono'
        FROM clientes
        WHERE 1=1
        '''
        params = []
        if city and city.lower() != "todas las ciudades":
            query += " AND LOWER(ciudad) = ?"
            params.append(city.lower())
        if commune and commune.lower() != "todas las comunas":
            query += " AND LOWER(comuna) = ?"
            params.append(commune.lower())
        if giro and giro.lower() != "todos los giros":
            query += " AND LOWER(giro) = ?"
            params.append(giro.lower())
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df

    def get_unique_values(self, column):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT DISTINCT LOWER({column}) FROM clientes WHERE {column} IS NOT NULL AND {column} != ''")
        values = [row[0] for row in cursor.fetchall()]
        conn.close()
        return sorted(values)

    def record_message_sent(self, razon_social, telefono, ciudad, resultado):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO historial_envios (razon_social, telefono, ciudad, resultado)
        VALUES (?, ?, ?, ?)
        ''', (razon_social, telefono, ciudad, resultado))
        conn.commit()
        conn.close()

    def get_sent_phones(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT telefono FROM historial_envios WHERE resultado = 'Éxito'")
        phones = [row[0] for row in cursor.fetchall()]
        conn.close()
        return set(phones)

    def get_message_history(self, limit=100):
        conn = self.get_connection()
        query = '''
        SELECT fecha_hora, razon_social, telefono, ciudad, resultado
        FROM historial_envios
        ORDER BY fecha_hora DESC
        LIMIT ?
        '''
        df = pd.read_sql_query(query, conn, params=[limit])
        conn.close()
        return df