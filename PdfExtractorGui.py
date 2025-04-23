import os
import re
import fitz  # PyMuPDF
import pandas as pd
import streamlit as st
from tempfile import NamedTemporaryFile

def extract_data_from_pdf_bytes(pdf_bytes):
    with fitz.open(stream=pdf_bytes.read(), filetype="pdf") as doc:
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
        ref_match = re.search(r"Ref\s+(\d{3,4}-\d+)", line)
        if ref_match:
            data["Número Ref"] = ref_match.group(1)
            candidates = [lines[i + j].strip() for j in range(-2, 3) if 0 <= i + j < len(lines)]
            full_name = [p.strip() for p in candidates if re.fullmatch(r"[A-ZÁÉÍÓÚÑa-z\s]{5,}", p) and "ARRAMPICATA" not in p and "NUEVA" not in p and "CANCELACIÓN" not in p]
            if full_name:
                data["Nombre Cliente"] = " ".join(full_name)
            break

    patterns = {
        "Fecha Creación": r"Fecha creación\s+(\d{2}-[A-Z]{3}\.-\d{2})",
        "Total Pasajeros": r"Total pasajeros\s+(.+?)\n",
        "Fecha Servicio": r"Fecha Servicio\s+(\d{2}-[A-Z]{3}\.-\d{2})",
        "Servicio": r"Servicio\s+([A-Z0-9\- ]{3,})",
        "Desc. Servicio": r"Desc.*?Servicio\s*[:\-]?\s*(.*?)\s*(\n|Modalidad|Idioma|$)",
        "Modalidad": r"Modalidad\s+([A-Z0-9]+)",
        "Desc. Modalidad": r"Desc.*?Modalidad\s*[:\-]?\s*(.*?)\s*(\n|Idioma|$)",
        "Idioma": r"Idioma\s+([A-Z]{2,3})",
        "Horario": r"Horario\s+(\d{2}:\d{2})",
        "Hotel": r"(?:hotel est[áa] vd\. alojado|Please advise the name of your hotel)\s*-\s*(.*?)(\n|$)"
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
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

# Streamlit UI
st.set_page_config(page_title="Extractor de PDFs", layout="centered")
st.title("📄 Extractor de datos desde PDFs")
st.write("Sube uno o varios archivos PDF para extraer los datos")

uploaded_files = st.file_uploader("Subir archivos PDF", type="pdf", accept_multiple_files=True)

if uploaded_files:
    data_list = []
    with st.spinner("Procesando PDFs..."):
        for uploaded_file in uploaded_files:
            try:
                data = extract_data_from_pdf_bytes(uploaded_file)
                data_list.append(data)
            except Exception as e:
                st.error(f"Error procesando {uploaded_file.name}: {e}")

    if data_list:
        df = pd.DataFrame(data_list)
        st.success("Proceso completado correctamente.")
        st.dataframe(df)

        tmp_file = NamedTemporaryFile(delete=False, suffix=".csv")
        df.to_csv(tmp_file.name, index=False, encoding='utf-8-sig')
        st.download_button("📥 Descargar CSV", open(tmp_file.name, "rb"), file_name="datos_extraidos.csv")
    else:
        st.warning("No se pudieron extraer datos de los archivos cargados.")
