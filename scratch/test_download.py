from streamlit.testing.v1 import AppTest

script = """
import streamlit as st

if 'calls' not in st.session_state:
    st.session_state['calls'] = 0

def my_data():
    st.session_state['calls'] += 1
    return b'data content'

st.download_button('Click me', data=my_data, file_name='file.txt', key='btn')
"""

at = AppTest.from_string(script, default_timeout=15).run()
print('Initial calls:', at.session_state['calls'])
at.download_button(key='btn').click().run()
print('After click calls:', at.session_state['calls'])
