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
        # 使用 utf-8-sig 處理 Excel 產生的隱形 BOM 字元
        df = pd.read_csv("data/rare_disease_ref.csv", encoding='utf-8-sig')
        
        # 清洗欄位名稱：移除空格並統一命名
        df.columns = [c.strip() for c in df.columns]
        
        # 自動映射欄位 (解決 KeyError)
        rename_map = {}
        for col in df.columns:
            if "英文病名" in col:
                rename_map[col] = "英文病名"
            elif "中文病名" in col:
                rename_map[col] = "中文病名"
            elif "ICD" in col:
                rename_map[col] = "ICD-10-CM"
        
        df = df.rename(columns=rename_map)
        
        # 檢查關鍵欄位是否存在
        if "英文病名" not in df.columns:
            st.error(f"基準檔案格式錯誤，找不到『英文病名』欄位。目前的欄位有：{df.columns.tolist()}")
            return None
        return df
    except Exception as e:
        st.error(f"讀取基準檔案失敗: {e}")
        return None

df_ref = get_ref()

# --- 2. 檔案上傳介面 ---
st.sidebar.header("上傳區域")
uploaded_file = st.sidebar.file_uploader("上傳藥品清單 (Excel/CSV)", type=["xlsx", "csv"])

if uploaded_file and df_ref is not None:
    # 讀取使用者檔案
    if uploaded_file.name.endswith('.xlsx'):
        df_user = pd.read_excel(uploaded_file)
    else:
        df_user = pd.read_csv(uploaded_file)
    
    st.subheader("Step 1: 預覽上傳資料")
    st.dataframe(df_user.head(5))
    
    # 選擇要比對的欄位
    target_col = st.selectbox("請選擇包含『適應症 (Indication)』的欄位", df_user.columns)
    
    # 比對門檻調整
    threshold = st.slider("比對精確度門檻 (建議 75-80)", 50, 100, 75)

    if st.button("🚀 開始自動比對"):
        st.subheader("Step 2: 比對結果")
        results = []
        progress_bar = st.progress(0)
        
        # 進行模糊比對
        for i, val in enumerate(df_user[target_col]):
            input_text = str(val)
            
            # 使用 token_set_ratio 處理帶有額外描述的字串 (如: Cystic Fibrosis (≥6y))
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
                    "匹配公告病名": matched_row['英文病名'],
                    "對應中文名": matched_row.get('中文病名', '-'),
                    "ICD編碼": matched_row.get('ICD-10-CM', '-'),
                    "信心分數": match[1]
                })
            else:
                results.append({
                    "原始輸入": input_text,
                    "比對狀態": "❌ 未命中",
                    "匹配公告病名": "-",
                    "對應中文名": "-",
                    "ICD編碼": "-",
                    "信心分數": match[1]
                })
            progress_bar.progress((i + 1) / len(df_user))
            
        # 組合結果並顯示
        res_df = pd.concat([df_user, pd.DataFrame(results).drop(columns="原始輸入")], axis=1)
        st.success("比對完成！")
        st.dataframe(res_df)
        
        # 下載按鈕
        csv_data = res_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 下載比對結果報告",
            data=csv_data,
            file_name="Rare_Disease_Match_Report.csv",
            mime="text/csv"
        )
else:
    st.warning("請在左側上傳藥品清單以開始比對。")
