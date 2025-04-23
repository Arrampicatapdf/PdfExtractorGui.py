import os
import re
import fitz  # PyMuPDF
import pandas as pd
import streamlit as st
from tempfile import NamedTemporaryFile

def extract_data_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = "".join([page.get_text() for page in doc])
    lines = text.splitlines()

    data = {
        "Tipo de Reserva": "NUEVA RESERVA" if "NUEVA RESERVA" in text else "",
        "Número Ref": "",
        "Nombre Cliente": "",
        "Fecha Creación": "",
        "Total Pasajeros": "",
        "Fecha Servicio": "",
        "Desc. Servicio": "",
        "Servicio": "",
        "Modalidad": "",
        "Desc. Modalidad": "",
        "Idioma": "",
        "Horario": "",
        "Hotel": ""
    }

    for i, line in enumerate(lines):
        ref_match = re.search(r"Ref\s+(\d{3}-\d+)", line)
        if ref_match:
            data["Número Ref"] = ref_match.group(1)
            candidates = [lines[i + j].strip() for j in range(-2, 3) if 0 <= i + j < len(lines)]
            full_name = [p.strip() for p in candidates if re.fullmatch(r"[A-ZÁÉÍÓÚÑ\s]{5,}", p) and "ARRAMPICATA" not in p and "NUEVA" not in p]
            if full_name:
                data["Nombre Cliente"] = " ".join(full_name)
            break

    patterns = {
        "Fecha Creación": r"Fecha creación\s+(\d{2}-[A-Z]{3}\.-\d{2})",
        "Total Pasajeros": r"Total pasajeros\s+(.+?)\n",
        "Fecha Servicio": r"Fecha Servicio\s+(\d{2}-[A-Z]{3}\.-\d{2})",
        "Servicio": r"Servicio\s+([A-Z0-9]+)",
        "Desc. Servicio": r"Desc\. Servicio\s+(.+?)\n",
        "Modalidad": r"Modalidad\s+([A-Z0-9]+)",
        "Desc. Modalidad": r"Desc\. Modalidad\s+(.+?)\n",
        "Idioma": r"Idioma\s+([A-Z]{2,3})",
        "Horario": r"Horario\s+(\d{2}:\d{2})",
        "Hotel": r"hotel está vd\. alojado\.\s*-\s*(.*?)\n"
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            data[key] = match.group(1).strip()

    edad_lines, capture = [], False
    for line in lines:
        if re.search(r"\bEdad\b", line):
            capture = True
            continue
        if capture and any(stop in line for stop in ["Número confirmación", "Total pasajeros", "Horario", "Modalidad", "Idioma", "Observaciones"]):
            break
        if capture:
            edad_lines.append(line.strip())

    edades = re.findall(r"\b\d{1,3}\b", " ".join(edad_lines))
    for i, edad in enumerate(edades):
        data[f"Edad {i+1}"] = edad

    return data

def process_all_pdfs(folder_path):
    data_list = []
    for file in os.listdir(folder_path):
        if file.lower().endswith(".pdf"):
            full_path = os.path.join(folder_path, file)
            try:
                data = extract_data_from_pdf(full_path)
                data_list.append(data)
            except Exception as e:
                st.error(f"Error procesando {file}: {e}")

    return pd.DataFrame(data_list)

# Streamlit UI
st.set_page_config(page_title="Extractor de PDFs", layout="centered")
st.title("📄 Extractor de datos desde PDFs")
st.write("Selecciona una carpeta para extraer los datos de todos los PDFs")

folder_path = st.text_input("Ruta completa de la carpeta:", "")
if folder_path:
    if os.path.isdir(folder_path):
        if st.button("Procesar PDFs"):
            with st.spinner("Procesando PDFs..."):
                df = process_all_pdfs(folder_path)
                if not df.empty:
                    st.success("Proceso completado correctamente.")
                    st.dataframe(df)

                    tmp_file = NamedTemporaryFile(delete=False, suffix=".csv")
                    df.to_csv(tmp_file.name, index=False, encoding='utf-8-sig')
                    st.download_button("📥 Descargar CSV", open(tmp_file.name, "rb"), file_name="datos_extraidos.csv")
                else:
                    st.warning("No se encontraron PDFs válidos en la carpeta.")
    else:
        st.error("La ruta ingresada no es válida.")