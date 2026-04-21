import streamlit as st
import pandas as pd
import re
import requests
import json
import time
import base64

st.set_page_config(page_title="TCG CSV 終極辨識工具", layout="wide")
st.title("🎯 TCG CSV 真·智能辨識工具")
st.write("✅ 移除了「不准猜測」的死板限制 | ✅ 使用高級圖片緩存強制獲取官網圖片")

api_key = st.text_input("🔑 請輸入你的 Google Gemini API Key:", type="password")
uploaded_file = st.file_uploader("📂 上傳 CSV 檔案", type=["csv"])

if uploaded_file:
    original_filename = uploaded_file.name
    download_filename = f"Fixed_{original_filename}"
    df = pd.read_csv(uploaded_file)
    st.success(f"成功讀取檔案：{original_filename}")
    
    if st.button("🚀 開始精準處理"):
        col_set = '系列 (product.metafields.custom.set)'
        col_rarity = '稀有度 (product.metafields.custom.rarity)'
        
        for col in [col_set, col_rarity]:
            if col not in df.columns: df[col] = ""
            
        df['Product Category'] = "Arts & Entertainment > Hobbies & Creative Arts > Collectibles > Collectible Trading Cards > Gaming Cards"
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        all_rarities = ['SAR', 'SSR', 'CSR', 'CHR', 'RRR', 'ACE', 'SR', 'AR', 'UR', 'HR', 'RR', 'PR', 'TR', 'K', 'S', 'A', 'R', 'U', 'C']
        
        for index, row in df.iterrows():
            title = str(row.get('Title', ''))
            img_url = str(row.get('Image Src', ''))
            
            status_text.text(f"分析中 ({index+1}/{len(df)}): {title}")
            
            # --- 1. 拆解資料 ---
            set_match = re.search(r'^(\[[A-Z0-9a-z]+\]\s[^\s]+)', title)
            if set_match: 
                df.at[index, col_set] = set_match.group(1)
            
            # --- 2. 判斷稀有度 ---
            rarity_pattern = r'\s(' + '|'.join(all_rarities) + r')$'
            rarity_match = re.search(rarity_pattern, title, re.IGNORECASE)
            
            if rarity_match:
                df.at[index, col_rarity] = rarity_match.group(1).upper()
            elif any(x in title.lower() for x in ['ex ', 'ex']):
                df.at[index, col_rarity] = 'RR'
            else:
                # 🌟 標題冇寫，進入 AI 模式 🌟
                if api_key:
                    try:
                        payload = {"contents": [{"parts": []}]}
                        prompt = f"Identify the rarity of this Pokemon card. Title: '{title}'. Possible rarities: {all_rarities}. Look at the bottom corners of the card for the rarity symbol. Return ONLY the exact rarity code from the list."
                        
                        # 🔥 使用 wsrv.nl 強制緩存並下載官網圖片 🔥
                        img_downloaded = False
                        if pd.notna(img_url) and img_url.startswith('http'):
                            proxy_url = f"https://wsrv.nl/?url={img_url}&output=webp"
                            try:
                                img_res = requests.get(proxy_url, timeout=5)
                                if img_res.status_code == 200:
                                    img_b64 = base64.b64encode(img_res.content).decode("utf-8")
                                    payload["contents"][0]["parts"].append({
                                        "inline_data": {"mime_type": "image/webp", "data": img_b64}
                                    })
                                    img_downloaded = True
                            except:
                                pass
                        
                        # 如果連 Proxy 都死，要求 AI 強制根據編號估算，唔准再答「手動檢查」
                        if not img_downloaded:
                            prompt += " (Image not available. You MUST infer the rarity based on the set code and card number in the title. Give your best exact rarity code.)"
                        
                        payload["contents"][0]["parts"].append({"text": prompt})

                        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
                        res_json = response.json()
                        
                        if "candidates" in res_json:
                            ans = res_json["candidates"][0]["content"]["parts"][0]["text"].strip().upper()
                            matched = next((r for r in all_rarities if r == ans or f" {r}" in ans or ans.startswith(r)), None)
                            if matched:
                                df.at[index, col_rarity] = matched
                            else:
                                df.at[index, col_rarity] = "C" # 如果 AI 答非所問，先畀 C
                        else:
                            df.at[index, col_rarity] = "C" 
                    except Exception as e:
                        df.at[index, col_rarity] = "C"
                else:
                    df.at[index, col_rarity] = "欠 API Key"
                
            progress_bar.progress((index + 1) / len(df))
            time.sleep(2) # 防限速
            
        st.success("✅ 處理完成！")
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(f"📥 下載 {download_filename}", csv, download_filename, "text/csv")
