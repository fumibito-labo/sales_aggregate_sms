import pandas as pd
import streamlit as st

import matplotlib.pyplot as plt


# 集計条件用パラメータ設定
# 全体
target_payment_all = [
    '引落',
    '現金',
    'クレジット',
    '滞納（コンビニ）',
    '払先未定（コンビニ）',
    'CTC',
    '債権回収',
    '織機給与天引き'
]

# 集計対象外
target_excluding_payment = [
    '振込',
    'その他',
    'アプリデモ'
]

# メインターゲット
target_payment_sms = [
    '引落',
    '現金',
    'クレジット',
    '滞納（コンビニ）',
    '払先未定（コンビニ）',
    '債権回収'
]

# 織機給与天引き
target_payment_shokki = [
    '織機給与天引き'
]

# CTC
target_payment_ctc = [
    'CTC'
]


def get_dataframe(file):
    return pd.read_csv(file, encoding='cp932')


def shokki_overwrite(df):
    _df = df
    _df['MEI_NAME_V'] = '織機給与天引き'
    return _df


def calc_aggregation(df):
    return pd.pivot_table(df, index=['MEI_NAME_V', 'HEAD_CD', 'SUB_CD', 'ACCOUNT_CD'], values='SEIKYU_TOTAL', aggfunc='sum').reset_index()


# def query_filtering(df, conditions):
#     filtered = f'MEI_NAME_V in @{conditions}'
#     return df.query(df, filtered)


def main():
    """
    Streamlit Application
    :return:
    """

    st.title('Sales Aggregation for SMS')
    with st.expander('集計条件について'):
        markdown = """
        1. 科目コードが 「9999」以外
        2. 支払サイクルが　「1」もしくは「0」 ※2以上は前受金計上扱い
        3. 支払手段が「振込」「その他」「アプリデモ」ではない 
        """
        st.markdown(markdown)

    st.sidebar.title('File Uploader')

    sms_uploaded_file = st.sidebar.file_uploader('SMS請求データを選択してください(.csv)', type='csv')
    shokki_uploaded_file = st.sidebar.file_uploader('織機請求データを選択してください(.csv)', type='csv')
    aggregation_btn = st.sidebar.button('集計')

    # サイドバーの集計ボタンを押した際の処理設定
    if aggregation_btn:

        # SMS売上の読み込み
        if sms_uploaded_file is not None:
            sms_df = get_dataframe(sms_uploaded_file)

        # 織機売上の読み込み
        if shokki_uploaded_file is not None:
            shokki_df = get_dataframe(shokki_uploaded_file)
            shokki_df = shokki_overwrite(shokki_df)

        # 前準備
        _df = pd.concat([sms_df, shokki_df])
        _df = _df.iloc[:,:-2]
        _df = _df.astype({'HEAD_CD': 'str', 'SUB_CD': 'str'})
        _df['ACCOUNT_CD'] = _df['HEAD_CD'] + '-' + _df['SUB_CD']
        _df.loc[_df['HEAD_CD'] == '5330', 'ACCOUNT_CD'] = '5330'

        # 集計条件の適用
        _df_subset_all = _df.query('MEI_NAME_V not in @target_excluding_payment')
        _df_subset = _df_subset_all.query('HEAD_CD != "9999"')
        _df_target = _df_subset.query('KAI_CYCLE <= 1')


        # 出力区分ごとの集計
        df_sms = _df_target.query('MEI_NAME_V in @target_payment_sms')
        df_shokki = _df_target.query('MEI_NAME_V in @target_payment_shokki')
        df_ctc = _df_target.query('MEI_NAME_V in @target_payment_ctc')

        # パラメータ取得
        total_sales = _df_target['SEIKYU_TOTAL'].sum()
        sms_total = df_sms['SEIKYU_TOTAL'].sum()
        shokki_total = df_shokki['SEIKYU_TOTAL'].sum()
        ctc_total = df_ctc['SEIKYU_TOTAL'].sum()

        st.metric('請求額',f'{total_sales:,} 円')
        st.write('---')
        col1, col2, col3 = st.columns(3)
        col1.metric('SMS：', f'{sms_total:,}円')
        col2.metric('織機：', f'{shokki_total:,}円')
        col3.metric('CTC：', f'{ctc_total:,}円')





        res_sms = calc_aggregation(df_sms)
        res_shokki = calc_aggregation(df_shokki)
        res_ctc = calc_aggregation(df_ctc)




        # 前受金対象分の切り出し
        df_advance_recieved = _df_subset.query('KAI_CYCLE > 1')
        res_advance = calc_aggregation(df_advance_recieved)






if __name__ == "__main__":
    main()
