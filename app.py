import streamlit as st
import pandas as pd
from fuzzywuzzy import process, fuzz

# 設定網頁標題
st.set_page_config(page_title="台灣罕藥自動比對工具", page_icon="💊", layout="wide")

st.title("💊 台灣公告罕見疾病藥品比對系統")
st.markdown("將您的藥品清單與 **1141020 公告之罕病名單** 進行比對。")

# --- 1. 載入基準資料 ---
@st.cache_data
def get_ref():
    try:
        # 讀取基準資料 CSV (確保路徑為 data/rare_disease_ref.csv)
        df = pd.read_csv("data/rare_disease_ref.csv", encoding='utf-8-sig')
        df.columns = [c.strip() for c in df.columns]
        
        # 欄位映射：確保程式能找到比對用的 Key
        rename_map = {}
        for col in df.columns:
            if "英文病名" in col: rename_map[col] = "英文病名"
            elif "中文病名" in col: rename_map[col] = "中文病名"
            elif "ICD" in col: rename_map[col] = "ICD-10-CM"
        
        df = df.rename(columns=rename_map)
        return df
    except Exception as e:
        st.error(f"基準檔案載入失敗，請檢查 data 目錄。錯誤: {e}")
        return None

df_ref = get_ref()

# --- 2. 檔案上傳 ---
st.sidebar.header("資料輸入")
uploaded_file = st.sidebar.file_uploader("上傳藥品清單 (Excel/CSV)", type=["xlsx", "csv"])

if uploaded_file and df_ref is not None:
    if uploaded_file.name.endswith('.xlsx'):
        df_user = pd.read_excel(uploaded_file)
    else:
        df_user = pd.read_csv(uploaded_file)
    
    st.subheader("Step 1: 預覽與設定")
    
    # --- 自動預設比對欄位邏輯 ---
    cols = df_user.columns.tolist()
    default_index = 0
    
    # 搜尋關鍵字：優先順序 Indication > 適應症
    for i, col in enumerate(cols):
        if any(keyword in col.lower() for keyword in ["indication", "適應症"]):
            default_index = i
            break
            
    target_col = st.selectbox("請確認要比對的欄位 (預設已為您選定適應症)", cols, index=default_index)
    
    # 設定相似度門檻
    threshold = st.slider("比對精確度門檻 (數字越高越嚴格，建議 75)", 50, 100, 75)

    if st.button("🚀 開始自動比對"):
        st.subheader("Step 2: 比對分析中...")
        results = []
        progress_bar = st.progress(0)
        
        for i, val in enumerate(df_user[target_col]):
            input_text = str(val)
            
            # 使用 token_set_ratio 處理帶括號的描述 (如: Cystic Fibrosis (≥6y))
            match = process.extractOne(
                input_text, 
                df_ref['英文病名'], 
                scorer=fuzz.token_set_ratio
            )
            
            if match and match[1] >= threshold:
                matched_row = df_ref.iloc[match[2]]
                results.append({
                    "原始輸入": input_text,
                    "比對狀態": "✅ 符合罕病",
                    "匹配公告英文名": matched_row['英文病名'],
                    "中文病名": matched_row.get('中文病名', '-'),
                    "ICD編碼": matched_row.get('ICD-10-CM', '-'),
                    "相似度分數": match[1]
                })
            else:
                results.append({
                    "原始輸入": input_text, "比對狀態": "❌ 未命中", "匹配公告英文名": "-", "中文病名": "-", "ICD編碼": "-", "相似度分數": match[1]
                })
            progress_bar.progress((i + 1) / len(df_user))
            
        # 組合結果
        res_df = pd.concat([df_user, pd.DataFrame(results).drop(columns="原始輸入")], axis=1)
        st.success("比對完成！")
        st.dataframe(res_df)
        
        # 下載報告
        csv_data = res_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載完整比對報告", csv_data, "Rare_Match_Report.csv", "text/csv")
else:
    st.info("💡 請在左側上傳藥品清單 Excel。系統會自動識別『Indication』或『適應症』欄位。")
