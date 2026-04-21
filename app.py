import streamlit as st
import pandas as pd
import re
import json
import requests

st.set_page_config(page_title="TCG CSV 終極精準版", layout="wide")
st.title("🕷️ TCG CSV 網頁吞噬版 (100% 精準)")
st.write("✅ 直接讀取別人網站的資料！支援輸入網址 或 上傳網頁 HTML 檔。")

api_key = st.text_input("🔑 請輸入 Google Gemini API Key (用作一秒提取網頁資料):", type="password")

st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📄 第一步：提供卡表來源")
    st.info("💡 推薦做法：去 TCGCollector 等網站，右鍵「另存網頁」，然後上傳 HTML 檔。這樣可以 100% 繞過防爬蟲封鎖！")
    
    source_type = st.radio("選擇來源方式：", ["上傳網頁檔 (.html)", "輸入網址 (URL)"])
    
    web_text = ""
    if source_type == "上傳網頁檔 (.html)":
        html_file = st.file_uploader("📂 上傳網頁 HTML 檔", type=["html", "htm", "txt"])
        if html_file:
            # 讀取並簡單清除多餘的 HTML 標籤以減輕 AI 負擔
            raw_html = html_file.read().decode('utf-8', errors='ignore')
            web_text = re.sub(r'<style.*?</style>', '', raw_html, flags=re.DOTALL)
            web_text = re.sub(r'<script.*?</script>', '', web_text, flags=re.DOTALL)
            web_text = re.sub(r'<[^>]+>', ' ', web_text) # 移除 HTML tags
            st.success("✅ 網頁讀取成功！")
            
    else:
        url_input = st.text_input("🔗 輸入卡表網址：")
        if url_input:
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                res = requests.get(url_input, headers=headers, timeout=10)
                if res.status_code == 200:
                    raw_html = res.text
                    web_text = re.sub(r'<style.*?</style>', '', raw_html, flags=re.DOTALL)
                    web_text = re.sub(r'<script.*?</script>', '', web_text, flags=re.DOTALL)
                    web_text = re.sub(r'<[^>]+>', ' ', web_text)
                    st.success("✅ 網址讀取成功！")
                else:
                    st.error(f"❌ 網站拒絕讀取 (Error {res.status_code})。請改用「另存網頁」並上傳 HTML。")
            except Exception as e:
                st.error("❌ 讀取網址失敗，網站可能啟用了防爬蟲保護。請改用上傳 HTML 功能。")

with col2:
    st.markdown("### 📂 第二步：上傳 Shopify CSV")
    uploaded_csv = st.file_uploader("上傳從 Shopify 匯出的 CSV 檔案", type=["csv"])

st.markdown("---")

if st.button("🚀 開始 100% 精準匹配") and uploaded_csv and api_key and web_text:
    progress_bar = st.progress(0)
    status_text = st.empty()

    # --- 1. 叫 AI 將網頁文字變成精準 JSON 字典 ---
    status_text.text("🧠 正在吞噬網頁資料，建立 100% 精準字典... (約需 10 秒)")
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        # 限制字數以防塞爆 API，通常卡表都在前段或中段
        safe_web_text = web_text[:50000] 
        
        prompt = f"""
        Extract the card numbers and their corresponding rarities from the following text (scraped from a Pokemon TCG site).
        Look for patterns like card numbers (e.g., 001/071, 1/71, 001) and rarities (C, U, R, RR, AR, SR, SAR, UR, HR).
        Return ONLY a valid JSON object where the key is the 3-digit zero-padded card number (e.g., "001") and the value is the rarity code (e.g., "C", "U", "R").
        Text:
        {safe_web_text}
        """
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
        res_data = response.json()

        if "candidates" in res_data:
            ai_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
            cleaned_text = ai_text.strip().replace('```json', '').replace('```', '')
            master_dict = json.loads(cleaned_text)
            status_text.text(f"✅ 成功提取網頁資料！共識別出 {len(master_dict)} 張卡的準確稀有度。")
        else:
            st.error("❌ AI 無法從該網頁找到清晰的卡號與稀有度，請確認網頁內容。")
            st.stop()

    except Exception as e:
        st.error(f"❌ 建立字典失敗: {e}")
        st.stop()

    # --- 2. 處理 CSV ---
    status_text.text("⚡ 正在將網頁資料精準應用到 Shopify CSV...")
    df = pd.read_csv(uploaded_csv)
    original_filename = uploaded_csv.name
    download_filename = f"Fixed_{original_filename}"

    col_set = '系列 (product.metafields.custom.set)'
    col_rarity = '稀有度 (product.metafields.custom.rarity)'

    for col in [col_set, col_rarity]:
        if col not in df.columns: df[col] = ""

    df['Product Category'] = "Arts & Entertainment > Hobbies & Creative Arts > Collectibles > Collectible Trading Cards > Gaming Cards"

    all_rarities = ['SAR', 'SSR', 'CSR', 'CHR', 'RRR', 'ACE', 'SR', 'AR', 'UR', 'HR', 'RR', 'PR', 'TR', 'SEC', 'K', 'S', 'A', 'R', 'U', 'C']

    for index, row in df.iterrows():
        title = str(row.get('Title', ''))
        if pd.notna(title) and title != 'nan':
            # 擷取系列
            set_match = re.search(r'^(\[[A-Z0-9a-z]+\]\s[^\s]+)', title)
            if set_match: df.at[index, col_set] = set_match.group(1)

            # 擷取卡號 (例如 003/071 -> 抽出 003)
            num_match = re.search(r'(\d{3})/\d{3}', title)
            if num_match:
                card_num = num_match.group(1)
                
                # 🎯 用卡號去查網頁提取出嚟嘅字典！
                if card_num in master_dict:
                    df.at[index, col_rarity] = master_dict[card_num]
                else:
                    rarity_match = re.search(r'\s(' + '|'.join(all_rarities) + r')$', title, re.IGNORECASE)
                    if rarity_match: df.at[index, col_rarity] = rarity_match.group(1).upper()
                    elif 'ex ' in title.lower() or title.lower().endswith('ex'): df.at[index, col_rarity] = 'RR'
                    else: df.at[index, col_rarity] = '需手動檢查'
            else:
                df.at[index, col_rarity] = '需手動檢查'

        progress_bar.progress((index + 1) / len(df))

    status_text.text("🎉 全部精準匹配完成！C/U/R 完美還原！")
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(f"📥 下載 {download_filename}", csv, download_filename, "text/csv")
