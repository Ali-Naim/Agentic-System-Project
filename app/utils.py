from fpdf import FPDF
import os
import numpy as np
import io
from PyPDF2 import PdfReader

def generate_pdf(topic, content):
    filepath = f"/tmp/{topic}.pdf"

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, content)
    pdf.output(filepath)

    print("PDF saved at:", filepath)
    return filepath

def extract_pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = []
    for page in reader.pages:
        try:
            txt = page.extract_text() or ""
            text.append(txt)
        except:
            continue
    return "\n".join(text)