# 1. Credit Risk Analysis and Default Prediction
## 1.1 Business Context & Project Overview

In the financial industry, accurately assessing a loan applicant's credit risk is crucial for minimizing financial losses and making informed lending decisions. This project addresses this challenge by developing a comprehensive solution to predict loan default.

This project was developed as the final capstone for the Talent Tech - Data Analysis Bootcamp in collaboration with the University of Antioquia. Using the Home Credit Default Risk dataset from a Kaggle competition, we performed an end-to-end data science lifecycle: from data acquisition and cleaning to exploratory data analysis, feature engineering, and the development of predictive machine learning models. The final outcome is a robust model capable of classifying applicants based on their probability of default and a set of key business insights derived from the data.

# 2 App Demostration

https://github.com/user-attachments/assets/3e0c1ce2-f7f7-4c7c-a315-0fcc5512ea82

# 3. The Dataset

The data was sourced from the Home Credit Default Risk competition on Kaggle. The dataset is composed of multiple related tables, providing a rich, real-world view of applicants' financial history.
application_train.csv / application_test.csv: The main table containing information about each loan application and the TARGET variable (1: client with payment difficulties, 0: all other cases).
bureau.csv & bureau_balance.csv: Data concerning clients' previous credits from other financial institutions. previous_application.csv: Data about previous loan applications with Home Credit.
credit_card_balance.csv / POS_CASH_balance.csv / installments_payments.csv: Data on previous points of sale, cash loans, and credit card balances.

# 4. Repository Structure

This project follows a structured and modular layout to ensure clarity, scalability, and reproducibility.

<img width="692" height="306" alt="image" src="https://github.com/user-attachments/assets/8ac1e387-7fff-4486-8317-165cc406a777" />

# 5. Methodology and Data Pipeline

We implemented a Bronze / Silver / Gold data pipeline structure to systematically process and refine the data for analysis and modeling.

## 5.1. Bronze Layer (Data Acquisition)
Raw data was downloaded from Kaggle as CSV files. These files were imported into a MySQL database instance to facilitate querying, joining, and large-scale data manipulation.

## 5.2. Silver Layer (Data Cleaning & Preprocessing)
- Collaborative Cleaning: Each team member was responsible for cleaning a specific set of tables.
- Key Actions: Data type conversion, handling of outliers and missing values, standardization of column names (e.g., SK_ID_CURR), and removal of redundant or uninformative columns.
  The cleaned tables were stored in the Silver layer, ready for exploratory analysis.

## 5.3. Gold Layer (Feature Engineering & Aggregation)
- Insight-Driven Features: Using insights from the EDA, we generated new, aggregated features that summarize customer behavior. Examples include FRAC_LATE_INSTALLMENTS, AVG_UTILIZATION_RATIO_TDC, and BUREAU_ACTIVE_COUNT.
- Table Consolidation: All relevant features were merged into final, wide tables optimized for modeling and dashboard consumption. This drastically reduced processing time in later stages.

# 6. Key Findings from Exploratory Data Analysis (EDA)

The EDA, conducted primarily with MySQL queries, revealed several critical patterns:

- Late Payment Behavior: While the majority of clients pay on time, a small but significant segment of clients consistently pays late, representing a high-risk group.
- Credit Utilization: Clients using close to or over 100% of their credit limit represent a higher financial stress and default risk.
- Approval Rates by Channel: In-person channels (like physical branches) showed significantly higher approval rates.
- Loan Amount vs. Status: Rejected applications were, on average, for much higher amounts than approved ones, indicating a conservative policy towards large loans.

# 7. Machine Learning Models

To address the diverse customer base, we developed two distinct classification models using Random Forest, chosen for its robustness with heterogeneous data and its interpretability via feature importance.

## 7.1. Model for New Applicants (No Prior History)
This model predicts default risk based on sociodemographic and behavioral data. Key features included AMT_INCOME_TOTAL, NAME_FAMILY_STATUS, and NAME_HOUSING_TYPE.

## 7.2. Model for Existing Clients (With Prior History)
This model leverages rich historical financial data. Key features included variables related to past credit history (BUREAU_LOAN, BUREAU_STATUS) and previous contract types.
This segmented approach allows for a more tailored and accurate risk assessment.

# 8. Project Management & Team Contributions
This project was executed within a demanding one-week sprint, applying the Scrum methodology. We used Trello to manage our product backlog and track progress.
If you want see Trello ----> https://trello.com/invite/b/688b808e4beda113d9301e95/ATTI5bf389b477c2866f5582c69c7966a5d09C8B703D/final-project-credit-risk

## Full Team Contributions

- Juan Pablo González Blandón: credit_card_balance, installments_payments,	ML Modeling, Project Structuring, Dashboard Architecture (Main and Credit sections), Leadership Trello and assign tasks.
- Juan Felipe Isaza Valencia: application_train, application_test (main tables)	ML Modeling, Project Structuring, Dashboard Architecture (Models Section).
- Jorge Antonio Álvarez Sayas: bureau, bureau_balance (external credit history).
- Alexis de Jesús Collante Genes: pos_cash_balance, previous_application (internal history), Dashboard Architecture (Applications section)

# 9. Technology Stack
- Programming Language: Python
- Data Manipulation & Analysis: Pandas, NumPy
- Database: MySQL
- Machine Learning: Scikit-learn
- Data Visualization: Matplotlib, Seaborn, (Library used for dashboard, Streamlit and Plotly Dash)
- Project Management: Trello, Git & GitHub
