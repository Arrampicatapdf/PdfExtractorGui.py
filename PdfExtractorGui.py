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
        "Hotel": "",
        "Contacto": ""
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

    for i, line in enumerate(lines):
        if "Total pasajeros" in line:
            match = re.search(r"Total pasajeros\s*[:\-\)]?\s*(\d+\s*Pax.*?)\s*$", line)
            if match:
                data["Total Pasajeros"] = match.group(1).strip()
            break

    patterns = {
        "Fecha Creación": r"Fecha creación\s*[:\-\)]?\s*(\d{2}-[A-Z]{3,4}\.?-\d{2})",
        "Fecha Servicio": r"Fecha Servicio\s*[:\-\)]?\s*(\d{2}-[A-Z]{3,4}\.?-\d{2})",
        "Desc. Servicio": r"Desc.*?Servicio\s*[:\-\)]?\s*(.*?)\s*(\n|Modalidad|Idioma|$)",
        "Modalidad": r"Modalidad\s*[:\-\)]?\s*([A-Z0-9]+)",
        "Desc. Modalidad": r"Desc.*?Modalidad\s*[:\-\)]?\s*(.*?)\s*(\n|Idioma|$)",
        "Idioma": r"Idioma\s*[:\-\)]?\s*([A-Z]{2,3})",
        "Horario": r"Horario\s*[:\-\)]?\s*(\d{2}:\d{2})"
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data[key] = match.group(1).strip()

    for line in lines:
        if line.strip().startswith("Servicio"):
            service_match = re.search(r"Servicio\s*[:\-\)]?\s*([A-Z0-9]{6,})", line)
            if service_match:
                data["Servicio"] = service_match.group(1).strip()
            break

    hotel = ""
    for pattern in [
        r"indique en qué hotel está(?:\s*vd\.)?\s*alojado\s*[-:]?\s*(.*?)\s*(\n|$)",
        r"por favor indique o hotel no qual está alojado\s*[-:]?\s*(.*?)\s*(\n|$)",
        r"vd\.?\s*alojado\s*[-:]?\s*(.*?)\s*(\n|$)",
        r"please advise the name of your hotel\s*[-:]?\s*(.*?)\s*(\n|$)"
    ]:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            hotel = match.group(1).strip(" :-•.")
            break

    if not hotel:
        for line in reversed(lines[-6:]):
            if "hotel" in line.lower():
                after = line.lower().split("hotel")[-1].strip(" :-•.\n")
                if len(after) > 2:
                    hotel = after.title()
                    break

    data["Hotel"] = hotel

    contacto = ""
    joined = " ".join(lines[-15:])
    match = re.search(r"(?:incluido|incluyendo|including).*?(?:internacional|international).*?([+\d][\d\s\-]{6,})", joined, re.IGNORECASE)
    if match:
        number = match.group(1).strip().replace(" ", "").replace("-", "")
        if number.startswith("00"):
            number = "+" + number[2:]
        contacto = number

    data["Contacto"] = contacto

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

st.set_page_config(page_title="Extractor de PDFs", layout="centered")
st.title("📄 Extractor de datos desde PDFs")
st.write("Sube uno o varios archivos PDF para extraer los datos - Arrampicata")

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
