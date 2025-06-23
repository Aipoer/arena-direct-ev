import streamlit as st
from functools import lru_cache
import pandas as pd

st.set_page_config(page_title="アリーナダイレクト期待報酬ツール")
st.title("アリーナダイレクト 期待報酬シミュレーター")

# パラメータ入力
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

# 分布計算
@lru_cache(None)
def dp(wins, losses, p):
    if losses>=2: return {wins:1.0}
    if wins>=7: return {7:1.0}
    res={}
    for win_inc,prob in ((1,p),(0,1-p)):
        nw, nl = wins+win_inc, losses + (win_inc==0)
        for k,v in dp(nw,nl,p).items(): res[k] = res.get(k,0)+v*prob
    return res

dist = dp(0,0,win_rate)
prob_box = dist.get(7,0)
prob_fail = 1 - prob_box

# 1回あたりの失敗時期待ジェム（7勝以外）
gem_fail_avg = sum(reward_table[k]*v for k,v in dist.items() if k<7)/ (prob_fail or 1)

st.subheader("◼ 基本期待値（1回あたり）")
st.write(f"期待ジェム: {sum(reward_table[k]*v for k,v in dist.items()):.2f} ジェム")
st.write(f"期待BOX: {sum(box_table[k]*v for k,v in dist.items()):.2f} 箱")

# シミュレーション
st.subheader("◼ シミュレーション: BOX獲得まで or 最大試行まで")
max_trials = st.number_input("最大試行回数", 1, 100, 10)

data=[]
tot_jem=0; tot_box=0; tot_dollar=0
for i in range(1, max_trials+1):
    # i回目でBOX初取得
    p_succ = (prob_fail**(i-1))*prob_box
    # 最大回数で未取得
    p_fail = prob_fail**max_trials if i==max_trials else 0
    # gem獲得: 失敗回数*(平均失敗時gem) + 成功時gem(reward_table[7])
    gem_gain = gem_fail_avg*(i-1) + reward_table[7]
    # box獲得: 成功時のみ box_table[7]
    box_gain = box_table[7]
    # ドル換算
    dollar_gain = gem_gain*jem_price_dollar + box_gain*box_price_dollar
    # 期待値
    exp_jem = gem_gain*(p_succ + p_fail)
    exp_box = box_gain*p_succ
    exp_dollar = dollar_gain*(p_succ + p_fail)
    data.append({
        "回数": i,
        "成功確率": p_succ,
        "未取得確率": p_fail,
        "期待ジェム": exp_jem,
        "期待BOX": exp_box,
        "期待ドル": exp_dollar
    })
    tot_jem+=exp_jem; tot_box+=exp_box; tot_dollar+=exp_dollar

df = pd.DataFrame(data)
st.dataframe(df, use_container_width=True)

st.write("### ✅ 合計期待収支")
st.write(f"期待ジェム: {tot_jem:.2f}")
st.write(f"期待BOX: {tot_box:.2f}")
st.write(f"期待ドル: ${tot_dollar:.2f}")
