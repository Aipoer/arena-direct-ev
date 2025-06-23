import streamlit as st
from functools import lru_cache
import pandas as pd

st.set_page_config(page_title="アリーナダイレクト期待報酬ツール")
st.title("アリーナダイレクト 期待報酬シミュレーター")

# 入力
win_rate = st.slider("勝率", 0.0, 1.0, 0.6, 0.01)

with st.expander("◼ コスト設定", expanded=True):
    entry_cost = st.number_input("参加費（ジェム）", value=8000)
    box_price_dollar = st.number_input("BOXの価格（ドル）", value=360.0)
    jem_price_dollar = st.number_input("ジェム単価（ドル/ジェム）", value=99.99/20000, format="%.6f")

# デフォルト報酬設定
default_rewards = {i: 0 for i in range(8)}
default_boxes = {i: 0.0 for i in range(8)}
default_rewards.update({3:3600,4:7200,5:10800,6:14400})
default_boxes[7] = 1.0

with st.expander("◼ 勝利数ごとの報酬入力（ジェム／BOX）", expanded=False):
    reward_table = {}
    box_table = {}
    for i in range(8):
        col1, col2 = st.columns(2)
        with col1:
            reward_table[i] = st.number_input(f"ジェム({i}勝)", key=f"gem_{i}", value=default_rewards[i])
        with col2:
            box_table[i] = st.number_input(f"BOX({i}勝)", key=f"box_{i}", value=default_boxes[i], step=0.1)

# 勝利数分布計算
def dp(wins, losses, p, memo={}):
    if (wins,losses) in memo:
        return memo[(wins,losses)]
    if losses >= 2:
        return {wins: 1.0}
    if wins >= 7:
        return {7: 1.0}
    res = {}
    for win_inc, prob in ((1, p), (0, 1-p)):
        nw, nl = wins + win_inc, losses + (win_inc == 0)
        for k, v in dp(nw, nl, p, memo).items():
            res[k] = res.get(k, 0) + v * prob
    memo[(wins,losses)] = res
    return res

dist = dp(0, 0, win_rate)

# 基本期待値（1回あたり）
# 期待収入
exp_jem = sum(reward_table[k] * v for k, v in dist.items())
exp_box = sum(box_table[k] * v for k, v in dist.items())
# ボックスをジェム換算した期待
exp_box_jem = exp_box * (box_price_dollar / jem_price_dollar)
# 期待収入合計（ジェム・ドル）
rev_jem = exp_jem + exp_box_jem
rev_dollar = exp_jem * jem_price_dollar + exp_box * box_price_dollar
# 純期待利益
net_jem = rev_jem - entry_cost
net_dollar = rev_dollar - entry_cost * jem_price_dollar

st.subheader("◼ 基本期待値（1回あたり）")
st.write(f"期待収入: {exp_jem:.2f} ジェム + {exp_box:.2f} 箱 (~{exp_box_jem:.2f} ジェム相当)")
st.write(f"期待収入(ドル): ${rev_dollar:.2f}")
st.write(f"参加費: {entry_cost} ジェム (~${entry_cost * jem_price_dollar:.2f})")
st.write(f"純期待利益: {net_jem:.2f} ジェム (~${net_dollar:.2f})")

# シミュレーション: 7勝達成まで or 最大試行まで
st.subheader("◼ シミュレーション: 7勝達成まで or 最大試行まで")
max_trials = st.number_input("最大試行回数", 1, 100, 10)

# 7勝確率・失敗確率
p7 = dist.get(7, 0)
p_fail = 1 - p7

# 失敗1回あたりの平均ジェム
gem_fail_avg = sum(reward_table[k] * dist[k] for k in dist if k != 7) / (p_fail or 1)

data = []
tot_jem = tot_box = tot_dollar = 0
for i in range(1, max_trials + 1):
    # i回目で7勝初達成
    p_succ = (p_fail ** (i-1)) * p7
    # i==max_trials かつ未達成
    p_end_fail = p_fail ** max_trials if i == max_trials else 0

    # 獲得ジェム = 失敗回数分 + 7勝時報酬
    gem_gain_succ = gem_fail_avg * (i-1) + reward_table[7]
    box_gain_succ = box_table[7]
    # 失敗ラスト
    gem_gain_fail = gem_fail_avg * max_trials
    box_gain_fail = 0

    # ドル換算
    dollar_succ = gem_gain_succ * jem_price_dollar + box_gain_succ * box_price_dollar
    dollar_fail = gem_gain_fail * jem_price_dollar

    # 期待値
    exp_jem_i = gem_gain_succ * p_succ + gem_gain_fail * p_end_fail
    exp_box_i = box_gain_succ * p_succ
    exp_dollar_i = dollar_succ * p_succ + dollar_fail * p_end_fail

    data.append({
        "回数": i,
        "獲得ジェム": gem_gain_succ if p_succ>0 else gem_gain_fail,
        "獲得BOX": box_gain_succ if p_succ>0 else box_gain_fail,
        "成功確率": p_succ,
        "未取得確率": p_end_fail,
        "期待ジェム": exp_jem_i,
        "期待BOX": exp_box_i,
        "期待ドル": exp_dollar_i
    })
    tot_jem += exp_jem_i
    tot_box += exp_box_i
    tot_dollar += exp_dollar_i

# 表示
st.dataframe(pd.DataFrame(data), use_container_width=True)

st.write("### ✅ 合計期待収支")
st.write(f"期待ジェム: {tot_jem:.2f}")
st.write(f"期待BOX: {tot_box:.2f}")
st.write(f"期待ドル: ${tot_dollar:.2f}")
