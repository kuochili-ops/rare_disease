import streamlit as st
import pandas as pd
from fuzzywuzzy import process, fuzz

st.set_page_config(page_title="罕藥自動化比對工具", layout="wide")

st.title("🇹🇼 罕見疾病藥品比對系統")
st.info("請上傳藥品清單 Excel，系統將自動比對 1141020 公告之罕病名單。")

# --- 1. 載入政府公告資料 (建議先轉成 CSV 加速讀取) ---
@st.cache_data
def load_reference():
    # 這裡放您解析 PDF 後的資料
    return pd.read_csv("data/rare_disease_list_1141020.csv")

df_ref = load_reference()

# --- 2. 檔案上傳 ---
uploaded_file = st.file_uploader("上傳藥品清單 (Excel/CSV)", type=["xlsx", "csv"])

if uploaded_file:
    df_user = pd.read_excel(uploaded_file) if ".xlsx" in uploaded_file.name else pd.read_csv(uploaded_file)
    
    st.write("### 原始資料預覽", df_user.head())
    
    target_col = st.selectbox("請選擇要比對的適應症欄位 (Indication)", df_user.columns)
    
    if st.button("開始自動比對"):
        results = []
        for text in df_user[target_col]:
            # 進行模糊比對 (比對英文病名)
            match = process.extractOne(str(text), df_ref['English_Name'], scorer=fuzz.token_set_ratio)
            
            if match and match[1] > 70: # 設定相似度門檻
                ref_row = df_ref.iloc[match[2]]
                results.append({
                    "原始輸入": text,
                    "比對結果": "✅ 命中",
                    "匹配病名": ref_row['English_Name'],
                    "中文病名": ref_row['Chinese_Name'],
                    "ICD-10": ref_row['ICD10'],
                    "信心分數": match[1]
                })
            else:
                results.append({"原始輸入": text, "比對結果": "❌ 未命中", "匹配病名": "-", "中文病名": "-", "ICD-10": "-", "信心分數": 0})
        
        df_res = pd.DataFrame(results)
        st.write("### 比對結果", df_res)
        
        # 下載按鈕
        st.download_button("下載比對報告", df_res.to_csv(index=False).encode('utf-8-sig'), "Match_Report.csv", "text/csv")
