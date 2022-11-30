import altair as alt
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


@st.cache
def load_file(sms, shokki):
    # ２つのファイルが読み込まれた時点でデータ連結処理と支払手段の抽出を実行
    if sms is not None and shokki is not None:
        # SMS請求ファイルの読込
        sms_df = get_dataframe(sms)

        # 織機天引きファイルの読込
        shokki_df = get_dataframe(shokki)
        # 支払方法 -> 織機給与天引へ　書き換え
        shokki_df = shokki_overwrite(shokki_df)

        # 前準備（科目コードカラム追加＆データ連結
        df_result = concat_df(sms_df, shokki_df)
        return df_result


def main():
    """
    Streamlit Application
    :return:
    """

    # ヘッダーセクション（ファイルアップロード ）
    st.title('Sales Aggregation App for SMS')

    # sidebar : ファイルアップローダー
    side_header = st.sidebar.container()
    side_header.write('集計用のファイルをアップロードしてください')
    head_col1, head_col2 = side_header.columns(2)

    sms_uploaded_file = head_col1.file_uploader('SMS請求金額', type='csv')
    shokki_uploaded_file = head_col2.file_uploader('織機給与天引請求額', type='csv')

    # ファイルの結合 と 科目コード情報カラムの追加
    concat_d = load_file(sms_uploaded_file, shokki_uploaded_file)

    # sidebar: 条件選択枠の設置
    side_selector = st.sidebar.container()

    if concat_d is not None:

        # 全データから 支払方法の一覧を取得
        options_method = get_payment_method(concat_d)
        # デフォルトの支払方法をリストとして作成
        default_select = [i for i in options_method if i not in target_excluding_payment]

        # 注意書きメモ表示
        with side_selector.expander('⚠ 支払手段の選択について'):
            markdown = """
            SMSとは別で請求しているものや、請求対象外のものは除外
            
            例：振込/アプリデモ/貸倒処理済み/口座封鎖/その他
            """
            st.markdown(markdown)
        # フィルター条件のマルチセレクトフィールド
        options = side_selector.multiselect(
            '対象の支払手段を選択してください',
            options_method,
            default_select
        )

        # 追加条件（チェックボックス)
        col_btn1, col_btn2 = side_selector.columns(2)
        filter_advance_recieved = col_btn1.checkbox('年払請求を含')
        filter_account_code = col_btn2.checkbox('売上対象外を含める')

        # 抽出条件の分岐
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

        # メインセクション
        container_main = st.container()
        container_main.write('---')
        # Data Preview
        container_main.header('Data Preview')
        container_main.write('適宜データを確認してください')

        # Previewデータの表示
        container_main.dataframe(df_target)

        # PreviewデータのCSVファイル作成
        output_preview_data = convert_df_to_csv(df_target)

        # サマリーセクション
        container_summary = st.container()
        container_summary.write('---')
        container_summary.subheader('データサマリ')
        main_col1, main_col2 = container_summary.columns(2)

        # 発生総額表示
        seikyu_total = df_target['SEIKYU_TOTAL'].sum()
        main_col1.metric('対象金額計', f'{seikyu_total:,}円')

        # 請求件数表示
        customer_total = df_target['INPUT_NO'].nunique()
        main_col1.metric('請求顧客数', f'{customer_total:,}件')

        # 平均請求額表示
        average_price = seikyu_total / customer_total
        main_col1.metric('平均単価', f'{average_price:,.1f}円')

        # 支払手段ごとの金額集計
        agg_payment_method = df_target[['MEI_NAME_V', 'ACCOUNT_CD', 'SEIKYU_TOTAL']]
        group_agg_payment = pd.pivot_table(agg_payment_method, index=['MEI_NAME_V'],
                                           values='SEIKYU_TOTAL', aggfunc=sum).reset_index()
        main_col2.dataframe(group_agg_payment)

        # グラフ化
        graph_data = group_agg_payment[['MEI_NAME_V', 'SEIKYU_TOTAL']]
        base = alt.Chart(graph_data)
        chart = base.mark_bar().encode(
            y=alt.Y('SEIKYU_TOTAL',
                    title='金額'
                    ),
            x=alt.X('MEI_NAME_V', title='支払方法'),
            tooltip=['SEIKYU_TOTAL']
        ).interactive().properties(height=600, title='支払手段別請求額')
        # グラフ表示
        container_summary.altair_chart(chart, use_container_width=True)

        # Sidebar: 結果出力セクション
        sidebar_result = st.sidebar.container()
        sidebar_result.write('---')
        sidebar_result.subheader('結果出力')
        res_col1, res_col2 = sidebar_result.columns(2)

        # 出力データの作成
        # 結果データ
        group_agg_target = calc_aggregation(df_target)
        output_result_group = convert_df_to_csv(group_agg_target)

        # 前受金計上金額の条件取得
        advance_subset = concat_d.query('MEI_NAME_V in @options')
        advance_subset = advance_subset.query('HEAD_CD != "9999"')
        advance_df_target = advance_subset.query('KAI_CYCLE > 1')

        # 科目合計
        res_advance = calc_aggregation(advance_df_target)
        output_advance_group = convert_df_to_csv(res_advance)

        # ダウンロードボタン
        res_col1.download_button(
            label='個人サービス別データ',
            data=output_preview_data,
            file_name='res_all.csv',
            mime='text/csv'
        )

        res_col2.download_button(
            label='科目別集計データ　　',
            data=output_result_group,
            file_name='res.csv',
            mime='text/csv'
        )

        res_col1.download_button(
            label='仕訳作成用データ　　',
            data='',
            file_name='',
            mime='text/csv'
        )

        res_col2.download_button(
            label='前受収益計上用データ',
            data=output_advance_group,
            file_name='res_advance.csv',
            mime='text/csv'
        )


if __name__ == "__main__":
    main()
