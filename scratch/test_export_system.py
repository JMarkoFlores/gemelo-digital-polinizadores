import io
import sys
from pathlib import Path
from PIL import Image
import openpyxl
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Add streamlit_app to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "streamlit_app"))
from export_helpers import (
    get_high_res_plotly_config,
    export_figure_to_600dpi,
    export_dataframe_to_excel,
)

def test_plotly_config():
    cfg = get_high_res_plotly_config("test_figure")
    assert cfg["toImageButtonOptions"]["format"] == "png"
    assert cfg["toImageButtonOptions"]["scale"] == 4
    assert cfg["toImageButtonOptions"]["height"] == 2200
    assert cfg["toImageButtonOptions"]["width"] == 3800
    print(" [PASS] get_high_res_plotly_config verification")

def test_figure_600dpi_export():
    fig = px.scatter(x=[1, 2, 3], y=[4, 5, 6], title="Test Scatter")
    raw_bytes = export_figure_to_600dpi(fig)
    assert len(raw_bytes) > 0, "Image bytes should not be empty"
    
    im = Image.open(io.BytesIO(raw_bytes))
    dpi = im.info.get("dpi")
    assert dpi is not None, "DPI metadata should be present in image header"
    assert round(dpi[0]) == 600, f"Expected 600 DPI, got {dpi[0]}"
    assert round(dpi[1]) == 600, f"Expected 600 DPI, got {dpi[1]}"
    assert im.size[0] >= 3000, f"Expected width >= 3000px, got {im.size[0]}"
    print(f" [PASS] export_figure_to_600dpi: dimensions={im.size}, dpi={dpi}")

def test_dataframe_excel_export():
    # 1. Normal DataFrame
    df = pd.DataFrame({
        "Modelo": ["Random Forest", "XGBoost", "DNN"],
        "R2": [0.9123, 0.8945, 0.8871],
        "MAE": [1.23, 1.45, 1.50],
    })
    raw_excel = export_dataframe_to_excel(df, sheet_name="Modelos", include_index=False)
    assert len(raw_excel) > 0
    wb = openpyxl.load_workbook(io.BytesIO(raw_excel))
    assert "Modelos" in wb.sheetnames
    ws = wb["Modelos"]
    assert ws.cell(row=1, column=1).value == "Modelo"
    assert ws.cell(row=2, column=1).value == "Random Forest"
    print(" [PASS] export_dataframe_to_excel (Standard DataFrame)")

    # 2. Styler DataFrame
    styler = df.style.format({"R2": "{:.2f}", "MAE": "{:.1f}"})
    raw_styler_excel = export_dataframe_to_excel(styler, sheet_name="Modelos_Styled", include_index=False)
    assert len(raw_styler_excel) > 0
    wb_s = openpyxl.load_workbook(io.BytesIO(raw_styler_excel))
    assert "Modelos_Styled" in wb_s.sheetnames
    print(" [PASS] export_dataframe_to_excel (Pandas Styler)")

    # 3. DataFrame with index (like describe or Nemenyi matrix)
    desc = df.describe()
    raw_desc_excel = export_dataframe_to_excel(desc, sheet_name="Stats", include_index=True)
    assert len(raw_desc_excel) > 0
    wb_d = openpyxl.load_workbook(io.BytesIO(raw_desc_excel))
    assert "Stats" in wb_d.sheetnames
    print(" [PASS] export_dataframe_to_excel (With Index)")

def test_app_imports_and_structure():
    import app
    assert hasattr(app, "render_high_res_chart")
    assert hasattr(app, "render_table_with_excel")
    
    import robust_tests
    assert hasattr(robust_tests, "render_high_res_chart")
    assert hasattr(robust_tests, "render_table_with_excel")
    print(" [PASS] app and robust_tests imports & integration")

if __name__ == "__main__":
    test_plotly_config()
    test_figure_600dpi_export()
    test_dataframe_excel_export()
    test_app_imports_and_structure()
    print("\nALL VERIFICATION TESTS COMPLETED SUCCESSFULLY!")
