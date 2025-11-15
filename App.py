# app1_complete_full_features.py - 带126邮箱验证的完整功能记账本
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import json
import os
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets
import re


class EmailManager:
    def __init__(self):
        self.smtp_config_file = "smtp_config.json"
        self.load_smtp_config()

    def load_smtp_config(self):
        """加载SMTP配置"""
        try:
            if os.path.exists(self.smtp_config_file):
                with open(self.smtp_config_file, 'r', encoding='utf-8') as f:
                    self.smtp_config = json.load(f)
            else:
                # 默认配置为126邮箱
                self.smtp_config = {
                    "smtp_server": "smtp.126.com",
                    "smtp_port": 465,
                    "sender_email": "",
                    "sender_password": "",
                    "enable_tls": False,
                    "use_ssl": True
                }
                self.save_smtp_config()
        except Exception as e:
            st.error(f"加载SMTP配置失败: {e}")
            self.smtp_config = {}

    def save_smtp_config(self):
        """保存SMTP配置"""
        try:
            with open(self.smtp_config_file, 'w', encoding='utf-8') as f:
                json.dump(self.smtp_config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            st.error(f"保存SMTP配置失败: {e}")

    def configure_smtp(self, smtp_server, smtp_port, sender_email, sender_password, enable_tls=False, use_ssl=True):
        """配置SMTP设置"""
        self.smtp_config = {
            "smtp_server": smtp_server,
            "smtp_port": smtp_port,
            "sender_email": sender_email,
            "sender_password": sender_password,
            "enable_tls": enable_tls,
            "use_ssl": use_ssl
        }
        self.save_smtp_config()
        return True

    def test_connection(self):
        """测试邮箱连接"""
        try:
            if self.smtp_config.get("use_ssl", False):
                # 使用SSL连接
                server = smtplib.SMTP_SSL(self.smtp_config["smtp_server"], self.smtp_config["smtp_port"])
            else:
                server = smtplib.SMTP(self.smtp_config["smtp_server"], self.smtp_config["smtp_port"])
                if self.smtp_config["enable_tls"]:
                    server.starttls()

            server.login(self.smtp_config["sender_email"], self.smtp_config["sender_password"])
            server.quit()
            return True, "邮箱连接测试成功"
        except Exception as e:
            return False, f"邮箱连接测试失败: {str(e)}"

    def send_reset_email(self, recipient_email, reset_token, username):
        """发送密码重置邮件"""
        try:
            # 创建邮件内容
            subject = "智能记账本 - 密码重置请求"

            body = f"""
            <html>
            <body>
                <h2>智能记账本 - 密码重置请求</h2>
                <p>尊敬的 {username}，</p>
                <p>我们收到了您的密码重置请求。请使用以下验证码来完成密码重置：</p>
                <div style="background-color: #f0f0f0; padding: 15px; border-radius: 5px; text-align: center; font-size: 24px; font-weight: bold; margin: 20px 0;">
                    {reset_token}
                </div>
                <p><strong>注意：</strong>该验证码在30分钟内有效，如非本人操作请忽略此邮件。</p>
                <hr>
                <p style="color: #666; font-size: 12px;">此为系统自动发送邮件，请勿回复。</p>
            </body>
            </html>
            """

            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = self.smtp_config["sender_email"]
            msg['To'] = recipient_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'html'))

            # 发送邮件
            if self.smtp_config.get("use_ssl", False):
                server = smtplib.SMTP_SSL(self.smtp_config["smtp_server"], self.smtp_config["smtp_port"])
            else:
                server = smtplib.SMTP(self.smtp_config["smtp_server"], self.smtp_config["smtp_port"])
                if self.smtp_config["enable_tls"]:
                    server.starttls()

            server.login(self.smtp_config["sender_email"], self.smtp_config["sender_password"])
            server.send_message(msg)
            server.quit()

            return True, "密码重置邮件发送成功"

        except Exception as e:
            return False, f"发送邮件失败: {str(e)}"


class UserManager:
    def __init__(self):
        self.users_file = "users.json"
        self.reset_tokens_file = "reset_tokens.json"
        self.email_manager = EmailManager()
        self.setup_files()

    def setup_files(self):
        """初始化数据文件"""
        # 初始化用户文件
        if not os.path.exists(self.users_file):
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)

        # 初始化重置令牌文件
        if not os.path.exists(self.reset_tokens_file):
            with open(self.reset_tokens_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)

    def hash_password(self, password):
        """密码加密"""
        return hashlib.sha256(password.encode()).hexdigest()

    def is_valid_email(self, email):
        """验证邮箱格式"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def generate_reset_token(self):
        """生成重置令牌"""
        return secrets.token_hex(8).upper()  # 16位大写令牌

    def register_user(self, username, password, email):
        """注册新用户"""
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                users = json.load(f)

            if username in users:
                return False, "用户名已存在"

            if not self.is_valid_email(email):
                return False, "邮箱格式不正确"

            # 检查邮箱是否已被使用
            for user_data in users.values():
                if user_data.get("email") == email:
                    return False, "该邮箱已被注册"

            # 创建用户数据目录
            user_data_dir = f"user_data/{username}"
            os.makedirs(user_data_dir, exist_ok=True)

            # 保存用户信息
            users[username] = {
                "password_hash": self.hash_password(password),
                "email": email,
                "created_at": datetime.now().isoformat(),
                "last_login": None,
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
                # 更新最后登录时间
                users[username]["last_login"] = datetime.now().isoformat()
                with open(self.users_file, 'w', encoding='utf-8') as f:
                    json.dump(users, f, ensure_ascii=False, indent=2)
                return True, "登录成功"
            else:
                return False, "用户名或密码错误"

        except Exception as e:
            return False, f"登录失败: {str(e)}"

    def init_user_data(self, username):
        """初始化用户数据 - 按月预算版本"""
        user_data_file = f"user_data/{username}/finance_data.json"
        if not os.path.exists(user_data_file):
            initial_data = {
                'transactions': [],
                'bank_accounts': {},
                'debts': {},
                'budgets': {}  # 按月存储预算
            }
            with open(user_data_file, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, ensure_ascii=False, indent=2)

    def get_user_email(self, username):
        """获取用户邮箱"""
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                users = json.load(f)
            return users.get(username, {}).get("email")
        except:
            return None

    def request_password_reset(self, username):
        """请求密码重置"""
        try:
            # 获取用户邮箱
            user_email = self.get_user_email(username)
            if not user_email:
                return False, "用户名不存在"

            # 生成重置令牌
            reset_token = self.generate_reset_token()
            expires_at = datetime.now() + timedelta(minutes=30)  # 30分钟有效期

            # 保存重置令牌
            with open(self.reset_tokens_file, 'r', encoding='utf-8') as f:
                reset_tokens = json.load(f)

            reset_tokens[reset_token] = {
                "username": username,
                "email": user_email,
                "expires_at": expires_at.isoformat(),
                "used": False
            }

            with open(self.reset_tokens_file, 'w', encoding='utf-8') as f:
                json.dump(reset_tokens, f, ensure_ascii=False, indent=2)

            # 发送重置邮件
            success, message = self.email_manager.send_reset_email(user_email, reset_token, username)
            if success:
                return True, f"密码重置邮件已发送到: {user_email}"
            else:
                return False, message

        except Exception as e:
            return False, f"密码重置请求失败: {str(e)}"

    def verify_reset_token(self, reset_token):
        """验证重置令牌"""
        try:
            with open(self.reset_tokens_file, 'r', encoding='utf-8') as f:
                reset_tokens = json.load(f)

            token_data = reset_tokens.get(reset_token)
            if not token_data:
                return False, "无效的重置令牌"

            if token_data.get("used", False):
                return False, "该重置令牌已被使用"

            expires_at = datetime.fromisoformat(token_data["expires_at"])
            if datetime.now() > expires_at:
                return False, "重置令牌已过期"

            return True, token_data["username"]

        except Exception as e:
            return False, f"验证令牌失败: {str(e)}"

    def reset_password(self, reset_token, new_password):
        """重置密码"""
        try:
            # 验证令牌
            success, result = self.verify_reset_token(reset_token)
            if not success:
                return False, result

            username = result

            # 更新密码
            with open(self.users_file, 'r', encoding='utf-8') as f:
                users = json.load(f)

            users[username]["password_hash"] = self.hash_password(new_password)
            users[username]["last_updated"] = datetime.now().isoformat()

            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(users, f, ensure_ascii=False, indent=2)

            # 标记令牌为已使用
            with open(self.reset_tokens_file, 'r', encoding='utf-8') as f:
                reset_tokens = json.load(f)

            reset_tokens[reset_token]["used"] = True
            reset_tokens[reset_token]["used_at"] = datetime.now().isoformat()

            with open(self.reset_tokens_file, 'w', encoding='utf-8') as f:
                json.dump(reset_tokens, f, ensure_ascii=False, indent=2)

            return True, "密码重置成功"

        except Exception as e:
            return False, f"密码重置失败: {str(e)}"


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

        # 交易编辑状态
        if 'editing_transaction_index' not in st.session_state:
            st.session_state.editing_transaction_index = None

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
        """显示交易记录 - 增强版（带编辑和删除功能）"""
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

            # 显示交易记录表格
            st.dataframe(
                filtered_df.style.format({
                    '金额': '{:,.2f}',
                    '汇率': '{:.2f}'
                }),
                use_container_width=True,
                height=400
            )

            # 交易编辑和删除功能
            st.subheader("✏️ 编辑和删除交易记录")

            # 选择要编辑的交易
            col_edit1, col_edit2 = st.columns([2, 1])

            with col_edit1:
                transaction_options = []
                for idx, row in st.session_state.transactions.iterrows():
                    transaction_options.append(
                        f"{idx + 1}. {row['日期']} - {row['类型']} - {row['项目描述']} - ¥{row['金额']:,.2f}")

                selected_transaction = st.selectbox(
                    "选择要编辑的交易记录",
                    transaction_options,
                    key="transaction_selector"
                )

            if selected_transaction:
                transaction_index = int(selected_transaction.split(".")[0]) - 1
                original_transaction = st.session_state.transactions.iloc[transaction_index].copy()

                with col_edit2:
                    action = st.radio(
                        "选择操作",
                        ["编辑交易", "删除交易"],
                        key=f"transaction_action_{transaction_index}"
                    )

                if action == "编辑交易":
                    # 编辑交易表单
                    with st.form(f"edit_transaction_form_{transaction_index}"):
                        st.subheader("📝 编辑交易")

                        col1, col2 = st.columns(2)

                        with col1:
                            edit_date = st.date_input(
                                "📅 日期",
                                datetime.strptime(original_transaction['日期'], "%Y-%m-%d"),
                                key=f"edit_date_{transaction_index}"
                            )
                            edit_type = st.selectbox(
                                "🔸 类型",
                                ["收入", "支出", "转账"],
                                index=["收入", "支出", "转账"].index(original_transaction['类型']),
                                key=f"edit_type_{transaction_index}"
                            )
                            edit_category = st.selectbox(
                                "📂 类别",
                                self.get_categories(edit_type),
                                index=self.get_categories(edit_type).index(original_transaction['类别']) if
                                original_transaction['类别'] in self.get_categories(edit_type) else 0,
                                key=f"edit_category_{transaction_index}"
                            )
                            edit_description = st.text_input(
                                "📝 项目描述",
                                value=original_transaction['项目描述'],
                                key=f"edit_description_{transaction_index}"
                            )
                            edit_amount = st.number_input(
                                "💰 金额",
                                min_value=0.0,
                                step=0.01,
                                value=float(original_transaction['金额']),
                                format="%.2f",
                                key=f"edit_amount_{transaction_index}"
                            )

                        with col2:
                            edit_currency = st.selectbox(
                                "🌐 币种",
                                ["人民币", "马币"],
                                index=0 if original_transaction['币种'] == "人民币" else 1,
                                key=f"edit_currency_{transaction_index}"
                            )

                            payment_options = list(st.session_state.bank_accounts.keys()) + ["现金", "微信支付",
                                                                                             "支付宝"]
                            edit_payment_method = st.selectbox(
                                "💳 支付方式",
                                payment_options,
                                index=payment_options.index(original_transaction['支付方式']) if original_transaction[
                                                                                                     '支付方式'] in payment_options else 0,
                                key=f"edit_payment_{transaction_index}"
                            )

                            if edit_type == "转账":
                                target_options = list(st.session_state.bank_accounts.keys()) + ["现金", "微信支付",
                                                                                                "支付宝", "其他银行卡"]
                                edit_target_account = st.selectbox(
                                    "➡️ 对方账户",
                                    target_options,
                                    index=target_options.index(original_transaction['对方账户']) if
                                    original_transaction['对方账户'] in target_options else 0,
                                    key=f"edit_target_{transaction_index}"
                                )
                                edit_exchange_rate = st.number_input(
                                    "🔁 汇率",
                                    min_value=0.0,
                                    step=0.01,
                                    value=float(original_transaction['汇率']),
                                    format="%.2f",
                                    key=f"edit_rate_{transaction_index}"
                                )
                            else:
                                edit_target_account = original_transaction['对方账户']
                                edit_exchange_rate = 1.0

                            edit_notes = st.text_input(
                                "📋 备注",
                                value=original_transaction['备注'],
                                key=f"edit_notes_{transaction_index}"
                            )

                        col_btn1, col_btn2 = st.columns(2)

                        with col_btn1:
                            if st.form_submit_button("✅ 更新交易", use_container_width=True):
                                # 恢复原始交易对余额的影响
                                self.reverse_transaction_effect(original_transaction)

                                # 创建更新后的交易数据
                                updated_transaction = {
                                    '日期': edit_date.strftime("%Y-%m-%d"),
                                    '类型': edit_type,
                                    '类别': edit_category,
                                    '项目描述': edit_description,
                                    '金额': edit_amount,
                                    '币种': edit_currency,
                                    '支付方式': edit_payment_method,
                                    '对方账户': edit_target_account,
                                    '汇率': edit_exchange_rate,
                                    '备注': edit_notes
                                }

                                # 更新交易记录
                                st.session_state.transactions.iloc[transaction_index] = updated_transaction

                                # 应用新交易对余额的影响
                                self.update_bank_balance(updated_transaction)

                                if updated_transaction['类型'] == '支出' and updated_transaction['类别'] == '还款':
                                    self.update_debt(updated_transaction['金额'])

                                st.success("✅ 交易记录更新成功！")
                                self.save_data()
                                st.rerun()

                        with col_btn2:
                            if st.form_submit_button("❌ 取消编辑", use_container_width=True, type="secondary"):
                                st.rerun()

                else:  # 删除交易
                    st.subheader("🗑️ 删除交易记录")

                    delete_confirmed = st.checkbox(
                        f"确认删除该交易记录",
                        key=f"confirm_delete_transaction_{transaction_index}"
                    )

                    if st.button(
                            "删除交易记录",
                            use_container_width=True,
                            type="secondary",
                            disabled=not delete_confirmed,
                            key=f"delete_transaction_{transaction_index}"
                    ):
                        # 恢复交易对余额的影响
                        self.reverse_transaction_effect(original_transaction)

                        # 删除交易记录
                        st.session_state.transactions = st.session_state.transactions.drop(
                            transaction_index).reset_index(drop=True)

                        st.success("✅ 交易记录删除成功！")
                        self.save_data()
                        st.rerun()

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

    def reverse_transaction_effect(self, transaction):
        """反转交易对余额的影响"""
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

                is_self_transfer = (payment_method in st.session_state.bank_accounts and
                                    target_account in st.session_state.bank_accounts)

                if is_self_transfer:
                    st.session_state.bank_accounts[payment_method]["余额"] += amount
                    st.session_state.bank_accounts[target_account]["余额"] -= amount * exchange_rate
                else:
                    st.session_state.bank_accounts[payment_method]["余额"] += amount

        # 如果是还款交易，恢复债务余额
        if transaction_type == '支出' and transaction['类别'] == '还款':
            for debt_name in st.session_state.debts:
                if st.session_state.debts[debt_name]["状态"] == "已还清" or st.session_state.debts[debt_name][
                    "状态"] == "还款中":
                    st.session_state.debts[debt_name]["剩余"] += amount
                    if st.session_state.debts[debt_name]["剩余"] > 0:
                        st.session_state.debts[debt_name]["状态"] = "还款中"
                    break

    def show_bank_accounts(self):
        """显示银行卡信息 - 增强版（带余额修改功能）"""
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
                            "币种": bank_currency,
                            "创建时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "最后更新": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        st.success(f"✅ 成功添加银行卡: {bank_name}")
                        self.save_data()
                        st.rerun()
                    else:
                        st.error("❌ 银行卡名称已存在")
                else:
                    st.error("❌ 请输入银行卡名称")

        st.markdown("---")

        # 显示银行卡列表和余额修改功能
        if st.session_state.bank_accounts:
            st.subheader("💳 银行卡列表")

            # 银行卡统计数据
            total_balance = sum(account["余额"] for account in st.session_state.bank_accounts.values())
            total_accounts = len(st.session_state.bank_accounts)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("银行卡数量", total_accounts)
            with col2:
                st.metric("总余额", f"¥{total_balance:,.2f}")
            with col3:
                avg_balance = total_balance / total_accounts if total_accounts > 0 else 0
                st.metric("平均余额", f"¥{avg_balance:,.2f}")

            # 银行卡数据表格
            bank_data = []
            for account, info in st.session_state.bank_accounts.items():
                currency_symbol = "¥" if info["币种"] == "人民币" else "RM"
                bank_data.append({
                    "银行卡": account,
                    "币种": info["币种"],
                    "当前余额": info["余额"],
                    "格式化余额": f"{currency_symbol}{info['余额']:,.2f}",
                    "创建时间": info.get("创建时间", "未知"),
                    "最后更新": info.get("最后更新", "未知")
                })

            bank_df = pd.DataFrame(bank_data)

            # 显示银行卡表格
            st.dataframe(
                bank_df[["银行卡", "币种", "格式化余额", "创建时间", "最后更新"]],
                use_container_width=True
            )

            st.markdown("---")

            # 银行卡余额修改功能
            st.subheader("✏️ 修改银行卡余额")
            col_edit1, col_edit2 = st.columns([2, 1])

            with col_edit1:
                edit_banks = list(st.session_state.bank_accounts.keys())
                selected_bank = st.selectbox("选择要修改余额的银行卡", edit_banks, key="bank_selector")

            if selected_bank:
                bank_info = st.session_state.bank_accounts[selected_bank]
                current_balance = bank_info["余额"]
                currency_symbol = "¥" if bank_info["币种"] == "人民币" else "RM"

                with col_edit2:
                    st.info(f"当前余额: **{currency_symbol}{current_balance:,.2f}**")

                # 余额修改选项
                st.subheader("💰 余额调整方式")
                adjustment_method = st.radio(
                    "选择调整方式",
                    ["直接设置新余额", "增加金额", "减少金额", "转账调整"],
                    key=f"adjust_method_{selected_bank}"
                )

                if adjustment_method == "直接设置新余额":
                    new_balance = st.number_input(
                        "新余额",
                        min_value=0.0,
                        step=100.0,
                        value=float(current_balance),
                        format="%.2f",
                        key=f"new_balance_{selected_bank}"
                    )

                    adjustment_amount = new_balance - current_balance
                    adjustment_type = "增加" if adjustment_amount > 0 else "减少" if adjustment_amount < 0 else "不变"

                elif adjustment_method == "增加金额":
                    increase_amount = st.number_input(
                        "增加金额",
                        min_value=0.0,
                        step=100.0,
                        value=0.0,
                        format="%.2f",
                        key=f"increase_{selected_bank}"
                    )
                    new_balance = current_balance + increase_amount
                    adjustment_amount = increase_amount
                    adjustment_type = "增加"

                elif adjustment_method == "减少金额":
                    decrease_amount = st.number_input(
                        "减少金额",
                        min_value=0.0,
                        max_value=float(current_balance),
                        step=100.0,
                        value=0.0,
                        format="%.2f",
                        key=f"decrease_{selected_bank}"
                    )
                    new_balance = current_balance - decrease_amount
                    adjustment_amount = -decrease_amount
                    adjustment_type = "减少"

                else:  # 转账调整
                    col_transfer1, col_transfer2 = st.columns(2)

                    with col_transfer1:
                        # 选择转出银行卡（不能是当前选中的银行卡）
                        from_banks = [bank for bank in st.session_state.bank_accounts.keys() if bank != selected_bank]
                        if from_banks:
                            from_bank = st.selectbox("从哪个银行卡转出", from_banks, key=f"from_bank_{selected_bank}")
                            from_bank_balance = st.session_state.bank_accounts[from_bank]["余额"]
                            from_currency_symbol = "¥" if st.session_state.bank_accounts[from_bank][
                                                              "币种"] == "人民币" else "RM"
                            st.info(f"**{from_bank}** 当前余额: {from_currency_symbol}{from_bank_balance:,.2f}")
                        else:
                            st.warning("⚠️ 没有其他银行卡可用于转账")
                            from_bank = None

                    with col_transfer2:
                        if from_bank:
                            transfer_amount = st.number_input(
                                "转账金额",
                                min_value=0.0,
                                max_value=float(from_bank_balance),
                                step=100.0,
                                value=min(500.0, float(from_bank_balance)),
                                format="%.2f",
                                key=f"transfer_{selected_bank}"
                            )

                            # 检查币种是否一致
                            from_currency = st.session_state.bank_accounts[from_bank]["币种"]
                            to_currency = bank_info["币种"]

                            if from_currency != to_currency:
                                st.warning(
                                    f"⚠️ 币种不同: {from_bank}({from_currency}) → {selected_bank}({to_currency})")
                                exchange_rate = st.number_input(
                                    "汇率",
                                    min_value=0.0,
                                    step=0.01,
                                    value=1.0,
                                    format="%.2f",
                                    key=f"exchange_{selected_bank}"
                                )
                                actual_transfer_amount = transfer_amount * exchange_rate
                            else:
                                exchange_rate = 1.0
                                actual_transfer_amount = transfer_amount

                            new_balance = current_balance + actual_transfer_amount
                            adjustment_amount = actual_transfer_amount
                            adjustment_type = "转账转入"

                # 显示调整摘要
                if adjustment_method != "转账调整" or (adjustment_method == "转账调整" and from_bank):
                    st.markdown("---")
                    st.subheader("📋 调整摘要")

                    col_sum1, col_sum2, col_sum3 = st.columns(3)

                    with col_sum1:
                        st.metric("当前余额", f"{currency_symbol}{current_balance:,.2f}")
                    with col_sum2:
                        if adjustment_type == "转账转入":
                            st.metric("转账金额", f"{currency_symbol}{adjustment_amount:,.2f}")
                        else:
                            st.metric("调整金额", f"{currency_symbol}{abs(adjustment_amount):,.2f}")
                    with col_sum3:
                        st.metric("新余额", f"{currency_symbol}{new_balance:,.2f}")

                    # 调整原因
                    adjustment_reason = st.text_input(
                        "调整原因（可选）",
                        placeholder="例如：工资到账、现金存入、转账等",
                        key=f"reason_{selected_bank}"
                    )

                    # 执行调整按钮
                    col_btn1, col_btn2 = st.columns(2)

                    with col_btn1:
                        if st.button("✅ 确认调整", use_container_width=True, key=f"confirm_adjust_{selected_bank}"):
                            # 更新银行卡余额
                            old_balance = st.session_state.bank_accounts[selected_bank]["余额"]
                            st.session_state.bank_accounts[selected_bank]["余额"] = new_balance
                            st.session_state.bank_accounts[selected_bank]["最后更新"] = datetime.now().strftime(
                                "%Y-%m-%d %H:%M:%S")

                            # 如果是转账调整，同时更新转出银行卡
                            if adjustment_method == "转账调整" and from_bank:
                                st.session_state.bank_accounts[from_bank]["余额"] -= transfer_amount
                                st.session_state.bank_accounts[from_bank]["最后更新"] = datetime.now().strftime(
                                    "%Y-%m-%d %H:%M:%S")

                                # 记录转账交易
                                transfer_transaction = {
                                    '日期': datetime.now().strftime("%Y-%m-%d"),
                                    '类型': '转账',
                                    '类别': '账户转账',
                                    '项目描述': f"银行卡间转账 {from_bank} → {selected_bank}",
                                    '金额': transfer_amount,
                                    '币种': st.session_state.bank_accounts[from_bank]["币种"],
                                    '支付方式': from_bank,
                                    '对方账户': selected_bank,
                                    '汇率': exchange_rate,
                                    '备注': f"余额调整转账 - {adjustment_reason}" if adjustment_reason else "余额调整转账"
                                }
                                new_transaction = pd.DataFrame([transfer_transaction])
                                st.session_state.transactions = pd.concat(
                                    [st.session_state.transactions, new_transaction], ignore_index=True)

                            else:
                                # 记录余额调整交易
                                transaction_type = "收入" if adjustment_amount > 0 else "支出"
                                transaction_category = "余额调整" + ("收入" if adjustment_amount > 0 else "支出")

                                adjustment_transaction = {
                                    '日期': datetime.now().strftime("%Y-%m-%d"),
                                    '类型': transaction_type,
                                    '类别': transaction_category,
                                    '项目描述': f"银行卡余额调整 - {adjustment_type}",
                                    '金额': abs(adjustment_amount),
                                    '币种': bank_info["币种"],
                                    '支付方式': selected_bank,
                                    '对方账户': "",
                                    '汇率': 1.0,
                                    '备注': adjustment_reason if adjustment_reason else f"余额调整 - {adjustment_type}"
                                }
                                new_transaction = pd.DataFrame([adjustment_transaction])
                                st.session_state.transactions = pd.concat(
                                    [st.session_state.transactions, new_transaction], ignore_index=True)

                            st.success(
                                f"✅ 成功调整 {selected_bank} 的余额: {currency_symbol}{old_balance:,.2f} → {currency_symbol}{new_balance:,.2f}")
                            self.save_data()
                            st.rerun()

                    with col_btn2:
                        if st.button("❌ 取消调整", use_container_width=True, key=f"cancel_adjust_{selected_bank}"):
                            st.rerun()

            st.markdown("---")

            # 银行卡删除功能
            st.subheader("🗑️ 删除银行卡")
            col_del1, col_del2 = st.columns([2, 1])

            with col_del1:
                delete_banks = list(st.session_state.bank_accounts.keys())
                selected_delete_bank = st.selectbox("选择要删除的银行卡", delete_banks, key="delete_bank_selector")

            if selected_delete_bank:
                delete_bank_info = st.session_state.bank_accounts[selected_delete_bank]
                delete_balance = delete_bank_info["余额"]
                delete_currency_symbol = "¥" if delete_bank_info["币种"] == "人民币" else "RM"

                with col_del2:
                    st.warning(f"当前余额: **{delete_currency_symbol}{delete_balance:,.2f}**")

                # 检查是否有交易关联
                has_transactions = False
                if not st.session_state.transactions.empty:
                    related_transactions = st.session_state.transactions[
                        (st.session_state.transactions['支付方式'] == selected_delete_bank) |
                        (st.session_state.transactions['对方账户'] == selected_delete_bank)
                        ]
                    has_transactions = len(related_transactions) > 0

                if has_transactions:
                    st.error("❌ 该银行卡有相关的交易记录，无法删除")
                    st.info("💡 请先删除或修改相关的交易记录后再删除银行卡")
                else:
                    delete_confirmed = st.checkbox(
                        f"确认删除银行卡 '{selected_delete_bank}'",
                        key=f"confirm_delete_bank_{selected_delete_bank}"
                    )

                    if st.button(
                            "删除银行卡",
                            use_container_width=True,
                            type="secondary",
                            disabled=not delete_confirmed,
                            key=f"delete_bank_{selected_delete_bank}"
                    ):
                        if delete_balance > 0:
                            st.warning(f"⚠️ 该银行卡还有 {delete_currency_symbol}{delete_balance:,.2f} 元余额")

                        # 执行删除
                        del st.session_state.bank_accounts[selected_delete_bank]
                        st.success(f"✅ 成功删除银行卡: {selected_delete_bank}")
                        self.save_data()
                        st.rerun()

            # 余额图表
            st.markdown("---")
            st.subheader("📊 银行卡余额分布")
            chart_data = []
            for account, info in st.session_state.bank_accounts.items():
                chart_data.append({
                    "银行卡": account,
                    "余额": info["余额"],
                    "币种": info["币种"]
                })

            chart_df = pd.DataFrame(chart_data)

            # 条形图
            fig_bar = px.bar(chart_df, x='银行卡', y='余额', title='银行卡余额分布', color='银行卡')
            fig_bar.update_layout(showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)

            # 饼图（如果有多张卡）
            if len(chart_df) > 1:
                fig_pie = px.pie(chart_df, values='余额', names='银行卡', title='银行卡余额占比')
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_pie, use_container_width=True)

        else:
            st.info("🏦 暂无银行卡数据，请先添加银行卡")

    def get_available_banks_for_repayment(self, debt_currency):
        """获取可用于还款的银行卡列表"""
        available_banks = []
        for bank_name, bank_info in st.session_state.bank_accounts.items():
            # 检查币种是否匹配且余额大于0
            if bank_info["币种"] == debt_currency and bank_info["余额"] > 0:
                available_banks.append(bank_name)
        return available_banks

    def process_repayment(self, debt_name, payment_amount, bank_name):
        """处理还款操作"""
        try:
            # 记录还款前的余额
            current_remaining = st.session_state.debts[debt_name]["剩余"]
            new_remaining = current_remaining - payment_amount

            if new_remaining < 0:
                st.error("❌ 还款金额不能超过剩余债务金额")
                return False

            # 更新债务信息
            st.session_state.debts[debt_name]["剩余"] = new_remaining

            # 更新债务状态
            if new_remaining == 0:
                st.session_state.debts[debt_name]["状态"] = "已还清"

            # 记录还款记录
            repayment_record = {
                "还款日期": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "还款金额": payment_amount,
                "还款方式": bank_name,
                "还款前余额": current_remaining,
                "还款后余额": new_remaining
            }

            # 初始化还款记录列表（如果不存在）
            if "还款记录" not in st.session_state.debts[debt_name]:
                st.session_state.debts[debt_name]["还款记录"] = []

            # 添加还款记录
            st.session_state.debts[debt_name]["还款记录"].append(repayment_record)

            # 更新银行卡余额
            if bank_name in st.session_state.bank_accounts:
                st.session_state.bank_accounts[bank_name]["余额"] -= payment_amount

            # 记录还款交易
            repayment_transaction = {
                '日期': datetime.now().strftime("%Y-%m-%d"),
                '类型': '支出',
                '类别': '还款',
                '项目描述': f"还款 {debt_name}",
                '金额': payment_amount,
                '币种': st.session_state.debts[debt_name].get("币种", "人民币"),
                '支付方式': bank_name,
                '对方账户': debt_name,
                '汇率': 1.0,
                '备注': f"债务还款 - {debt_name}"
            }

            new_transaction = pd.DataFrame([repayment_transaction])
            st.session_state.transactions = pd.concat([st.session_state.transactions, new_transaction],
                                                      ignore_index=True)

            return True

        except Exception as e:
            st.error(f"❌ 还款处理失败: {str(e)}")
            return False

    def delete_repayment_record(self, debt_name, record_index):
        """删除还款记录"""
        try:
            if debt_name in st.session_state.debts and "还款记录" in st.session_state.debts[debt_name]:
                repayment_records = st.session_state.debts[debt_name]["还款记录"]

                if 0 <= record_index < len(repayment_records):
                    # 获取要删除的记录信息
                    record_to_delete = repayment_records[record_index]
                    repayment_amount = record_to_delete.get("还款金额", 0)
                    repayment_bank = record_to_delete.get("还款方式", "")

                    # 恢复债务余额
                    st.session_state.debts[debt_name]["剩余"] += repayment_amount

                    # 更新债务状态
                    if st.session_state.debts[debt_name]["剩余"] > 0:
                        st.session_state.debts[debt_name]["状态"] = "还款中"

                    # 恢复银行卡余额
                    if repayment_bank in st.session_state.bank_accounts:
                        st.session_state.bank_accounts[repayment_bank]["余额"] += repayment_amount

                    # 删除还款记录
                    st.session_state.debts[debt_name]["还款记录"].pop(record_index)

                    # 删除对应的交易记录
                    self.delete_repayment_transaction(debt_name, record_to_delete.get("还款日期", ""))

                    return True
                else:
                    st.error("❌ 无效的还款记录索引")
                    return False
            else:
                st.error("❌ 未找到还款记录")
                return False

        except Exception as e:
            st.error(f"❌ 删除还款记录失败: {str(e)}")
            return False

    def delete_repayment_transaction(self, debt_name, repayment_date):
        """删除还款对应的交易记录"""
        try:
            if not st.session_state.transactions.empty:
                # 查找对应的还款交易记录
                df = st.session_state.transactions.copy()
                mask = (df['项目描述'] == f"还款 {debt_name}") & (df['日期'] == repayment_date.split(' ')[0])

                if mask.any():
                    # 删除对应的交易记录
                    st.session_state.transactions = st.session_state.transactions[~mask].reset_index(drop=True)

        except Exception as e:
            st.error(f"❌ 删除还款交易记录失败: {str(e)}")

    def show_debts(self):
        """显示债务管理 - 完整版（带还款记录管理）"""
        st.header("📋 债务管理")

        # 添加债务
        st.subheader("➕ 添加新债务")
        with st.form("add_debt_form"):
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                debt_name = st.text_input("债务名称", placeholder="例如：信用卡、个人借款等")
            with col2:
                debt_total = st.number_input("借款总额", min_value=0.0, step=100.0, value=1000.0, format="%.2f")
            with col3:
                debt_remaining = st.number_input("剩余金额", min_value=0.0, step=100.0, value=1000.0, format="%.2f")
            with col4:
                debt_currency = st.selectbox("币种", ["人民币", "马币"])

            submitted = st.form_submit_button("✅ 添加债务", use_container_width=True)

            if submitted:
                if debt_name and debt_name.strip():
                    if debt_name not in st.session_state.debts:
                        status = "已还清" if debt_remaining == 0 else "还款中"
                        st.session_state.debts[debt_name] = {
                            "总额": debt_total,
                            "剩余": debt_remaining,
                            "状态": status,
                            "币种": debt_currency,
                            "创建时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "还款记录": []  # 初始化还款记录
                        }
                        st.success(f"✅ 成功添加债务: {debt_name}")
                        self.save_data()
                        st.rerun()
                    else:
                        st.error("❌ 债务名称已存在")
                else:
                    st.error("❌ 请输入债务名称")

        st.markdown("---")

        # 显示债务列表和编辑功能
        if st.session_state.debts:
            st.subheader("📊 债务概览")

            # 债务统计数据
            total_debt = sum(debt["总额"] for debt in st.session_state.debts.values())
            remaining_debt = sum(debt["剩余"] for debt in st.session_state.debts.values())
            paid_debt = total_debt - remaining_debt
            overall_progress = (paid_debt / total_debt * 100) if total_debt > 0 else 0

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("总债务金额", f"¥{total_debt:,.2f}")
            with col2:
                st.metric("剩余债务", f"¥{remaining_debt:,.2f}")
            with col3:
                st.metric("已还金额", f"¥{paid_debt:,.2f}")
            with col4:
                st.metric("总还款进度", f"{overall_progress:.1f}%")

            st.markdown("---")

            # 债务详细列表
            st.subheader("📝 债务详情")

            # 创建债务数据表格
            debt_data = []
            for debt_name, debt_info in st.session_state.debts.items():
                total = debt_info["总额"]
                remaining = debt_info["剩余"]
                paid = total - remaining
                progress = (paid / total * 100) if total > 0 else 0
                currency_symbol = "¥" if debt_info.get("币种", "人民币") == "人民币" else "RM"

                debt_data.append({
                    "债务名称": debt_name,
                    "币种": debt_info.get("币种", "人民币"),
                    "借款总额": total,
                    "剩余金额": remaining,
                    "已还金额": paid,
                    "还款进度": progress,
                    "状态": debt_info["状态"],
                    "创建时间": debt_info.get("创建时间", "未知")
                })

            debt_df = pd.DataFrame(debt_data)

            if not debt_df.empty:
                # 格式化显示用的DataFrame
                display_df = debt_df.copy()
                display_df["借款总额"] = display_df.apply(
                    lambda x: f"{'¥' if x['币种'] == '人民币' else 'RM'}{x['借款总额']:,.2f}", axis=1
                )
                display_df["剩余金额"] = display_df.apply(
                    lambda x: f"{'¥' if x['币种'] == '人民币' else 'RM'}{x['剩余金额']:,.2f}", axis=1
                )
                display_df["已还金额"] = display_df.apply(
                    lambda x: f"{'¥' if x['币种'] == '人民币' else 'RM'}{x['已还金额']:,.2f}", axis=1
                )
                display_df["还款进度"] = display_df["还款进度"].apply(lambda x: f"{x:.1f}%")

                st.dataframe(
                    display_df[
                        ["债务名称", "币种", "借款总额", "剩余金额", "已还金额", "还款进度", "状态", "创建时间"]],
                    use_container_width=True,
                    height=400
                )

                # 债务编辑功能
                st.subheader("✏️ 编辑债务")
                col1, col2, col3 = st.columns([2, 1, 1])

                with col1:
                    edit_debts = list(st.session_state.debts.keys())
                    selected_debt = st.selectbox("选择要编辑的债务", edit_debts, key="debt_selector")

                if selected_debt:
                    debt_info = st.session_state.debts[selected_debt]

                    col2, col3, col4 = st.columns(3)

                    with col2:
                        new_debt_total = st.number_input(
                            "借款总额",
                            min_value=0.0,
                            step=100.0,
                            value=float(debt_info["总额"]),
                            format="%.2f",
                            key="edit_debt_total"
                        )

                    with col3:
                        new_debt_remaining = st.number_input(
                            "剩余金额",
                            min_value=0.0,
                            step=100.0,
                            value=float(debt_info["剩余"]),
                            format="%.2f",
                            key="edit_debt_remaining"
                        )

                    with col4:
                        new_debt_currency = st.selectbox(
                            "币种",
                            ["人民币", "马币"],
                            index=0 if debt_info.get("币种", "人民币") == "人民币" else 1,
                            key="edit_debt_currency"
                        )

                    # 按钮列
                    col5, col6, col7 = st.columns(3)

                    with col5:
                        if st.button("✅ 更新债务", use_container_width=True, key="update_debt"):
                            # 验证数据
                            if new_debt_remaining > new_debt_total:
                                st.error("❌ 剩余金额不能大于借款总额")
                            else:
                                st.session_state.debts[selected_debt]["总额"] = new_debt_total
                                st.session_state.debts[selected_debt]["剩余"] = new_debt_remaining
                                st.session_state.debts[selected_debt]["币种"] = new_debt_currency

                                # 更新状态
                                status = "已还清" if new_debt_remaining == 0 else "还款中"
                                st.session_state.debts[selected_debt]["状态"] = status

                                st.success(f"✅ 成功更新债务: {selected_debt}")
                                self.save_data()
                                st.rerun()

                    with col6:
                        # 快速还款功能 - 增强版（带银行卡选择）
                        if debt_info["状态"] == "还款中":
                            st.subheader("💳 快速还款")

                            # 获取可用的银行卡
                            available_banks = self.get_available_banks_for_repayment(debt_info.get("币种", "人民币"))

                            if not available_banks:
                                st.warning("⚠️ 没有可用的银行卡进行还款，请先添加银行卡")
                            else:
                                # 还款金额输入
                                quick_payment = st.number_input(
                                    "还款金额",
                                    min_value=0.0,
                                    max_value=float(debt_info["剩余"]),
                                    step=100.0,
                                    value=min(500.0, float(debt_info["剩余"])),
                                    format="%.2f",
                                    key="quick_payment"
                                )

                                # 银行卡选择
                                selected_bank = st.selectbox(
                                    "选择还款银行卡",
                                    available_banks,
                                    key="repayment_bank"
                                )

                                # 显示银行卡余额信息
                                if selected_bank in st.session_state.bank_accounts:
                                    bank_balance = st.session_state.bank_accounts[selected_bank]["余额"]
                                    bank_currency = st.session_state.bank_accounts[selected_bank]["币种"]
                                    currency_symbol = "¥" if bank_currency == "人民币" else "RM"
                                    st.info(f"**{selected_bank}** 当前余额: {currency_symbol}{bank_balance:,.2f}")

                                    # 检查余额是否足够
                                    if quick_payment > bank_balance:
                                        st.error("❌ 银行卡余额不足，无法完成还款")
                                    else:
                                        if st.button("💳 确认还款", use_container_width=True, key="quick_repay"):
                                            # 执行还款操作
                                            success = self.process_repayment(
                                                selected_debt,
                                                quick_payment,
                                                selected_bank
                                            )
                                            if success:
                                                st.success(f"✅ 成功从 {selected_bank} 还款 {quick_payment:,.2f} 元")
                                                self.save_data()
                                                st.rerun()

                    with col7:
                        # 删除功能
                        st.subheader("🗑️ 删除债务")
                        delete_confirmed = st.checkbox(
                            f"确认删除 '{selected_debt}' 债务",
                            key=f"confirm_delete_debt_{selected_debt}"
                        )

                        if st.button(
                                "删除债务",
                                use_container_width=True,
                                type="secondary",
                                disabled=not delete_confirmed,
                                key=f"delete_debt_{selected_debt}"
                        ):
                            if st.session_state.debts[selected_debt]["剩余"] > 0:
                                st.warning(
                                    f"⚠️ 该债务还有 {st.session_state.debts[selected_debt]['剩余']:,.2f} 元未还清")

                            # 执行删除
                            del st.session_state.debts[selected_debt]
                            st.success(f"✅ 成功删除债务: {selected_debt}")
                            self.save_data()
                            st.rerun()

                    # 还款记录管理
                    st.markdown("---")
                    st.subheader("📋 还款记录管理")

                    # 显示还款记录
                    if "还款记录" in st.session_state.debts[selected_debt] and st.session_state.debts[selected_debt][
                        "还款记录"]:
                        repayment_records = st.session_state.debts[selected_debt]["还款记录"]

                        st.write(f"**{selected_debt} 的还款记录:**")

                        # 创建还款记录表格
                        record_data = []
                        for i, record in enumerate(repayment_records):
                            record_data.append({
                                "序号": i + 1,
                                "还款日期": record.get("还款日期", "未知"),
                                "还款金额": record.get("还款金额", 0),
                                "还款方式": record.get("还款方式", "未知"),
                                "还款前余额": record.get("还款前余额", 0),
                                "还款后余额": record.get("还款后余额", 0)
                            })

                        record_df = pd.DataFrame(record_data)

                        if not record_df.empty:
                            # 格式化显示
                            display_record_df = record_df.copy()
                            display_record_df["还款金额"] = display_record_df["还款金额"].apply(lambda x: f"¥{x:,.2f}")
                            display_record_df["还款前余额"] = display_record_df["还款前余额"].apply(
                                lambda x: f"¥{x:,.2f}")
                            display_record_df["还款后余额"] = display_record_df["还款后余额"].apply(
                                lambda x: f"¥{x:,.2f}")

                            st.dataframe(
                                display_record_df,
                                use_container_width=True,
                                height=300
                            )

                            # 删除特定还款记录
                            st.subheader("🗑️ 删除还款记录")
                            col_del1, col_del2 = st.columns([2, 1])

                            with col_del1:
                                record_to_delete = st.selectbox(
                                    "选择要删除的还款记录",
                                    [f"{i + 1}. {record['还款日期']} - ¥{record['还款金额']:,.2f}" for i, record in
                                     enumerate(repayment_records)],
                                    key="record_selector"
                                )

                            with col_del2:
                                if record_to_delete:
                                    record_index = int(record_to_delete.split(".")[0]) - 1
                                    delete_record_confirmed = st.checkbox(
                                        f"确认删除该还款记录",
                                        key=f"confirm_delete_record_{record_index}"
                                    )

                                    if st.button(
                                            "删除还款记录",
                                            use_container_width=True,
                                            type="secondary",
                                            disabled=not delete_record_confirmed,
                                            key=f"delete_record_{record_index}"
                                    ):
                                        success = self.delete_repayment_record(selected_debt, record_index)
                                        if success:
                                            st.success("✅ 成功删除还款记录")
                                            self.save_data()
                                            st.rerun()
                    else:
                        st.info("📝 暂无还款记录")

                    # 债务可视化
                    st.markdown("---")
                    st.subheader("📊 债务分析")

                    # 还款进度条
                    for _, debt_row in debt_df.iterrows():
                        debt_name = debt_row["债务名称"]
                        progress = debt_row["还款进度"]
                        total = debt_row["借款总额"]
                        remaining = debt_row["剩余金额"]
                        currency_symbol = "¥" if debt_row["币种"] == "人民币" else "RM"

                        col1, col2 = st.columns([3, 1])

                        with col1:
                            # 设置进度条颜色
                            if progress == 100:
                                color = "green"
                            elif progress >= 50:
                                color = "blue"
                            else:
                                color = "orange"

                            st.progress(
                                progress / 100,
                                text=f"{debt_name}: {currency_symbol}{total - remaining:,.2f} / {currency_symbol}{total:,.2f} ({progress:.1f}%)"
                            )

                        with col2:
                            status_text = debt_row["状态"]
                            if "已还清" in status_text:
                                st.markdown(f"<span style='color: green'>🎉 已还清</span>", unsafe_allow_html=True)
                            else:
                                st.markdown(f"<span style='color: orange'>⏳ 还款中</span>", unsafe_allow_html=True)

                    # 债务分布饼图
                    if len(debt_df) > 1:
                        st.subheader("🥧 债务分布")
                        chart_data = []
                        for debt_name, info in st.session_state.debts.items():
                            if info["状态"] == "还款中":  # 只显示未还清的债务
                                chart_data.append({
                                    "债务名称": debt_name,
                                    "剩余金额": info["剩余"],
                                    "币种": info.get("币种", "人民币")
                                })

                        if chart_data:
                            chart_df = pd.DataFrame(chart_data)
                            fig = px.pie(
                                chart_df,
                                values='剩余金额',
                                names='债务名称',
                                title='剩余债务分布',
                                hover_data=['币种']
                            )
                            fig.update_traces(textposition='inside', textinfo='percent+label')
                            st.plotly_chart(fig, use_container_width=True)

        else:
            st.info("📝 暂无债务数据，请先添加债务")

    def get_previous_month(self, year, month):
        """获取上个月的月份键"""
        if month == 1:
            return f"{year - 1}-12"
        else:
            return f"{year}-{str(month - 1).zfill(2)}"

    def calculate_monthly_budget_usage(self, year, month):
        """计算指定月份的实际预算使用情况"""
        month_key = f"{year}-{str(month).zfill(2)}"

        if month_key not in st.session_state.budgets:
            return

        # 重置所有类别的已用金额
        for category in st.session_state.budgets[month_key]:
            st.session_state.budgets[month_key][category]["已用金额"] = 0

        # 计算实际支出
        if not st.session_state.transactions.empty:
            df = st.session_state.transactions.copy()
            df['日期'] = pd.to_datetime(df['日期'])
            df['年月'] = df['日期'].dt.strftime('%Y-%m')

            monthly_expenses = df[(df['类型'] == '支出') & (df['年月'] == month_key)]

            for category, group in monthly_expenses.groupby('类别'):
                if category in st.session_state.budgets[month_key]:
                    budget_currency = st.session_state.budgets[month_key][category].get("币种", "人民币")
                    category_expenses = group[group['币种'] == budget_currency]
                    st.session_state.budgets[month_key][category]["已用金额"] = category_expenses['金额'].sum()

    def show_budgets(self):
        """显示预算管理 - 按月设置版本"""
        st.header("💰 月度预算管理")

        # 月份选择器
        st.subheader("📅 选择月份")
        col1, col2 = st.columns(2)

        with col1:
            # 年份选择：从2025年到2099年
            years = list(range(2025, 2100))
            selected_year = st.selectbox("选择年份", years, index=0)  # 默认2025年

        with col2:
            # 月份选择
            months = list(range(1, 13))
            month_names = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"]
            selected_month = st.selectbox("选择月份", month_names, index=10)  # 默认11月

        # 生成月份键（例如：2025-11）
        month_key = f"{selected_year}-{str(month_names.index(selected_month) + 1).zfill(2)}"
        current_month_key = datetime.now().strftime("%Y-%m")

        # 显示当前查看的月份
        st.info(f"📊 正在查看 {selected_year}年{selected_month} 的预算情况")

        # 初始化该月份的预算数据（如果不存在）
        if month_key not in st.session_state.budgets:
            st.session_state.budgets[month_key] = {}

        # 添加新预算
        st.subheader("➕ 添加新预算")
        with st.form("add_budget_form"):
            col1, col2, col3 = st.columns(3)

            with col1:
                new_category = st.text_input("预算类别", placeholder="例如：房租、餐饮、交通等")
            with col2:
                new_amount = st.number_input("预算金额", min_value=0.0, step=100.0, value=1000.0, format="%.2f")
            with col3:
                new_currency = st.selectbox("币种", ["人民币", "马币"])

            add_submitted = st.form_submit_button("✅ 添加预算", use_container_width=True)

            if add_submitted:
                if new_category and new_category.strip():
                    if new_category not in st.session_state.budgets[month_key]:
                        st.session_state.budgets[month_key][new_category] = {
                            "预算金额": new_amount,
                            "已用金额": 0,
                            "币种": new_currency
                        }
                        st.success(f"✅ 成功为 {month_key} 添加预算类别: {new_category}")
                        self.save_data()
                        st.rerun()
                    else:
                        st.error(f"❌ {selected_month} 中该预算类别已存在")
                else:
                    st.error("❌ 请输入预算类别名称")

        st.markdown("---")

        # 复制上月预算功能
        if month_key != "2025-11":  # 第一个月不需要复制
            st.subheader("🔄 快速复制预算")
            prev_month = self.get_previous_month(selected_year, month_names.index(selected_month) + 1)

            if st.button(f"📋 复制 {prev_month} 的预算设置", use_container_width=True, key="copy_budget"):
                if prev_month in st.session_state.budgets and st.session_state.budgets[prev_month]:
                    st.session_state.budgets[month_key] = {}
                    for category, budget_info in st.session_state.budgets[prev_month].items():
                        st.session_state.budgets[month_key][category] = {
                            "预算金额": budget_info["预算金额"],
                            "已用金额": 0,  # 重置已用金额
                            "币种": budget_info["币种"]
                        }
                    st.success(f"✅ 已从 {prev_month} 复制预算设置到 {month_key}")
                    self.save_data()
                    st.rerun()
                else:
                    st.warning(f"⚠️ {prev_month} 没有可复制的预算数据")

        # 预算编辑和删除
        if st.session_state.budgets[month_key]:
            st.subheader("📊 预算执行情况")

            # 计算该月的实际支出
            self.calculate_monthly_budget_usage(selected_year, month_names.index(selected_month) + 1)

            # 创建预算数据的副本用于显示和编辑
            budget_data = []
            total_budget = 0
            total_used = 0

            for category, budget_info in st.session_state.budgets[month_key].items():
                currency = budget_info.get("币种", "人民币")
                budget_amount = budget_info["预算金额"]
                used_amount = budget_info["已用金额"]
                remaining = budget_amount - used_amount
                usage_percent = (used_amount / budget_amount * 100) if budget_amount > 0 else 0
                currency_symbol = "¥" if currency == "人民币" else "RM"

                total_budget += budget_amount
                total_used += used_amount

                # 状态判断
                if usage_percent <= 80:
                    status = "🟢 正常"
                elif usage_percent <= 100:
                    status = "🟡 警告"
                else:
                    status = "🔴 超支"

                budget_data.append({
                    "类别": category,
                    "币种": currency,
                    "预算金额": budget_amount,
                    "已用金额": used_amount,
                    "剩余金额": remaining,
                    "使用进度": usage_percent,
                    "状态": status
                })

            # 显示月度总览
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("总预算", f"¥{total_budget:,.2f}")
            with col2:
                st.metric("已使用", f"¥{total_used:,.2f}")
            with col3:
                st.metric("剩余预算", f"¥{total_budget - total_used:,.2f}")
            with col4:
                overall_usage = (total_used / total_budget * 100) if total_budget > 0 else 0
                st.metric("总使用率", f"{overall_usage:.1f}%")

            budget_df = pd.DataFrame(budget_data)

            # 显示预算表格
            if not budget_df.empty:
                # 格式化显示用的DataFrame
                display_df = budget_df.copy()
                display_df["预算金额"] = display_df.apply(
                    lambda x: f"{'¥' if x['币种'] == '人民币' else 'RM'}{x['预算金额']:,.2f}", axis=1
                )
                display_df["已用金额"] = display_df.apply(
                    lambda x: f"{'¥' if x['币种'] == '人民币' else 'RM'}{x['已用金额']:,.2f}", axis=1
                )
                display_df["剩余金额"] = display_df.apply(
                    lambda x: f"{'¥' if x['币种'] == '人民币' else 'RM'}{x['剩余金额']:,.2f}", axis=1
                )
                display_df["使用进度"] = display_df["使用进度"].apply(lambda x: f"{x:.1f}%")

                st.dataframe(
                    display_df[["类别", "币种", "预算金额", "已用金额", "剩余金额", "使用进度", "状态"]],
                    use_container_width=True
                )

                # 预算编辑和删除功能
                st.subheader("✏️ 编辑和删除预算")
                col1, col2, col3 = st.columns([2, 1, 1])

                with col1:
                    edit_categories = list(st.session_state.budgets[month_key].keys())
                    selected_category = st.selectbox("选择要编辑的预算类别", edit_categories, key=f"edit_{month_key}")

                if selected_category:
                    budget_info = st.session_state.budgets[month_key][selected_category]

                    with col2:
                        new_budget_amount = st.number_input(
                            "新预算金额",
                            min_value=0.0,
                            step=100.0,
                            value=float(budget_info["预算金额"]),
                            format="%.2f",
                            key=f"amount_{month_key}_{selected_category}"
                        )

                    with col3:
                        new_budget_currency = st.selectbox(
                            "币种",
                            ["人民币", "马币"],
                            index=0 if budget_info.get("币种", "人民币") == "人民币" else 1,
                            key=f"currency_{month_key}_{selected_category}"
                        )

                    col4, col5 = st.columns(2)

                    with col4:
                        if st.button("✅ 更新预算", use_container_width=True,
                                     key=f"update_{month_key}_{selected_category}"):
                            st.session_state.budgets[month_key][selected_category]["预算金额"] = new_budget_amount
                            st.session_state.budgets[month_key][selected_category]["币种"] = new_budget_currency
                            st.success(f"✅ 成功更新 {selected_category} 的预算")
                            self.save_data()
                            st.rerun()

                    with col5:
                        # 删除功能
                        delete_confirmed = st.checkbox(
                            f"确认删除 '{selected_category}' 预算",
                            key=f"confirm_delete_{month_key}_{selected_category}"
                        )

                        if st.button(
                                "🗑️ 删除预算",
                                use_container_width=True,
                                type="secondary",
                                disabled=not delete_confirmed,
                                key=f"delete_{month_key}_{selected_category}"
                        ):
                            if st.session_state.budgets[month_key][selected_category]["已用金额"] > 0:
                                st.warning(
                                    f"⚠️ 该预算类别已有 {st.session_state.budgets[month_key][selected_category]['已用金额']} 元的使用记录")

                            # 执行删除
                            del st.session_state.budgets[month_key][selected_category]
                            st.success(f"✅ 成功删除预算类别: {selected_category}")
                            self.save_data()
                            st.rerun()

                # 预算使用情况图表
                st.subheader("📈 预算执行情况图表")

                # 进度条显示
                for _, budget_row in budget_df.iterrows():
                    category = budget_row["类别"]
                    usage_percent = budget_row["使用进度"]
                    budget_amount = budget_row["预算金额"]
                    used_amount = budget_row["已用金额"]
                    currency_symbol = "¥" if budget_row["币种"] == "人民币" else "RM"

                    col1, col2 = st.columns([3, 1])

                    with col1:
                        # 设置进度条颜色
                        if usage_percent <= 80:
                            color = "green"
                        elif usage_percent <= 100:
                            color = "orange"
                        else:
                            color = "red"

                        st.progress(
                            min(usage_percent / 100, 1.0),
                            text=f"{category}: {currency_symbol}{used_amount:,.2f} / {currency_symbol}{budget_amount:,.2f} ({usage_percent:.1f}%)"
                        )

                    with col2:
                        status_text = budget_row["状态"]
                        if "正常" in status_text:
                            st.markdown(f"<span style='color: green'>🟢 正常</span>", unsafe_allow_html=True)
                        elif "警告" in status_text:
                            st.markdown(f"<span style='color: orange'>🟡 警告</span>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<span style='color: red'>🔴 超支</span>", unsafe_allow_html=True)

                # 预算分布饼图
                if len(st.session_state.budgets[month_key]) > 0:
                    st.subheader("🥧 预算分布")
                    chart_data = []
                    for category, info in st.session_state.budgets[month_key].items():
                        chart_data.append({
                            "类别": category,
                            "预算金额": info["预算金额"],
                            "币种": info.get("币种", "人民币")
                        })

                    if chart_data:
                        chart_df = pd.DataFrame(chart_data)
                        fig = px.pie(
                            chart_df,
                            values='预算金额',
                            names='类别',
                            title=f'{selected_year}年{selected_month} 预算分布',
                            hover_data=['币种']
                        )
                        fig.update_traces(textposition='inside', textinfo='percent+label')
                        st.plotly_chart(fig, use_container_width=True)

            else:
                st.info("📝 本月暂无预算数据")

        else:
            st.info("📝 本月暂无预算数据，请先添加预算")

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

            # 月度趋势分析
            st.subheader("📊 月度趋势")
            if not st.session_state.transactions.empty:
                df = st.session_state.transactions.copy()
                df['日期'] = pd.to_datetime(df['日期'])
                df['年月'] = df['日期'].dt.strftime('%Y-%m')

                monthly_data = df.groupby(['年月', '类型']).agg({'金额': 'sum'}).reset_index()

                # 创建月度趋势图
                fig_trend = px.line(
                    monthly_data,
                    x='年月',
                    y='金额',
                    color='类型',
                    title='月度收支趋势',
                    markers=True
                )
                fig_trend.update_layout(xaxis_title='月份', yaxis_title='金额')
                st.plotly_chart(fig_trend, use_container_width=True)

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


def show_email_configuration():
    """显示邮箱配置界面"""
    st.header("📧 邮箱服务配置")

    email_manager = EmailManager()

    # 邮箱类型快速选择
    st.subheader("🚀 快速配置")
    email_choices = {
        "126邮箱": {"server": "smtp.126.com", "port": 465, "ssl": True, "tls": False},
        "QQ邮箱": {"server": "smtp.qq.com", "port": 587, "ssl": False, "tls": True},
        "163邮箱": {"server": "smtp.163.com", "port": 465, "ssl": True, "tls": False},
        "Gmail": {"server": "smtp.gmail.com", "port": 587, "ssl": False, "tls": True},
        "自定义": {"server": "", "port": 587, "ssl": False, "tls": True}
    }

    selected_email = st.selectbox("选择邮箱类型", list(email_choices.keys()))

    if selected_email != "自定义":
        config = email_choices[selected_email]
        st.info(f"💡 自动配置: {selected_email} - {config['server']}:{config['port']}")

    st.markdown("---")
    st.subheader("⚙️ 详细配置")

    with st.form("email_config_form"):
        col1, col2 = st.columns(2)

        with col1:
            if selected_email == "自定义":
                smtp_server = st.text_input("SMTP服务器", value=email_manager.smtp_config.get("smtp_server", ""))
            else:
                smtp_server = st.text_input("SMTP服务器", value=config['server'])

            sender_email = st.text_input("发件邮箱", value=email_manager.smtp_config.get("sender_email", ""),
                                         placeholder="your_email@126.com")

            if selected_email == "自定义":
                use_ssl = st.checkbox("使用SSL", value=email_manager.smtp_config.get("use_ssl", False))
                enable_tls = st.checkbox("启用TLS", value=email_manager.smtp_config.get("enable_tls", True))
            else:
                use_ssl = st.checkbox("使用SSL", value=config['ssl'])
                enable_tls = st.checkbox("启用TLS", value=config['tls'])

        with col2:
            if selected_email == "自定义":
                smtp_port = st.number_input("SMTP端口", min_value=1, max_value=65535,
                                            value=email_manager.smtp_config.get("smtp_port", 587))
            else:
                smtp_port = st.number_input("SMTP端口", min_value=1, max_value=65535, value=config['port'])

            sender_password = st.text_input("邮箱授权码", type="password",
                                            value=email_manager.smtp_config.get("sender_password", ""),
                                            placeholder="请输入邮箱授权码，不是登录密码")

        # 126邮箱特别提示
        if selected_email == "126邮箱":
            st.warning("""
            **126邮箱配置说明：**
            1. 登录126邮箱网页版
            2. 进入【设置】→ 【POP3/SMTP/IMAP】
            3. 开启【SMTP服务】
            4. 根据提示获取**授权码**（不是邮箱密码！）
            5. 将授权码填写在上面的"邮箱授权码"字段中
            """)

        col3, col4 = st.columns(2)
        with col3:
            save_btn = st.form_submit_button("💾 保存配置", use_container_width=True)
        with col4:
            test_btn = st.form_submit_button("🔍 测试连接", use_container_width=True)

        if save_btn:
            if all([smtp_server, smtp_port, sender_email, sender_password]):
                email_manager.configure_smtp(smtp_server, smtp_port, sender_email, sender_password, enable_tls, use_ssl)
                st.success("✅ 邮箱配置保存成功！")

                # 显示配置摘要
                st.info(f"""
                **配置摘要：**
                - 服务器: {smtp_server}:{smtp_port}
                - 发件箱: {sender_email}
                - 加密: {'SSL' if use_ssl else 'TLS' if enable_tls else '无'}
                """)
            else:
                st.error("❌ 请填写所有配置项")

        if test_btn:
            if all([smtp_server, smtp_port, sender_email, sender_password]):
                email_manager.configure_smtp(smtp_server, smtp_port, sender_email, sender_password, enable_tls, use_ssl)
                success, message = email_manager.test_connection()
                if success:
                    st.success("✅ " + message)

                    # 测试发送邮件
                    try:
                        test_success, test_msg = email_manager.send_reset_email(
                            sender_email, "TEST123", "TestUser"
                        )
                        if test_success:
                            st.success("✅ 测试邮件发送成功！请检查您的收件箱")
                        else:
                            st.warning("⚠️ 连接成功但发送测试邮件失败: " + test_msg)
                    except Exception as e:
                        st.warning(f"⚠️ 连接成功但发送测试邮件失败: {str(e)}")
                else:
                    st.error("❌ " + message)

                    # 提供故障排除建议
                    if "126.com" in smtp_server:
                        st.error("""
                        **126邮箱故障排除：**
                        1. 确认已开启SMTP服务
                        2. 确认使用的是**授权码**而不是邮箱密码
                        3. 尝试使用端口465 + SSL
                        4. 检查邮箱地址是否正确
                        """)
            else:
                st.error("❌ 请先填写所有配置项")


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
    if 'show_forgot_password' not in st.session_state:
        st.session_state.show_forgot_password = False
    if 'show_email_config' not in st.session_state:
        st.session_state.show_email_config = False
    if 'reset_stage' not in st.session_state:
        st.session_state.reset_stage = "request"  # request, verify, reset

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
    .token-display {
        background-color: #f0f0f0;
        padding: 15px;
        border-radius: 5px;
        text-align: center;
        font-size: 24px;
        font-weight: bold;
        margin: 20px 0;
        border: 2px dashed #ccc;
    }
    </style>
    """, unsafe_allow_html=True)

    # 用户管理
    user_manager = UserManager()

    # 检查URL参数中的重置令牌
    query_params = st.query_params
    reset_token_from_url = query_params.get("reset_token", [""])[0]

    if reset_token_from_url and not st.session_state.logged_in:
        st.session_state.show_forgot_password = True
        st.session_state.reset_stage = "verify"
        st.session_state.reset_token = reset_token_from_url

    if not st.session_state.logged_in:
        # 登录/注册界面
        st.markdown('<h1 class="main-header">🔒 智能记账本 - 安全版</h1>', unsafe_allow_html=True)

        # 邮箱配置按钮
        if not st.session_state.show_forgot_password and not st.session_state.show_email_config:
            col1, col2, col3 = st.columns([2, 1, 2])
            with col2:
                if st.button("⚙️ 配置邮箱服务", use_container_width=True):
                    st.session_state.show_email_config = True
                    st.rerun()

        # 密码找回按钮
        if not st.session_state.show_forgot_password and not st.session_state.show_email_config:
            col1, col2, col3 = st.columns([2, 1, 2])
            with col2:
                if st.button("🔑 忘记密码？", use_container_width=True):
                    st.session_state.show_forgot_password = True
                    st.session_state.reset_stage = "request"
                    st.rerun()

        # 邮箱配置界面
        if st.session_state.show_email_config:
            show_email_configuration()
            if st.button("↩️ 返回登录", use_container_width=True):
                st.session_state.show_email_config = False
                st.rerun()

        # 密码找回界面
        elif st.session_state.show_forgot_password:
            if st.session_state.reset_stage == "request":
                # 请求密码重置
                st.subheader("🔑 密码找回 - 请求重置")

                with st.form("forgot_password_request"):
                    username = st.text_input("请输入您的用户名", placeholder="输入要找回密码的用户名")

                    submitted = st.form_submit_button("📧 发送重置邮件", use_container_width=True)

                    if submitted:
                        if username:
                            success, message = user_manager.request_password_reset(username)
                            if success:
                                st.success("✅ " + message)
                                st.session_state.reset_stage = "verify"
                                st.session_state.reset_username = username
                                st.rerun()
                            else:
                                st.error("❌ " + message)
                        else:
                            st.error("❌ 请输入用户名")

                if st.button("↩️ 返回登录", use_container_width=True):
                    st.session_state.show_forgot_password = False
                    st.rerun()

            elif st.session_state.reset_stage == "verify":
                # 验证重置令牌
                st.subheader("🔑 密码找回 - 验证令牌")

                # 如果从URL获取了令牌，自动填充
                if 'reset_token' not in st.session_state:
                    st.session_state.reset_token = ""

                reset_token = st.text_input(
                    "请输入重置令牌",
                    value=st.session_state.reset_token,
                    placeholder="请输入邮件中的16位重置令牌"
                ).upper().replace(" ", "")

                col1, col2 = st.columns(2)

                with col1:
                    if st.button("✅ 验证令牌", use_container_width=True):
                        if reset_token:
                            success, result = user_manager.verify_reset_token(reset_token)
                            if success:
                                st.success("✅ 令牌验证成功！")
                                st.session_state.reset_stage = "reset"
                                st.session_state.reset_token = reset_token
                                st.session_state.reset_username = result
                                st.rerun()
                            else:
                                st.error("❌ " + result)
                        else:
                            st.error("❌ 请输入重置令牌")

                with col2:
                    if st.button("🔄 重新发送邮件", use_container_width=True):
                        if hasattr(st.session_state, 'reset_username'):
                            success, message = user_manager.request_password_reset(st.session_state.reset_username)
                            if success:
                                st.success("✅ " + message)
                            else:
                                st.error("❌ " + message)
                        else:
                            st.error("❌ 无法重新发送邮件，请返回上一步")

                if st.button("↩️ 返回上一步", use_container_width=True):
                    st.session_state.reset_stage = "request"
                    st.rerun()

            elif st.session_state.reset_stage == "reset":
                # 重置密码
                st.subheader("🔑 密码找回 - 设置新密码")

                with st.form("reset_password_form"):
                    st.info(f"正在为用户 **{st.session_state.reset_username}** 重置密码")

                    new_password = st.text_input("新密码", type="password", placeholder="请输入新密码（至少6位）")
                    confirm_password = st.text_input("确认新密码", type="password", placeholder="请再次输入新密码")

                    submitted = st.form_submit_button("🔐 重置密码", use_container_width=True)

                    if submitted:
                        if new_password and confirm_password:
                            if len(new_password) < 6:
                                st.error("❌ 密码长度至少6位")
                            elif new_password != confirm_password:
                                st.error("❌ 两次输入的密码不一致")
                            else:
                                success, message = user_manager.reset_password(
                                    st.session_state.reset_token, new_password
                                )
                                if success:
                                    st.success("✅ " + message)
                                    st.session_state.show_forgot_password = False
                                    st.session_state.reset_stage = "request"
                                    st.rerun()
                                else:
                                    st.error("❌ " + message)
                        else:
                            st.error("❌ 请填写所有字段")

                if st.button("↩️ 返回上一步", use_container_width=True):
                    st.session_state.reset_stage = "verify"
                    st.rerun()

        else:
            # 原有的登录/注册标签页
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
                    email = st.text_input("邮箱", placeholder="请输入有效的邮箱地址")

                    register_btn = st.form_submit_button("注册", use_container_width=True)

                    if register_btn:
                        if not all([new_username, new_password, confirm_password, email]):
                            st.error("❌ 请填写所有字段")
                        elif len(new_username) < 3 or len(new_username) > 20:
                            st.error("❌ 用户名长度应在3-20位之间")
                        elif len(new_password) < 6:
                            st.error("❌ 密码长度至少6位")
                        elif new_password != confirm_password:
                            st.error("❌ 两次输入的密码不一致")
                        elif not user_manager.is_valid_email(email):
                            st.error("❌ 邮箱格式不正确")
                        else:
                            success, message = user_manager.register_user(new_username, new_password, email)
                            if success:
                                st.success("✅ " + message)
                                st.info("请返回登录页面进行登录")
                            else:
                                st.error("❌ " + message)

    else:
        # 已登录，显示主应用
        finance_app = FinanceApp(st.session_state.current_user)
        finance_app.run_app()


if __name__ == "__main__":
    main()