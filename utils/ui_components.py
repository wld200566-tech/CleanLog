"""
CleanLog 统一 UI 组件
侧边栏配置、主内容区、报告卡片、结果下载
"""
import streamlit as st
import pandas as pd
import io
import base64
from pathlib import Path


def render_page_header(title: str, dingjia_scenario: str):
    """页面标题 + 鼎甲业务场景标注"""
    st.title(f"📊 {title}")
    st.caption(f"🏢 对应鼎甲业务场景：{dingjia_scenario}")
    st.divider()


def render_standard_report(report: dict):
    """标准化报告展示：问题发现 → 清洗动作 → 效果验证"""
    # 1. 问题发现
    with st.expander("🔍 问题发现", expanded=True):
        for k, v in report.get("problem_discovery", {}).items():
            st.write(f"**{k}**：{v}")

    # 2. 清洗动作
    if report.get("cleaning_actions"):
        with st.expander("⚙️ 清洗/分析动作"):
            for i, action in enumerate(report["cleaning_actions"], 1):
                st.write(f"{i}. {action}")

    # 3. 效果验证
    with st.expander("✅ 效果验证", expanded=True):
        for k, v in report.get("effect_verification", {}).items():
            st.metric(k, v)

    # 额外详情
    if report.get("details"):
        with st.expander("📋 详细数据"):
            st.json(report["details"])


def render_download_section(report: dict, filename_prefix: str = "report"):
    """结果下载区：支持 JSON、CSV、Excel"""
    if not report:
        return

    col1, col2, col3 = st.columns(3)

    # JSON 报告
    if "report_json" in report:
        with col1:
            st.download_button(
                "📥 下载 JSON 报告",
                report["report_json"],
                file_name=f"{filename_prefix}_report.json",
                mime="application/json",
                use_container_width=True,
            )

    # CSV 数据
    if "raw_df" in report and report["raw_df"] is not None and not report["raw_df"].empty:
        df = report["raw_df"]
        csv = df.to_csv(index=False).encode("utf-8-sig")
        with col2:
            st.download_button(
                "📥 下载 CSV 数据",
                csv,
                file_name=f"{filename_prefix}_data.csv",
                mime="text/csv",
                use_container_width=True,
            )

    # 图表
    if "chart_base64" in report and report["chart_base64"]:
        with col3:
            st.download_button(
                "📥 下载图表",
                base64.b64decode(report["chart_base64"]),
                file_name=f"{filename_prefix}_chart.png",
                mime="image/png",
                use_container_width=True,
            )


def render_sidebar_nav():
    """侧边栏导航：选择功能模块"""
    st.sidebar.title("🧹 CleanLog")
    st.sidebar.markdown("*个人数据治理 · 鼎甲风格*")
    st.sidebar.divider()

    module = st.sidebar.radio(
        "选择功能",
        ["📁 文件去重", "💬 微信分析", "💰 财务对账"],
        label_visibility="collapsed",
    )
    return module


def paths_input(label: str, default_paths: list, help_text: str = ""):
    """多路径输入组件"""
    paths_str = st.sidebar.text_area(
        label,
        value="\n".join(default_paths),
        height=100,
        help=help_text,
    )
    return [p.strip() for p in paths_str.split("\n") if p.strip()]
