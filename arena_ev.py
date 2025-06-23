import streamlit as st
from functools import lru_cache
import pandas as pd

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

    expected_jem_per_try = sum(reward_table.get(wins, 0) * prob for wins, prob in distribution.items())
    expected_box_per_try = sum(box_table.get(wins, 0) * prob for wins, prob in distribution.items())
    expected_box_jem_equivalent = expected_box_per_try * (box_price_dollar / jem_price_dollar)
    total_expected_reward_jem = expected_jem_per_try + expected_box_jem_equivalent
    entry_cost_dollar = entry_cost * jem_price_dollar
    net_jem = total_expected_reward_jem - entry_cost
    net_dollar = (total_expected_reward_jem * jem_price_dollar) - entry_cost_dollar

    st.subheader("◼ 期待報酬")
    st.write(f"ジェム: {expected_jem_per_try:.2f} ジェム")
    st.write(f"BOX: {expected_box_per_try:.2f} 箱（{expected_box_per_try * box_price_dollar:.2f}ドル ≒ {expected_box_jem_equivalent:.2f}ジェム相当）")

    st.subheader("◼ 期待利益")
    st.write(f"ジェム換算での期待利益: {net_jem:.2f} ジェム")
    st.write(f"ドル換算での期待利益: ${net_dollar:.2f}")

    st.subheader("◼ シミュレーション：BOXが出るまでの試行回数別パターン")
    sim_box_try = st.number_input("最大試行回数", min_value=1, value=10)
    box_prob = distribution.get(7, 0)
    box_miss_prob = 1 - box_prob

    try_data = {
        "回数": [],
        "BOX獲得（確率）": [],
        "BOX未獲得（確率）": [],
        "合計": [],
        "期待ジェム": [],
        "期待BOX": [],
        "期待ドル": []
    }
    for i in range(1, sim_box_try + 1):
        prob_success_on_i = box_miss_prob ** (i - 1) * box_prob
        prob_fail_all = box_miss_prob ** i

        jem_if_success = expected_jem_per_try * i
        box_if_success = expected_box_per_try * i
        dollar_if_success = (jem_if_success + box_if_success * (box_price_dollar / jem_price_dollar)) * jem_price_dollar

        jem_if_fail = expected_jem_per_try * i
        box_if_fail = expected_box_per_try * i
        dollar_if_fail = (jem_if_fail + box_if_fail * (box_price_dollar / jem_price_dollar)) * jem_price_dollar

        total_jem = prob_success_on_i * jem_if_success + prob_fail_all * jem_if_fail
        total_box = prob_success_on_i * box_if_success + prob_fail_all * box_if_fail
        total_dollar = prob_success_on_i * dollar_if_success + prob_fail_all * dollar_if_fail

        try_data["回数"].append(i)
        try_data["BOX獲得（確率）"].append(prob_success_on_i)
        try_data["BOX未獲得（確率）"].append(prob_fail_all)
        try_data["合計"].append(prob_success_on_i + prob_fail_all)
        try_data["期待ジェム"].append(total_jem)
        try_data["期待BOX"].append(total_box)
        try_data["期待ドル"].append(total_dollar)

    try_df = pd.DataFrame(try_data)
    st.dataframe(try_df, use_container_width=True)
