with open('streamlit_app/app.py', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines[760:920], start=761):
    print(f"{i}: {line.rstrip()}")
