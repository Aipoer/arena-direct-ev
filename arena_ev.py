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
    box_price_dollar = st.number_input("BOXの価格（ドル）", value=164.7)
    jem_price_dollar = st.number_input("ジェム単価（ドル/ジェム）", value=99.99/20000, format="%.6f")

# --- 報酬設定 ---
default_rewards = {i: 0 for i in range(8)}
default_boxes = {i: 0.0 for i in range(8)}
default_rewards.update({3:3600,4:7200,5:10800})
default_boxes[6] = 1.0
default_boxes[7] = 2.0
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
        return {wins: 1.0}
    if wins >= 7:
        return {7: 1.0}
    res = {}
    for win_inc, prob in ((1, p), (0, 1-p)):
        nw, nl = wins + win_inc, losses + (win_inc == 0)
        for k, v in dp(nw, nl, p).items():
            res[k] = res.get(k, 0) + v * prob
    return res

dist = dp(0, 0, win_rate)

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

if stop_on7:
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
        data.append({
            "回数": i,
            "成功確率(%)": p_succ*100,
            "未取得確率(%)": p_end_fail*100,
            "期待ジェム": ej,
            "期待BOX": eb,
            "期待ドル": ed
        })
        tot_jem += ej; tot_box += eb; tot_dollar += ed
    sim_df = pd.DataFrame(data)
    st.dataframe(sim_df, use_container_width=True)

    # --- 合計期待収支 ---
    rev_jem_total = tot_jem + tot_box * (box_price_dollar / jem_price_dollar)
    rev_dollar_total = tot_jem * jem_price_dollar + tot_box * box_price_dollar
    cost_jem_total = entry_cost * exp_trials
    cost_dollar_total = entry_cost * jem_price_dollar * exp_trials
    net_jem_total = rev_jem_total - cost_jem_total
    net_dollar_total = rev_dollar_total - cost_dollar_total

    st.write("### ✅ 合計期待収支（純利益）")
    st.write(f"期待試行回数: {exp_trials:.2f} 回")
    st.write(f"期待収入合計: {rev_jem_total:.2f} ジェム + {tot_box:.2f} 箱 (~${rev_dollar_total:.2f})")
    st.write(f"総コスト: {cost_jem_total:.2f} ジェム (~${cost_dollar_total:.2f})")
    st.write(f"純期待利益: {net_jem_total:.2f} ジェム (~${net_dollar_total:.2f})")

    # --- シミュレーション後の勝利数分布 ---
    sim_dist = {k: dist[k] * exp_trials for k in dist}
    sim_df2 = pd.DataFrame({
        "勝利数": list(sim_dist.keys()),
        "期待回数": list(sim_dist.values()),
        "期待ジェム": [reward_table[k] * dist[k] * exp_trials for k in dist],
        "期待BOX": [box_table[k] * dist[k] * exp_trials for k in dist]
    })
    st.subheader("◼ シミュレーション後の勝利数分布（期待回数・期待報酬）")
    st.write(f"(母数: 期待試行回数 {exp_trials:.2f} 回)")
    st.table(sim_df2.sort_values("勝利数").reset_index(drop=True))
else:
    trials = max_trials
    rev_jem_total = rev_jem * trials
    rev_box_total = exp_box * trials
    rev_dollar_total = rev_dollar * trials
    cost_jem_total = entry_cost * trials
    cost_dollar_total = entry_cost * jem_price_dollar * trials
    net_jem_total = rev_jem_total - cost_jem_total
    net_dollar_total = rev_dollar_total - cost_dollar_total

    st.write("### ✅ 継続プレイ モード")
    st.write(f"期待収入合計: {rev_jem_total:.2f} ジェム + {rev_box_total:.2f} 箱 (~${rev_dollar_total:.2f})")
    st.write(f"総コスト: {cost_jem_total:.2f} ジェム (~${cost_dollar_total:.2f})")
    st.write(f"純期待利益: {net_jem_total:.2f} ジェム (~${net_dollar_total:.2f})")

    sim_dist2 = {k: dist[k] * trials for k in dist}
    sim_df3 = pd.DataFrame({
        "勝利数": list(sim_dist2.keys()),
        "期待回数": list(sim_dist2.values()),
        "期待ジェム": [reward_table[k] * dist[k] * trials for k in dist],
        "期待BOX": [box_table[k] * dist[k] * trials for k in dist]
    })
    st.subheader("◼ 継続プレイ後の勝利数分布（期待回数・期待報酬）")
    st.table(sim_df3.sort_values("勝利数").reset_index(drop=True))

# --- 勝率シナリオ比較 ---
st.subheader("◼ 勝率シナリオ比較")
wr_stop_on7 = st.checkbox("7勝達成までシミュレーションする", key="wr_stop_on7")
if wr_stop_on7:
    wr_max_trials = st.number_input(
        "最大試行回数", min_value=1, max_value=30, value=10, key="wr_max_trials"
    )
col1, col2, col3 = st.columns(3)
with col1:
    wr_min = st.number_input("勝率範囲下限", min_value=0.0, max_value=1.0, value=0.3, step=0.02, format="%.2f")
with col2:
    wr_max = st.number_input("勝率範囲上限", min_value=0.0, max_value=1.0, value=0.7, step=0.02, format="%.2f")
with col3:
    wr_step = st.number_input("勝率刻み", min_value=0.01, max_value=0.1, value=0.02, step=0.01, format="%.2f")

wr_list = np.arange(wr_min, wr_max + 1e-6, wr_step)
scenario = []
for p in wr_list:
    d = dp(0, 0, p)
    if wr_stop_on7:
        p7 = d.get(7, 0)
        p_fail = 1 - p7
        gem_fail_avg = sum(reward_table[k] * d[k] for k in d if k != 7) / (p_fail or 1)
        tot_jem = tot_box = 0.0
        exp_trials = 0.0
        for i in range(1, wr_max_trials + 1):
            p_succ = (p_fail ** (i - 1)) * p7
            p_end_fail = p_fail ** wr_max_trials if i == wr_max_trials else 0
            gem_succ = gem_fail_avg * (i - 1) + reward_table[7]
            box_succ = box_table[7]
            gem_fail = gem_fail_avg * wr_max_trials
            ej = gem_succ * p_succ + gem_fail * p_end_fail
            eb = box_succ * p_succ
            exp_trials += i * (p_succ + p_end_fail)
            tot_jem += ej
            tot_box += eb
        rev_jem_total = tot_jem + tot_box * (box_price_dollar / jem_price_dollar)
        nj = rev_jem_total - entry_cost * exp_trials
    else:
        ej = sum(reward_table[k] * v for k, v in d.items())
        eb = sum(box_table[k] * v for k, v in d.items())
        rev_jem_total = ej + eb * (box_price_dollar / jem_price_dollar)
        nj = rev_jem_total - entry_cost
        exp_trials = 1
    cost = entry_cost * exp_trials
    cost_dollar = cost * jem_price_dollar
    rev_dollar_total = rev_jem_total * jem_price_dollar
    nj_dollar = rev_dollar_total - cost_dollar
    ev_pct = (rev_dollar_total / cost_dollar * 100) if cost_dollar else 0
    scenario.append({
        "勝率": p,
        "純期待利益(ジェム)": nj,
        "純期待利益(ドル)": nj_dollar,
        "期待値(%)": ev_pct
    })
sc_df = pd.DataFrame(scenario)

st.subheader("◼ 勝率 vs 純期待利益")
st.line_chart(sc_df.set_index("勝率")["純期待利益(ジェム)"])
st.dataframe(sc_df, use_container_width=True)

# --- ランダム勝率シミュレーション ---
st.subheader("◼ ランダム勝率シミュレーション")
rand_stop7 = st.checkbox("7勝達成で終了", key="rand_stop7")
rand_trials = st.number_input("参加回数上限", min_value=1, max_value=30, value=5, key="rand_trials")

col1, col2, col3 = st.columns(3)
with col1:
    base_wr = st.number_input("基本勝率", 0.0, 1.0, 0.6, 0.01, key="base_wr")
with col2:
    spread_wr = st.number_input("ブレ幅(±)", 0.0, 1.0, 0.1, 0.01, key="spread_wr")
with col3:
    shape_k = st.number_input("分布形状k(1=均等、<1極端)", 0.1, 5.0, 1.0, 0.1, key="shape_k")

sample_size = 1000
samples = np.clip(base_wr + (np.random.beta(shape_k, shape_k, sample_size)-0.5)*2*spread_wr, 0, 1)
hist, bins = np.histogram(samples, bins=20, range=(0,1))
hist_df = pd.DataFrame({"win_rate": (bins[:-1]+bins[1:])/2, "count": hist})
st.bar_chart(hist_df.set_index("win_rate"))

if st.button("シミュレーション開始"):
    results = []
    total_gem = total_box = 0
    played = 0
    for i in range(int(rand_trials)):
        p = float(np.clip(base_wr + (np.random.beta(shape_k, shape_k)-0.5)*2*spread_wr, 0, 1))
        wins = losses = 0
        while wins < 7 and losses < 2:
            if np.random.random() < p:
                wins += 1
            else:
                losses += 1
        gem = reward_table[wins]
        box = box_table[wins]
        results.append({"回数": i+1, "勝率": round(p,3), "勝利数": wins, "ジェム": gem, "BOX": box})
        total_gem += gem
        total_box += box
        played += 1
        if rand_stop7 and wins == 7:
            break
    res_df = pd.DataFrame(results)
    st.dataframe(res_df, use_container_width=True)

    rev_jem_total = total_gem + total_box * (box_price_dollar / jem_price_dollar)
    rev_dollar_total = total_gem * jem_price_dollar + total_box * box_price_dollar
    cost_jem_total = entry_cost * played
    cost_dollar_total = entry_cost * jem_price_dollar * played
    net_jem_total = rev_jem_total - cost_jem_total
    net_dollar_total = rev_dollar_total - cost_dollar_total

    st.write("### ✅ シミュレーション結果")
    st.write(f"プレイ回数: {played}")
    st.write(f"総収入: {total_gem} ジェム + {total_box} 箱 (~${rev_dollar_total:.2f})")
    st.write(f"総コスト: {cost_jem_total} ジェム (~${cost_dollar_total:.2f})")
    st.write(f"純利益: {net_jem_total:.2f} ジェム (~${net_dollar_total:.2f})")

# --- ランダム勝率シミュレーション(ジェム) ---
st.subheader("◼ ランダム勝率シミュレーション(ジェム)")
init_gem = st.number_input("開始ジェム残高", min_value=0, value=entry_cost, step=1000)
randg_stop7 = st.checkbox("7勝達成で終了", key="randg_stop7")
randg_trials = st.number_input("参加回数上限", min_value=1, max_value=100, value=10, key="randg_trials")

cg1, cg2, cg3 = st.columns(3)
with cg1:
    base_wr_g = st.number_input("基本勝率", 0.0, 1.0, 0.6, 0.01, key="base_wr_g")
with cg2:
    spread_wr_g = st.number_input("ブレ幅(±)", 0.0, 1.0, 0.1, 0.01, key="spread_wr_g")
with cg3:
    shape_k_g = st.number_input("分布形状k(1=均等、<1極端)", 0.1, 5.0, 1.0, 0.1, key="shape_k_g")

if st.button("シミュレーション開始(ジェム)", key="randg_start"):
    bal = int(init_gem)
    total_box_g = 0
    results_g = []
    plays = 0
    while bal >= entry_cost and plays < int(randg_trials):
        bal -= entry_cost
        p = float(np.clip(base_wr_g + (np.random.beta(shape_k_g, shape_k_g)-0.5)*2*spread_wr_g, 0, 1))
        wins = losses = 0
        while wins < 7 and losses < 2:
            if np.random.random() < p:
                wins += 1
            else:
                losses += 1
        gem = reward_table[wins]
        box = box_table[wins]
        bal += gem
        total_box_g += box
        plays += 1
        results_g.append({"回数": plays, "勝率": round(p,3), "勝利数": wins, "ジェム": gem, "BOX": box, "残高": bal})
        if randg_stop7 and wins == 7:
            break
    resg_df = pd.DataFrame(results_g)
    st.dataframe(resg_df, use_container_width=True)

    rev_jem_total = bal + total_box_g * (box_price_dollar / jem_price_dollar)
    rev_dollar_total = bal * jem_price_dollar + total_box_g * box_price_dollar
    net_jem_total = rev_jem_total - init_gem
    net_dollar_total = rev_dollar_total - init_gem * jem_price_dollar

    st.write("### ✅ シミュレーション結果(ジェム)")
    st.write(f"プレイ回数: {plays}")
    st.write(f"最終ジェム残高: {bal}")
    st.write(f"獲得BOX: {total_box_g}")
    st.write(f"純利益: {net_jem_total:.2f} ジェム (~${net_dollar_total:.2f})")
