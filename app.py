import pdfplumber
import pandas as pd
from fuzzywuzzy import process

# 1. 解析 PDF 公告
def extract_rare_disease_list(pdf_path):
    all_data = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if table:
                # 假設表格欄位為: [序號, 中文病名, 英文病名, ICD編碼]
                all_data.extend(table[1:]) # 跳過標題列
    return pd.DataFrame(all_data, columns=['ID', 'Name_CH', 'Name_EN', 'ICD10'])

# 2. 模糊比對邏輯
def find_match(indication, ref_list):
    # 同時比對英文與中文病名，取最高分者
    match_en = process.extractOne(indication, ref_list['Name_EN'])
    # 回傳格式: (匹配到的字串, 分數, 索引)
    return match_en

# 主程式流程
df_rare = extract_rare_disease_list("公告名單.pdf")
df_drugs = pd.read_excel("RD_Test.xlsx")

# 執行比對並產生結果
df_drugs['Match_Result'] = df_drugs['Indication'].apply(lambda x: find_match(x, df_rare))
df_drugs.to_excel("比對結果報告.xlsx")
