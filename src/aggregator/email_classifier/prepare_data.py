import pandas as pd


NON_TRANSACTION_SENDERS = [
    "notifications@acquire.com",
    "noreply@mailers.zomato.com",
    "alerts@indigobluchipalerts.goindigo.in",
    "no-reply@accounts.google.com",
    "mailers@marketing.goindigo.in",
    "no-reply@tldv.io",
    "no-reply@sg.newsletter.agoda-emails.com",
    "replyto@email.microsoft.com",
    "customercare@dotandkey.com",
    "newsletters@valueresearchonline.net",
    "no-reply@promo.flights.airasia.com",
    "email@mailer.axismaxlife.com",
    "noreply@email.openai.com",
    "messages-noreply@linkedin.com",
    "notifications@github.com",
    "noreply@weblate.org",
    "jeremy@builtwithscience.com",
    "noreply@respondent.io",
    "support@mail.meditatehappier.com",
    "themouthful@mail.beehiiv.com",
    "sandeep.jethwani@dezerv.in",
    "no-reply@ultimate-guitar.com",
    "entertainment@mailer.jio.com",
    "messaging-digest-noreply@linkedin.com",
    "naukrialerts@naukri.com",
    "hello@mkt.getyourguide.com",
    "noreply@instahyre.com",
    "cassie@devpost.com",
    "hello@theclubb.co",
    "support@quickride.in",
    "noreply@zen-makemytrip.com",
    "jiofiber@mailer.jio.com",
    "calendar-notification@google.com",
    "do-not-reply@in4.actcorp.in",
    "donotreply.evoting@cdslindia.co.in",
    "onlinecourses@nptel.iitm.ac.in",
    "noreply@glassdoor.com",
    "hello@justinguitar.com",
    "welcome@hello.fable.co",
    "updates@comm.perforacare.com",
    "notify@cutshort.iozach.m@educative.io",
    "updates-noreply@linkedin.com",
    "suraj@pointer.io",
    "voila@alerts.cutshort.io",
    "info@axismf.com",
    "bwrewards@email.bloomandwild.com",
    "care@emaila.1mg.com",
    "donotreply@mailer11.actcorp.in",
    "uber@uber.com",
    "noreply@communication.porter.in",
    "info@mail.musescore.com",
    "rf-writers-noreply@quora.com",
    "happiness@moments.fnp.com",
    "nse_alerts@nse.co.in",
    "james@jamesclear.com",
    "Innercircle@tajhotels.com",
    "welcome@openrouter.ai",
    "team@news.fly.io",
    "noreply@capacities.io",
    "jonathan+j@wonsulting.com",
    "info@consumereducation-in.experian.com",
    "email@deals.priceline.com",
    "customer-reviews-messages@amazon.in",
    "algomaster@substack.com",
    "promotions@exclusive.goindigo.in",
    "mail@madrasinherited.in",
    "no-reply@grab.com",
    "em@em1.cloudflare.com",
    "communication@quant.in",
    "marc@master.dev",
    "notifications@vercel.com",
    "hello+all@wonsulting.com",
    "order-update@amazon.in",
    "shipment-tracking@amazon.in",
    "prime@amazon.in",
    "informational@email.snapchat.com",
    "support@educative.io",
    "no-reply@notice.ihub.image.canon",
    "noreply@github.com",
    "no-reply@github.com",
    "jerrylee@wonsulting.com",
    "newsletter@email.bloomandwild.com",
    "info@bseindia.in",
    "hello@tokenrouter.com",
    "Team-Jio@mailer.jio.com",
    "info@communication.dspim.com",
    "services@custcomm.icici.bank.in",
    "chennaipy@python.org",
    "info@n.myprotein.com",
    "no-reply@promo.airasia.com",
    "google-maps-noreply@google.comnoreply@respondent.io",
    "info@respondent.io",
    "team@levels.fyi",
    "mailers@IndiGoBluChip.goindigo.in",
    "support@cleartax.in",
    "no-reply@amazonmusic.com",
    "payments-noreply@google.com",
    "hi@mlh.io",
    "security@mail.instagram.com",
    "noreply@zomato.com",
    "googleplay-noreply@google.com",
    "recommended@abslmf.adityabirlacapital.org",
    "katie@rescuetime.com",
    "nps-alerts@proteantech.in",
    "hello@circleci.com",
    "learn@eccouncil.org",
    "invitations@linkedin.com",
    "no-reply@email.github.com",
    "team@chessly.com",
    "bisman+6a995d35ccfb5716b5f11977@reply.cutshort.io",
    "team@mail.clickup.com",
    "event@myiclubonline.com",
    "alert@info.bigbasket.com",
    "noreply@communication.hdfcergo.com",
    "billing@fly.io",
    "kotakmutualfund@camsonline.com",
    "noreply@usertesting.com",
    "innercircle@tajhotels.com",
    "hugo@hello.tidewave.ai",
    "jatan@comm.perforacare.com",
    "googleone-noreply@google.com",
    "support@digitalocean.com",
    "noreply@steampowered.com",
    "noreply@nvidia.com",
    "noreply-cloud-accounts@nvidia.com",
    "account@nvidia.com",
    "hi@himalayas.app",
    "info@chordify.net",
    "no-reply@emails.mistral.ai",
    "no-reply@alerts.spotify.com",
    "no-reply@bitwarden.com",
    "notifications_jiofiber@jio.com",
    "no-reply@backblaze.com",
    "instructors@updates.freeletics.com",
    "noreply@mailer13.actcorp.in",
    "kartic06@gmail.com",
    "vishnurm19@gmail.com",
    "events@dezerv.in",
    "no-reply@cashkaro.com",
    "communications1@sbicard.com",
    "no-reply@mailer17.actcorp.in",
    "yjayavel@kitmanlabs.com",
    "no-reply@alerts.actcorp.in",
    "jyuvaraj03@gmail.com",
    "info@backblaze.com",
    "offers@ihcltata.com",
    "noreply@swiggy.in",
    "no-reply@builds.circleci.com",
    "security@updates.linear.app",
    "email@mailer.maxlifeinsurance.com",
    "Notification@Jio.com",
    "evoting@nsdl.com",
    "notification@jio.com",
    "noreply@agoda.com",
    "hello@hinge.co",
    "info@realpython.com",
    "hello@levels.fyi",
    "googledevelopers-noreply@google.com",
    "marketing@royalbrothers.com",
    "hello@updates.truecaller.com",
]


df = pd.read_csv("data/emails.csv")
df.dropna(subset=["from"], inplace=True)


non_transaction_mask = df["from"].isin(NON_TRANSACTION_SENDERS)
df_unfiltered_count = df[~non_transaction_mask].shape[0]

print(f"Total emails: {df.shape[0]}")
print(df_unfiltered_count)

df["is_transaction_alert"] = float("nan")
df.loc[non_transaction_mask, "is_transaction_alert"] = 0

# -------------------------------------------------
# We have filtered out some known non-transactional senders. Now we will filter out emails that are likely to be transactional based on their subject lines.

transaction_subjects = [
    "❗  You have done a UPI txn. Check details!",
    "View: Account update for your HDFC Bank A/c",
    "A payment was made using your Credit Card",
    "❗ New Deposit Alert: Check your A/c balance now!",
    "Transaction alert for your ICICI Bank Credit Card",
    "Transaction Success notification for Standing Instruction on your ICICI Bank Credit Card ",
    "Transaction notification on your Pluxee Card",
    "Transaction confirmation on your Pluxee Card",
    "Transaction Reversal on your Pluxee Card",
    "Your Pluxee Card has been credited",
    "Recurring E-mandate debit success on your SBI Credit Card",
    "Transaction Alert from SBI Card",
    "Your monthly reward points for using Amazon Pay ICICI Bank credit\r\n card added to your Amazon Pay balance"
]
non_transaction_subjects = [
    "NFO Alert: Own India's malls and office parks!",
    "Your HDFC Bank - Swiggy HDFC Bank Credit Card Statement - September-2026",
    "HDFC Bank App update: A Quick Guide for Mobile Number Update",
    "HDFC Bank Combined Email Statement for August-2026 ",
    "⚠️ Scheduled Downtime Alert for HDFC Bank UPI Services - April 2025",
    "HDFC Bank Combined Email Statement for Mar-2025 ",
    "Payment unsuccessful HDFC Bank Debit Card xx3358",
    "⚠️ Tax Season Alert: Stay Safe from Tax Fraud",
    "NFO Closes today! HDFC Nifty Metal ETF",
    "HDFC Bank Combined Email Statement for July-2026 ",
    "Sum Insured & Claim Details Of Your HDFC ERGO Policy",
    "HDFC Bank Combined Email Statement for June-2026 ",
    "📊 Monetary Policy Review – June 2026: Key Signals & Outlook",
    "Successful registration of Standing Instructions on your ICICI Bank Credit Card ",
    "Amazon Pay ICICI Bank Credit Card Statement for the period August\r\n 3, 2026 to September 2, 2026",
    "Book your trip on Monday ➡️",
    "Beware of fake Customer Care numbers",
    "Amazon Pay ICICI Bank Credit Card Statement for the period April 3,\r\n 2025 to May 2, 2025",
    "Latest iPhone - Up to ₹4,000 instant cashback 💳",
    "Xiaomi smartphones on sale! Up to ₹10,000 off ➡️",
    "This IPL, get exciting offers on your ICICI Bank Visa Credit Card.",
    "Redemption request received throughKUVERA",
    "What kind of future are you building?",
    "NFO Alert 🔔",
    "Amazon Pay ICICI Bank Credit Card Statement for the period March 3,\r\n 2025 to April 2, 2025"
    "Year End Update! Few Edge+ Cards Left",
    "Exclusive discounts on traveling to Dubai ✨",
    "You missed out on Aurora!",
    "Aurora early access, now live",
    "You asked, we answered. Here’s Aurora’s price",
    "Experience luxury like never before",
    "Here’s the upgrade your lifestyle deserves",
    "Make every journey memorable",
    "Aurora is calling. Will you answer?",
    "Experience luxury like never before!",
    "📄 Your Federal Bank Account Statement is ready to download",
    "Rewards like never before. Rarer than ever before.",
    "Founder’s note: We chose a few. You are one of them",
    "You may have earned your spot for this!",
    "Earn Up to 7% on your account balance!",
    "Does your insurance cover medical inflation?",
    "Is your existing health insurance enough?",
    "Zero Joining Fee on Edge+ RuPay Credit Card.",
    "Cashback on every spend, every day!",
    "Save ₹50,000+ with this credit card",
    "It’s live: The Grandmaster of rewards, in action 🎬",
    "Yuvaraj, save ₹50,000+ with this credit card",
    "Yuvaraj, here’s what’s new for you on Jupiter ✨",
    "Get the lifetime free Edge CSB Bank RuPay Credit Card",
    "Earn up to ₹3,000 cashback every month",
    "Up to ₹7,00,000 credit limit for Yuvaraj",
    "Love to dine? Earn 2% cashback on every food order",
    "The best RuPay Credit Card for shoppers!",
    "Filing your ITR for FY 24-25? 💰",
    "Earn 2% cashback on flights, hotels, and all travel books",
    "Up to ₹7,00,000 credit limit for Yuvaraj",
    "Payment Declined.",
    "Usage Settings Modified Successfully for your PluxeeCard",
    "Your My Meal Wallet benefit is now active",
    "Your Meal benefit is now active",
    "Your Pluxee Card has been Activated!",
    "Pluxee Card Activation Code",
    "Congratulations on your new Pluxee Card!",
    "E-account statement for your SBI account(s).",
    "Enjoy Up To 10% Savings on Your Visa SBI Credit Card",
    "Your SimplySAVE - SBI Card Monthly Statement -Sep 2026",
    "Great Savings on EMI purchases on Amazon🛍",
    "Your Guide to Smart Credit Card Usage: Chapter 2",
    "Secure yourself with SBI General's Personal Accident Insurance Policy",
    "A year of rewards on Fuel & more, without any joining fee!",
    "Make the most of your SimplySAVE SBI Card",
    "Unbeatable Offers for Your Next Travel Booking",
    "⚠️Beware of Malicious Applications on Your Phone",
    "Wishing you Happy Raksha Bandhan",
    "Rakhi Celebrations with SBI Card E-Store",
]


def _is_a_transaction_email_subject(subject: str) -> int | float:
    if subject in transaction_subjects:
        return 1
    elif subject in non_transaction_subjects:
        return 0
    else:
        return float("nan")


unprocessed_mask = df["is_transaction_alert"].isna()
df.loc[unprocessed_mask, "is_transaction_alert"] = df.loc[unprocessed_mask, "subject"].apply(
    _is_a_transaction_email_subject
)

# -------------------------------------------------
# Sampling
definitely_transaction_mask = df['is_transaction_alert'] == 1
definitely_not_transaction_mask = df['is_transaction_alert'] == 0
RANDOM_STATE = 42

# First sample: 450 definitely not transaction emails
definitely_not_transaction_sample = df[definitely_not_transaction_mask].sample(n=450, random_state=RANDOM_STATE)

# Second sample: 20 per subject of definitely transaction emails
definitely_transaction_sample = (
    transaction_df
    .sample(frac=1, random_state=RANDOM_STATE) # random shuffle first
    .groupby('subject', group_keys=False)
    .head(20)
).sample(n=150, random_state=RANDOM_STATE)
samples_together = pd.concat([definitely_not_transaction_sample, definitely_transaction_sample])

# write the labelled samples to CSV
samples_together.to_csv("data/labelled_samples.csv", index=False)
