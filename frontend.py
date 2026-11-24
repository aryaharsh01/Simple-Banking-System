
import streamlit as st
import pandas as pd
import backend

# Page Settings
st.set_page_config(page_title="Simple Banking System", page_icon="🏦", layout="wide")

st.title("🏦 Simple Banking System")
st.write("Python + Streamlit + SQLite")
st.divider()

# Session State
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "account_number" not in st.session_state:
    st.session_state.account_number = None

if "user_name" not in st.session_state:
    st.session_state.user_name = ""


# LOGIN AND CREATE ACCOUNT
if not st.session_state.logged_in:

    login_tab, create_tab = st.tabs(["Login", "Create Account"])

    with login_tab:

        st.subheader("Login")

        account = st.text_input("Account Number")
        pin = st.text_input("PIN", type="password", max_chars=4)

        if st.button("Login"):

            success, result = backend.login(account.strip(), pin.strip())

            if success:
                st.session_state.logged_in = True
                st.session_state.account_number = result["account_number"]
                st.session_state.user_name = result["full_name"]
                st.rerun()
            else:
                st.error(result)

    with create_tab:

        st.subheader("Create New Account")

        name = st.text_input("Full Name")
        mobile = st.text_input("Mobile Number", max_chars=10)
        email = st.text_input("Email")
        new_pin = st.text_input("Create PIN", type="password", max_chars=4)
        confirm_pin = st.text_input("Confirm PIN", type="password", max_chars=4)

        if st.button("Create Account"):

            if new_pin != confirm_pin:
                st.error("PIN does not match.")

            else:
                success, result = backend.create_account(
                    name, mobile, email, new_pin
                )

                if success:
                    st.success("Account Created Successfully!")
                    st.write("Your Account Number:", result)
                else:
                    st.error(result)


# BANKING DASHBOARD
else:

    account = st.session_state.account_number

    st.sidebar.title("Banking Menu")
    st.sidebar.write("Welcome", st.session_state.user_name)

    page = st.sidebar.radio(
        "Select Option",
        [
            "Dashboard",
            "Deposit Money",
            "Withdraw Money",
            "Send Money",
            "Transaction History",
            "Account Report"
        ]
    )

    if st.sidebar.button("Logout"):
        backend.logout(st.session_state)
        st.rerun()

    success, balance = backend.check_balance(account)

    if not success:
        st.error(balance)
        st.stop()

    # DASHBOARD
    if page == "Dashboard":

        st.subheader("Dashboard")
        st.metric("Available Balance", f"₹{balance:,.2f}")

        success, report = backend.account_report(account)

        if success:
            st.write("Total Transactions:", report["total_transactions"])
            st.write("Account Status:", report["status"])

    # DEPOSIT
    elif page == "Deposit Money":

        st.subheader("Deposit Money")
        amount = st.number_input("Enter Amount", min_value=0.01)

        if st.button("Deposit"):
            success, message = backend.deposit_money(account, amount)

            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    # WITHDRAW
    elif page == "Withdraw Money":

        st.subheader("Withdraw Money")
        amount = st.number_input("Enter Amount", min_value=0.01)

        if st.button("Withdraw"):
            success, message = backend.withdraw_money(account, amount)

            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    # SEND MONEY
    elif page == "Send Money":

        st.subheader("Send Money")
        receiver = st.text_input("Receiver Account Number")
        amount = st.number_input("Enter Amount", min_value=0.01)

        if st.button("Send"):
            if not receiver.strip().isdigit():
                st.error("Enter valid account number.")
            else:
                success, message = backend.send_money(
                    account, int(receiver), amount
                )

                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

    # TRANSACTION HISTORY
    elif page == "Transaction History":

        st.subheader("Transaction History")
        history = backend.transaction_history(account)

        if history:
            df = pd.DataFrame(history)
            st.dataframe(df, use_container_width=True)

            st.download_button(
                "Download History",
                df.to_csv(index=False),
                file_name="transaction_history.csv"
            )
        else:
            st.info("No transactions available.")

    # ACCOUNT REPORT
    elif page == "Account Report":

        st.subheader("Account Report")
        success, report = backend.account_report(account)

        if success:
            st.write("Account Number:", report["account_number"])
            st.write("Name:", report["full_name"])
            st.write("Mobile:", report["mobile_number"])
            st.write("Email:", report["email"])
            st.write("Balance:", report["balance"])
            st.write("Created At:", report["created_at"])
            st.write("Status:", report["status"])
            st.write("Total Transactions:", report["total_transactions"])
        else:
            st.error(report)

st.divider()
st.caption("Simple Banking System - College Micro Project")
