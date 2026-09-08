import io
import pandas as pd
from datetime import datetime

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
except ImportError:
    pass

try:
    from docx import Document
except ImportError:
    pass


def generate_excel_report(metrics_df: pd.DataFrame, best_model: str) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        metrics_df.to_excel(writer, sheet_name='Resultados_Modelos', index=False)
        
        info_df = pd.DataFrame([
            {"Propiedad": "Fecha de reporte", "Valor": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
            {"Propiedad": "Mejor Modelo Seleccionado", "Valor": best_model},
        ])
        info_df.to_excel(writer, sheet_name='Metadatos', index=False)
    
    return output.getvalue()


def generate_word_report(metrics_df: pd.DataFrame, best_model: str) -> bytes:
    doc = Document()
    doc.add_heading('Reporte de Evaluación de Modelos IA', 0)
    
    doc.add_paragraph(f'Fecha de generación: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    doc.add_paragraph(f'El mejor modelo seleccionado fue: {best_model}')
    
    doc.add_heading('Métricas por Modelo', level=1)
    
    table = doc.add_table(rows=1, cols=len(metrics_df.columns))
    table.style = 'Table Grid'
    hdr_cells = table.rows[0].cells
    for i, col in enumerate(metrics_df.columns):
        hdr_cells[i].text = str(col)
        
    for index, row in metrics_df.iterrows():
        row_cells = table.add_row().cells
        for i, val in enumerate(row):
            if isinstance(val, float):
                row_cells[i].text = f"{val:.4f}"
            else:
                row_cells[i].text = str(val)
                
    output = io.BytesIO()
    doc.save(output)
    return output.getvalue()


def generate_pdf_report(metrics_df: pd.DataFrame, best_model: str) -> bytes:
    output = io.BytesIO()
    c = canvas.Canvas(output, pagesize=letter)
    width, height = letter
    
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "Reporte de Evaluación de Modelos IA")
    
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 80, f'Fecha: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    c.drawString(50, height - 100, f'Mejor modelo seleccionado: {best_model}')
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 140, "Resumen de Métricas (Media general por modelo)")
    
    y = height - 170
    c.setFont("Helvetica", 10)
    
    # Header
    headers = list(metrics_df.columns)
    x_pos = [50, 200, 300, 400, 500]
    for i, h in enumerate(headers[:5]):
        c.drawString(x_pos[i] if i < len(x_pos) else 500, y, str(h))
    
    y -= 20
    # Rows
    for _, row in metrics_df.iterrows():
        for i, val in enumerate(row[:5]):
            v_str = f"{val:.4f}" if isinstance(val, float) else str(val)
            c.drawString(x_pos[i] if i < len(x_pos) else 500, y, v_str)
        y -= 20
        if y < 50:
            c.showPage()
            y = height - 50

    c.save()
    return output.getvalue()
