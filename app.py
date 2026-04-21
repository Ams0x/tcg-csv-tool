import streamlit as st
import pandas as pd
import re
import time
import requests
 
st.set_page_config(page_title="TCG CSV 稀有度填充工具", layout="wide")
st.title("🃏 TCG CSV 稀有度填充工具 (Pokémon TCG API 版)")
st.write("✅ 智能本地過濾 | ✅ Pokémon TCG API 精準查詢 | ✅ 自動填入系列 + 稀有度")
 
# ── Rarity mapping: English API → Short Code ──────────────────────────────
RARITY_MAP = {
    "Common": "C",
    "Uncommon": "U",
    "Rare": "R",
    "Double Rare": "RR",
    "Rare Holo": "R",
    "Rare Holo EX": "RR",
    "Rare Holo GX": "RR",
    "Rare Holo V": "RR",
    "Rare Holo VMAX": "RR",
    "Rare Holo VSTAR": "RR",
    "Ultra Rare": "UR",
    "Special Illustration Rare": "SAR",
    "Illustration Rare": "AR",
    "Super Rare": "SR",
    "Hyper Rare": "UR",
    "Rare Secret": "UR",
    "Trainer Gallery Rare Holo": "TR",
    "ACE SPEC Rare": "ACE",
    "Promo": "PR",
    "Amazing Rare": "AR",
    "Radiant Rare": "R",
    "Shiny Rare": "SR",
    "Shiny Ultra Rare": "SAR",
}
 
# ── Set ID mapping: title bracket code → pokemontcg.io set ID ────────────
SET_ID_MAP = {
    "SV1": "sv1", "SV1A": "sve", "SV1S": "sv1",
    "SV2": "sv2", "SV2A": "sv3pt5", "SV2P": "sv2p",
    "SV3": "sv3", "SV3A": "sv3a", "SV3P": "sv4",  # placeholder
    "SV4": "sv4", "SV4A": "sv4pt5", "SV4K": "sv4pt5",
    "SV5": "sv5", "SV5A": "sv5a", "SV5K": "sv5",
    "SV6": "sv6", "SV6A": "sv6a",
    "SV7": "sv7", "SV7A": "sv7a",
    "SV8": "sv8", "SV8A": "sv8a",
    # Add more as needed
}
 
# Inline local rarity rules (fast, no API needed)
ALL_RARITIES_LOCAL = [
    'SAR', 'SSR', 'CHR', 'RRR', 'ACE', 'CSR',
    'SR', 'AR', 'UR', 'HR', 'RR', 'PR', 'TR',
    'SEC', 'K', 'S', 'A', 'R', 'U', 'C'
]
TRAINER_KW = ['道具', '工具', '能量', 'Item', 'Tool', 'Trainer', '訓練家', '釣竿', '牛奶', '反轉']
 
# Cache for API calls
@st.cache_data(ttl=3600)
def query_ptcg_api(set_id: str, number: str) -> str | None:
    """Query Pokémon TCG API and return short rarity code or None."""
    try:
        # Strip leading zeros for API query
        num_clean = str(int(number)) if number.isdigit() else number
        url = f"https://api.pokemontcg.io/v2/cards?q=set.id:{set_id}+number:{num_clean}"
        resp = requests.get(url, timeout=8)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if data.get("data"):
            card = data["data"][0]
            api_rarity = card.get("rarity", "")
            return RARITY_MAP.get(api_rarity, None)
    except Exception:
        pass
    return None
 
def extract_set_local(title: str) -> str:
    """Extract set name from title bracket."""
    SET_NAMES = {
        'SV1': '[SV1] 朱與紫', 'SV1A': '[SV1a] 三連音爆', 'SV1S': '[SV1s] 朱與紫',
        'SV2': '[SV2] 雪原之神', 'SV2A': '[SV2a] 寶可夢151', 'SV2P': '[SV2P] 冰雪險境',
        'SV3': '[SV3] 黑焰支配者', 'SV3A': '[SV3a] 怪獸之島', 'SV3P': '[SV3P] 黑焰支配者',
        'SV4': '[SV4] 古代的轟鳴', 'SV4A': '[SV4a] 超電磁波', 'SV4K': '[SV4K] 蒼藍的圓盤',
        'SV5': '[SV5] 時空的裂縫', 'SV5A': '[SV5a] 閃烙龍的歸來', 'SV5K': '[SV5K] 碧藍之面具',
        'SV6': '[SV6] 面具的變革', 'SV6A': '[SV6a] 夜明之島',
        'SV7': '[SV7] 星晶奇蹟', 'SV7A': '[SV7a] 悠然時光',
        'SV8': '[SV8] 超越宇宙', 'SV8A': '[SV8a] 閃烙聯盟',
    }
    m = re.search(r'\[([A-Z0-9]+)\]', title, re.IGNORECASE)
    if not m:
        return ''
    code = m.group(1).upper()
    return SET_NAMES.get(code, f'[{code}]')
 
def extract_rarity_local(title: str) -> str:
    """Local rarity extraction: explicit > trainer/energy > ex rule > C default."""
    sorted_rv = sorted(ALL_RARITIES_LOCAL, key=len, reverse=True)
    for rv in sorted_rv:
        if re.search(r'(?:^|\s)' + rv + r'(?:\s|$)', title):
            return rv
    for kw in TRAINER_KW:
        if kw.lower() in title.lower():
            return 'U'
    if re.search(r'ex(?:\s|$)', title, re.IGNORECASE):
        return 'RR'
    return ''  # Return empty → will try API
 
def parse_set_and_number(title: str):
    """Return (set_code_upper, card_number_str) or (None, None)."""
    # Match [SV2P] ... 028/071 or 28/071
    m = re.search(r'\[([A-Z0-9]+)\].*?(\d{3})/\d{3}', title, re.IGNORECASE)
    if m:
        return m.group(1).upper(), m.group(2)
    m2 = re.search(r'\[([A-Z0-9]+)\].*?(\d+)/\d+', title, re.IGNORECASE)
    if m2:
        return m2.group(1).upper(), m2.group(2)
    return None, None
 
 
# ── UI ───────────────────────────────────────────────────────────────────
uploaded_file = st.file_uploader("📂 上傳從 Shopify 匯出的 CSV 檔案", type=["csv"])
 
st.info(
    "**工作原理：**\n"
    "1. 先用本地規則從卡名抽取稀有度（ex卡→RR，道具→U，名字末有稀有度代碼直接用）\n"
    "2. 本地搵唔到嘅卡，自動用 **Pokémon TCG API** 按 [系列代號 + 卡號] 查詢精確稀有度\n"
    "3. API 都查唔到嘅才填 C（通常係訓練家牌或 Promo）"
)
 
if uploaded_file:
    original_filename = uploaded_file.name
    download_filename = f"Fixed_{original_filename}"
    df = pd.read_csv(uploaded_file)
    st.success(f"✅ 成功讀取：{original_filename}，共 {len(df)} 行")
 
    col_set = '系列 (product.metafields.custom.set)'
    col_rarity = '稀有度 (product.metafields.custom.rarity)'
    title_col = 'Title'
 
    product_rows = df[df[title_col].notna() & (df[title_col].str.strip() != '')]
    st.write(f"📊 有效 Product 行數：**{len(product_rows)}**")
 
    # Preview
    if col_rarity in df.columns:
        missing_rarity = df[
            df[title_col].notna() &
            (df[title_col].str.strip() != '') &
            (df[col_rarity].isna() | (df[col_rarity].str.strip() == ''))
        ]
        st.write(f"⚠️ 目前缺少稀有度的行數：**{len(missing_rarity)}**")
 
    use_api = st.checkbox("🌐 啟用 Pokémon TCG API 查詢（更精準，但較慢）", value=True)
    api_delay = st.slider("API 請求間隔 (秒)", 0.3, 2.0, 0.5, 0.1) if use_api else 0
 
    if st.button("🚀 開始處理"):
        # Ensure columns exist
        for col in [col_set, col_rarity]:
            if col not in df.columns:
                df[col] = ""
        df['Product Category'] = "Arts & Entertainment > Hobbies & Creative Arts > Collectibles > Collectible Trading Cards > Gaming Cards"
 
        progress_bar = st.progress(0)
        status_text = st.empty()
        metrics = st.empty()
 
        local_filled = 0
        api_filled = 0
        api_failed = 0
        api_calls = 0
 
        rows_to_process = df[
            df[title_col].notna() &
            (df[title_col].str.strip() != '')
        ].index.tolist()
        total = len(rows_to_process)
 
        for i, idx in enumerate(rows_to_process):
            title = str(df.at[idx, title_col])
 
            # ── Set ──────────────────────────────────────────────────────
            if pd.isna(df.at[idx, col_set]) or str(df.at[idx, col_set]).strip() == '':
                s = extract_set_local(title)
                if s:
                    df.at[idx, col_set] = s
 
            # ── Rarity: try local first ───────────────────────────────────
            current_rarity = str(df.at[idx, col_rarity]).strip() if pd.notna(df.at[idx, col_rarity]) else ''
            if current_rarity == '' or current_rarity == 'nan':
                local_r = extract_rarity_local(title)
                if local_r:
                    df.at[idx, col_rarity] = local_r
                    local_filled += 1
                elif use_api:
                    # ── Try Pokémon TCG API ───────────────────────────────
                    set_code, card_num = parse_set_and_number(title)
                    if set_code and card_num:
                        set_id = SET_ID_MAP.get(set_code)
                        if set_id:
                            status_text.text(f"🌐 API 查詢中：{title[:50]}...")
                            api_rarity = query_ptcg_api(set_id, card_num)
                            api_calls += 1
                            if api_rarity:
                                df.at[idx, col_rarity] = api_rarity
                                api_filled += 1
                            else:
                                df.at[idx, col_rarity] = 'C'
                                api_failed += 1
                            time.sleep(api_delay)
                        else:
                            df.at[idx, col_rarity] = 'C'
                            api_failed += 1
                    else:
                        df.at[idx, col_rarity] = 'C'
                        api_failed += 1
                else:
                    df.at[idx, col_rarity] = 'C'
                    local_filled += 1
 
            progress_bar.progress((i + 1) / total)
            if (i + 1) % 10 == 0 or (i + 1) == total:
                metrics.markdown(
                    f"**本地填充:** {local_filled} | **API 查到:** {api_filled} | "
                    f"**API 查唔到(填C):** {api_failed} | **API 請求數:** {api_calls}"
                )
 
        status_text.text("✅ 全部處理完成！")
        progress_bar.progress(1.0)
 
        # Results summary
        st.success(f"🎉 完成！本地填充 {local_filled} 張，API 精準填充 {api_filled} 張，{api_failed} 張填 C")
 
        # Preview table
        preview_cols = [title_col, col_set, col_rarity]
        st.dataframe(df[[c for c in preview_cols if c in df.columns]].head(30))
 
        # Download
        csv_bytes = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            f"📥 下載 {download_filename}",
            csv_bytes,
            download_filename,
            "text/csv",
            key="download_btn"
        )
 
