"""
手动情报中心 - Streamlit
URL 订单序列解析 + 飞书物流匹配 + 状态表与一键复制（无自动化填单、无 RPA）
"""
import re
import warnings

import pyperclip
import streamlit as st

warnings.filterwarnings("ignore", category=FutureWarning)


def parse_feishu_shipping_map(text: str) -> dict:
    """从飞书粘贴文本解析 订单号 -> 物流号。"""
    shipping_map = {}
    order_pattern = re.compile(r"\d{3}-\d{7}-\d{7}")
    token_pattern = re.compile(r"[A-Za-z0-9]+")
    for line in text.splitlines():
        m = order_pattern.search(line)
        if not m:
            continue
        order_no = m.group(0)
        remain = line.replace(order_no, " ", 1)
        preferred, fallback = [], []
        for raw in remain.split():
            if "-" in raw:
                continue
            for token in token_pattern.findall(raw):
                if len(token) <= 5 or len(token) >= 25:
                    continue
                if token.startswith(("TBA", "XM")):
                    preferred.append(token)
                else:
                    fallback.append(token)
        if preferred or fallback:
            shipping_map[order_no] = (preferred or fallback)[0]
    return shipping_map


st.set_page_config(page_title="手动情报中心 - 物流单号", layout="wide")
st.title("📋 手动情报中心")
st.caption("快 · 准 · 稳：匹配后点「复制」即可粘贴到亚马逊，无需划线选中。")

st.markdown("---")
st.subheader("第一步：解析亚马逊订单序列")
url_input = st.text_input(
    "发货页 URL（用于提取订单号）",
    placeholder="https://sellercentral.amazon.com/orders-v3/bulk-confirm-shipment/...",
    key="ship_url_input",
)

if url_input:
    order_pattern = re.compile(r"\d{3}-\d{7}-\d{7}")
    web_orders = order_pattern.findall(url_input)
    if web_orders:
        st.success(f"已提取 {len(web_orders)} 个订单号")
        st.session_state["web_orders"] = web_orders
    else:
        st.error("URL 中未发现有效订单号")
        st.session_state.pop("web_orders", None)

if "web_orders" not in st.session_state:
    st.stop()

st.markdown("---")
st.subheader("第二步：飞书物流 + 一键匹配")

if "shipping_map" not in st.session_state:
    st.session_state["shipping_map"] = {}

fs_text = st.text_area(
    "粘贴飞书订单与物流号（每行含订单号与物流号）",
    height=200,
    placeholder="例如：111-1234567-1234567 1Z999AA10123456784",
    key="feishu_paste_area",
)

if st.button("🔍 匹配", type="primary", use_container_width=True, key="btn_match"):
    st.session_state["shipping_map"] = parse_feishu_shipping_map(fs_text)
    st.session_state["match_done"] = True

if st.session_state.get("match_done"):
    shipping_map = st.session_state["shipping_map"]
    web_orders = st.session_state["web_orders"]

    st.markdown("---")
    st.subheader("匹配结果")
    st.markdown("下方每行：`st.code` 自带一键复制；右侧按钮可将物流号写入系统剪贴板。")
    h = st.columns([0.6, 2.2, 2.8, 1.2])
    h[0].markdown("**序号**")
    h[1].markdown("**订单号**")
    h[2].markdown("**物流号**")
    h[3].markdown("**操作**")

    for i, order_no in enumerate(web_orders):
        trk = shipping_map.get(order_no)
        c0, c1, c2, c3 = st.columns([0.6, 2.2, 2.8, 1.2])
        c0.write(i + 1)
        c1.code(order_no, language=None)
        if trk:
            c2.code(trk, language=None)
        else:
            c2.warning("未匹配到物流号")
        btn_label = "复制物流号" if trk else "无内容"
        if c3.button(btn_label, key=f"copy_trk_{i}_{order_no}", disabled=not trk):
            pyperclip.copy(trk)
            try:
                st.toast("已复制到剪贴板", icon="✅")
            except Exception:
                st.success("已复制到剪贴板")

    missing = sum(1 for o in web_orders if o not in shipping_map)
    if missing:
        st.warning(f"仍有 {missing} 个订单未匹配到物流号，请补全飞书数据后再次点击「匹配」。")
