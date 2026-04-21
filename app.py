import streamlit as st
import pandas as pd
import re
import requests
import json
import time
import base64
import cloudscraper

st.set_page_config(page_title="TCG CSV 終極辨識工具", layout="wide")
st.title("👁️ TCG CSV 智能辨識工具 (視覺 + 知識雙修版)")
st.write("✅ 直接讀取 CSV 圖片連結 | ✅ 如果官網封鎖圖片，自動轉用 AI 知識庫分析編號")

api_key = st.text_input("🔑 請輸入你的 Google Gemini API Key:", type="password")
uploaded_file = st.file_uploader("📂 上傳 CSV 檔案", type=["csv"])

if uploaded_file:
    original_filename = uploaded_file.name
    download_filename = f"Fixed_{original_filename}"
    df = pd.read_csv(uploaded_file)
    st.success(f"成功讀取檔案：{original_filename}")
    
    if st.button("🚀 開始智能處理"):
        col_set = '系列 (product.metafields.custom.set)'
        col_rarity = '稀有度 (product.metafields.custom.rarity)'
        
        for col in [col_set, col_rarity]:
            if col not in df.columns: df[col] = ""
            
        df['Product Category'] = "Arts & Entertainment > Hobbies & Creative Arts > Collectibles > Collectible Trading Cards > Gaming Cards"
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        all_rarities = ['SAR', 'SSR', 'CSR', 'CHR', 'RRR', 'ACE', 'SR', 'AR', 'UR', 'HR', 'RR', 'PR', 'TR', 'K', 'S', 'A', 'R', 'U', 'C']
        scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
        
        for index, row in df.iterrows():
            title = str(row.get('Title', ''))
            img_url = str(row.get('Image Src', ''))
            
            status_text.text(f"分析中 ({index+1}/{len(df)}): {title}")
            
            # 1. 優先從標題擷取系列
            set_match = re.search(r'^(\[[A-Z0-9a-z]+\]\s[^\s]+)', title)
            if set_match: df.at[index, col_set] = set_match.group(1)

            # 2. 判斷稀有度
            # 先試標題
            rarity_pattern = r'\s(' + '|'.join(all_rarities) + r')$'
            rarity_match = re.search(rarity_pattern, title, re.IGNORECASE)
            
            if rarity_match:
                df.at[index, col_rarity] = rarity_match.group(1).upper()
            elif any(x in title.lower() for x in ['ex ', 'ex']):
                df.at[index, col_rarity] = 'RR'
            else:
                # 🌟 標題冇寫，呼叫 AI 大腦 🌟
                if api_key:
                    try:
                        # 準備 AI 指令
                        prompt = f"Identify the rarity of this Pokemon card: '{title}'. Possible: {all_rarities}. Return ONLY the code."
                        payload = {"contents": [{"parts": [{"text": prompt}]}]}
                        
                        # 📸 嘗試下載 CSV 入面條 Image Src 畀 AI 睇
                        try:
                            img_response = scraper.get(img_url, timeout=5)
                            if img_response.status_code == 200:
                                img_b64 = base64.b64encode(img_response.content).decode("utf-8")
                                payload["contents"][0]["parts"].append({
                                    "inline_data": {"mime_type": "image/png", "data": img_b64}
                                })
                        except:
                            # 圖片下載唔到 (例如官網 Block 咗)，就叫 AI 憑標題嘅編號估
                            payload["contents"][0]["parts"][0]["text"] += " (Image not available, please use your knowledge to infer rarity from the card number in the title.)"

                        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
                        res_json = response.json()
                        
                        if "candidates" in res_json:
                            ans = res_json["candidates"][0]["content"]["parts"][0]["text"].strip().upper()
                            # 確保 AI 唔好答非所問
                            df.at[index, col_rarity] = next((r for r in all_rarities if r in ans), "C")
                        else:
                            df.at[index, col_rarity] = "C" # 最終保險：通常標題無寫又估唔到嘅都係普通卡 C
                    except:
                        df.at[index, col_rarity] = "C"
                
            progress_bar.progress((index + 1) / len(df))
            time.sleep(2) # 避開限速
            
        st.success("✅ 處理完成！")
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(f"📥 下載 {download_filename}", csv, download_filename, "text/csv")
