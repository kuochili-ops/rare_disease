import streamlit as st
import pandas as pd
from fuzzywuzzy import process, fuzz

st.set_page_config(page_title="台灣罕藥比對工具", page_icon="💊")

st.title("💊 台灣公告罕見疾病藥品比對系統")
st.caption("基準資料版本：1141020 公告名單")

# 載入預先處理好的 CSV
@st.cache_data
def get_ref():
    return pd.read_csv("data/rare_disease_ref.csv")

df_ref = get_ref()

uploaded_file = st.file_uploader("請上傳您的藥品清單 (Excel 或 CSV)", type=["xlsx", "csv"])

if uploaded_file:
    # 讀取使用者上傳的資料
    df_user = pd.read_excel(uploaded_file) if "xlsx" in uploaded_file.name else pd.read_csv(uploaded_file)
    cols = df_user.columns.tolist()
    
    target_col = st.selectbox("選擇包含「適應症 (Indication)」的欄位", cols)
    
    if st.button("執行自動比對"):
        output_data = []
        progress_bar = st.progress(0)
        
        for i, val in enumerate(df_user[target_col]):
            # 模糊比對邏輯
            # 我們同時比對英文病名，並設定 token_set_ratio 以應對複雜的 Indication 描述
            best_match = process.extractOne(
                str(val), 
                df_ref['英文病名'], 
                scorer=fuzz.token_set_ratio
            )
            
            # 門檻設定：相似度 75 以上通常為正確匹配
            if best_match and best_match[1] >= 75:
                match_row = df_ref.iloc[best_match[2]]
                result = {
                    "原始輸入": val,
                    "比對狀態": "✅ 符合罕病",
                    "匹配公告病名": match_row['英文病名'],
                    "中文名稱": match_row['中文病名'],
                    "ICD編碼": match_row['ICD-10-CM'],
                    "相似度得分": best_match[1]
                }
            else:
                result = {
                    "原始輸入": val,
                    "比對狀態": "❌ 非罕病或需人工確認",
                    "匹配公告病名": "-",
                    "中文名稱": "-",
                    "ICD編碼": "-",
                    "相似度得分": best_match[1]
                }
            output_data.append(result)
            progress_bar.progress((i + 1) / len(df_user))
            
        res_df = pd.concat([df_user, pd.DataFrame(output_data).drop(columns="原始輸入")], axis=1)
        st.success("比對完成！")
        st.dataframe(res_df)
        
        # 提供下載
        csv = res_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("下載完整比對報告 (Excel相容格式)", csv, "Rare_Match_Report.csv", "text/csv")
