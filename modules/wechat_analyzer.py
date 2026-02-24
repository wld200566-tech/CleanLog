"""
CleanLog - 微信日志分析模块
对应鼎甲：备份日志审计、多源异构数据整合、任务异常告警
"""
import csv
import sqlite3
import base64
import io
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns


DINGJIA_SCENARIO = "备份日志审计 · 多源异构数据整合 · 任务异常告警 · 数据治理建议"

# 表头行识别：至少匹配其中 2 个即视为有效表头
HEADER_KEYWORDS = ["交易时间", "交易类型", "交易对方", "商品", "金额", "收/支", "时间", "日期", "支付方式", "交易单号"]

# 微信账单 CSV/Excel 列名映射 → 标准列
WECHAT_BILL_MAPPING = {
    "createTime": ["交易时间", "交易创建时间", "时间", "日期"],
    "content": ["商品", "交易类型", "类型", "备注", "交易说明", "商品说明"],
    "sender": ["交易对方", "对方账户", "商户"],
    "nickname": ["交易对方", "对方账户", "商户"],
    "amount": ["金额(元)", "金额", "交易金额", "订单金额"],
    "type": [],  # 默认 0
}


def _find_header_row(lines: list) -> int:
    """找到包含表头关键词的第一行，至少匹配 2 个关键词"""
    for i, line in enumerate(lines):
        try:
            reader = csv.reader(io.StringIO(line))
            cells = [c.strip().strip('"\'') for row in reader for c in row]
            if not cells:
                continue
            matches = sum(1 for c in cells for kw in HEADER_KEYWORDS if kw in str(c))
            if matches >= 2:
                return i
        except Exception:
            continue
    return -1


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """删除空列、Unnamed 列，清理无效数据"""
    # 删除 Unnamed 和空名列
    drop_cols = [
        c for c in df.columns
        if str(c).startswith("Unnamed") or (isinstance(c, str) and not c.strip())
    ]
    df = df.drop(columns=drop_cols, errors="ignore")
    # 删除全空列
    df = df.dropna(axis=1, how="all")
    # 清理列名：去除前后空白、引号
    df.columns = [str(c).strip().strip('"\'') for c in df.columns]
    return df


def _read_wechat_csv_robust(get_src, raw) -> pd.DataFrame:
    """
    容错读取微信账单 CSV：跳过元数据行，自动定位表头，忽略空列
    """
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            src = get_src()
            if hasattr(src, "seek"):
                src.seek(0)
            content = src.read()
            if isinstance(content, bytes):
                text = content.decode(enc)
            else:
                text = content
            lines = text.replace("\r\n", "\n").replace("\r", "\n").strip().split("\n")
            break
        except (UnicodeDecodeError, Exception):
            continue
    else:
        raise ValueError("无法解码 CSV 文件编码")

    header_row = _find_header_row(lines)
    if header_row < 0:
        raise ValueError("未找到有效表头行（需包含「交易时间」「金额」等关键词）")

    src = get_src()
    if hasattr(src, "seek"):
        src.seek(0)
    df = pd.read_csv(
        src,
        encoding=enc,
        header=header_row,
        dtype=str,
        keep_default_na=False,
    )
    return _clean_dataframe(df)


def _read_wechat_excel_robust(get_src, ext: str) -> pd.DataFrame:
    """
    容错读取微信账单 Excel：尝试定位表头行，清理空列
    """
    engine = "openpyxl" if ext == ".xlsx" else None
    df_raw = pd.read_excel(get_src(), header=None, engine=engine)
    # 查找表头行
    header_row = -1
    for i in range(min(30, len(df_raw))):
        row_vals = [str(v).strip() for v in df_raw.iloc[i].tolist() if pd.notna(v)]
        matches = sum(1 for v in row_vals for kw in HEADER_KEYWORDS if kw in str(v))
        if matches >= 2:
            header_row = i
            break
    if header_row < 0:
        df = df_raw.copy()
    else:
        df = pd.read_excel(get_src(), header=header_row, engine=engine)
    return _clean_dataframe(df)


def load_data(file_path_or_bytes, filename: str = "", time_unit: str = "s") -> pd.DataFrame:
    """
    多格式自动识别加载：支持 .db / .csv / .xlsx / .xls
    - .db: SQLite 查询（聊天消息）
    - .csv / .xlsx / .xls: Pandas 直接读取（账单等表格数据）
    """
    raw = file_path_or_bytes
    if hasattr(raw, "name"):
        filename = filename or getattr(raw, "name", "")
    if hasattr(raw, "getvalue"):
        raw = raw.getvalue()

    fn = (filename or (str(raw) if isinstance(raw, str) else "")).lower()
    ext = Path(fn).suffix.lower() if fn else ""

    def _get_src():
        """每次返回可重新读取的源"""
        if isinstance(raw, bytes):
            return io.BytesIO(raw)
        return raw

    if ext == ".db":
        if not isinstance(raw, str):
            raise ValueError(".db 文件需提供本地路径，不支持上传的二进制流")
        conn = sqlite3.connect(raw)
        query = """
        SELECT m.createTime, m.content, m.type, r.username as sender, r.nickname
        FROM message m LEFT JOIN rcontact r ON m.talker = r.username
        WHERE m.createTime > 0
        """
        df = pd.read_sql(query, conn)
        conn.close()
        df["createTime"] = pd.to_datetime(df["createTime"], unit=time_unit)
    else:
        # CSV 或 Excel
        if ext in (".xlsx", ".xls"):
            df = _read_wechat_excel_robust(_get_src, ext)
        else:
            df = _read_wechat_csv_robust(_get_src(), raw)

        # 映射微信账单列到标准 schema
        def _first_match(col_options):
            cols = [str(c).strip() for c in df.columns]
            for opt in col_options:
                for i, c in enumerate(cols):
                    if c and (c == opt or opt in c):
                        return df.columns[i]
            return None

        df = df.copy()
        time_col = _first_match(WECHAT_BILL_MAPPING["createTime"])
        content_col = _first_match(WECHAT_BILL_MAPPING["content"])
        sender_col = _first_match(WECHAT_BILL_MAPPING["sender"])
        nickname_col = _first_match(WECHAT_BILL_MAPPING["nickname"])

        if time_col is None:
            raise ValueError(f"未找到时间列，当前列: {list(df.columns)}")
        df["createTime"] = pd.to_datetime(df[time_col], errors="coerce")
        df["content"] = (
            df[content_col].astype(str) if content_col
            else df.index.astype(str)
        )
        df["sender"] = df[sender_col].astype(str) if sender_col else "-"
        df["nickname"] = df[nickname_col].astype(str) if nickname_col else df["sender"]
        df["type"] = 0

    df = df.dropna(subset=["createTime"])
    df = df.drop_duplicates(subset=["createTime", "content", "sender"], keep="first")
    df = df[df["content"].astype(str).str.len() < 1000]
    return df


class WeChatAnalyzer:
    """微信日志分析器"""

    TIME_UNIT = "s"

    def __init__(self, file_path: str, time_unit: str = None):
        self.file_path = file_path
        self.messages = None
        if time_unit:
            self.TIME_UNIT = time_unit

    def extract_and_clean(self) -> pd.DataFrame:
        """数据提取与清洗（支持 .db / .csv / .xlsx）"""
        df = load_data(self.file_path, time_unit=self.TIME_UNIT)
        self.messages = df
        return df

    def anomaly_detection(self):
        """异常检测"""
        if self.messages is None:
            return {"night_messages": 0, "anomaly_days": {}, "risk_score": 0.0}

        df = self.messages.copy()
        df["hour"] = df["createTime"].dt.hour
        night_owl = df[(df["hour"] >= 3) & (df["hour"] <= 5)]

        daily_count = df.groupby(df["createTime"].dt.date).size()
        mean_count = daily_count.mean()
        std_count = daily_count.std()

        if pd.isna(std_count) or std_count == 0:
            anomalies = pd.Series(dtype=int)
        else:
            anomalies = daily_count[abs(daily_count - mean_count) > 3 * std_count]

        risk_score = len(anomalies) / len(daily_count) * 100 if len(daily_count) > 0 else 0.0

        return {
            "night_messages": len(night_owl),
            "anomaly_days": anomalies.to_dict(),
            "risk_score": round(risk_score, 2),
        }

    def generate_heatmap(self) -> bytes:
        """生成活跃度热力图"""
        if self.messages is None or self.messages.empty:
            return b""

        df = self.messages.copy()
        weekday_order = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        df["weekday_num"] = df["createTime"].dt.dayofweek
        df["weekday"] = df["weekday_num"].map({i: weekday_order[i] for i in range(7)})
        df["hour"] = df["createTime"].dt.hour

        pivot = df.groupby(["weekday", "hour"]).size().unstack(fill_value=0).reindex(weekday_order)

        fig, ax = plt.subplots(figsize=(14, 6))
        sns.heatmap(pivot, cmap="YlOrRd", annot=False, ax=ax)
        ax.set_title("个人消息活跃度热力图（鼎甲备份任务监控风格）")
        ax.set_xlabel("小时")
        ax.set_ylabel("星期")
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=120)
        plt.close()
        buf.seek(0)
        return buf.read()

    def run(self) -> dict:
        """执行分析，返回标准化报告"""
        df = self.extract_and_clean()
        anomaly = self.anomaly_detection()

        insights = {
            "total_messages": len(df),
            "date_range": (str(df["createTime"].min()), str(df["createTime"].max())),
            "top_contacts": df["nickname"].value_counts().head(10).to_dict(),
            "active_hours": df["createTime"].dt.hour.value_counts().sort_index().to_dict(),
            "message_types": df["type"].value_counts().to_dict(),
            "anomaly": anomaly,
        }

        # 标准化报告
        report = {
            "module": "wechat_analyzer",
            "dingjia_scenario": DINGJIA_SCENARIO,
            "problem_discovery": {
                "总消息数": f"{insights['total_messages']:,}",
                "日期范围": f"{insights['date_range'][0][:10]} ~ {insights['date_range'][1][:10]}",
                "凌晨活跃消息 (3-5点)": f"{anomaly['night_messages']}",
                "异常日数量": f"{len(anomaly['anomaly_days'])}",
                "异常风险分": f"{anomaly['risk_score']}%",
            },
            "cleaning_actions": [
                "已执行：去空、去重、过滤异常长消息",
                "已检测：凌晨异常活跃、单日消息量突增",
                "建议：关注高异常风险日的消息内容",
            ],
            "effect_verification": {
                "数据质量": "已清洗" if len(df) > 0 else "无数据",
                "异常风险分": f"{anomaly['risk_score']}%",
                "活跃联系人 Top1": list(insights["top_contacts"].keys())[0] if insights["top_contacts"] else "-",
            },
            "details": {
                "top_contacts": insights["top_contacts"],
                "message_types": {int(k): int(v) for k, v in insights["message_types"].items()},
            },
            "raw_df": df[["createTime", "content", "sender", "nickname", "type"]].head(1000),
            "report_json": __import__("json").dumps(
                {
                    "total_messages": insights["total_messages"],
                    "date_range": insights["date_range"],
                    "anomaly_risk_score": anomaly["risk_score"],
                    "night_messages": anomaly["night_messages"],
                },
                ensure_ascii=False,
                indent=2,
            ),
        }

        chart_bytes = self.generate_heatmap()
        if chart_bytes:
            report["chart_base64"] = base64.b64encode(chart_bytes).decode()

        return report


def run_wechat_analyzer(db_path: str, time_unit: str = "s") -> dict:
    """对外接口：执行微信日志分析"""
    analyzer = WeChatAnalyzer(db_path, time_unit)
    return analyzer.run()
