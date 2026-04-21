import streamlit as st
import pandas as pd
import google.generativeai as genai
import PIL.Image
import requests
from io import BytesIO
import json

st.set_page_config(page_title="TCG CSV AI 助手", layout="wide")
st.title("🃏 TCG Shopify CSV 自動補完工具")

api_key = st.text_input("1️⃣ 請輸入你的 Google Gemini API Key (貼上後撳 Enter):", type="password")
uploaded_file = st.file_uploader("2️⃣ 上傳從 Shopify 匯出的 CSV 檔案", type=["csv"])

if uploaded_file and api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    df = pd.read_csv(uploaded_file)
    st.success(f"成功讀取！總共有 {len(df)} 件產品。")
    
    if st.button("🚀 3️⃣ 開始自動睇圖加系列同稀有度"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        error_log = st.empty()
        
        # 🌟 根據你嘅要求，更新咗呢兩個欄位名稱 🌟
        col_set = '系列 (product.metafields.custom.set)'
        col_rarity = '稀有度 (product.metafields.custom.rarity)'
        
        if col_set not in df.columns:
            df[col_set] = ""
        if col_rarity not in df.columns:
            df[col_rarity] = ""
            
        df['Product Category'] = "Arts & Entertainment > Hobbies & Creative Arts > Collectibles > Collectible Trading Cards > Gaming Cards"
        
        for index, row in df.iterrows():
            title = str(row.get('Title', ''))
            img_url = str(row.get('Image Src', ''))
            
            status_text.text(f"處理緊第 {index+1} 張卡: {title}")
            
            if pd.notna(img_url) and img_url.startswith('http'):
                try:
                    # 加入 User-Agent 扮成 Chrome 瀏覽器，防止被 Pokémon 官網 Block
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
                    }
                    response = requests.get(img_url, headers=headers, timeout=10)
                    response.raise_for_status() 
                    
                    img = PIL.Image.open(BytesIO(response.content))
                    
                    prompt = f"""
                    你是一個 TCG (Pokemon/One Piece) 專家。請分析卡牌標題: "{title}" 和圖片。
                    找出該卡牌的：
                    1. 完整系列名稱，請嚴格按照這個格式輸出：「[系列代碼] 系列中文名稱」，例如: "[SV2P] 冰雪險境"。請直接從標題中提取正確的中文名稱和代碼來組合。
                    2. 稀有度 (例如: SAR, SR, AR, RR, R, U, C, SEC)
                    請只回傳 JSON 格式，例如：{{"set": "[SV2P] 冰雪險境", "rarity": "SAR"}}。不要其他文字。
                    """
                    
                    result = model.generate_content([prompt, img])
                    cleaned_text = result.text.strip().replace('```json', '').replace('```', '')
                    ai_data = json.loads(cleaned_text)
                    
                    # 填入你指定嘅欄位
                    df.at[index, col_set] = ai_data.get('set', '')
                    df.at[index, col_rarity] = ai_data.get('rarity', '')
                    
                except Exception as e:
                    error_log.warning(f"跳過咗第 {index+1} 行 ({title}) - 原因: {str(e)[:50]}...")
                    
            progress_bar.progress((index + 1) / len(df))
            
        status_text.text("✅ 全部處理完成！")
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 4️⃣ 下載更新後的 CSV", csv, "Shopify_TCG_Updated.csv", "text/csv")

elif uploaded_file and not api_key:
    st.warning("請先喺上面輸入 API Key 呀！")
