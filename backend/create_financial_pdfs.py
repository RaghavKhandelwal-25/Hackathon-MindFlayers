"""Utility script to generate authentic financial education PDF documents

for Finbot local knowledge base testing and demonstration.
"""

from pathlib import Path
import pymupdf as fitz

DATA_DIR = Path(__file__).resolve().parent / "data" / "pdfs"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def create_personal_finance_pdf():
    pdf_path = DATA_DIR / "personal_finance_and_budgeting.pdf"
    doc = fitz.open()

    # Page 1: 50/30/20 Budgeting Rule
    page1 = doc.new_page(width=595, height=842)  # A4 size
    text_page1 = (
        "Personal Finance and Budgeting Mastery\n\n"
        "Chapter 1: The 50/30/20 Budgeting Framework\n\n"
        "Budgeting is the foundational cornerstone of personal financial health. One of the most effective, "
        "time-tested frameworks for managing personal cash flow is the 50/30/20 budgeting rule, popularized by Senator Elizabeth Warren.\n\n"
        "The framework divides your after-tax net income into three distinct categories:\n\n"
        "1. 50% for Needs: Essential living expenses required for survival and baseline functioning. This includes rent or mortgage payments, "
        "utilities (electricity, water, heating), essential groceries, minimum debt obligations, and health insurance. If your needs exceed 50%, "
        "it indicates that housing or fixed overhead costs may need to be restructured.\n\n"
        "2. 30% for Wants: Discretionary expenses that improve quality of life but are not strictly necessary. Examples include dining at restaurants, "
        "streaming subscriptions, recreational travel, designer clothing, and entertainment. Maintaining wants at 30% ensures that you enjoy life today "
        "without sacrificing your future financial independence.\n\n"
        "3. 20% for Savings and Extra Debt Repayment: Capital earmarked for wealth building and debt acceleration. This includes contributions toward an "
        "emergency fund, workplace retirement plans (like a 401k), individual retirement accounts (IRAs), and payments toward principal on high-interest loans.\n\n"
        "Adhering to this balanced allocation prevents lifestyle inflation and guarantees steady net worth expansion over time."
    )
    rect1 = fitz.Rect(50, 50, 545, 790)
    page1.insert_textbox(rect1, text_page1, fontsize=11, fontname="helv", align=fitz.TEXT_ALIGN_LEFT)

    # Page 2: Emergency Funds
    page2 = doc.new_page(width=595, height=842)
    text_page2 = (
        "Personal Finance and Budgeting Mastery\n\n"
        "Chapter 2: Building and Maintaining an Emergency Fund\n\n"
        "An emergency fund is a dedicated cash reserve designed to shield individuals and households from unexpected, disruptive financial shocks. "
        "Common emergencies include unexpected medical bills, urgent car or home repairs, or sudden involuntary unemployment.\n\n"
        "1. Recommended Fund Size: Financial advisors broadly recommend accumulating between 3 to 6 months of essential living expenses (your 'needs' "
        "from the 50/30/20 rule). Individuals with volatile freelance income, single-income households, or high dependents should target 6 to 9 months of expenses.\n\n"
        "2. Ideal Placement: Emergency funds must prioritize liquidity and capital preservation over aggressive investment returns. They should never be invested "
        "in the stock market, cryptocurrencies, or illiquid assets. The premier vehicle is a High-Yield Savings Account (HYSA) or a government money market fund, "
        "offering federal deposit insurance (FDIC or NCUA) and daily liquidity while earning competitive yield.\n\n"
        "3. Replenishment Discipline: If an emergency requires drawing down funds, pausing extra discretionary spending and prioritizing fund replenishment "
        "is essential before resuming aggressive long-term investing."
    )
    rect2 = fitz.Rect(50, 50, 545, 790)
    page2.insert_textbox(rect2, text_page2, fontsize=11, fontname="helv", align=fitz.TEXT_ALIGN_LEFT)

    # Page 3: Debt Payoff Strategies
    page3 = doc.new_page(width=595, height=842)
    text_page3 = (
        "Personal Finance and Budgeting Mastery\n\n"
        "Chapter 3: Debt Payoff Methodologies: Avalanche vs. Snowball\n\n"
        "Eliminating high-interest consumer debt (such as credit card balances carrying 20%+ APR) is the single most mathematically impactful action "
        "a person can take toward financial wellness. Two structured methodologies exist for systematic debt elimination:\n\n"
        "1. The Debt Avalanche Method: In this approach, you make minimum payments on all outstanding debts, then allocate all remaining debt-repayment capital "
        "toward the loan with the highest interest rate. Once that loan is completely paid off, roll the entire payment amount into the loan with the next highest interest rate. "
        "Mathematically, the Avalanche method minimizes total interest paid and results in the fastest debt-free date.\n\n"
        "2. The Debt Snowball Method: Developed by Dave Ramsey, this approach orders debts from smallest balance to largest balance, regardless of interest rate. "
        "You make minimum payments on all debts and aggressively pay off the smallest balance first. Eliminating smaller balances quickly provides psychological momentum "
        "and behavioral wins, which helps individuals stick to their financial plan.\n\n"
        "Conclusion: While Avalanche is mathematically optimal, Snowball is behaviorally powerful. The superior strategy is whichever method you can execute consistently."
    )
    rect3 = fitz.Rect(50, 50, 545, 790)
    page3.insert_textbox(rect3, text_page3, fontsize=11, fontname="helv", align=fitz.TEXT_ALIGN_LEFT)

    doc.set_metadata({"title": "Personal Finance and Budgeting Mastery", "author": "Finbot Educational Series"})
    doc.save(str(pdf_path))
    doc.close()
    print(f"Created: {pdf_path}")


def create_investing_fundamentals_pdf():
    pdf_path = DATA_DIR / "investing_fundamentals_guide.pdf"
    doc = fitz.open()

    # Page 1: Asset Classes
    page1 = doc.new_page(width=595, height=842)
    text_page1 = (
        "Fundamentals of Investing and Asset Classes\n\n"
        "Chapter 1: Overview of Core Asset Classes\n\n"
        "Investing is the act of allocating capital with the expectation of generating an income or profit over time. Understanding core asset classes "
        "is critical to designing a balanced portfolio:\n\n"
        "1. Equities (Stocks): Purchasing a stock gives you fractional ownership in a corporation. Historically, equities offer the highest long-term growth "
        "potential (averaging ~7-10% annual historical nominal return for broad indices like the S&P 500), but come with market volatility and principal risk in the short term.\n\n"
        "2. Fixed Income (Bonds): A bond is a loan made by an investor to a borrower (corporate or government). In return, the issuer pays periodic interest (coupon) "
        "and returns the principal upon maturity. Bonds provide portfolio stability, income generation, and downside cushioning during economic downturns.\n\n"
        "3. Cash Equivalents: Short-term instruments such as Treasury bills, certificates of deposit (CDs), and money market funds. They protect capital and provide "
        "near-instant liquidity, but expose long-term purchasing power to inflation drag.\n\n"
        "4. Real Estate: Physical properties or Real Estate Investment Trusts (REITs) that offer rental income and capital appreciation, often serving as an inflation hedge."
    )
    rect1 = fitz.Rect(50, 50, 545, 790)
    page1.insert_textbox(rect1, text_page1, fontsize=11, fontname="helv", align=fitz.TEXT_ALIGN_LEFT)

    # Page 2: Index Funds and ETFs
    page2 = doc.new_page(width=595, height=842)
    text_page2 = (
        "Fundamentals of Investing and Asset Classes\n\n"
        "Chapter 2: Index Funds and Exchange-Traded Funds (ETFs)\n\n"
        "Pioneered by John Bogle, founder of Vanguard, index investing transformed retail wealth accumulation by emphasizing low fees and broad diversification:\n\n"
        "1. What is an Index Fund? An index fund is a pooled mutual fund or ETF designed to replicate the performance of a specific financial market benchmark, "
        "such as the S&P 500 (the 500 largest publicly traded American companies) or the Russell 2000.\n\n"
        "2. Passive vs. Active Management: Active mutual fund managers attempt to beat the market through stock picking and market timing. Decades of data "
        "(such as the SPIVA report) reveal that over 85-90% of active fund managers underperform broad index benchmarks over 10-to-15-year periods after fees.\n\n"
        "3. The Impact of Expense Ratios: The expense ratio is the annual fee charged by the fund, expressed as a percentage of your investment. "
        "Broad index ETFs often boast expense ratios as low as 0.03% per year ($3 per $10,000 invested), whereas actively managed funds charge 0.75% to 1.50%. "
        "Over a 30-year investing career, an extra 1% fee can consume up to 25-30% of your total terminal portfolio value due to lost compound growth."
    )
    rect2 = fitz.Rect(50, 50, 545, 790)
    page2.insert_textbox(rect2, text_page2, fontsize=11, fontname="helv", align=fitz.TEXT_ALIGN_LEFT)

    # Page 3: Compound Interest & Time Horizon
    page3 = doc.new_page(width=595, height=842)
    text_page3 = (
        "Fundamentals of Investing and Asset Classes\n\n"
        "Chapter 3: The Mechanics of Compound Interest and Time Horizon\n\n"
        "Compound interest is interest calculated on the initial principal, which also includes all of the accumulated interest from previous periods.\n\n"
        "1. The Compounding Equation: The future value of an investment is governed by A = P(1 + r/n)^(nt), where P is principal, r is annual interest rate, "
        "n is compounding frequency per year, and t is time in years. Because time (t) resides in the exponent, duration is the most powerful variable in wealth creation.\n\n"
        "2. The Rule of 72: A quick mental shortcut to estimate the number of years required to double your money at a fixed annual return. "
        "Divide 72 by the expected annual rate of return. For example, at an 8% annual return, an investment will double approximately every 9 years (72 / 8 = 9).\n\n"
        "3. The Cost of Delay: An investor who invests $300 per month from age 20 to 30 and never adds another penny will often accumulate more wealth by retirement "
        "than someone who starts investing $300 per month at age 30 and continues every single month until age 65, purely due to the exponential snowball of early compounding."
    )
    rect3 = fitz.Rect(50, 50, 545, 790)
    page3.insert_textbox(rect3, text_page3, fontsize=11, fontname="helv", align=fitz.TEXT_ALIGN_LEFT)

    doc.set_metadata({"title": "Fundamentals of Investing and Asset Classes", "author": "Finbot Educational Series"})
    doc.save(str(pdf_path))
    doc.close()
    print(f"Created: {pdf_path}")


def create_retirement_accounts_pdf():
    pdf_path = DATA_DIR / "retirement_and_tax_advantaged_accounts.pdf"
    doc = fitz.open()

    # Page 1: 401(k) and Employer Match
    page1 = doc.new_page(width=595, height=842)
    text_page1 = (
        "Retirement and Tax-Advantaged Accounts\n\n"
        "Chapter 1: Workplace 401(k) Plans and the Employer Match\n\n"
        "Employer-sponsored retirement plans, most commonly 401(k) accounts, are specialized investment vehicles established to incentivize long-term retirement savings.\n\n"
        "1. Tax Structure of Traditional 401(k): Contributions are deducted directly from your gross paycheck before federal and state taxes are withheld. "
        "This immediately reduces your taxable income for the current calendar year. Investments grow tax-deferred within the account until retirement, "
        "at which point withdrawals are taxed as ordinary income.\n\n"
        "2. The Employer Match (Free Money): Many employers offer matching contributions, such as dollar-for-dollar up to 3% of salary, or 50 cents on the dollar up to 6%. "
        "Contributing enough to secure the full employer match is considered rule number one in personal finance: capturing an immediate, guaranteed 50% to 100% return on your investment.\n\n"
        "3. Vesting Schedules: Some companies implement vesting schedules, requiring employees to stay at the organization for a defined tenure (e.g., 2 to 4 years) "
        "before fully owning the employer matching funds. Employee contributions are always 100% immediately vested."
    )
    rect1 = fitz.Rect(50, 50, 545, 790)
    page1.insert_textbox(rect1, text_page1, fontsize=11, fontname="helv", align=fitz.TEXT_ALIGN_LEFT)

    # Page 2: Traditional IRA vs Roth IRA
    page2 = doc.new_page(width=595, height=842)
    text_page2 = (
        "Retirement and Tax-Advantaged Accounts\n\n"
        "Chapter 2: Traditional IRA vs. Roth IRA: Key Differences\n\n"
        "Individual Retirement Accounts (IRAs) allow individuals to invest independently of their employer with significant tax advantages:\n\n"
        "1. Traditional IRA: Contributions are typically tax-deductible in the year they are made, subject to income thresholds if covered by a workplace retirement plan. "
        "Money grows tax-deferred. In retirement (starting after age 59.5), withdrawals are taxed at your future ordinary income tax bracket. "
        "Traditional IRAs are best suited for individuals who anticipate being in a lower tax bracket during retirement than in their peak earning years.\n\n"
        "2. Roth IRA: Established by the Taxpayer Relief Act of 1997, Roth IRAs are funded with post-tax dollars (no immediate tax deduction). "
        "However, investment earnings grow completely tax-free, and qualified withdrawals after age 59.5 are 100% tax-free. Furthermore, your direct contributions "
        "(principal) can be withdrawn at any time without taxes or penalties. Roth IRAs are ideal for young earners and early-career professionals currently in low tax brackets.\n\n"
        "3. Contribution Limits: Annual contributions across Traditional and Roth IRAs are subject to statutory IRS limits (e.g., $7,000 for 2024, with catch-up contributions for individuals age 50 and older)."
    )
    rect2 = fitz.Rect(50, 50, 545, 790)
    page2.insert_textbox(rect2, text_page2, fontsize=11, fontname="helv", align=fitz.TEXT_ALIGN_LEFT)

    doc.set_metadata({"title": "Retirement and Tax-Advantaged Accounts", "author": "Finbot Educational Series"})
    doc.save(str(pdf_path))
    doc.close()
    print(f"Created: {pdf_path}")


if __name__ == "__main__":
    create_personal_finance_pdf()
    create_investing_fundamentals_pdf()
    create_retirement_accounts_pdf()
    print("All financial education reference documents created successfully.")
