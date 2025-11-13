import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import json
import os


class FinanceApp:
    def __init__(self):
        self.data_file = "finance_data.json"
        self.setup_session_state()
        self.load_data()

    def setup_session_state(self):
        """初始化会话状态"""
        if 'transactions' not in st.session_state:
            st.session_state.transactions = pd.DataFrame(columns=[
                '日期', '类型', '类别', '项目描述', '金额', '币种', '支付方式', '对方账户', '汇率', '备注'
            ])

        if 'bank_accounts' not in st.session_state:
            st.session_state.bank_accounts = {
                "中国银行": {"余额": 20200, "币种": "人民币"},
                "浦发银行": {"余额": 4044, "币种": "人民币"},
                "Maybank": {"余额": 644.28, "币种": "马币"},
                "农业银行": {"余额": 0, "币种": "人民币"},
                "建设银行": {"余额": 0, "币种": "人民币"},
                "工商银行": {"余额": 0, "币种": "人民币"}
            }

        if 'debts' not in st.session_state:
            st.session_state.debts = {
                "花呗": {"总额": 1650, "剩余": 0, "状态": "已还清"},
                "白条": {"总额": 13782.24, "剩余": 13782.24, "状态": "还款中", "月供": 810.72},
                "金条": {"总额": 86112, "剩余": 86112, "状态": "还款中", "月供": 3744},
                "其他贷款": {"总额": 20000, "剩余": 20000, "状态": "还款中"}
            }

        # 初始化预算
        if 'budgets' not in st.session_state:
            st.session_state.budgets = {
                "餐饮": {"预算金额": 1000, "已用金额": 0, "周期": "月度", "币种": "人民币"},
                "购物": {"预算金额": 2000, "已用金额": 0, "周期": "月度", "币种": "人民币"},
                "交通": {"预算金额": 500, "已用金额": 0, "周期": "月度", "币种": "人民币"},
                "娱乐": {"预算金额": 800, "已用金额": 0, "周期": "月度", "币种": "人民币"},
                "医疗": {"预算金额": 300, "已用金额": 0, "周期": "月度", "币种": "人民币"}
            }

        # 初始化编辑状态
        if 'editing_index' not in st.session_state:
            st.session_state.editing_index = None

        # 初始化债务管理状态
        if 'editing_debt' not in st.session_state:
            st.session_state.editing_debt = None

        # 初始化预算管理状态
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

                # 重新计算预算使用情况
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
        # 重置所有预算的已用金额
        for category in st.session_state.budgets:
            st.session_state.budgets[category]["已用金额"] = 0

        # 计算本月支出
        if not st.session_state.transactions.empty:
            df = st.session_state.transactions.copy()
            df['日期'] = pd.to_datetime(df['日期'])
            current_month = datetime.now().strftime('%Y-%m')
            df['年月'] = df['日期'].dt.strftime('%Y-%m')

            # 只计算本月的支出
            monthly_expenses = df[(df['类型'] == '支出') & (df['年月'] == current_month)]

            for category, group in monthly_expenses.groupby('类别'):
                if category in st.session_state.budgets:
                    # 只统计相同币种的支出
                    budget_currency = st.session_state.budgets[category].get("币种", "人民币")
                    category_expenses = group[group['币种'] == budget_currency]
                    st.session_state.budgets[category]["已用金额"] = category_expenses['金额'].sum()

    def get_currency_statistics(self, df):
        """获取币种统计信息"""
        currency_stats = {}

        # 收入统计
        income_by_currency = df[df['类型'] == '收入'].groupby('币种')['金额'].sum()
        for currency, amount in income_by_currency.items():
            if currency not in currency_stats:
                currency_stats[currency] = {'收入': 0, '支出': 0}
            currency_stats[currency]['收入'] = amount

        # 支出统计
        expense_by_currency = df[df['类型'] == '支出'].groupby('币种')['金额'].sum()
        for currency, amount in expense_by_currency.items():
            if currency not in currency_stats:
                currency_stats[currency] = {'收入': 0, '支出': 0}
            currency_stats[currency]['支出'] = amount

        # 计算结余
        for currency in currency_stats:
            currency_stats[currency]['结余'] = (
                    currency_stats[currency]['收入'] - currency_stats[currency]['支出']
            )

        return currency_stats

    def sidebar(self):
        """侧边栏"""
        st.sidebar.title("💼 智能记账本")
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
        st.sidebar.info("💡 提示：所有数据自动实时保存")

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
                payment_method = st.selectbox("💳 支付方式",
                                              list(st.session_state.bank_accounts.keys()) + ["现金", "微信支付",
                                                                                             "支付宝"])

                # 改进的转账功能
                if transaction_type == "转账":
                    target_account = st.selectbox("➡️ 对方账户",
                                                  list(st.session_state.bank_accounts.keys()) + ["现金", "微信支付",
                                                                                                 "支付宝",
                                                                                                 "其他银行卡"])
                    exchange_rate = st.number_input("🔁 汇率", min_value=0.0, step=0.01, value=1.0, format="%.2f")

                    # 判断是否为本人账户间转账
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

        # 更新银行卡余额
        self.update_bank_balance(transaction_data)

        # 如果是还款，更新债务
        if transaction_data['类型'] == '支出' and transaction_data['类别'] == '还款':
            self.update_debt(transaction_data['金额'])

        # 更新预算使用情况
        if transaction_data['类型'] == '支出' and transaction_data['类别'] in st.session_state.budgets:
            self.calculate_budget_usage()

    def edit_transaction(self, index, updated_data):
        """编辑交易记录"""
        if 0 <= index < len(st.session_state.transactions):
            # 获取原始交易数据
            original_transaction = st.session_state.transactions.iloc[index].copy()

            # 恢复原始交易的影响
            self.reverse_bank_balance(original_transaction)
            if original_transaction['类型'] == '支出' and original_transaction['类别'] == '还款':
                self.reverse_debt(original_transaction['金额'])

            # 更新交易数据
            for key, value in updated_data.items():
                st.session_state.transactions.at[index, key] = value

            # 应用新交易的影响
            self.update_bank_balance(updated_data)
            if updated_data['类型'] == '支出' and updated_data['类别'] == '还款':
                self.update_debt(updated_data['金额'])

            # 更新预算使用情况
            self.calculate_budget_usage()

            return True
        return False

    def delete_transaction(self, index):
        """删除交易记录"""
        if 0 <= index < len(st.session_state.transactions):
            # 获取要删除的交易信息
            transaction = st.session_state.transactions.iloc[index]

            # 恢复银行卡余额
            self.reverse_bank_balance(transaction)

            # 恢复债务状态（如果是还款）
            if transaction['类型'] == '支出' and transaction['类别'] == '还款':
                self.reverse_debt(transaction['金额'])

            # 删除交易记录
            st.session_state.transactions = st.session_state.transactions.drop(index).reset_index(drop=True)

            # 更新预算使用情况
            if transaction['类型'] == '支出' and transaction['类别'] in st.session_state.budgets:
                self.calculate_budget_usage()

            st.success("✅ 交易记录删除成功！")
            self.save_data()
            return True
        return False

    def reverse_bank_balance(self, transaction):
        """反向更新银行卡余额（用于删除或编辑交易时恢复）"""
        payment_method = transaction['支付方式']
        amount = transaction['金额']
        transaction_type = transaction['类型']

        if payment_method in st.session_state.bank_accounts:
            if transaction_type == "收入":
                st.session_state.bank_accounts[payment_method]["余额"] -= amount
            elif transaction_type == "支出":
                st.session_state.bank_accounts[payment_method]["余额"] += amount
            elif transaction_type == "转账":
                target_account = transaction['对方账户']
                exchange_rate = transaction['汇率']

                # 判断是否为本人账户间转账
                is_self_transfer = (payment_method in st.session_state.bank_accounts and
                                    target_account in st.session_state.bank_accounts)

                if is_self_transfer:
                    # 本人账户间转账：恢复原始状态
                    st.session_state.bank_accounts[payment_method]["余额"] += amount
                    st.session_state.bank_accounts[target_account]["余额"] -= amount * exchange_rate
                else:
                    # 向他人转账：恢复为支出前的状态
                    st.session_state.bank_accounts[payment_method]["余额"] += amount

    def reverse_debt(self, amount):
        """反向更新债务（用于删除或编辑交易时恢复）"""
        for debt_name in st.session_state.debts:
            if st.session_state.debts[debt_name]["状态"] == "已还清" and st.session_state.debts[debt_name]["剩余"] == 0:
                st.session_state.debts[debt_name]["剩余"] = amount
                st.session_state.debts[debt_name]["状态"] = "还款中"
                break
            elif st.session_state.debts[debt_name]["状态"] == "还款中":
                st.session_state.debts[debt_name]["剩余"] += amount
                break

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

                # 判断是否为本人账户间转账
                is_self_transfer = (payment_method in st.session_state.bank_accounts and
                                    target_account in st.session_state.bank_accounts)

                if is_self_transfer:
                    # 本人账户间转账：不计入收支，只是资金转移
                    st.session_state.bank_accounts[payment_method]["余额"] -= amount
                    st.session_state.bank_accounts[target_account]["余额"] += amount * exchange_rate
                else:
                    # 向他人转账：计入支出
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
            # 添加筛选功能
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                filter_type = st.selectbox("筛选类型", ["全部", "收入", "支出", "转账"])
            with col2:
                filter_category = st.selectbox("筛选类别",
                                               ["全部"] + list(st.session_state.transactions['类别'].unique()))
            with col3:
                filter_bank = st.selectbox("筛选银行卡", ["全部"] + list(st.session_state.bank_accounts.keys()))
            with col4:
                date_range = st.selectbox("时间范围", ["全部", "最近7天", "最近30天", "本月"])

            # 应用筛选
            filtered_df = st.session_state.transactions.copy()

            if filter_type != "全部":
                filtered_df = filtered_df[filtered_df['类型'] == filter_type]
            if filter_category != "全部":
                filtered_df = filtered_df[filtered_df['类别'] == filter_category]
            if filter_bank != "全部":
                filtered_df = filtered_df[filtered_df['支付方式'] == filter_bank]

            # 时间筛选
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

            # 显示数据
            st.dataframe(
                filtered_df.style.format({
                    '金额': '{:,.2f}',
                    '汇率': '{:.2f}'
                }),
                use_container_width=True,
                height=400
            )

            # 交易管理功能
            st.subheader("🛠️ 交易管理")
            col1, col2 = st.columns([3, 1])

            with col1:
                if not filtered_df.empty:
                    # 显示带索引的交易记录供选择
                    manage_options = []
                    for idx, row in filtered_df.iterrows():
                        option_text = f"{row['日期']} - {row['类型']} - {row['类别']} - {row['项目描述']} - {row['币种']}{row['金额']:,.2f}"
                        manage_options.append((idx, option_text))

                    selected_option = st.selectbox(
                        "选择要管理的交易记录",
                        options=manage_options,
                        format_func=lambda x: x[1],
                        key="manage_select"
                    )

                    if selected_option:
                        original_index = selected_option[0]

            with col2:
                st.write("")  # 空行用于对齐
                col_edit, col_delete = st.columns(2)

                with col_edit:
                    if st.button("✏️ 编辑", use_container_width=True):
                        st.session_state.editing_index = original_index
                        st.rerun()

                with col_delete:
                    if st.button("❌ 删除", use_container_width=True):
                        if self.delete_transaction(original_index):
                            st.rerun()

            # 编辑交易表单
            if st.session_state.editing_index is not None:
                self.show_edit_form(st.session_state.editing_index)

            # 币种统计信息
            st.subheader("💰 币种统计")
            currency_stats = self.get_currency_statistics(filtered_df)

            if currency_stats:
                cols = st.columns(len(currency_stats))
                for i, (currency, stats) in enumerate(currency_stats.items()):
                    with cols[i]:
                        currency_symbol = "¥" if currency == "人民币" else "RM"
                        st.metric(
                            f"{currency}收入",
                            f"{currency_symbol}{stats['收入']:,.2f}"
                        )
                        st.metric(
                            f"{currency}支出",
                            f"{currency_symbol}{stats['支出']:,.2f}"
                        )
                        st.metric(
                            f"{currency}结余",
                            f"{currency_symbol}{stats['结余']:,.2f}",
                            delta=f"{currency_symbol}{stats['结余']:,.2f}"
                        )

        else:
            st.info("📝 暂无交易记录，请添加第一笔交易")

    def show_edit_form(self, index):
        """显示编辑交易表单"""
        st.subheader("✏️ 编辑交易记录")

        transaction = st.session_state.transactions.iloc[index]

        with st.form("edit_transaction_form"):
            col1, col2 = st.columns(2)

            with col1:
                date = st.date_input("📅 日期", datetime.strptime(transaction['日期'], "%Y-%m-%d"))
                transaction_type = st.selectbox("🔸 类型", ["收入", "支出", "转账"],
                                                index=["收入", "支出", "转账"].index(transaction['类型']))
                category = st.selectbox("📂 类别", self.get_categories(transaction_type),
                                        index=self.get_categories(transaction_type).index(transaction['类别'])
                                        if transaction['类别'] in self.get_categories(transaction_type) else 0)
                description = st.text_input("📝 项目描述", value=transaction['项目描述'])
                amount = st.number_input("💰 金额", min_value=0.0, step=0.01, value=float(transaction['金额']),
                                         format="%.2f")

            with col2:
                currency = st.selectbox("🌐 币种", ["人民币", "马币"],
                                        index=["人民币", "马币"].index(transaction['币种']))
                payment_method = st.selectbox("💳 支付方式",
                                              list(st.session_state.bank_accounts.keys()) + ["现金", "微信支付",
                                                                                             "支付宝"],
                                              index=(list(st.session_state.bank_accounts.keys()) + ["现金", "微信支付",
                                                                                                    "支付宝"]).index(
                                                  transaction['支付方式']))

                if transaction_type == "转账":
                    target_account = st.selectbox("➡️ 对方账户",
                                                  list(st.session_state.bank_accounts.keys()) + ["现金", "微信支付",
                                                                                                 "支付宝",
                                                                                                 "其他银行卡"],
                                                  index=(list(st.session_state.bank_accounts.keys()) + ["现金",
                                                                                                        "微信支付",
                                                                                                        "支付宝",
                                                                                                        "其他银行卡"]).index(
                                                      transaction['对方账户'])
                                                  if transaction['对方账户'] in (
                                                              list(st.session_state.bank_accounts.keys()) + ["现金",
                                                                                                             "微信支付",
                                                                                                             "支付宝",
                                                                                                             "其他银行卡"]) else 0)
                    exchange_rate = st.number_input("🔁 汇率", min_value=0.0, step=0.01,
                                                    value=float(transaction['汇率']), format="%.2f")

                    # 判断是否为本人账户间转账
                    is_self_transfer = (payment_method in st.session_state.bank_accounts and
                                        target_account in st.session_state.bank_accounts)

                    if is_self_transfer:
                        st.info("💡 本人账户间转账，不计入收支")
                    else:
                        st.info("💡 向他人转账，将计入支出")
                else:
                    target_account = transaction['对方账户']
                    exchange_rate = float(transaction['汇率'])

                notes = st.text_input("📋 备注", value=transaction['备注'])

            col_save, col_cancel = st.columns(2)
            with col_save:
                submitted = st.form_submit_button("💾 保存修改", use_container_width=True)
            with col_cancel:
                if st.form_submit_button("❌ 取消", use_container_width=True):
                    st.session_state.editing_index = None
                    st.rerun()

            if submitted:
                if amount <= 0:
                    st.error("❌ 金额必须大于0")
                elif transaction_type == "转账" and payment_method == target_account:
                    st.error("❌ 转账时支付方式和对方账户不能相同")
                else:
                    updated_data = {
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
                    }

                    if self.edit_transaction(index, updated_data):
                        st.success("✅ 交易记录修改成功！")
                        st.session_state.editing_index = None
                        self.save_data()
                        st.rerun()

    def show_bank_accounts(self):
        """显示银行卡信息"""
        st.header("🏦 银行卡管理")

        # 创建银行卡数据表格
        bank_data = []
        for account, info in st.session_state.bank_accounts.items():
            currency_symbol = "¥" if info["币种"] == "人民币" else "RM"
            bank_data.append({
                "银行卡": account,
                "币种": info["币种"],
                "当前余额": f"{currency_symbol}{info['余额']:,.2f}",
                "状态": "正常"
            })

        bank_df = pd.DataFrame(bank_data)
        st.dataframe(bank_df, use_container_width=True)

        # 银行卡余额图表
        st.subheader("💳 银行卡余额分布")

        # 直接使用原始余额数据，避免字符串转换
        chart_data = []
        for account, info in st.session_state.bank_accounts.items():
            chart_data.append({
                "银行卡": account,
                "余额": info["余额"],
                "币种": info["币种"]
            })

        chart_df = pd.DataFrame(chart_data)

        fig = px.bar(
            chart_df,
            x='银行卡',
            y='余额',
            title='银行卡余额分布',
            color='银行卡',
            labels={'余额': '余额', '银行卡': '银行卡'}
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    def show_debts(self):
        """显示债务管理页面"""
        st.header("📋 债务管理")

        # 还款功能
        st.subheader("💰 还款功能")
        with st.form("repayment_form"):
            col1, col2, col3 = st.columns(3)

            with col1:
                # 选择要还款的债务
                active_debts = {name: info for name, info in st.session_state.debts.items()
                                if info["状态"] == "还款中"}
                if active_debts:
                    debt_to_repay = st.selectbox("选择要还款的债务", list(active_debts.keys()))
                    max_repayment = active_debts[debt_to_repay]["剩余"]
                    st.info(f"剩余金额: ¥{max_repayment:,.2f}")
                else:
                    debt_to_repay = None
                    st.info("暂无需要还款的债务")

            with col2:
                # 选择还款银行卡
                repayment_bank = st.selectbox("选择还款银行卡", list(st.session_state.bank_accounts.keys()))
                bank_balance = st.session_state.bank_accounts[repayment_bank]["余额"]
                bank_currency = st.session_state.bank_accounts[repayment_bank]["币种"]
                st.info(f"当前余额: {bank_balance:,.2f} {bank_currency}")

            with col3:
                # 还款金额
                if debt_to_repay:
                    repayment_amount = st.number_input("还款金额",
                                                       min_value=0.0,
                                                       max_value=min(max_repayment, bank_balance),
                                                       step=100.0,
                                                       value=min(max_repayment, bank_balance),
                                                       format="%.2f")
                else:
                    repayment_amount = 0

            notes = st.text_input("还款备注", placeholder="例如：10月还款")

            submitted = st.form_submit_button("✅ 确认还款", use_container_width=True)

            if submitted:
                if debt_to_repay and repayment_amount > 0:
                    if bank_balance >= repayment_amount:
                        # 添加还款交易记录
                        self.add_transaction({
                            '日期': datetime.now().strftime("%Y-%m-%d"),
                            '类型': '支出',
                            '类别': '还款',
                            '项目描述': f"还款 {debt_to_repay}",
                            '金额': repayment_amount,
                            '币种': bank_currency,
                            '支付方式': repayment_bank,
                            '对方账户': debt_to_repay,
                            '汇率': 1.0,
                            '备注': notes
                        })

                        # 更新债务
                        st.session_state.debts[debt_to_repay]["剩余"] -= repayment_amount
                        if st.session_state.debts[debt_to_repay]["剩余"] <= 0:
                            st.session_state.debts[debt_to_repay]["状态"] = "已还清"
                            st.session_state.debts[debt_to_repay]["剩余"] = 0

                        st.success(f"✅ 成功还款 ¥{repayment_amount:,.2f} 给 {debt_to_repay}")
                        self.save_data()
                        st.rerun()
                    else:
                        st.error("❌ 银行卡余额不足")
                else:
                    st.error("❌ 请选择债务并输入有效的还款金额")

        st.markdown("---")

        # 债务管理功能
        st.subheader("🛠️ 债务管理")

        # 添加新债务
        with st.expander("➕ 添加新债务"):
            with st.form("add_debt_form"):
                col1, col2, col3 = st.columns(3)

                with col1:
                    new_debt_name = st.text_input("债务名称", placeholder="例如：信用卡、个人借款等")
                with col2:
                    debt_total = st.number_input("借款总额", min_value=0.0, step=100.0, value=1000.0, format="%.2f")
                with col3:
                    debt_monthly = st.number_input("月供金额", min_value=0.0, step=100.0, value=0.0, format="%.2f")

                submitted = st.form_submit_button("✅ 添加债务")

                if submitted:
                    if new_debt_name and new_debt_name not in st.session_state.debts:
                        st.session_state.debts[new_debt_name] = {
                            "总额": debt_total,
                            "剩余": debt_total,
                            "状态": "还款中",
                            "月供": debt_monthly
                        }
                        st.success(f"✅ 成功添加债务: {new_debt_name}")
                        self.save_data()
                        st.rerun()
                    elif new_debt_name in st.session_state.debts:
                        st.error("❌ 债务名称已存在")
                    else:
                        st.error("❌ 请输入债务名称")

        # 编辑债务
        with st.expander("✏️ 编辑债务"):
            if st.session_state.debts:
                debt_to_edit = st.selectbox("选择要编辑的债务", list(st.session_state.debts.keys()))

                if debt_to_edit:
                    debt_info = st.session_state.debts[debt_to_edit]

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        new_total = st.number_input("借款总额", value=float(debt_info["总额"]), format="%.2f")
                    with col2:
                        new_remaining = st.number_input("剩余金额",
                                                        value=float(debt_info["剩余"]),
                                                        max_value=float(debt_info["总额"]),
                                                        format="%.2f")
                    with col3:
                        new_status = st.selectbox("状态", ["还款中", "已还清"],
                                                  index=0 if debt_info["状态"] == "还款中" else 1)

                    if st.button("💾 保存修改", key="save_debt_edit"):
                        st.session_state.debts[debt_to_edit]["总额"] = new_total
                        st.session_state.debts[debt_to_edit]["剩余"] = new_remaining
                        st.session_state.debts[debt_to_edit]["状态"] = new_status

                        st.success("✅ 债务信息更新成功")
                        self.save_data()
                        st.rerun()

        # 删除债务
        with st.expander("🗑️ 删除债务"):
            if st.session_state.debts:
                debt_to_delete = st.selectbox("选择要删除的债务", list(st.session_state.debts.keys()))

                if st.button("❌ 删除债务", use_container_width=True):
                    if st.session_state.debts[debt_to_delete]["剩余"] > 0:
                        st.warning(
                            f"⚠️ 该债务还有 ¥{st.session_state.debts[debt_to_delete]['剩余']:,.2f} 未还清，确定删除吗？")

                    if st.button("✅ 确认删除", key="confirm_delete_debt"):
                        del st.session_state.debts[debt_to_delete]
                        st.success(f"✅ 成功删除债务: {debt_to_delete}")
                        self.save_data()
                        st.rerun()

        st.markdown("---")

        # 显示债务信息表格
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
                "状态": debt_info["状态"],
                "月供": f"¥{debt_info.get('月供', 0):,.2f}" if debt_info.get('月供', 0) > 0 else "-"
            })

        debt_df = pd.DataFrame(debt_data)
        st.dataframe(debt_df, use_container_width=True)

        # 债务进度图
        st.subheader("📈 债务还款进度")

        fig = go.Figure()

        for debt_name, debt_info in st.session_state.debts.items():
            total = debt_info["总额"]
            remaining = debt_info["剩余"]
            paid = total - remaining

            fig.add_trace(go.Bar(
                name=f'{debt_name} - 已还',
                x=[debt_name],
                y=[paid],
                marker_color='green',
                text=f'¥{paid:,.0f}',
                textposition='inside',
            ))

            fig.add_trace(go.Bar(
                name=f'{debt_name} - 剩余',
                x=[debt_name],
                y=[remaining],
                marker_color='red',
                text=f'¥{remaining:,.0f}',
                textposition='inside',
            ))

        fig.update_layout(
            title="债务还款进度",
            barmode='stack',
            showlegend=True
        )
        st.plotly_chart(fig, use_container_width=True)

    def show_budgets(self):
        """显示预算管理"""
        st.header("💰 预算管理")

        # 预算管理功能
        st.subheader("🛠️ 预算管理")

        # 添加新预算
        with st.expander("➕ 添加新预算项目"):
            with st.form("add_budget_form"):
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    new_budget_category = st.text_input("预算类别", placeholder="例如：旅游、学习等",
                                                        key="new_budget_category")
                with col2:
                    new_budget_amount = st.number_input("预算金额", min_value=0.0, step=100.0, value=1000.0,
                                                        format="%.2f", key="new_budget_amount")
                with col3:
                    new_budget_period = st.selectbox("预算周期", ["月度", "年度"], key="new_budget_period")
                with col4:
                    new_budget_currency = st.selectbox("预算币种", ["人民币", "马币"], key="new_budget_currency")

                submitted = st.form_submit_button("✅ 添加预算")

                if submitted:
                    if new_budget_category and new_budget_category.strip():
                        if new_budget_category not in st.session_state.budgets:
                            st.session_state.budgets[new_budget_category] = {
                                "预算金额": new_budget_amount,
                                "已用金额": 0,
                                "周期": new_budget_period,
                                "币种": new_budget_currency
                            }
                            st.success(f"✅ 成功添加预算: {new_budget_category}")
                            self.save_data()
                            st.rerun()
                        else:
                            st.error("❌ 预算类别已存在")
                    else:
                        st.error("❌ 请输入预算类别")

        # 编辑和删除预算 - 使用列表示方式
        st.subheader("✏️ 预算编辑与删除")

        if st.session_state.budgets:
            # 创建预算列表表格，每行都有编辑和删除按钮
            st.write("### 预算列表")

            for i, (category, budget_info) in enumerate(st.session_state.budgets.items()):
                with st.container():
                    st.markdown("---")
                    col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 2, 2, 1, 1])

                    with col1:
                        st.write(f"**{category}**")
                    with col2:
                        currency_symbol = "¥" if budget_info.get("币种", "人民币") == "人民币" else "RM"
                        st.write(f"预算: {currency_symbol}{budget_info['预算金额']:,.2f}")
                    with col3:
                        st.write(f"已用: {currency_symbol}{budget_info['已用金额']:,.2f}")
                    with col4:
                        remaining = budget_info['预算金额'] - budget_info['已用金额']
                        usage_percent = (budget_info['已用金额'] / budget_info['预算金额'] * 100) if budget_info[
                                                                                                         '预算金额'] > 0 else 0
                        st.write(f"剩余: {currency_symbol}{remaining:,.2f} ({usage_percent:.1f}%)")
                    with col5:
                        # 编辑按钮
                        edit_key = f"edit_{category}_{i}"
                        if st.button("✏️", key=edit_key, help=f"编辑 {category}"):
                            st.session_state.editing_budget = category
                    with col6:
                        # 删除按钮
                        delete_key = f"delete_{category}_{i}"
                        if st.button("🗑️", key=delete_key, help=f"删除 {category}"):
                            st.session_state.budget_to_delete = category

            # 处理删除操作
            if hasattr(st.session_state, 'budget_to_delete') and st.session_state.budget_to_delete:
                category_to_delete = st.session_state.budget_to_delete
                st.warning(f"⚠️ 确定要删除预算 '{category_to_delete}' 吗？")

                col_confirm, col_cancel = st.columns(2)
                with col_confirm:
                    if st.button("✅ 确认删除", key="confirm_delete_budget"):
                        del st.session_state.budgets[category_to_delete]
                        del st.session_state.budget_to_delete
                        st.success(f"✅ 成功删除预算: {category_to_delete}")
                        self.save_data()
                        st.rerun()
                with col_cancel:
                    if st.button("❌ 取消", key="cancel_delete_budget"):
                        del st.session_state.budget_to_delete
                        st.rerun()

            # 编辑预算表单
            if hasattr(st.session_state, 'editing_budget') and st.session_state.editing_budget:
                category_to_edit = st.session_state.editing_budget
                budget_info = st.session_state.budgets[category_to_edit]

                st.markdown("---")
                st.subheader(f"✏️ 编辑预算: {category_to_edit}")

                with st.form("edit_budget_form"):
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        new_category = st.text_input("预算类别", value=category_to_edit, key="edit_category")
                    with col2:
                        new_amount = st.number_input("预算金额",
                                                     value=float(budget_info["预算金额"]),
                                                     min_value=0.0,
                                                     format="%.2f",
                                                     key="edit_amount")
                    with col3:
                        new_period = st.selectbox("预算周期", ["月度", "年度"],
                                                  index=0 if budget_info["周期"] == "月度" else 1,
                                                  key="edit_period")
                    with col4:
                        new_currency = st.selectbox("预算币种", ["人民币", "马币"],
                                                    index=0 if budget_info.get("币种", "人民币") == "人民币" else 1,
                                                    key="edit_currency")

                    col_save, col_cancel = st.columns(2)

                    with col_save:
                        submitted = st.form_submit_button("💾 保存修改", use_container_width=True)
                    with col_cancel:
                        if st.form_submit_button("❌ 取消", use_container_width=True):
                            del st.session_state.editing_budget
                            st.rerun()

                    if submitted:
                        if new_category and new_category.strip():
                            # 如果类别名称改变了
                            if new_category != category_to_edit:
                                # 检查新名称是否已存在
                                if new_category in st.session_state.budgets and new_category != category_to_edit:
                                    st.error("❌ 预算类别名称已存在")
                                else:
                                    # 删除旧的，添加新的
                                    budget_data = st.session_state.budgets[category_to_edit].copy()
                                    del st.session_state.budgets[category_to_edit]
                                    st.session_state.budgets[new_category] = budget_data
                                    st.session_state.budgets[new_category]["预算金额"] = new_amount
                                    st.session_state.budgets[new_category]["周期"] = new_period
                                    st.session_state.budgets[new_category]["币种"] = new_currency

                                    st.success(f"✅ 预算已更新: {category_to_edit} → {new_category}")
                                    del st.session_state.editing_budget
                                    self.save_data()
                                    st.rerun()
                            else:
                                # 只更新信息
                                st.session_state.budgets[category_to_edit]["预算金额"] = new_amount
                                st.session_state.budgets[category_to_edit]["周期"] = new_period
                                st.session_state.budgets[category_to_edit]["币种"] = new_currency

                                st.success("✅ 预算信息更新成功")
                                del st.session_state.editing_budget
                                self.save_data()
                                st.rerun()
                        else:
                            st.error("❌ 预算类别不能为空")
        else:
            st.info("📝 暂无预算数据，请先添加预算")

        st.markdown("---")

        # 显示预算执行情况
        st.subheader("📊 预算执行情况")

        if st.session_state.budgets:
            budget_data = []
            for category, budget_info in st.session_state.budgets.items():
                currency = budget_info.get("币种", "人民币")
                budget_amount = budget_info["预算金额"]
                used_amount = budget_info["已用金额"]
                remaining = budget_amount - used_amount
                usage_percent = (used_amount / budget_amount * 100) if budget_amount > 0 else 0
                currency_symbol = "¥" if currency == "人民币" else "RM"

                # 根据使用百分比设置状态
                if usage_percent <= 80:
                    status = "正常"
                    status_color = "green"
                elif usage_percent <= 100:
                    status = "警告"
                    status_color = "orange"
                else:
                    status = "超支"
                    status_color = "red"

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

            # 预算执行情况图表
            st.subheader("📈 预算执行进度")

            categories = list(st.session_state.budgets.keys())
            budget_amounts = [budget["预算金额"] for budget in st.session_state.budgets.values()]
            used_amounts = [budget["已用金额"] for budget in st.session_state.budgets.values()]
            currencies = [budget.get("币种", "人民币") for budget in st.session_state.budgets.values()]

            fig = go.Figure()

            fig.add_trace(go.Bar(
                name='预算金额',
                x=categories,
                y=budget_amounts,
                marker_color='lightblue',
                text=[f'¥{amt:,.0f}' if cur == "人民币" else f'RM{amt:,.0f}'
                      for amt, cur in zip(budget_amounts, currencies)],
                textposition='outside',
            ))

            fig.add_trace(go.Bar(
                name='已用金额',
                x=categories,
                y=used_amounts,
                marker_color='orange',
                text=[f'¥{amt:,.0f}' if cur == "人民币" else f'RM{amt:,.0f}'
                      for amt, cur in zip(used_amounts, currencies)],
                textposition='inside',
            ))

            fig.update_layout(
                title="预算执行情况",
                barmode='overlay',
                showlegend=True
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📝 暂无预算数据")
    def show_analytics(self):
        """显示分析图表"""
        st.header("📈 财务分析")

        if not st.session_state.transactions.empty:
            # 币种收支分析
            st.subheader("💰 币种收支分析")

            currency_stats = self.get_currency_statistics(st.session_state.transactions)

            if currency_stats:
                # 收入饼图
                income_data = []
                for currency, stats in currency_stats.items():
                    if stats['收入'] > 0:
                        income_data.append({
                            '币种': currency,
                            '金额': stats['收入'],
                            '类型': '收入'
                        })

                if income_data:
                    income_df = pd.DataFrame(income_data)
                    col1, col2 = st.columns(2)

                    with col1:
                        fig_income = px.pie(
                            income_df,
                            values='金额',
                            names='币种',
                            title='收入币种分布',
                            color='币种'
                        )
                        st.plotly_chart(fig_income, use_container_width=True)

                    with col2:
                        # 支出饼图
                        expense_data = []
                        for currency, stats in currency_stats.items():
                            if stats['支出'] > 0:
                                expense_data.append({
                                    '币种': currency,
                                    '金额': stats['支出'],
                                    '类型': '支出'
                                })

                        if expense_data:
                            expense_df = pd.DataFrame(expense_data)
                            fig_expense = px.pie(
                                expense_df,
                                values='金额',
                                names='币种',
                                title='支出币种分布',
                                color='币种'
                            )
                            st.plotly_chart(fig_expense, use_container_width=True)

            # 月度收支趋势（按币种）
            st.subheader("📊 月度收支趋势（按币种）")

            df = st.session_state.transactions.copy()
            df['日期'] = pd.to_datetime(df['日期'])
            df['年月'] = df['日期'].dt.to_period('M').astype(str)

            # 按币种和月份分组
            monthly_currency_data = df.groupby(['年月', '类型', '币种'])['金额'].sum().reset_index()

            if not monthly_currency_data.empty:
                # 收入趋势
                income_trend = monthly_currency_data[monthly_currency_data['类型'] == '收入']
                if not income_trend.empty:
                    fig_income_trend = px.line(
                        income_trend,
                        x='年月',
                        y='金额',
                        color='币种',
                        title='月度收入趋势（按币种）',
                        markers=True
                    )
                    st.plotly_chart(fig_income_trend, use_container_width=True)

                # 支出趋势
                expense_trend = monthly_currency_data[monthly_currency_data['类型'] == '支出']
                if not expense_trend.empty:
                    fig_expense_trend = px.line(
                        expense_trend,
                        x='年月',
                        y='金额',
                        color='币种',
                        title='月度支出趋势（按币种）',
                        markers=True
                    )
                    st.plotly_chart(fig_expense_trend, use_container_width=True)

            # 支出类别分析（按币种）
            st.subheader("💸 支出类别分析（按币种）")
            expense_df = df[df['类型'] == '支出']

            if not expense_df.empty:
                # 按币种和类别分组
                expense_by_currency_category = expense_df.groupby(['币种', '类别'])['金额'].sum().reset_index()

                for currency in expense_by_currency_category['币种'].unique():
                    currency_expenses = expense_by_currency_category[expense_by_currency_category['币种'] == currency]
                    currency_symbol = "¥" if currency == "人民币" else "RM"

                    st.write(f"**{currency}支出类别分布**")
                    fig_currency_pie = px.pie(
                        currency_expenses,
                        values='金额',
                        names='类别',
                        title=f'{currency}支出类别分布',
                        color='类别'
                    )
                    st.plotly_chart(fig_currency_pie, use_container_width=True)
        else:
            st.info("暂无足够数据进行分析")

    def export_data(self):
        """数据导出功能"""
        st.header("📤 数据导出")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.subheader("交易记录")
            if not st.session_state.transactions.empty:
                csv = st.session_state.transactions.to_csv(index=False)
                st.download_button(
                    label="📥 下载CSV",
                    data=csv,
                    file_name="交易记录.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.warning("暂无交易记录")

        with col2:
            st.subheader("银行卡数据")
            bank_data = []
            for account, info in st.session_state.bank_accounts.items():
                bank_data.append({
                    "银行卡": account,
                    "币种": info["币种"],
                    "余额": info["余额"]
                })
            bank_df = pd.DataFrame(bank_data)
            csv = bank_df.to_csv(index=False)
            st.download_button(
                label="📥 下载银行卡数据",
                data=csv,
                file_name="银行卡数据.csv",
                mime="text/csv",
                use_container_width=True
            )

        with col3:
            st.subheader("债务数据")
            debt_data = []
            for debt_name, debt_info in st.session_state.debts.items():
                debt_data.append({
                    "债务名称": debt_name,
                    "总额": debt_info["总额"],
                    "剩余": debt_info["剩余"],
                    "状态": debt_info["状态"]
                })
            debt_df = pd.DataFrame(debt_data)
            csv = debt_df.to_csv(index=False)
            st.download_button(
                label="📥 下载债务数据",
                data=csv,
                file_name="债务数据.csv",
                mime="text/csv",
                use_container_width=True
            )

        with col4:
            st.subheader("预算数据")
            budget_data = []
            for category, budget_info in st.session_state.budgets.items():
                budget_data.append({
                    "类别": category,
                    "预算金额": budget_info["预算金额"],
                    "已用金额": budget_info["已用金额"],
                    "周期": budget_info["周期"],
                    "币种": budget_info.get("币种", "人民币")
                })
            budget_df = pd.DataFrame(budget_data)
            csv = budget_df.to_csv(index=False)
            st.download_button(
                label="📥 下载预算数据",
                data=csv,
                file_name="预算数据.csv",
                mime="text/csv",
                use_container_width=True
            )

    def run(self):
        """运行APP"""
        st.set_page_config(
            page_title="智能记账本",
            page_icon="💰",
            layout="wide",
            initial_sidebar_state="expanded"
        )

        # 自定义CSS
        st.markdown("""
        <style>
        .main-header {
            font-size: 2.5rem;
            color: #1f77b4;
            text-align: center;
            margin-bottom: 2rem;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown('<h1 class="main-header">💼 智能记账本</h1>', unsafe_allow_html=True)

        self.sidebar()

        # 主内容区域 - 添加预算管理标签页
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "💰 添加交易", "📊 交易记录", "🏦 银行卡", "📋 债务管理", "💰 预算管理", "📈 财务分析", "📤 数据导出"
        ])

        with tab1:
            self.add_transaction_form()

        with tab2:
            self.show_transactions()

        with tab3:
            self.show_bank_accounts()

        with tab4:
            self.show_debts()

        with tab5:
            self.show_budgets()

        with tab6:
            self.show_analytics()

        with tab7:
            self.export_data()


# 直接运行Streamlit应用
if __name__ == "__main__":
    app = FinanceApp()
    app.run()