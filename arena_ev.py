import streamlit as st
from functools import lru_cache
import pandas as pd

st.set_page_config(page_title="アリーナダイレクト期待報酬ツール")
st.title("アリーナダイレクト 期待報酬シミュレーター")

# --- 入力 ---
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
        c1, c2 = st.columns(2)
        with c1:
            reward_table[i] = st.number_input(f"ジェム({i}勝)", key=f"gem_{i}", value=default_rewards[i])
        with c2:
            box_table[i] = st.number_input(f"BOX({i}勝)", key=f"box_{i}", value=default_boxes[i], step=0.1)

# 確率分布計算
@lru_cache(None)
def dp(wins, losses, p):
    if losses >= 2: return {wins:1.0}
    if wins >= 7:   return {7:1.0}
    res = {}
    for win_inc, prob in ((1,p),(0,1-p)):
        nw, nl = wins+win_inc, losses+(win_inc==0)
        for k, v in dp(nw, nl, p).items(): res[k] = res.get(k,0) + v * prob
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

# --- 分布表示 ---
st.subheader("◼ 勝利数分布（0~7勝）")
dist_df = pd.DataFrame({"勝利数": list(dist.keys()), "確率": list(dist.values())})
dist_df = dist_df.sort_values("勝利数").reset_index(drop=True)
st.table(dist_df)

# --- シミュレーション ---
st.subheader("◼ シミュレーション")
stop_on7 = st.checkbox("7勝達成までシミュレーションする", value=True)
max_trials = st.number_input("最大試行回数", 1, 100, 10)

if stop_on7:
    st.write("**7勝達成まで** のシミュレーションを実行します。")
    p7 = dist.get(7, 0)
    p_fail = 1 - p7
    gem_fail_avg = sum(reward_table[k] * dist[k] for k in dist if k != 7) / (p_fail or 1)
    data = []
    tot_jem = tot_box = tot_dollar = 0
    exp_trials = 0
    for i in range(1, max_trials + 1):
        p_succ = (p_fail ** (i-1)) * p7
        p_end_fail = p_fail ** max_trials if i == max_trials else 0
        gem_succ = gem_fail_avg * (i-1) + reward_table[7]
        box_succ = box_table[7]
        gem_fail = gem_fail_avg * max_trials
        dollar_succ = gem_succ * jem_price_dollar + box_succ * box_price_dollar
        dollar_fail = gem_fail * jem_price_dollar
        ej = gem_succ * p_succ + gem_fail * p_end_fail
        eb = box_succ * p_succ
        ed = dollar_succ * p_succ + dollar_fail * p_end_fail
        exp_trials += i * (p_succ + p_end_fail)
        data.append({"回数": i, "成功確率": p_succ, "未取得確率": p_end_fail,
                     "期待ジェム": ej, "期待BOX": eb, "期待ドル": ed})
        tot_jem += ej; tot_box += eb; tot_dollar += ed
    sim_df = pd.DataFrame(data)
    st.dataframe(sim_df, use_container_width=True)
    
    # 合計期待収支
    rev_jem_total = tot_jem + tot_box * (box_price_dollar / jem_price_dollar)
    rev_dollar_total = tot_jem * jem_price_dollar + tot_box * box_price_dollar
    cost_jem_total = entry_cost * exp_trials
    cost_dollar_total = entry_cost * jem_price_dollar * exp_trials
    net_jem_total = rev_jem_total - cost_jem_total
    net_dollar_total = rev_dollar_total - cost_dollar_total

    st.write("### ✅ 合計期待収支（純利益）")
    st.write(f"期待試行回数: {exp_trials:.2f} 回")
    st.write(f"期待収入合計: {rev_jem_total:.2f} ジェム + {tot_box:.2f} 箱 (~{rev_jem_total - tot_jem:.2f} ジェム換算BOX)")
    st.write(f"期待収入合計(ドル): ${rev_dollar_total:.2f}")
    st.write(f"総コスト: {cost_jem_total:.2f} ジェム (~${cost_dollar_total:.2f})")
    st.write(f"純期待利益: {net_jem_total:.2f} ジェム (~${net_dollar_total:.2f})")
    
    # 分布表示（シミュレーション結果）
    st.subheader("◼ シミュレーション後の勝利数分布（期待回数）")
    sim_trials = exp_trials
    sim_dist = {k: v * sim_trials for k, v in dist.items()}
    sim_df2 = pd.DataFrame({"勝利数": list(sim_dist.keys()), "期待回数": list(sim_dist.values())})
    sim_df2 = sim_df2.sort_values("勝利数").reset_index(drop=True)
    st.table(sim_df2)
else:
    st.write("**最大試行回数** までシミュレーションを実行。7勝達成後も継続します。")
    trials = max_trials
    # 単純期待収支
    rev_jem_total = rev_jem * trials
    rev_box_total = exp_box * trials
    rev_dollar_total = rev_dollar * trials
    cost_jem_total = entry_cost * trials
    cost_dollar_total = entry_cost * jem_price_dollar * trials
    net_jem_total = rev_jem_total - cost_jem_total
    net_dollar_total = rev_dollar_total - cost_dollar_total

    st.write(f"期待収入合計: {rev_jem_total:.2f} ジェム + {rev_box_total:.2f} 箱 (~${rev_dollar_total:.2f})")
    st.write(f"総コスト: {cost_jem_total:.2f} ジェム (~${cost_dollar_total:.2f})")
    st.write(f"純期待利益: {net_jem_total:.2f} ジェム (~${net_dollar_total:.2f})")
    # 分布表示（継続プレイ）
    sim_dist2 = {k: v * trials for k, v in dist.items()}
    sim_df3 = pd.DataFrame({"勝利数": list(sim_dist2.keys()), "期待回数": list(sim_dist2.values())})
    sim_df3 = sim_df3.sort_values("勝利数").reset_index(drop=True)
    st.subheader("◼ シミュレーション後の勝利数分布（期待回数）")
    st.table(sim_df3)
