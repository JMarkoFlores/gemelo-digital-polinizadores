from streamlit.testing.v1 import AppTest

def test_underscore_key():
    code = """
import streamlit as st
if "_my_key" not in st.session_state:
    st.session_state["_my_key"] = "initial"
st.write(f"val={st.session_state['_my_key']}")
if st.button("Click"):
    st.session_state["_my_key"] = "clicked"
"""
    at = AppTest.from_string(code).run()
    print("Run 1:", at.markdown[0].value)
    at.button[0].click().run()
    print("Run 2:", at.markdown[0].value)
    print("Session state keys:", list(at.session_state.keys()))

if __name__ == "__main__":
    test_underscore_key()
