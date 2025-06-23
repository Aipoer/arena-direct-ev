import streamlit as st
from functools import lru_cache

# 単位ジェムあたりのドル換算レート
dollar_per_gem = 99.99 / 20000

# 勝利数ごとの報酬（ジェム）
reward_table = {
    3: 3600,
    4: 7200,
    5: 10800,
    6: 14400,
    7: 360 / dollar_per_gem  # BOX報酬をジェム換算
}

# 参加費
entry_cost = 8000

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

# Streamlitアプリ
st.title("アリーナダイレクト 期待値計算ツール")

win_rate = st.slider("勝率 (p)", min_value=0.01, max_value=0.99, value=0.6, step=0.01)

with st.spinner("計算中..."):
    distribution = dp(0, 0, win_rate)

    expected_reward = sum(reward_table.get(wins, 0) * prob for wins, prob in distribution.items())
    net_gain = expected_reward - entry_cost
    expected_dollar_value = expected_reward * dollar_per_gem
    net_dollar_gain = net_gain * dollar_per_gem

    st.subheader("結果")
    st.write(f"期待報酬：{expected_reward:.2f} ジェム")
    st.write(f"期待利益：{net_gain:.2f} ジェム")
    st.write(f"期待値（ドル換算）：{expected_dollar_value:.2f} USD")
    st.write(f"期待利益（ドル換算）：{net_dollar_gain:.2f} USD")

    st.subheader("勝利数ごとの確率")
    for wins in sorted(distribution.keys()):
        st.write(f"{wins}勝：{distribution[wins] * 100:.2f}%")
