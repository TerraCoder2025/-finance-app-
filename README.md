# 💰 智能记账本

一个基于Streamlit开发的个人财务管理应用，帮助用户轻松管理收入、支出、债务和预算。

![财务分析](https://img.shields.io/badge/版本-1.0.0-brightgreen)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28%2B-red)

## ✨ 功能特色

### 📊 交易记录管理
- 完整的收入、支出、转账记录
- 支持多币种（人民币、马币）
- 智能分类和筛选
- 交易记录编辑和删除

### 🏦 多银行卡管理
- 支持多个银行账户
- 实时余额跟踪
- 银行卡间转账
- 余额分布可视化

### 📋 债务管理系统
- **智能还款功能** - 指定还款银行卡和债务
- 债务进度跟踪
- 支持添加新债务
- 债务信息编辑

### 💰 预算管理
- 自定义预算类别
- 预算执行情况监控
- 预算使用进度可视化
- 超支预警提醒

### 📈 财务分析
- 收支趋势图表
- 币种统计分析
- 支出类别分布
- 月度财务报告

### 📤 数据管理
- CSV格式数据导出
- 交易记录导出
- 自动数据保存
- 本地JSON存储

## 🚀 快速开始

### 在线使用（推荐）
直接访问：[Streamlit Cloud部署链接]

### 本地运行
```bash
# 1. 克隆项目
git clone https://github.com/TerraCoder2025/finance-app.git

# 2. 进入项目目录
cd finance-app

# 3. 安装依赖
pip install -r requirements.txt

# 4. 运行应用
streamlit run App.py
