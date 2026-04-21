import streamlit as st
import pandas as pd
import re
import requests
import json
import time
import base64
import cloudscraper

st.set_page_config(page_title="TCG CSV 終極視覺處理工具", layout="wide")
st.title("👁️ TCG Shopify CSV 終極視覺處理工具 (突破防線版)")
st.write("✅ 標題齊全 = 一秒極速處理 | ✅ 標題殘缺 = 自動突破防線下載圖片，強迫 AI 睇圖！")

api_key = st.text_input("🔑 請輸入你的 Google Gemini API Key (用作睇圖補底):", type="password")
uploaded_file = st.file_uploader("📂 上傳從 Shopify 匯出的 CSV 檔案", type=["csv"])

if uploaded_file:
    original_filename = uploaded_file.name
    download_filename = f"Fixed_{original_filename}"
    
    df = pd.read_csv(uploaded_file)
    st.success(f"成功讀取檔案：{original_filename}，總共有 {len(df)} 件產品。")
    
    if st.button("🚀 開始智能處理"):
        col_set = '系列 (product.metafields.custom.set)'
        col_rarity = '稀有度 (product.metafields.custom.rarity)'
        
        if col_set not in df.columns:
            df[col_set] = ""
        if col_rarity not in df.columns:
            df[col_rarity] = ""
            
        df['Product Category'] = "Arts & Entertainment > Hobbies & Creative Arts > Collectibles > Collectible Trading Cards > Gaming Cards"
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        all_rarities = ['SAR', 'SSR', 'CSR', 'CHR', 'RRR', 'ACE', 'SR', 'AR', 'UR', 'HR', 'RR', 'PR', 'TR', 'K', 'S', 'A', 'R', 'U', 'C']
        
        # 🛠️ 建立突破防線嘅模擬瀏覽器 (扮成真人用 Chrome 睇網頁)
        scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
        
        for index, row in df.iterrows():
            title = str(row.get('Title', ''))
            img_url = str(row.get('Image Src', ''))
            
            if pd.notna(title) and title != 'nan':
                # --- 1. 擷取系列 ---
                set_match = re.search(r'^(\[[A-Z0-9a-z]+\]\s[^\s]+)', title)
                if set_match:
                    df.at[index, col_set] = set_match.group(1)
                else:
                    backup_match = re.search(r'(\[.*?\])', title)
                    if backup_match:
                        df.at[index, col_set] = backup_match.group(1)

                # --- 2. 擷取稀有度 (有寫就秒速抽) ---
                rarity_pattern = r'\s(' + '|'.join(all_rarities) + r')$'
                rarity_match = re.search(rarity_pattern, title, re.IGNORECASE)
                
                if rarity_match:
                    df.at[index, col_rarity] = rarity_match.group(1).upper()
                elif 'ex ' in title or title.endswith('ex'):
                    df.at[index, col_rarity] = 'RR'
                elif ' VMAX ' in title or title.endswith('VMAX') or ' VSTAR ' in title or title.endswith('VSTAR'):
                    df.at[index, col_rarity] = 'RRR'
                elif ' V ' in title or title.endswith('V'):
                    df.at[index, col_rarity] = 'RR'
                else:
                    # --- 3. 終極 AI 睇圖補底 (遇到標題無寫嘅卡) ---
                    if api_key:
                        status_text.text(f"👁️ 標題無寫，正嘗試下載圖片畀 AI 分析: {title} ...")
                        try:
                            rarity_str = ", ".join(all_rarities)
                            text_prompt = f"You are a Pokemon TCG expert. Look at this card image and its name: '{title}'. Return ONLY the rarity code from this list: [{rarity_str}]. No other text. Check the bottom left or right corner of the card for the rarity symbol."
                            
                            payload = {"contents": [{"parts": [{"text": text_prompt}]}]}
                            
                            # 📸 嘗試下載圖片並轉換畀 AI 睇
                            if pd.notna(img_url) and img_url.startswith('http'):
                                try:
                                    img_response = scraper.get(img_url, timeout=10)
                                    if img_response.status_code == 200:
                                        img_b64 = base64.b64encode(img_response.content).decode("utf-8")
                                        payload["contents"][0]["parts"].append({
                                            "inline_data": {
                                                "mime_type": "image/jpeg",
                                                "data": img_b64
                                            }
                                        })
                                except Exception:
                                    pass # 如果真係極端情況下死 Link，就跌返落純文字模式
                            
                            # 呼叫支援視覺嘅 gemini-1.5-flash 大腦
                            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                            headers = {"Content-Type": "application/json"}
                            
                            response = requests.post(url, json=payload, headers=headers)
                            response_data = response.json()
                            
                            if "candidates" in response_data:
                                ai_rarity = response_data["candidates"][0]["content"]["parts"][0]["text"].strip().upper()
                                if any(r == ai_rarity for r in all_rarities):
                                    df.at[index, col_rarity] = ai_rarity
                                else:
                                    matched_rarity = next((r for r in all_rarities if r in ai_rarity), '需手動檢查')
                                    df.at[index, col_rarity] = matched_rarity
                            else:
                                df.at[index, col_rarity] = '需手動檢查'
                                
                            time.sleep(3) # 睇圖需時，俾 AI 抖 3 秒避免當機
                        except Exception as e:
                            df.at[index, col_rarity] = 'API錯誤'
                    else:
                        df.at[index, col_rarity] = '欠 API Key'
                        
            progress_bar.progress((index + 1) / len(df))
            
        status_text.text("✅ 全部處理完成！")
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(f"📥 下載 {download_filename}", csv, download_filename, "text/csv")

elif uploaded_file and not api_key:
    st.warning("請先喺上面輸入 API Key 呀！")
