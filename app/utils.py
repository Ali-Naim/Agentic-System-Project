from fpdf import FPDF
import os

def generate_pdf(topic, content):
    filepath = f"/tmp/{topic}.pdf"

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, content)
    pdf.output(filepath)

    print("PDF saved at:", filepath)
    return filepath