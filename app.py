import streamlit as st
import pandas as pd
import google.generativeai as genai
import PIL.Image
import requests
from io import BytesIO
import json

st.set_page_config(page_title="TCG CSV AI 助手", layout="wide")
st.title("🃏 TCG Shopify CSV 自動補完工具")

# 讓你自己輸入 API Key
api_key = st.text_input("1️⃣ 請輸入你的 Google Gemini API Key (貼上後撳 Enter):", type="password")
uploaded_file = st.file_uploader("2️⃣ 上傳從 Shopify 匯出的 CSV 檔案", type=["csv"])

if uploaded_file and api_key:
    genai.configure(api_key=api_key)
    # 使用免費且快速的 1.5 flash 模型
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    df = pd.read_csv(uploaded_file)
    st.success(f"成功讀取！總共有 {len(df)} 件產品。")
    
    if st.button("🚀 3️⃣ 開始自動睇圖加系列同稀有度"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 準備 Shopify 要求的 Metafield 欄位
        col_set = 'Metafield: custom.set [single_line_text_field]'
        col_rarity = 'Metafield: shopify.rarity [single_line_text_field]'
        
        if col_set not in df.columns:
            df[col_set] = ""
        if col_rarity not in df.columns:
            df[col_rarity] = ""
            
        # 批量填入 Product Category
        df['Product Category'] = "Arts & Entertainment > Hobbies & Creative Arts > Collectibles > Collectible Trading Cards > Gaming Cards"
        
        for index, row in df.iterrows():
            title = row.get('Title', '')
            img_url = row.get('Image Src', '')
            
            status_text.text(f"處理緊第 {index+1} 張卡: {title}")
            
            if pd.notna(img_url) and str(img_url).startswith('http'):
                try:
                    # 下載圖片畀 AI 睇
                    response = requests.get(img_url)
                    img = PIL.Image.open(BytesIO(response.content))
                    
                    # 給 AI 的指令
                    prompt = f"""
                    你是一個 TCG (Pokemon/One Piece) 專家。
                    請分析卡牌標題: "{title}" 和圖片。
                    找出該卡牌的：
                    1. 系列代碼 (例如: SV4a, OP05, 151)
                    2. 稀有度 (例如: SAR, SR, AR, R, C, SEC)
                    
                    請只回傳 JSON 格式，例如：{{"set": "SV4a", "rarity": "SAR"}}。不要其他文字。
                    """
                    
                    result = model.generate_content([prompt, img])
                    # 清理 AI 回傳的文字確保係 JSON
                    cleaned_text = result.text.strip().replace('```json', '').replace('```', '')
                    ai_data = json.loads(cleaned_text)
                    
                    # 填入 Excel
                    df.at[index, col_set] = ai_data.get('set', '')
                    df.at[index, col_rarity] = ai_data.get('rarity', '')
                    
                except Exception as e:
                    # 如果某張圖死 link 或者 AI 睇唔明，直接跳過保平安
                    pass
                    
            progress_bar.progress((index + 1) / len(df))
            
        status_text.text("✅ 全部處理完成！")
        
        # 輸出 CSV (utf-8-sig 確保 Excel 開啟時中文唔會亂碼)
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 4️⃣ 下載更新後的 CSV", csv, "Shopify_TCG_Updated.csv", "text/csv")

elif uploaded_file and not api_key:
    st.warning("請先喺上面輸入 API Key 呀！")
