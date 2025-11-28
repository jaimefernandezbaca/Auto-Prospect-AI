import streamlit as st
from layout.main_layout import render_main_page


def main() -> None:
    st.set_page_config(
        page_title="Auto Prospect AI",
        layout="wide",
    )
    render_main_page()


if __name__ == "__main__":
    main()
