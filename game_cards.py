"""Hand-written cards for the "Scam or Legit?" game.

Cards are written and checked by hand on purpose: the game teaches, so a wrong
label would be worse than no game. All names, numbers and links are made up.

Fields
- id        unique short id
- channel   where the message arrives (shown as a label)
- sender    who it claims to be from
- text      the message the player judges
- verdict   "scam" or "legit"
- flags     3 short points: red flags for scams, green flags for legit cards
- why       one or two sentences explaining the verdict
- tip       one practical habit to remember
"""
from __future__ import annotations

from typing import Any, Dict, List

CARDS: List[Dict[str, Any]] = [
    # ------------------------------------------------------------------ SCAMS
    {
        "id": "s01", "channel": "Instagram reel", "sender": "@WealthWithRohit", "verdict": "scam",
        "text": "This penny stock will 10x by Diwali! I made ₹4 lakh in 2 weeks. Join my VIP Telegram group, only ₹999. Last 10 seats!",
        "flags": ["Promises a 10x return", "Fake scarcity: \"last 10 seats\"", "Sells stock tips with no registration shown"],
        "why": "Nobody can predict prices, and a person who sells paid stock advice must be registered with SEBI. A promise of 10x is bait, not analysis.",
        "tip": "Ask for the SEBI registration number and check it on SEBI's website before trusting any paid tip.",
    },
    {
        "id": "s02", "channel": "WhatsApp", "sender": "Unknown number", "verdict": "scam",
        "text": "Congratulations! You are selected for a part-time job. Like YouTube videos and earn ₹3,000 per day. Pay ₹500 registration fee to start.",
        "flags": ["Money first: you pay to \"earn\"", "Huge pay for a trivial task", "Unsolicited message from a stranger"],
        "why": "Real employers never charge you to start work. These \"task\" jobs show small early payouts, then ask for bigger deposits.",
        "tip": "If you have to pay before you can earn, walk away.",
    },
    {
        "id": "s03", "channel": "SMS", "sender": "BANK-ALERT", "verdict": "scam",
        "text": "Dear customer, your KYC has expired and your account will be blocked in 24 hours. Click bit.ly/kyc-upd8 to update now.",
        "flags": ["Urgent threat with a deadline", "Shortened link hides the real site", "Banks do not fix KYC through SMS links"],
        "why": "The link leads to a fake page that steals your login or card details. Fear and a ticking clock are the scammer's main tools.",
        "tip": "Never tap links in alerts. Open your bank's official app or visit the branch instead.",
    },
    {
        "id": "s04", "channel": "UPI app", "sender": "Amit (Refund)", "verdict": "scam",
        "text": "You have received ₹5,000 from Amit. To accept the money, enter your UPI PIN.",
        "flags": ["Your PIN is never needed to receive money", "Surprise money you did not expect", "\"Accept\" wording hides a payment request"],
        "why": "A UPI PIN is only for sending money. This is a collect request: entering your PIN sends ₹5,000 out of your account.",
        "tip": "Receiving money never needs a PIN. If a screen asks for it, you are about to pay.",
    },
    {
        "id": "s05", "channel": "Telegram", "sender": "CryptoKing Official", "verdict": "scam",
        "text": "Guaranteed 30% returns every month on crypto. Invest ₹10,000 today and withdraw anytime. Already 2,000 happy investors!",
        "flags": ["\"Guaranteed\" returns on a risky asset", "30% a month is far beyond any real investment", "Crowd claims you cannot verify"],
        "why": "Real investments move up and down, and no one can guarantee a monthly profit. Such schemes pay early members with new members' money until they collapse.",
        "tip": "A guaranteed high return is the biggest red flag in investing.",
    },
    {
        "id": "s06", "channel": "SMS", "sender": "Unknown mobile number", "verdict": "scam",
        "text": "Electricity dept: your bill is unpaid and power will be cut tonight at 9:30 PM. Call 98XXXXXXXX immediately to avoid disconnection.",
        "flags": ["Disconnection tonight creates panic", "A personal mobile number, not an official helpline", "Asks you to call instead of using the bill or app"],
        "why": "The caller will talk you into paying a small \"pending amount\" or installing a remote-access app that empties your account.",
        "tip": "Check dues only on the official website, app, or the number printed on your own bill.",
    },
    {
        "id": "s07", "channel": "Loan app", "sender": "QuickCash Now", "verdict": "scam",
        "text": "Instant ₹50,000 with no documents! Allow access to your contacts, photos and messages to continue.",
        "flags": ["Asks for contacts and photos, not needed for a loan", "\"No documents\" skips basic checks", "Unknown lender with no regulator details"],
        "why": "Predatory loan apps use your contact list to harass you and your friends if you are late. Real lenders are regulated and do not need your gallery.",
        "tip": "Borrow only from lenders regulated by the RBI, and deny permissions an app does not need.",
    },
    {
        "id": "s08", "channel": "Phone call", "sender": "\"Customs officer\"", "verdict": "scam",
        "text": "A parcel in your name contains illegal items. You will be arrested unless you transfer ₹40,000 now to clear your name. Stay on this video call.",
        "flags": ["Threat of arrest", "Orders you to stay on the call", "Demands money to \"clear\" a case"],
        "why": "No agency arrests people or settles cases over a video call. This \"digital arrest\" trick works by keeping you scared and isolated.",
        "tip": "Hang up and talk to a family member or call the police helpline yourself. Real authorities do not ask for payment on calls.",
    },
    {
        "id": "s09", "channel": "WhatsApp group", "sender": "Smart Money Circle", "verdict": "scam",
        "text": "Official SEBI-registered mutual fund app! Download the APK from this link and double your money in 45 days.",
        "flags": ["App installed from a link, not the app store", "\"Double in 45 days\"", "Claims to be registered without proof"],
        "why": "Installing an APK from a chat link can give a stranger access to your phone. Mutual funds never promise to double money on a date.",
        "tip": "Install finance apps only from the official app store and check the company on the regulator's website.",
    },
    {
        "id": "s10", "channel": "Facebook ad", "sender": "News24 Money (lookalike page)", "verdict": "scam",
        "text": "A famous cricketer reveals: turn ₹21,000 into ₹2 lakh every month with this AI trading robot. Click now before it's banned!",
        "flags": ["Celebrity endorsement that is often faked", "An \"AI robot\" with no track record", "\"Before it's banned\" pressure"],
        "why": "Scam ads often use fake or edited videos of famous people. If a robot could print ₹2 lakh a month, its owners would not be advertising it.",
        "tip": "Treat any celebrity-backed \"secret\" money-making tool as a scam until proven otherwise.",
    },
    {
        "id": "s11", "channel": "Resale app chat", "sender": "Buyer: \"Vikas K\"", "verdict": "scam",
        "text": "I'll pay ₹12,000 for your sofa. I can't talk now, just scan this QR code and I will send the money.",
        "flags": ["Scanning a QR sends money, it does not receive it", "Buyer avoids talking", "Sends you a QR instead of asking for yours"],
        "why": "A QR code you scan is a payment request. Money only comes to you if the buyer scans yours or pays your UPI ID.",
        "tip": "To receive money, you share your own UPI ID or QR. You never scan one.",
    },
    {
        "id": "s12", "channel": "Email", "sender": "refund@incometax-gov-support.example", "verdict": "scam",
        "text": "Your income tax refund of ₹18,540 is approved. Enter your card number, CVV and OTP to receive the refund.",
        "flags": ["Refunds do not need your card, CVV or OTP", "Lookalike email address", "Surprise refund with a form to fill"],
        "why": "A refund is credited to your bank account, so no card details are needed. CVV and OTP let a thief spend your money.",
        "tip": "Check refund status only on the official income tax portal that you type in yourself.",
    },
    # ------------------------------------------------------------------ LEGIT
    {
        "id": "l01", "channel": "SMS", "sender": "Your bank (registered sender)", "verdict": "legit",
        "text": "₹2,500 debited from A/c XX1234 on 31-Oct via UPI to SWIGGY. If this was not you, call your bank's official helpline or visit your branch.",
        "flags": ["Only informs, asks you for nothing", "No link and no request for details", "Tells you to use official channels"],
        "why": "This is a normal transaction alert. It gives facts and points you to the bank's own helpline if something looks wrong.",
        "tip": "Read your alerts. A surprise debit is how you catch fraud early.",
    },
    {
        "id": "l02", "channel": "SMS", "sender": "Mutual fund company", "verdict": "legit",
        "text": "Your SIP of ₹2,000 in Example Flexi Cap Fund (folio 123456) was processed. Units allotted at NAV ₹48.21. Mutual fund investments are subject to market risks.",
        "flags": ["Confirms something you set up yourself", "Includes folio number, NAV and the risk line", "No promise of returns and no link to click"],
        "why": "This confirms a SIP you started. It states the NAV and carries the standard market-risk reminder instead of promising profit.",
        "tip": "Keep your folio numbers handy so you can match these confirmations to what you invested in.",
    },
    {
        "id": "l03", "channel": "SMS", "sender": "Your bank", "verdict": "legit",
        "text": "123456 is your OTP for a ₹799 payment at an online store. Do not share it with anyone. Bank staff never ask for your OTP. (You just tapped Pay in a shopping app.)",
        "flags": ["You started this payment yourself", "Warns you not to share the OTP", "Amount and purpose match what you did"],
        "why": "An OTP you receive right after you start a payment is normal. It becomes a scam only if someone else asks you to read it out.",
        "tip": "An OTP you did not trigger, or one a caller asks for, is always a red flag.",
    },
    {
        "id": "l04", "channel": "Bank website", "sender": "Small finance bank", "verdict": "legit",
        "text": "1-year fixed deposit at 7.5% a year. Deposits up to ₹5 lakh per depositor are insured by DICGC. Open it in the bank's official app.",
        "flags": ["A fixed, stated rate with no \"guarantee\" hype", "Mentions deposit insurance and its limit", "Sends you to the official app"],
        "why": "The rate is higher than big banks but plausible for a small finance bank, and the offer states the insurance cover and its limit.",
        "tip": "Higher rates can mean more risk. Never put more than the insured limit in one bank without a reason.",
    },
    {
        "id": "l05", "channel": "Email", "sender": "Your broker (from the official domain)", "verdict": "legit",
        "text": "Welcome! Complete your KYC inside the official app of our SEBI-registered brokerage using DigiLocker. We will never ask for your password or OTP on a call.",
        "flags": ["Uses the official app and DigiLocker", "States it is regulated and shows how to verify", "Warns you about calls asking for secrets"],
        "why": "This points you to the broker's own app and a government verification service, and tells you what it will never ask for.",
        "tip": "Verify any broker on SEBI's website before you open an account.",
    },
    {
        "id": "l06", "channel": "LinkedIn message", "sender": "Independent adviser", "verdict": "legit",
        "text": "Hi, I'm a SEBI-registered investment adviser. My registration number is in my profile and you can verify it on SEBI's website. Fee: fixed ₹10,000 per year, no commissions, no return guarantees.",
        "flags": ["Registration number you can check", "Clear fixed fee, no commission", "Explicitly makes no return promises"],
        "why": "Registered advisers can be looked up and charge disclosed fees. Refusing to promise returns is a sign of honesty, not weakness.",
        "tip": "Verify first, then talk. A real adviser will be happy to be checked.",
    },
    {
        "id": "l07", "channel": "RBI website", "sender": "Reserve Bank of India", "verdict": "legit",
        "text": "Individuals can buy government securities directly by opening an account on the RBI's official Retail Direct portal. The interest rate is fixed for the issue.",
        "flags": ["Official government source", "Describes a product without hype", "Rate comes from the issue, not from a promoter"],
        "why": "Government securities are backed by the government, so default risk is very low. Prices can still change if you sell before maturity.",
        "tip": "Low risk does not mean no risk. Match the maturity to when you need the money.",
    },
    {
        "id": "l08", "channel": "Email", "sender": "Your bank (official domain)", "verdict": "legit",
        "text": "Your October statement is ready. Log in to the official app or website to view it. We will never ask for your PIN or password by email.",
        "flags": ["Asks you to log in yourself, no link to a form", "Says what it will never ask for", "Matches a routine monthly event"],
        "why": "Statement notices are routine. This one does not ask you to confirm any details or open an attachment.",
        "tip": "Type the bank's address yourself or use its app, even when an email looks real.",
    },
    {
        "id": "l09", "channel": "UPI app", "sender": "Rahul (your friend)", "verdict": "legit",
        "text": "Rahul has requested ₹450: \"Dinner split\". You were at the dinner. Check the name and amount, then pay with your PIN if correct.",
        "flags": ["You know the person and the reason", "Amount matches what you owe", "You are paying, which is when a PIN is needed"],
        "why": "A request from someone you know for a bill you actually shared is fine. The PIN is correctly used to send money you agreed to pay.",
        "tip": "Before approving any request, check who it is from, how much, and why.",
    },
]

REQUIRED_FIELDS = ("id", "channel", "sender", "text", "verdict", "flags", "why", "tip")


def validate_cards(cards: List[Dict[str, Any]] = CARDS) -> None:
    """Raise ValueError if the card bank is malformed. Used by the tests."""
    seen = set()
    for c in cards:
        missing = [f for f in REQUIRED_FIELDS if not c.get(f)]
        if missing:
            raise ValueError(f"Card {c.get('id')} is missing: {missing}")
        if c["id"] in seen:
            raise ValueError(f"Duplicate card id {c['id']}")
        seen.add(c["id"])
        if c["verdict"] not in ("scam", "legit"):
            raise ValueError(f"Card {c['id']} has a bad verdict")
        if len(c["flags"]) != 3:
            raise ValueError(f"Card {c['id']} must have exactly 3 flags")
