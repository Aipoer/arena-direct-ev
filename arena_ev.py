import streamlit as st
from functools import lru_cache

st.set_page_config(page_title="アリーナダイレクト期待報酬ツール")

# UI - 入力セクション
st.title("アリーナダイレクト 期待報酬シミュレーター")

# 勝率
win_rate = st.slider("勝率", min_value=0.0, max_value=1.0, step=0.01, value=0.6)

# 費用設定
with st.expander("◼ コスト設定", expanded=True):
    entry_cost = st.number_input("参加費（ジェム）", value=8000)
    box_price_dollar = st.number_input("BOXの価格（ドル）", value=360.0)
    jem_price_dollar = st.number_input("ジェム単価（ドル/ジェム）", value=99.99 / 20000, format="%.6f")

# 報酬設定（デフォルト値）
default_rewards = {
    0: (0, 0.0, 0),
    1: (0, 0.0, 0),
    2: (0, 0.0, 0),
    3: (3600, 0.0, 0),
    4: (7200, 0.0, 0),
    5: (10800, 0.0, 0),
    6: (14400, 0.0, 0),
    7: (0, 1.0, 0),
}

with st.expander("◼ 勝利数ごとの報酬入力（ジェム／BOX／パック）", expanded=False):
    reward_table = {}
    box_table = {}
    pack_table = {}

    for i in range(0, 8):
        st.markdown(f"**{i}勝**")
        col1, col2, col3 = st.columns(3)
        with col1:
            reward_table[i] = st.number_input(f"ジェム({i}勝)", key=f"gem_{i}", value=default_rewards[i][0])
        with col2:
            box_table[i] = st.number_input(f"BOX({i}勝)", key=f"box_{i}", value=default_rewards[i][1], step=0.1)
        with col3:
            pack_table[i] = st.number_input(f"パック({i}勝)", key=f"pack_{i}", value=default_rewards[i][2])

# メモ化再帰で確率分布を計算
@lru_cache(None)
def dp(wins, losses, p):
    if losses >= 2:
        return {wins: 1.0}
    if wins >= 7:
        return {7: 1.0}

    result = {}
    win_branch = dp(wins + 1, losses, p)
    lose_branch = dp(wins, losses + 1, p)

    for k, v in win_branch.items():
        result[k] = result.get(k, 0) + v * p
    for k, v in lose_branch.items():
        result[k] = result.get(k, 0) + v * (1 - p)
    return result

# 計算
with st.spinner("計算中..."):
    distribution = dp(0, 0, win_rate)

    expected_jem = sum(reward_table.get(wins, 0) * prob for wins, prob in distribution.items())
    expected_box = sum(box_table.get(wins, 0) * prob for wins, prob in distribution.items())

    expected_box_jem_equivalent = expected_box * (box_price_dollar / jem_price_dollar)
    total_expected_reward_jem = expected_jem + expected_box_jem_equivalent

    net_jem = total_expected_reward_jem - entry_cost
    expected_dollar_value = total_expected_reward_jem * jem_price_dollar

    st.subheader("◼ 期待報酬")
    st.write(f"ジェム: {expected_jem:.2f} ジェム")
    st.write(f"BOX: {expected_box:.2f} 箱（{expected_box * box_price_dollar:.2f}ドル ≒ {expected_box_jem_equivalent:.2f}ジェム相当）")

    st.subheader("◼ 期待利益")
    st.write(f"ジェム換算での期待利益: {net_jem:.2f} ジェム")
    st.write(f"ドル換算での期待利益: ${expected_dollar_value:.2f}")

    st.subheader("◼ 勝利数ごとの確率")
    for wins in sorted(distribution.keys()):
        st.write(f"{wins}勝：{distribution[wins] * 100:.2f}%")
