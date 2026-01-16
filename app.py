import streamlit as st
import pandas as pd
from fuzzywuzzy import process, fuzz

# 設定網頁標題與圖示
st.set_page_config(page_title="台灣罕藥自動比對工具", page_icon="💊", layout="wide")

st.title("💊 台灣公告罕見疾病藥品比對系統")
st.markdown("將您的藥品清單與 **1141020 公告之罕病名單** 進行語意對齊比對。")

# --- 1. 載入並校正基準資料 ---
@st.cache_data
def get_ref():
    try:
        df = pd.read_csv("data/rare_disease_ref.csv", encoding='utf-8-sig')
        df.columns = [c.strip() for c in df.columns]
        rename_map = {}
        for col in df.columns:
            if "英文病名" in col: rename_map[col] = "英文病名"
            elif "中文病名" in col: rename_map[col] = "中文病名"
            elif "ICD" in col: rename_map[col] = "ICD-10-CM"
        df = df.rename(columns=rename_map)
        return df
    except Exception as e:
        st.error(f"讀取基準檔案失敗: {e}")
        return None

df_ref = get_ref()

# --- 2. 檔案上傳介面 ---
st.sidebar.header("上傳區域")
uploaded_file = st.sidebar.file_uploader("上傳藥品清單 (Excel/CSV)", type=["xlsx", "csv"])

if uploaded_file and df_ref is not None:
    # 讀取使用者檔案 (加入 engine='openpyxl' 確保 Excel 讀取穩定)
    if uploaded_file.name.endswith('.xlsx'):
        df_user = pd.read_excel(uploaded_file, engine='openpyxl')
    else:
        df_user = pd.read_csv(uploaded_file, encoding='utf-8-sig')
    
    st.subheader("Step 1: 預覽與設定")
    
    # --- 智慧欄位預設邏輯 ---
    user_cols = df_user.columns.tolist()
    # 搜尋關鍵字：優先找 'indication' 或 '適應症'
    default_idx = 0
    for i, col_name in enumerate(user_cols):
        c_low = col_name.lower()
        if "indication" in c_low or "適應症" in c_low:
            default_idx = i
            break
            
    target_col = st.selectbox("請確認包含『適應症 (Indication)』的欄位", user_cols, index=default_idx)
    
    threshold = st.slider("比對精確度門檻 (建議 75)", 50, 100, 75)

    if st.button("🚀 開始自動比對"):
        st.subheader("Step 2: 比對結果")
        results = []
        progress_bar = st.progress(0)
        
        for i, val in enumerate(df_user[target_col]):
            input_text = str(val)
            match = process.extractOne(input_text, df_ref['英文病名'], scorer=fuzz.token_set_ratio)
            
            if match and match[1] >= threshold:
                matched_row = df_ref.iloc[match[2]]
                results.append({
                    "比對狀態": "✅ 符合罕病",
                    "匹配公告病名": matched_row['英文病名'],
                    "對應中文名": matched_row.get('中文病名', '-'),
                    "ICD編碼": matched_row.get('ICD-10-CM', '-'),
                    "信心分數": match[1]
                })
            else:
                results.append({"比對狀態": "❌ 未命中", "匹配公告病名": "-", "對應中文名": "-", "ICD編碼": "-", "信心分數": match[1]})
            progress_bar.progress((i + 1) / len(df_user))
            
        res_df = pd.concat([df_user, pd.DataFrame(results)], axis=1)
        st.success("比對完成！")
        st.dataframe(res_df)
        
        csv_data = res_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載比對結果報告", csv_data, "Rare_Match_Report.csv", "text/csv")
else:
    st.warning("請在左側上傳藥品清單以開始比對。")
