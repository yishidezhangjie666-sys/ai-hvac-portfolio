# 建筑空调系统能耗分析项目

本项目围绕建筑类型与温度相关性、日周期和工作日模式，以及非工作时段高负荷事件进行描述性分析。报告和 PPT 使用同一批生成的统计结果。

## 数据来源

输入是 `../hidden_files/data/` 下已有的四份 CSV：`metadata.csv`、`weather.csv`、`electricity_cleaned.csv`、`chilledwater_cleaned.csv`。现有文件未提供可核验的原始发布网址、许可或表计量纲；项目不修改原始数据。

## 复现步骤

在 `../hidden_files/` 中运行：

```bash
python3 -m pip install pandas numpy matplotlib pillow python-pptx
python3 scripts/load_data.py
python3 scripts/clean_data.py
python3 scripts/analysis.py
python3 scripts/build_deliverables.py --output ../files
```

`clean_data.py` 生成 `clean_summary.csv` 与 `data_quality_report.csv`；`analysis.py` 读取质量筛选结果，只用缺失率不超过 50% 的建筑×表计记录，生成统计表、事件清单及四张图。`build_deliverables.py` 从这些输出重建本目录的文档、PPT、图像副本及简历描述。所有时间按 CSV 中记录的时间戳处理；工作日按周一至周五定义，工作时段按 08:00–18:00 定义。

## 文件清单

| 路径 | 内容 |
|---|---|
| `建筑空调系统能耗分析报告.md` | 五章节正式报告 |
| `建筑空调系统能耗分析.pptx` | 10 页汇报演示，嵌入四张图 |
| `简历描述.txt` | 5 条中文项目经历描述 |
| `figures/*.png` | 报告引用的四张图 |
| `../hidden_files/data_quality_report.csv` | 逐建筑×表计质量等级及纳入标记 |
| `../hidden_files/correlation_by_type.csv` | RQ1 六类建筑统计 |
| `../hidden_files/profile_summary.csv` | RQ2 工作日/周末逐时均值 |
| `../hidden_files/anomaly_period.csv` | RQ3 逐小时标记清单 |
| `../hidden_files/anomaly_events.csv` | RQ3 连续事件清单 |
| `../hidden_files/correlation.csv` | 单建筑×表计相关系数 |
| `../hidden_files/scripts/*.py` | 数据检查、筛选、分析和交付脚本 |
