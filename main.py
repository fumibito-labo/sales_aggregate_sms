import pandas as pd
import streamlit as st


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
    '織機給与天引き',
    '貸倒処理待ち'
]

# 集計対象外
target_excluding_payment = [
    '振込',
    'その他',
    'アプリデモ',
    '口座閉鎖'
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


@st.cache
def get_payment_method(df):
    payment_list = df['MEI_NAME_V'].unique().tolist()
    return payment_list


@st.cache
def concat_df(df1, df2):
    _df = pd.concat([df1, df2])
    # _df = _df.iloc[:, :-2]
    _df = _df.astype({'HEAD_CD': 'str', 'SUB_CD': 'str'})
    _df['ACCOUNT_CD'] = _df['HEAD_CD'] + '-' + _df['SUB_CD']
    _df.loc[_df['HEAD_CD'] == '5330', 'ACCOUNT_CD'] = '5330'
    return _df


def calc_aggregation(df):
    return pd.pivot_table(df, index=['MEI_NAME_V', 'HEAD_CD', 'SUB_CD', 'ACCOUNT_CD'],
                          values='SEIKYU_TOTAL', aggfunc='sum').reset_index()


@st.cache
def convert_df_to_csv(df, index=True):
    return df.to_csv().encode('cp932')


def main():
    """
    Streamlit Application
    :return:
    """

    # ヘッダーセクション（ファイルアップロード ）
    st.title('Sales Aggregation App for SMS')

    # ファイルアップローダー
    upload_container = st.container()
    upload_container.write('集計用のファイルをアップロードしてください')
    head_col1, head_col2 = upload_container.columns(2)

    sms_uploaded_file = head_col1.file_uploader('file: keiri_sms_after_detail', type='csv')
    shokki_uploaded_file = head_col2.file_uploader('file: keiri_shokki_after_detail', type='csv')

    # SMS売上の読み込み
    if sms_uploaded_file is not None:
        sms_df = get_dataframe(sms_uploaded_file)

    # 織機売上の読み込み
    if shokki_uploaded_file is not None:
        shokki_df = get_dataframe(shokki_uploaded_file)
        shokki_df = shokki_overwrite(shokki_df)

    # セクション 条件
    container_selector = st.container()

    # ２つのファイルが読み込まれた時点でデータ連結処理と支払手段の抽出を実行
    if sms_uploaded_file is not None and shokki_uploaded_file is not None:

        # 前準備（科目コードカラム追加＆データ連結
        concat_d = concat_df(sms_df, shokki_df)

        # 連結データから、支払手段のリストを取得
        options_method = get_payment_method(concat_d)
        default_select = [i for i in options_method if i not in target_excluding_payment]

        with container_selector.expander('支払手段の選択について'):
            markdown = """
            「振込」「アプリデモ」「貸倒処理済み」「口座封鎖」「その他」は除外
            """
            st.markdown(markdown)

        options = container_selector.multiselect(
            '対象の支払手段を選択してください',
            options_method,
            default_select
        )

        # 表示ボタン（トリガー）
        col_btn1, col_btn2, col_btn3 = container_selector.columns(3)
        filter_advance_recieved = col_btn2.checkbox('年払いを含める')
        filter_account_code = col_btn3.checkbox('売上対象外を含める')
        aggregation_btn = col_btn1.button('データ表示')


        # 集計ボタンを押した際の処理設定
        if aggregation_btn:
            st.session_state.key = 3
            st.write('データ取得')

            try:
                st.text(f'state:{st.session_state.key}')
            except AttributeError:
                # st.session_state.state に値が保存されていないときのみ最初の読込と判断して初期化
                st.session_state.key = 1

            # すべてのデータを含めるパターン
            if filter_advance_recieved and filter_account_code:
                df_target = concat_d.query('MEI_NAME_V in @options')

            # 年払い除外（売上全項目出力）
            elif filter_advance_recieved and not filter_account_code:
                df_subset = concat_d.query('MEI_NAME_V in @options')
                df_target = df_subset.query('KAI_CYCLE <= 1')

            # 売上対象外を除く（年払含む）
            elif not filter_advance_recieved and filter_account_code:
                df_subset = concat_d.query('MEI_NAME_V in @options')
                df_target = df_subset.query('HEAD_CD != "9999"')

            else:
                df_subset = concat_d.query('MEI_NAME_V in @options')
                df_subset = df_subset.query('HEAD_CD != "9999"')
                df_target = df_subset.query('KAI_CYCLE <= 1')


            container_main = st.container()
            container_main.write('---')
            container_main.header('Data Preview')
            container_main.write('適宜データを確認してください')
            # Data Preview
            container_main.dataframe(df_target)
            outout_preview_data = convert_df_to_csv(df_target)
            container_main.download_button(
                label='Download Data',
                data=outout_preview_data,
                file_name='detail_all.csv',
                mime='text/csv'
            )

            # サマリーセクション
            container_summary = st.container()
            container_summary.write('---')
            container_summary.subheader('データサマリ')
            main_col1, main_col2 = container_summary.columns(2)

            # 発生総額の取得
            seikyu_total = df_target['SEIKYU_TOTAL'].sum()
            main_col1.metric('対象金額計', f'{seikyu_total:,}円')

            # 請求件数
            customer_total = df_target['INPUT_NO'].nunique()
            main_col1.metric('請求顧客数', f'{customer_total:,}件')

            # 平均請求額
            average_price = seikyu_total / customer_total
            main_col1.metric('平均単価', f'{average_price:,.1f}円')

            # 支払手段ごとの金額集計
            agg_payment_method = df_target[['MEI_NAME_V', 'ACCOUNT_CD', 'SEIKYU_TOTAL']]
            group_agg_payment = pd.pivot_table(agg_payment_method, index=['MEI_NAME_V'],
                                               values='SEIKYU_TOTAL', aggfunc=sum).reset_index()
            main_col2.dataframe(group_agg_payment)



            # 結果出力セクション
            container_result = st.container()
            container_result.write('---')
            container_result.subheader('結果出力')

            res_col1, res_col2 = container_result.columns(2)
            group_agg_target = calc_aggregation(df_target)
            output_result_group = convert_df_to_csv(group_agg_target)
            res_col1.write('支払手段別科目合計結果')
            res_col2.download_button(
                label='Download Data',
                data=output_result_group,
                file_name='result.csv',
                mime='text/csv'
            )

            # 前受金計上金額の条件取得
            advance_subset = concat_d.query('MEI_NAME_V in @options')
            advance_subset = advance_subset.query('HEAD_CD != "9999"')
            advance_df_target = advance_subset.query('KAI_CYCLE > 1')
            # 科目合計
            res_advance = calc_aggregation(advance_df_target)
            output_advance_group = convert_df_to_csv(res_advance)
            res_col1.write('前受金')
            res_col2.download_button(
                label='Download Data',
                data=output_advance_group,
                file_name='res_advance.csv',
                mime='text/csv'
            )


if __name__ == "__main__":
    main()
