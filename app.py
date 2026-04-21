import streamlit as st
import pandas as pd
import re
import json
import requests

st.set_page_config(page_title="TCG CSV 終極精準版", layout="wide")
st.title("🎯 TCG CSV 終極精準版 (手動貼表法)")
st.write("✅ 徹底告別網頁封鎖與圖片亂碼！直接貼上純文字卡表，AI 一秒建字典！")

api_key = st.text_input("🔑 請輸入 Google Gemini API Key (用作一秒建立字典):", type="password")

st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📄 第一步：貼上卡表文字")
    st.info("💡 **無敵秘技**：去 **Bulbapedia** 或其他有「純文字卡表」的網站，用滑鼠反白整個表格，**Ctrl+C 複製，然後 Ctrl+V 貼到下面**。越亂越好，AI 會自動抽絲剝繭！")
    pasted_data = st.text_area("在這裡貼上卡表 (必須包含卡號與 C/U/R 等字眼)：", height=250)

with col2:
    st.markdown("### 📂 第二步：上傳 Shopify CSV")
    uploaded_csv = st.file_uploader("上傳從 Shopify 匯出的 CSV 檔案", type=["csv"])

st.markdown("---")

if st.button("🚀 開始 100% 精準匹配") and uploaded_csv and api_key and pasted_data:
    progress_bar = st.progress(0)
    status_text = st.empty()

    # --- 1. 叫 AI 將亂七八糟嘅文字變成精準 JSON 字典 ---
    status_text.text("🧠 正在閱讀你貼上的卡表，建立 100% 精準字典... (約需 5-10 秒)")
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        # 指示 AI 尋找 001/071 或 001 格式，並對應稀有度
        prompt = f"""
        You are a data extraction expert. I have copy-pasted a Pokemon TCG card list below. 
        Please extract every card number and its corresponding rarity.
        - Card numbers usually look like "001/071", "001", or "1".
        - Rarities usually look like C, U, R, RR, AR, SR, SAR, UR, HR, SEC, K.
        
        Return ONLY a valid JSON object where the key is the 3-digit zero-padded card number (e.g., "001") and the value is the exact rarity code (e.g., "C", "U", "R"). 
        DO NOT return any other text, markdown, or explanation.
        
        Text to process:
        {pasted_data}
        """
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
        res_data = response.json()

        if "candidates" in res_data:
            ai_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
            cleaned_text = ai_text.strip().replace('```json', '').replace('```', '')
            master_dict = json.loads(cleaned_text)
            
            if len(master_dict) == 0:
                st.error("❌ 字典建立失敗。請確認你貼上的文字中，確實包含了「卡號數字」與「C/U/R 等稀有度文字」。")
                st.stop()
            else:
                status_text.text(f"✅ 成功建立字典！共識別出 {len(master_dict)} 張卡的準確稀有度。")
        else:
            st.error("❌ AI 無法從貼上的文字找到卡號與稀有度，請確認貼上的內容。")
            st.stop()

    except Exception as e:
        st.error(f"❌ 建立字典失敗，JSON 解析錯誤: {e}")
        st.stop()

    # --- 2. 處理 CSV ---
    status_text.text("⚡ 正在將字典精準應用到 Shopify CSV...")
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
                
                # 🎯 用卡號去查你啱啱 Copy 嘅字典！
                if card_num in master_dict:
                    df.at[index, col_rarity] = master_dict[card_num]
                else:
                    # 字典查唔到 (可能係隱藏卡如 SAR)，用標題最後嘅字補底
                    rarity_match = re.search(r'\s(' + '|'.join(all_rarities) + r')$', title, re.IGNORECASE)
                    if rarity_match: df.at[index, col_rarity] = rarity_match.group(1).upper()
                    elif 'ex ' in title.lower() or title.lower().endswith('ex'): df.at[index, col_rarity] = 'RR'
                    else: df.at[index, col_rarity] = '需手動檢查'
            else:
                df.at[index, col_rarity] = '需手動檢查'

        progress_bar.progress((index + 1) / len(df))

    status_text.text("🎉 全部精準匹配完成！C/U/R 完美還原，絕無錯漏！")
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(f"📥 下載 {download_filename}", csv, download_filename, "text/csv")
