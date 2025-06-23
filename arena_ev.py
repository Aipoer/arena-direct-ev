import streamlit as st
from functools import lru_cache
import pandas as pd
import numpy as np

st.set_page_config(page_title="アリーナダイレクト期待報酬ツール")
st.title("アリーナダイレクト 期待報酬シミュレーター")

# --- 入力 ---
win_rate = st.slider("勝率", 0.0, 1.0, 0.6, 0.01)
with st.expander("◼ コスト設定", expanded=True):
    entry_cost = st.number_input("参加費（ジェム）", value=8000)
    box_price_dollar = st.number_input("BOXの価格（ドル）", value=360.0)
    jem_price_dollar = st.number_input("ジェム単価（ドル/ジェム）", value=99.99/20000, format="%.6f")

# --- 報酬設定 ---
default_rewards = {i: 0 for i in range(8)}
default_boxes = {i: 0.0 for i in range(8)}
default_rewards.update({3:3600,4:7200,5:10800,6:14400})
default_boxes[7] = 1.0
with st.expander("◼ 勝利数ごとの報酬入力（ジェム／BOX）", expanded=False):
    reward_table, box_table = {}, {}
    for i in range(8):
        c1, c2 = st.columns(2)
        with c1:
            reward_table[i] = st.number_input(f"ジェム({i}勝)", key=f"gem_{i}", value=default_rewards[i])
        with c2:
            box_table[i] = st.number_input(f"BOX({i}勝)", key=f"box_{i}", value=default_boxes[i], step=0.1)

# --- 確率分布計算 ---
@lru_cache(None)
def dp(wins, losses, p):
    if losses >= 2: return {wins:1.0}
    if wins >= 7:   return {7:1.0}
    res = {}
    for win_inc, prob in ((1,p),(0,1-p)):
        nw, nl = wins+win_inc, losses+(win_inc==0)
        sub = dp(nw, nl, p)
        for k, v in sub.items(): res[k] = res.get(k,0) + v * prob
    return res

dist = dp(0,0,win_rate)

# --- 基本期待値 ---
exp_jem = sum(reward_table[k] * v for k, v in dist.items())
exp_box = sum(box_table[k] * v for k, v in dist.items())
exp_box_jem = exp_box * (box_price_dollar / jem_price_dollar)
rev_jem = exp_jem + exp_box_jem
rev_dollar = exp_jem * jem_price_dollar + exp_box * box_price_dollar
net_jem = rev_jem - entry_cost
net_dollar = rev_dollar - entry_cost * jem_price_dollar

st.subheader("◼ 基本期待値（1回あたり）")
st.write(f"期待収入: {exp_jem:.2f} ジェム + {exp_box:.2f} 箱 (~{exp_box_jem:.2f} ジェム相当)")
st.write(f"期待収入(ドル): ${rev_dollar:.2f}")
st.write(f"参加費: {entry_cost} ジェム (~${entry_cost * jem_price_dollar:.2f})")
st.write(f"純期待利益: {net_jem:.2f} ジェム (~${net_dollar:.2f})")

# --- 勝利数分布 ---
st.subheader("◼ 勝利数分布（0~7勝）")
dist_df = pd.DataFrame({"勝利数": list(dist.keys()), "確率(%)": [v*100 for v in dist.values()]})
dist_df = dist_df.sort_values("勝利数").reset_index(drop=True)
st.table(dist_df)

# --- シミュレーション ---
st.subheader("◼ シミュレーション")
stop_on7 = st.checkbox("7勝達成までシミュレーションする", value=True)
max_trials = st.number_input("最大試行回数", 1, 100, 10)

# シミュレーション設定
p7 = dist.get(7,0)
p_fail = 1 - p7
gem_fail_avg = sum(reward_table[k]*dist[k] for k in dist if k!=7)/(p_fail or 1)

data = []
exp_trials = 0
for i in range(1, max_trials+1):
    p_succ = (p_fail**(i-1))*p7
    p_end_fail = p_fail**max_trials if i==max_trials else 0
    gem_succ = gem_fail_avg*(i-1) + reward_table[7]
    box_succ = box_table[7]
    gem_fail = gem_fail_avg*max_trials
    # 期待回数：probability of ending at i
    exp_count = p_succ + p_end_fail
    # 期待値
    exp_j = gem_succ * exp_count
    exp_b = box_succ * p_succ
    exp_trials += i * exp_count
    data.append({
        "回数": i,
        "期待回数": exp_count,
        "期待獲得ジェム": exp_j,
        "期待獲得BOX": exp_b,
        "成功確率(%)": p_succ*100,
        "未取得確率(%)": p_end_fail*100
    })
# テーブル
sim_df = pd.DataFrame(data)
# 合計行
totals = {
    "回数": "Total",
    "期待回数": sim_df["期待回数"].sum(),
    "期待獲得ジェム": sim_df["期待獲得ジェム"].sum(),
    "期待獲得BOX": sim_df["期待獲得BOX"].sum(),
    "成功確率(%)": "-",
    "未取得確率(%)": "-"
}
sim_df = sim_df.append(totals, ignore_index=True)
st.dataframe(sim_df, use_container_width=True)

# --- シナリオ比較 ---
st.subheader("◼ 勝率シナリオ比較")
col1, col2, col3 = st.columns(3)
with col1:
    wr_min = st.number_input("勝率範囲下限", 0.0, 1.0, 0.3, 0.02)
with col2:
    wr_max = st.number_input("勝率範囲上限", 0.0, 1.0, 0.7, 0.02)
with col3:
    wr_step = st.number_input("勝率刻み", 0.01, 0.1, 0.02, 0.01)
wr_list = np.arange(wr_min, wr_max+1e-6, wr_step)
scenario = []
for p in wr_list:
    d = dp(0,0,p)
    ej = sum(reward_table[k]*v for k,v in d.items())
    eb = sum(box_table[k]*v for k,v in d.items())
    rev = ej + eb*(box_price_dollar/jem_price_dollar)
    nj = rev - entry_cost
    scenario.append({"勝率": p, "純期待利益(ジェム)": nj})
sc_df = pd.DataFrame(scenario)
st.line_chart(sc_df.set_index("勝率")["純期待利益(ジェム)"])
st.dataframe(sc_df, use_container_width=True)
