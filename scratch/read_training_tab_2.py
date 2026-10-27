with open('streamlit_app/app.py', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines[920:1060], start=921):
    print(f"{i}: {line.rstrip()}")
