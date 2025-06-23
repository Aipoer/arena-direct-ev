import streamlit as st
from functools import lru_cache
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

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
    reward_table = {}
    box_table = {}
    for i in range(8):
        c1, c2 = st.columns(2)
        with c1:
            reward_table[i] = st.number_input(f"ジェム({i}勝)", key=f"gem_{i}", value=default_rewards[i])
        with c2:
            box_table[i] = st.number_input(f"BOX({i}勝)", key=f"box_{i}", value=default_boxes[i], step=0.1)

# --- 確率分布計算 ---
@lru_cache(None)
def dp(wins, losses, p):
    if losses >= 2:
        return {wins:1.0}
    if wins >= 7:
        return {7:1.0}
    res = {}
    for win_inc, prob in ((1,p),(0,1-p)):
        nw, nl = wins+win_inc, losses+(win_inc==0)
        for k, v in dp(nw, nl, p).items():
            res[k] = res.get(k,0) + v * prob
    return res

# --- 基本期待値 ---
dist = dp(0,0,win_rate)
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

# シミュレーション処理は省略…（既存実装）
# [ここに従来のシミューロジックを保持]

# --- 勝率シナリオ比較 ---
st.subheader("◼ 勝率シナリオ比較")
col1, col2, col3 = st.columns(3)
with col1:
    wr_min = st.number_input("勝率範囲下限", min_value=0.0, max_value=1.0, value=0.3, step=0.05, format="%.2f")
with col2:
    wr_max = st.number_input("勝率範囲上限", min_value=0.0, max_value=1.0, value=0.9, step=0.05, format="%.2f")
with col3:
    wr_step = st.number_input("勝率刻み", min_value=0.01, max_value=0.5, value=0.1, step=0.01, format="%.2f")

# データ生成
wr_list = np.arange(wr_min, wr_max+1e-6, wr_step)
scenario = []
for p in wr_list:
    d = dp(0,0,p)
    ej = sum(reward_table[k] * v for k,v in d.items()) + sum(box_table[k]*v for k,v in d.items()) * (box_price_dollar/jem_price_dollar)
    nj = ej - entry_cost
    scenario.append({"勝率": p, "純期待利益(ジェム)": nj, "純期待利益(ドル)": nj * jem_price_dollar})
sc_df = pd.DataFrame(scenario)

# 表示
st.dataframe(sc_df, use_container_width=True)

# グラフ
fig, ax = plt.subplots()
ax.plot(sc_df["勝率"], sc_df["純期待利益(ジェム)"].values)
ax.set_xlabel("勝率")
ax.set_ylabel("純期待利益 (ジェム)")
ax.set_title("勝率 vs 純期待利益")
st.pyplot(fig)
