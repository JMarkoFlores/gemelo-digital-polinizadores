with open('streamlit_app/app.py', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines[1060:1220], start=1061):
    print(f"{i}: {line.rstrip()}")
