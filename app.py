import streamlit as st
import pandas as pd
import requests
import json
import time

st.set_page_config(page_title="TCG CSV AI 助手", layout="wide")
st.title("🃏 TCG Shopify CSV 自動補完工具")

api_key = st.text_input("1️⃣ 請輸入你的 Google Gemini API Key (貼上後撳 Enter):", type="password")
uploaded_file = st.file_uploader("2️⃣ 上傳從 Shopify 匯出的 CSV 檔案", type=["csv"])

if uploaded_file and api_key:
    df = pd.read_csv(uploaded_file)
    st.success(f"成功讀取！總共有 {len(df)} 件產品。")
    st.info("💡 提示：程式會自動『每 4 秒處理一張』以防當機，請耐心等候。")
    
    if st.button("🚀 3️⃣ 開始自動睇圖加系列同稀有度"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        error_log = st.empty()
        
        col_set = '系列 (product.metafields.custom.set)'
        col_rarity = '稀有度 (product.metafields.custom.rarity)'
        
        if col_set not in df.columns:
            df[col_set] = ""
        if col_rarity not in df.columns:
            df[col_rarity] = ""
            
        df['Product Category'] = "Arts & Entertainment > Hobbies & Creative Arts > Collectibles > Collectible Trading Cards > Gaming Cards"
        
        for index, row in df.iterrows():
            title = str(row.get('Title', ''))
            
            status_text.text(f"處理緊第 {index+1}/{len(df)} 張卡: {title} (處理中...)")
            
            if pd.notna(title) and title != 'nan':
                try:
                    text_prompt = f"""
                    你是一個 TCG 專家。請純粹根據卡牌標題: "{title}" 進行分析。
                    找出該卡牌的：
                    1. 完整系列名稱，嚴格按照格式「[系列代碼] 系列中文名稱」，例如: "[SV2P] 冰雪險境"。
                    2. 稀有度 (例如: SAR, SR, AR, RR, R, U, C, SEC)。如果標題沒寫，請憑藉你對 Pokemon TCG 的專業知識，推斷這張卡的稀有度。
                    請只回傳 JSON 格式，例如：{{"set": "[SV2P] 冰雪險境", "rarity": "C"}}。不要其他文字。
                    """
                    
                    # 🔥 繞過舊套件，直接將問題 Send 去 Google 總機 🔥
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                    payload = {
                        "contents": [{"parts": [{"text": text_prompt}]}]
                    }
                    headers = {"Content-Type": "application/json"}
                    
                    response = requests.post(url, json=payload, headers=headers)
                    response_data = response.json()
                    
                    # 嘗試解析 AI 回傳嘅資料
                    if "candidates" in response_data:
                        ai_text = response_data["candidates"][0]["content"]["parts"][0]["text"]
                        cleaned_text = ai_text.strip().replace('```json', '').replace('```', '')
                        ai_data = json.loads(cleaned_text)
                        
                        df.at[index, col_set] = ai_data.get('set', '')
                        df.at[index, col_rarity] = ai_data.get('rarity', '')
                    else:
                        error_log.warning(f"第 {index+1} 行 AI 回覆異常 (可能限速)，已略過。")
                        
                except Exception as ai_e:
                    error_log.warning(f"第 {index+1} 行出錯 ({title})，已略過。")
                    
            progress_bar.progress((index + 1) / len(df))
            time.sleep(4) 
            
        status_text.text("✅ 全部處理完成！")
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 4️⃣ 下載更新後的 CSV", csv, "Shopify_TCG_Updated.csv", "text/csv")

elif uploaded_file and not api_key:
    st.warning("請先喺上面輸入 API Key 呀！")
