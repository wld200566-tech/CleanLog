import streamlit as st

from modules.file_cleaner import render_file_cleaner_ui
from modules.log_analyzer import render_log_analyzer_ui
from modules.finance_etl import render_finance_etl_ui


st.set_page_config(page_title="CleanLog", page_icon="🛡️")
st.title("🛡️ CleanLog - 个人数据治理中心")

st.sidebar.title("功能导航")
module = st.sidebar.radio(
    "选择模块",
    ["📁 智能文件去重", "💬 聊天记录洞察", "💰 多账本对账"],
)

if module == "📁 智能文件去重":
    render_file_cleaner_ui()
elif module == "💬 聊天记录洞察":
    render_log_analyzer_ui()
elif module == "💰 多账本对账":
    render_finance_etl_ui()
else:
    st.write("选择模块开始测试")
