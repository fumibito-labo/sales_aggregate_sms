import pandas as pd
import streamlit as st


def get_dataframe(file):
    return pd.read_csv(file, encoding='cp932')


def main():
    """
    Streamlit Application
    :return:
    """

    st.title('Sales Aggregation for SMS')
    sms_uploaded_file = st.file_uploader('SMS請求データを選択してください(.csv)', type='csv')
    shokki_uploaded_file = st.file_uploader('織機請求データを選択してください(.csv)', type='csv')

    if sms_uploaded_file is not None:
        sms_df = get_dataframe(sms_uploaded_file)
        st.dataframe(sms_df)




if __name__ == "__main__":
    main()
