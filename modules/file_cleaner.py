"""
CleanLog - 文件去重模块
对应鼎甲：企业级数据治理、备份索引、存储优化
"""
import os
import hashlib
import json
import pandas as pd
from pathlib import Path


DINGJIA_SCENARIO = "企业级数据治理 · 备份索引库 · 客户端 Agent 扫描 · 全局去重 · 存储优化报告"


class FileCleaner:
    """文件去重分析器"""

    def __init__(self, root_paths: list):
        self.root_paths = [Path(p) for p in root_paths]

    def scan_and_index(self):
        """全盘扫描建立索引"""
        file_index = []
        for root in self.root_paths:
            if not root.exists():
                continue
            for file_path in root.rglob("*"):
                if file_path.is_file():
                    try:
                        stat = file_path.stat()
                        file_index.append({
                            "path": str(file_path),
                            "size": stat.st_size,
                            "mtime": stat.st_mtime,
                            "type": file_path.suffix.lower(),
                            "hash": None,
                        })
                    except (PermissionError, OSError):
                        pass
        return pd.DataFrame(file_index)

    def calculate_hashes(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算文件指纹"""

        def file_hash(filepath):
            h = hashlib.md5()
            try:
                with open(filepath, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        h.update(chunk)
                return h.hexdigest()
            except (PermissionError, OSError):
                return None

        df = df.copy()
        df["hash"] = df["path"].apply(file_hash)
        return df

    def run(self, df: pd.DataFrame) -> dict:
        """执行分析，返回标准化报告"""
        if df.empty:
            return self._empty_report()

        df_valid = df[df["hash"].notna()].copy()
        total_files = len(df)
        total_size = df["size"].sum()

        duplicates = df_valid[df_valid.duplicated(subset=["hash"], keep=False)]
        dup_groups = (
            duplicates.groupby("hash")
            .agg({"path": list, "size": "first"})
            .reset_index()
        )

        if dup_groups.empty:
            savings = 0.0
            recommendation = []
        else:
            savings = ((dup_groups["path"].apply(len) - 1) * dup_groups["size"]).sum()
            recommendation = self._generate_recommendation(dup_groups)

        savings_ratio = (savings / total_size * 100) if total_size > 0 else 0.0

        # 标准化报告
        report = {
            "module": "file_cleaner",
            "dingjia_scenario": DINGJIA_SCENARIO,
            "problem_discovery": {
                "扫描文件总数": f"{total_files:,}",
                "总占用容量": f"{total_size / 1e9:.2f} GB",
                "发现重复组": f"{len(dup_groups)} 组",
                "重复文件数": f"{len(duplicates)} 个",
            },
            "cleaning_actions": [
                f"建议保留每组中最新的文件，删除其余副本",
                f"Top 重复组可节省约 {savings / 1e9:.2f} GB",
            ]
            + [f"保留: {r['keep']}，可删 {len(r['delete'])} 个副本" for r in recommendation[:3]],
            "effect_verification": {
                "可节省空间 (GB)": f"{savings / 1e9:.2f}",
                "节省比例 (%)": f"{savings_ratio:.1f}%",
                "去重后预估文件数": f"{total_files - len(duplicates) + len(dup_groups):,}",
            },
            "details": {
                "duplicate_groups": len(dup_groups),
                "potential_savings_gb": round(savings / 1e9, 2),
                "recommendation_preview": recommendation[:5],
            },
            "raw_df": df[["path", "size", "type", "hash"]],
            "report_json": json.dumps(
                {
                    "total_files": total_files,
                    "total_size_gb": round(total_size / 1e9, 2),
                    "duplicate_groups": len(dup_groups),
                    "potential_savings_gb": round(savings / 1e9, 2),
                    "savings_ratio": round(savings_ratio, 2),
                },
                ensure_ascii=False,
                indent=2,
            ),
        }
        return report

    def _empty_report(self):
        return {
            "module": "file_cleaner",
            "dingjia_scenario": DINGJIA_SCENARIO,
            "problem_discovery": {"提示": "未发现任何文件，请检查路径"},
            "cleaning_actions": [],
            "effect_verification": {},
            "details": {},
            "raw_df": pd.DataFrame(),
            "report_json": json.dumps({"error": "no_files"}, ensure_ascii=False),
        }

    def _generate_recommendation(self, dup_groups: pd.DataFrame) -> list:
        actions = []
        for _, row in dup_groups.head(10).iterrows():
            paths = row["path"]
            if not paths:
                continue
            try:
                keep = max(paths, key=lambda p: os.path.getmtime(p))
            except OSError:
                keep = paths[0]
            delete = [p for p in paths if p != keep]
            if delete:
                actions.append({"keep": keep, "delete": delete, "save_space_mb": row["size"] * len(delete) / 1e6})
        return actions


# 兼容主入口命名
FileDeduplicationEngine = FileCleaner


def run_file_cleaner(root_paths: list) -> dict:
    """对外接口：执行文件去重分析"""
    cleaner = FileCleaner(root_paths)
    df = cleaner.scan_and_index()
    df = cleaner.calculate_hashes(df)
    return cleaner.run(df)


def render_file_cleaner_ui():
    """Streamlit 界面：文件去重引擎"""
    import streamlit as st
    from utils.ui_components import (
        render_page_header,
        render_standard_report,
        render_download_section,
        paths_input,
    )

    paths = paths_input(
        "扫描目录（每行一个）",
        [str(Path.home() / "Downloads"), str(Path.home() / "Documents")],
        help_text="输入要扫描的文件夹路径，每行一个",
    )
    st.caption("💡 建议：先选择小目录测试，避免首次扫描过久")

    if st.button("▶ 开始扫描分析", type="primary"):
        with st.spinner("正在扫描文件并计算指纹..."):
            try:
                report = run_file_cleaner(paths)
                render_page_header("文件去重", report["dingjia_scenario"])
                render_standard_report(report)
                render_download_section(report, "file_cleaner")
            except Exception as e:
                st.error(f"执行失败: {e}")
    else:
        render_page_header("文件去重", DINGJIA_SCENARIO)
        st.info("👆 在侧边栏输入扫描目录后，点击运行按钮")
