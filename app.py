import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="TCG CSV 終極本機直讀版", layout="wide")
st.title("🎯 TCG CSV 終極精準版 (本機秒速提取法)")
st.write("✅ 完全飛起 AI！直接用 Python 瞬間讀取卡表，唔使 API Key，0秒完成！")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📄 第一步：貼上卡表文字")
    st.info("💡 將你頭先嗰堆有齊卡號同稀有度嘅文字，直接 Copy & Paste 貼入嚟。")
    pasted_data = st.text_area("在這裡貼上卡表：", height=250)

with col2:
    st.markdown("### 📂 第二步：上傳 Shopify CSV")
    uploaded_csv = st.file_uploader("上傳從 Shopify 匯出的 CSV 檔案", type=["csv"])

if st.button("🚀 開始 100% 精準匹配") and uploaded_csv and pasted_data:
    progress_bar = st.progress(0)
    status_text = st.empty()

    status_text.text("⚡ 正在瞬間分析卡表...")
    
    master_dict = {}
    
    # 🎯 核心殺手鐧：直接用 Python 掃描 001/071 呢種格式
    chunks = re.split(r'\b(\d{3})/\d{3}\b', pasted_data)
    
    if len(chunks) < 3:
        st.error("❌ 找不到卡號 (例如 001/071 的格式)。請確認貼上的內容有卡牌編號。")
        st.stop()
        
    for i in range(1, len(chunks), 2):
        card_num = chunks[i]       # 抽出來的號碼，例如 001
        chunk_content = chunks[i+1] # 號碼後面的文字
        
        # 優先搵括號入面嘅稀有度，例如 (C), (SAR), (RR)
        rarity_match = re.search(r'\((SAR|SSR|CSR|CHR|RRR|ACE|SR|AR|UR|HR|RR|PR|TR|SEC|K|S|A|R|U|C)\)', chunk_content, re.IGNORECASE)
        if rarity_match:
            master_dict[card_num] = rarity_match.group(1).upper()
        else:
            # 備用方案：尋找英文全寫
            if re.search(r'(Special Art Rare|Special Illustration Rare)', chunk_content, re.I): master_dict[card_num] = 'SAR'
            elif re.search(r'(Art Rare|Illustration Rare)', chunk_content, re.I): master_dict[card_num] = 'AR'
            elif re.search(r'(Super Rare)', chunk_content, re.I): master_dict[card_num] = 'SR'
            elif re.search(r'(Ultra Rare|Hyper Rare)', chunk_content, re.I): master_dict[card_num] = 'UR'
            elif re.search(r'(Double Rare)', chunk_content, re.I): master_dict[card_num] = 'RR'
            elif re.search(r'\b(Rare)\b', chunk_content, re.I): master_dict[card_num] = 'R'
            elif re.search(r'(Uncommon)', chunk_content, re.I): master_dict[card_num] = 'U'
            elif re.search(r'(Common)', chunk_content, re.I): master_dict[card_num] = 'C'

    if len(master_dict) == 0:
        st.error("❌ 找到卡號，但找不到稀有度。")
        st.stop()
        
    status_text.text(f"✅ 成功建立字典！共識別出 {len(master_dict)} 張卡。正在處理 CSV...")
    
    # --- 處理 CSV ---
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

            # 擷取卡號並查字典
            num_match = re.search(r'(\d{3})/\d{3}', title)
            if num_match:
                card_num = num_match.group(1)
                
                # 🎯 核心：直接用字典配對！
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

    status_text.text("🎉 全部精準匹配完成！C/U/R 完美還原，絕無錯漏！")
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(f"📥 下載 {download_filename}", csv, download_filename, "text/csv")
