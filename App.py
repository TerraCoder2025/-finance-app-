# app1.py - 带用户登录的智能记账本
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import json
import os
import hashlib
import secrets


class UserManager:
    def __init__(self):
        self.users_file = "users.json"
        self.setup_users_file()

    def setup_users_file(self):
        """初始化用户文件"""
        if not os.path.exists(self.users_file):
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)

    def hash_password(self, password):
        """密码加密"""
        return hashlib.sha256(password.encode()).hexdigest()

    def register_user(self, username, password):
        """注册新用户"""
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                users = json.load(f)

            if username in users:
                return False, "用户名已存在"

            # 创建用户数据目录
            user_data_dir = f"user_data/{username}"
            os.makedirs(user_data_dir, exist_ok=True)

            # 保存用户信息
            users[username] = {
                "password_hash": self.hash_password(password),
                "created_at": datetime.now().isoformat(),
                "data_dir": user_data_dir
            }

            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(users, f, ensure_ascii=False, indent=2)

            # 初始化用户数据文件
            self.init_user_data(username)
            return True, "注册成功"

        except Exception as e:
            return False, f"注册失败: {str(e)}"

    def verify_user(self, username, password):
        """验证用户登录"""
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                users = json.load(f)

            if username in users and users[username]["password_hash"] == self.hash_password(password):
                return True, "登录成功"
            else:
                return False, "用户名或密码错误"

        except Exception as e:
            return False, f"登录失败: {str(e)}"

    def init_user_data(self, username):
        """初始化用户数据"""
        user_data_file = f"user_data/{username}/finance_data.json"
        if not os.path.exists(user_data_file):
            initial_data = {
                'transactions': [],
                'bank_accounts': {},
                'debts': {},
                'budgets': {
                    "餐饮": {"预算金额": 1000, "已用金额": 0, "周期": "月度", "币种": "人民币"},
                    "购物": {"预算金额": 2000, "已用金额": 0, "周期": "月度", "币种": "人民币"},
                    "交通": {"预算金额": 500, "已用金额": 0, "周期": "月度", "币种": "人民币"},
                    "娱乐": {"预算金额": 800, "已用金额": 0, "周期": "月度", "币种": "人民币"},
                    "医疗": {"预算金额": 300, "已用金额": 0, "周期": "月度", "币种": "人民币"}
                }
            }
            with open(user_data_file, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, ensure_ascii=False, indent=2)


class FinanceApp:
    def __init__(self, username):
        self.username = username
        self.data_file = f"user_data/{username}/finance_data.json"
        self.setup_session_state()
        self.load_data()

    def setup_session_state(self):
        """初始化会话状态"""
        if 'transactions' not in st.session_state:
            st.session_state.transactions = pd.DataFrame(columns=[
                '日期', '类型', '类别', '项目描述', '金额', '币种', '支付方式', '对方账户', '汇率', '备注'
            ])

        if 'bank_accounts' not in st.session_state:
            st.session_state.bank_accounts = {}

        if 'debts' not in st.session_state:
            st.session_state.debts = {}

        if 'budgets' not in st.session_state:
            st.session_state.budgets = {}

        # 初始化编辑状态
        if 'editing_index' not in st.session_state:
            st.session_state.editing_index = None
        if 'editing_debt' not in st.session_state:
            st.session_state.editing_debt = None
        if 'editing_budget' not in st.session_state:
            st.session_state.editing_budget = None

    def load_data(self):
        """从文件加载数据"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if 'transactions' in data and data['transactions']:
                    st.session_state.transactions = pd.DataFrame(data['transactions'])
                if 'bank_accounts' in data:
                    st.session_state.bank_accounts = data['bank_accounts']
                if 'debts' in data:
                    st.session_state.debts = data['debts']
                if 'budgets' in data:
                    st.session_state.budgets = data['budgets']

                self.calculate_budget_usage()
        except Exception as e:
            st.error(f"加载数据失败: {e}")

    def save_data(self):
        """保存数据到文件"""
        try:
            data = {
                'transactions': st.session_state.transactions.to_dict('records'),
                'bank_accounts': st.session_state.bank_accounts,
                'debts': st.session_state.debts,
                'budgets': st.session_state.budgets
            }
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            st.error(f"保存数据失败: {e}")

    def calculate_budget_usage(self):
        """计算预算使用情况"""
        for category in st.session_state.budgets:
            st.session_state.budgets[category]["已用金额"] = 0

        if not st.session_state.transactions.empty:
            df = st.session_state.transactions.copy()
            df['日期'] = pd.to_datetime(df['日期'])
            current_month = datetime.now().strftime('%Y-%m')
            df['年月'] = df['日期'].dt.strftime('%Y-%m')

            monthly_expenses = df[(df['类型'] == '支出') & (df['年月'] == current_month)]

            for category, group in monthly_expenses.groupby('类别'):
                if category in st.session_state.budgets:
                    budget_currency = st.session_state.budgets[category].get("币种", "人民币")
                    category_expenses = group[group['币种'] == budget_currency]
                    st.session_state.budgets[category]["已用金额"] = category_expenses['金额'].sum()

    def get_currency_statistics(self, df):
        """获取币种统计信息"""
        currency_stats = {}

        income_by_currency = df[df['类型'] == '收入'].groupby('币种')['金额'].sum()
        for currency, amount in income_by_currency.items():
            if currency not in currency_stats:
                currency_stats[currency] = {'收入': 0, '支出': 0}
            currency_stats[currency]['收入'] = amount

        expense_by_currency = df[df['类型'] == '支出'].groupby('币种')['金额'].sum()
        for currency, amount in expense_by_currency.items():
            if currency not in currency_stats:
                currency_stats[currency] = {'收入': 0, '支出': 0}
            currency_stats[currency]['支出'] = amount

        for currency in currency_stats:
            currency_stats[currency]['结余'] = (
                    currency_stats[currency]['收入'] - currency_stats[currency]['支出']
            )

        return currency_stats

    def sidebar(self):
        """侧边栏"""
        st.sidebar.title(f"💼 {self.username}的记账本")
        st.sidebar.markdown("---")

        # 快速统计
        total_assets = sum(account["余额"] for account in st.session_state.bank_accounts.values())
        total_debts = sum(debt["剩余"] for debt in st.session_state.debts.values())
        net_worth = total_assets - total_debts

        st.sidebar.metric("💰 总资产", f"¥{total_assets:,.2f}")
        st.sidebar.metric("📋 总债务", f"¥{total_debts:,.2f}")
        st.sidebar.metric("🏆 净资产", f"¥{net_worth:,.2f}")

        st.sidebar.markdown("---")

        # 银行卡快速查看
        st.sidebar.subheader("🏦 银行卡余额")
        for account, info in st.session_state.bank_accounts.items():
            currency_symbol = "¥" if info["币种"] == "人民币" else "RM"
            st.sidebar.write(f"**{account}**: {currency_symbol}{info['余额']:,.2f}")

        st.sidebar.markdown("---")

        # 退出登录按钮
        if st.sidebar.button("🚪 退出登录", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.current_user = None
            st.rerun()

        st.sidebar.info("💡 提示：数据自动保存，仅您本人可见")

    def add_transaction_form(self):
        """添加交易表单"""
        st.header("➕ 添加新交易")

        with st.form("transaction_form", clear_on_submit=True):
            col1, col2 = st.columns(2)

            with col1:
                date = st.date_input("📅 日期", datetime.now())
                transaction_type = st.selectbox("🔸 类型", ["收入", "支出", "转账"])
                category = st.selectbox("📂 类别", self.get_categories(transaction_type))
                description = st.text_input("📝 项目描述", placeholder="例如：11月工资、超市购物等")
                amount = st.number_input("💰 金额", min_value=0.0, step=0.01, format="%.2f")

            with col2:
                currency = st.selectbox("🌐 币种", ["人民币", "马币"])

                payment_options = list(st.session_state.bank_accounts.keys()) + ["现金", "微信支付", "支付宝"]
                payment_method = st.selectbox("💳 支付方式", payment_options)

                if transaction_type == "转账":
                    target_options = list(st.session_state.bank_accounts.keys()) + ["现金", "微信支付", "支付宝",
                                                                                    "其他银行卡"]
                    target_account = st.selectbox("➡️ 对方账户", target_options)
                    exchange_rate = st.number_input("🔁 汇率", min_value=0.0, step=0.01, value=1.0, format="%.2f")

                    is_self_transfer = (payment_method in st.session_state.bank_accounts and
                                        target_account in st.session_state.bank_accounts)

                    if is_self_transfer:
                        st.info("💡 本人账户间转账，不计入收支")
                    else:
                        st.info("💡 向他人转账，将计入支出")
                else:
                    target_account = ""
                    exchange_rate = 1.0

                notes = st.text_input("📋 备注", placeholder="可选备注信息")

            submitted = st.form_submit_button("✅ 添加交易", use_container_width=True)

            if submitted:
                if amount <= 0:
                    st.error("❌ 金额必须大于0")
                elif transaction_type == "转账" and payment_method == target_account:
                    st.error("❌ 转账时支付方式和对方账户不能相同")
                else:
                    self.add_transaction({
                        '日期': date.strftime("%Y-%m-%d"),
                        '类型': transaction_type,
                        '类别': category,
                        '项目描述': description,
                        '金额': amount,
                        '币种': currency,
                        '支付方式': payment_method,
                        '对方账户': target_account,
                        '汇率': exchange_rate,
                        '备注': notes
                    })
                    st.success("✅ 交易添加成功！")
                    self.save_data()

    def get_categories(self, transaction_type):
        """根据交易类型返回类别"""
        income_categories = ["工资", "兼职", "投资收入", "奖金", "退款", "其他收入"]
        expense_categories = ["房租", "水电费", "生活费", "奶粉", "学费", "购物", "餐饮", "交通", "娱乐", "医疗",
                              "还款", "其他支出"]

        if transaction_type == "收入":
            return income_categories
        elif transaction_type == "支出":
            return expense_categories
        else:
            return [""]

    def add_transaction(self, transaction_data):
        """添加交易到数据"""
        new_transaction = pd.DataFrame([transaction_data])
        st.session_state.transactions = pd.concat([st.session_state.transactions, new_transaction], ignore_index=True)

        self.update_bank_balance(transaction_data)

        if transaction_data['类型'] == '支出' and transaction_data['类别'] == '还款':
            self.update_debt(transaction_data['金额'])

        if transaction_data['类型'] == '支出' and transaction_data['类别'] in st.session_state.budgets:
            self.calculate_budget_usage()

    def update_bank_balance(self, transaction):
        """更新银行卡余额"""
        payment_method = transaction['支付方式']
        amount = transaction['金额']
        transaction_type = transaction['类型']

        if payment_method in st.session_state.bank_accounts:
            if transaction_type == "收入":
                st.session_state.bank_accounts[payment_method]["余额"] += amount
            elif transaction_type == "支出":
                st.session_state.bank_accounts[payment_method]["余额"] -= amount
            elif transaction_type == "转账":
                target_account = transaction['对方账户']
                exchange_rate = transaction['汇率']

                is_self_transfer = (payment_method in st.session_state.bank_accounts and
                                    target_account in st.session_state.bank_accounts)

                if is_self_transfer:
                    st.session_state.bank_accounts[payment_method]["余额"] -= amount
                    st.session_state.bank_accounts[target_account]["余额"] += amount * exchange_rate
                else:
                    st.session_state.bank_accounts[payment_method]["余额"] -= amount

    def update_debt(self, amount):
        """更新债务"""
        for debt_name in st.session_state.debts:
            if st.session_state.debts[debt_name]["状态"] == "还款中":
                remaining = st.session_state.debts[debt_name]["剩余"]
                if remaining > 0:
                    new_remaining = max(0, remaining - amount)
                    st.session_state.debts[debt_name]["剩余"] = new_remaining
                    if new_remaining == 0:
                        st.session_state.debts[debt_name]["状态"] = "已还清"
                    break

    def show_transactions(self):
        """显示交易记录"""
        st.header("📊 交易记录")

        if not st.session_state.transactions.empty:
            # 筛选功能
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                filter_type = st.selectbox("筛选类型", ["全部", "收入", "支出", "转账"])
            with col2:
                filter_category = st.selectbox("筛选类别",
                                               ["全部"] + list(st.session_state.transactions['类别'].unique()))
            with col3:
                bank_options = list(st.session_state.bank_accounts.keys()) + ["现金", "微信支付", "支付宝"]
                filter_bank = st.selectbox("筛选支付方式", ["全部"] + bank_options)
            with col4:
                date_range = st.selectbox("时间范围", ["全部", "最近7天", "最近30天", "本月"])

            filtered_df = st.session_state.transactions.copy()

            if filter_type != "全部":
                filtered_df = filtered_df[filtered_df['类型'] == filter_type]
            if filter_category != "全部":
                filtered_df = filtered_df[filtered_df['类别'] == filter_category]
            if filter_bank != "全部":
                filtered_df = filtered_df[filtered_df['支付方式'] == filter_bank]

            if date_range != "全部":
                today = datetime.now().date()
                if date_range == "最近7天":
                    start_date = today - timedelta(days=7)
                elif date_range == "最近30天":
                    start_date = today - timedelta(days=30)
                elif date_range == "本月":
                    start_date = today.replace(day=1)

                filtered_df['日期'] = pd.to_datetime(filtered_df['日期'])
                filtered_df = filtered_df[filtered_df['日期'] >= pd.Timestamp(start_date)]
                filtered_df['日期'] = filtered_df['日期'].dt.strftime('%Y-%m-%d')

            st.dataframe(
                filtered_df.style.format({
                    '金额': '{:,.2f}',
                    '汇率': '{:.2f}'
                }),
                use_container_width=True,
                height=400
            )

            # 币种统计
            st.subheader("💰 币种统计")
            currency_stats = self.get_currency_statistics(filtered_df)

            if currency_stats:
                cols = st.columns(len(currency_stats))
                for i, (currency, stats) in enumerate(currency_stats.items()):
                    with cols[i]:
                        currency_symbol = "¥" if currency == "人民币" else "RM"
                        st.metric(f"{currency}收入", f"{currency_symbol}{stats['收入']:,.2f}")
                        st.metric(f"{currency}支出", f"{currency_symbol}{stats['支出']:,.2f}")
                        st.metric(f"{currency}结余", f"{currency_symbol}{stats['结余']:,.2f}")

        else:
            st.info("📝 暂无交易记录，请添加第一笔交易")

    def show_bank_accounts(self):
        """显示银行卡信息"""
        st.header("🏦 银行卡管理")

        # 添加银行卡
        st.subheader("➕ 添加银行卡")
        with st.form("add_bank_form"):
            col1, col2, col3 = st.columns(3)

            with col1:
                bank_name = st.text_input("银行卡名称", placeholder="例如：中国银行储蓄卡")
            with col2:
                initial_balance = st.number_input("初始余额", min_value=0.0, step=100.0, value=0.0, format="%.2f")
            with col3:
                bank_currency = st.selectbox("币种", ["人民币", "马币"])

            submitted = st.form_submit_button("✅ 添加银行卡", use_container_width=True)

            if submitted:
                if bank_name and bank_name.strip():
                    if bank_name not in st.session_state.bank_accounts:
                        st.session_state.bank_accounts[bank_name] = {
                            "余额": initial_balance,
                            "币种": bank_currency
                        }
                        st.success(f"✅ 成功添加银行卡: {bank_name}")
                        self.save_data()
                        st.rerun()
                    else:
                        st.error("❌ 银行卡名称已存在")
                else:
                    st.error("❌ 请输入银行卡名称")

        st.markdown("---")

        # 显示银行卡列表
        if st.session_state.bank_accounts:
            st.subheader("💳 银行卡列表")
            bank_data = []
            for account, info in st.session_state.bank_accounts.items():
                currency_symbol = "¥" if info["币种"] == "人民币" else "RM"
                bank_data.append({
                    "银行卡": account,
                    "币种": info["币种"],
                    "当前余额": f"{currency_symbol}{info['余额']:,.2f}"
                })

            bank_df = pd.DataFrame(bank_data)
            st.dataframe(bank_df, use_container_width=True)

            # 余额图表
            st.subheader("📊 银行卡余额分布")
            chart_data = []
            for account, info in st.session_state.bank_accounts.items():
                chart_data.append({
                    "银行卡": account,
                    "余额": info["余额"],
                    "币种": info["币种"]
                })

            chart_df = pd.DataFrame(chart_data)
            fig = px.bar(chart_df, x='银行卡', y='余额', title='银行卡余额分布', color='银行卡')
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("🏦 暂无银行卡数据，请先添加银行卡")

    def show_debts(self):
        """显示债务管理"""
        st.header("📋 债务管理")

        # 添加债务
        st.subheader("➕ 添加新债务")
        with st.form("add_debt_form"):
            col1, col2, col3 = st.columns(3)

            with col1:
                debt_name = st.text_input("债务名称", placeholder="例如：信用卡、个人借款等")
            with col2:
                debt_total = st.number_input("借款总额", min_value=0.0, step=100.0, value=1000.0, format="%.2f")
            with col3:
                debt_remaining = st.number_input("剩余金额", min_value=0.0, step=100.0, value=1000.0, format="%.2f")

            submitted = st.form_submit_button("✅ 添加债务")

            if submitted:
                if debt_name and debt_name.strip():
                    if debt_name not in st.session_state.debts:
                        status = "已还清" if debt_remaining == 0 else "还款中"
                        st.session_state.debts[debt_name] = {
                            "总额": debt_total,
                            "剩余": debt_remaining,
                            "状态": status
                        }
                        st.success(f"✅ 成功添加债务: {debt_name}")
                        self.save_data()
                        st.rerun()
                    else:
                        st.error("❌ 债务名称已存在")
                else:
                    st.error("❌ 请输入债务名称")

        st.markdown("---")

        # 显示债务列表
        if st.session_state.debts:
            st.subheader("📊 债务概览")
            debt_data = []
            for debt_name, debt_info in st.session_state.debts.items():
                total = debt_info["总额"]
                remaining = debt_info["剩余"]
                paid = total - remaining
                progress = (paid / total * 100) if total > 0 else 0

                debt_data.append({
                    "债务名称": debt_name,
                    "借款总额": f"¥{total:,.2f}",
                    "剩余金额": f"¥{remaining:,.2f}",
                    "已还金额": f"¥{paid:,.2f}",
                    "还款进度": f"{progress:,.1f}%",
                    "状态": debt_info["状态"]
                })

            debt_df = pd.DataFrame(debt_data)
            st.dataframe(debt_df, use_container_width=True)
        else:
            st.info("📝 暂无债务数据，请先添加债务")

    def show_budgets(self):
        """显示预算管理"""
        st.header("💰 预算管理")

        if st.session_state.budgets:
            st.subheader("📊 预算执行情况")
            budget_data = []
            for category, budget_info in st.session_state.budgets.items():
                currency = budget_info.get("币种", "人民币")
                budget_amount = budget_info["预算金额"]
                used_amount = budget_info["已用金额"]
                remaining = budget_amount - used_amount
                usage_percent = (used_amount / budget_amount * 100) if budget_amount > 0 else 0
                currency_symbol = "¥" if currency == "人民币" else "RM"

                if usage_percent <= 80:
                    status = "正常"
                elif usage_percent <= 100:
                    status = "警告"
                else:
                    status = "超支"

                budget_data.append({
                    "类别": category,
                    "币种": currency,
                    "预算金额": f"{currency_symbol}{budget_amount:,.2f}",
                    "已用金额": f"{currency_symbol}{used_amount:,.2f}",
                    "剩余金额": f"{currency_symbol}{remaining:,.2f}",
                    "使用进度": f"{usage_percent:.1f}%",
                    "状态": status
                })

            budget_df = pd.DataFrame(budget_data)
            st.dataframe(budget_df, use_container_width=True)
        else:
            st.info("📝 暂无预算数据")

    def show_analytics(self):
        """显示分析图表"""
        st.header("📈 财务分析")

        if not st.session_state.transactions.empty:
            # 收支分析
            st.subheader("💰 收支分析")
            currency_stats = self.get_currency_statistics(st.session_state.transactions)

            if currency_stats:
                col1, col2 = st.columns(2)

                with col1:
                    # 收入饼图
                    income_data = []
                    for currency, stats in currency_stats.items():
                        if stats['收入'] > 0:
                            income_data.append({'币种': currency, '金额': stats['收入']})

                    if income_data:
                        income_df = pd.DataFrame(income_data)
                        fig_income = px.pie(income_df, values='金额', names='币种', title='收入币种分布')
                        st.plotly_chart(fig_income, use_container_width=True)

                with col2:
                    # 支出饼图
                    expense_data = []
                    for currency, stats in currency_stats.items():
                        if stats['支出'] > 0:
                            expense_data.append({'币种': currency, '金额': stats['支出']})

                    if expense_data:
                        expense_df = pd.DataFrame(expense_data)
                        fig_expense = px.pie(expense_df, values='金额', names='币种', title='支出币种分布')
                        st.plotly_chart(fig_expense, use_container_width=True)
        else:
            st.info("暂无足够数据进行分析")

    def run_app(self):
        """运行应用"""
        self.sidebar()

        tabs = st.tabs([
            "💰 添加交易", "📊 交易记录", "🏦 银行卡", "📋 债务管理", "💰 预算管理", "📈 财务分析"
        ])

        with tabs[0]:
            self.add_transaction_form()
        with tabs[1]:
            self.show_transactions()
        with tabs[2]:
            self.show_bank_accounts()
        with tabs[3]:
            self.show_debts()
        with tabs[4]:
            self.show_budgets()
        with tabs[5]:
            self.show_analytics()


def main():
    """主函数"""
    st.set_page_config(
        page_title="智能记账本 - 安全版",
        page_icon="🔒",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # 初始化会话状态
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'current_user' not in st.session_state:
        st.session_state.current_user = None

    # 自定义CSS
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .login-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 2rem;
        border: 1px solid #ddd;
        border-radius: 10px;
        background-color: #f9f9f9;
    }
    </style>
    """, unsafe_allow_html=True)

    # 用户管理
    user_manager = UserManager()

    if not st.session_state.logged_in:
        # 登录/注册界面
        st.markdown('<h1 class="main-header">🔒 智能记账本 - 安全版</h1>', unsafe_allow_html=True)

        tab1, tab2 = st.tabs(["🚪 登录", "📝 注册"])

        with tab1:
            with st.form("login_form"):
                st.subheader("用户登录")
                username = st.text_input("用户名", placeholder="请输入用户名")
                password = st.text_input("密码", type="password", placeholder="请输入密码")
                login_btn = st.form_submit_button("登录", use_container_width=True)

                if login_btn:
                    if username and password:
                        success, message = user_manager.verify_user(username, password)
                        if success:
                            st.session_state.logged_in = True
                            st.session_state.current_user = username
                            st.success(f"欢迎回来，{username}！")
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.error("请输入用户名和密码")

        with tab2:
            with st.form("register_form"):
                st.subheader("新用户注册")
                new_username = st.text_input("用户名", placeholder="请输入用户名（3-20位字符）")
                new_password = st.text_input("密码", type="password", placeholder="请输入密码（至少6位）")
                confirm_password = st.text_input("确认密码", type="password", placeholder="请再次输入密码")
                register_btn = st.form_submit_button("注册", use_container_width=True)

                if register_btn:
                    if new_username and new_password and confirm_password:
                        if len(new_username) < 3 or len(new_username) > 20:
                            st.error("用户名长度应在3-20位之间")
                        elif len(new_password) < 6:
                            st.error("密码长度至少6位")
                        elif new_password != confirm_password:
                            st.error("两次输入的密码不一致")
                        else:
                            success, message = user_manager.register_user(new_username, new_password)
                            if success:
                                st.success(message)
                                st.info("请返回登录页面进行登录")
                            else:
                                st.error(message)
                    else:
                        st.error("请填写所有字段")

    else:
        # 已登录，显示主应用
        finance_app = FinanceApp(st.session_state.current_user)
        finance_app.run_app()


if __name__ == "__main__":
    main()