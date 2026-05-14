# Credit Risk Assessment

## Introduction
Credit risk is the possibility that a borrower will fail to meet their obligations in accordance with agreed terms. Effective credit risk assessment is fundamental to financial institution profitability and stability.

## Types of Credit Risk

### Default Risk
- **Definition**: Risk that borrower will not repay principal or interest
- **Impact**: Direct financial loss
- **Mitigation**: Credit scoring, collateral, guarantees

### Concentration Risk
- **Definition**: Excessive exposure to single borrower, industry, or geography
- **Impact**: Amplified losses if concentration area fails
- **Mitigation**: Diversification, exposure limits

### Country Risk
- **Definition**: Risk from political, economic, or social instability in borrower's country
- **Factors**: Government stability, economic policies, currency risk
- **Mitigation**: Country limits, political risk insurance

### Counterparty Risk
- **Definition**: Risk that other party in financial transaction will default
- **Common in**: Derivatives, securities lending, trade finance
- **Mitigation**: Collateral, margining, netting agreements

## Credit Assessment Components

### Borrower Analysis

**The 5 Cs of Credit**:

1. **Character**:
   - Credit history
   - Payment patterns
   - Reputation
   - Legal history
   - Management quality (for businesses)

2. **Capacity**:
   - Income level and stability
   - Debt-to-income ratio
   - Cash flow analysis
   - Employment history
   - Business performance trends

3. **Capital**:
   - Net worth
   - Asset ownership
   - Investment in business (for business loans)
   - Down payment or equity contribution

4. **Collateral**:
   - Asset value
   - Liquidity of asset
   - Ease of repossession and sale
   - Loan-to-value ratio

5. **Conditions**:
   - Economic environment
   - Industry conditions
   - Purpose of loan
   - Loan terms and structure

### Financial Analysis

**For Individuals**:
- Income verification
- Employment stability
- Existing debt obligations
- Savings and assets
- Recent credit inquiries

**For Businesses**:
- **Liquidity ratios**:
  - Current ratio (Current Assets / Current Liabilities)
  - Quick ratio ((Current Assets - Inventory) / Current Liabilities)
  
- **Leverage ratios**:
  - Debt-to-equity (Total Debt / Total Equity)
  - Interest coverage (EBIT / Interest Expense)
  
- **Profitability ratios**:
  - Net profit margin (Net Income / Revenue)
  - Return on assets (Net Income / Total Assets)
  
- **Cash flow analysis**:
  - Operating cash flow
  - Free cash flow
  - Cash conversion cycle

## Credit Scoring Models

### FICO Score (Consumer)
**Range**: 300-850

**Components**:
- Payment history (35%)
- Amounts owed (30%)
- Length of credit history (15%)
- New credit (10%)
- Credit mix (10%)

**Score bands**:
- Exceptional: 800-850
- Very Good: 740-799
- Good: 670-739
- Fair: 580-669
- Poor: 300-579

### VantageScore (Consumer)
**Range**: 300-850

**Components**:
- Payment history (Extremely influential)
- Age and type of credit (Highly influential)
- Percentage of credit used (Highly influential)
- Total balances/debt (Moderately influential)
- Recent credit behavior (Less influential)
- Available credit (Less influential)

### Custom Scorecards

**Development process**:
1. **Data collection**: Historical loan performance
2. **Variable selection**: Identify predictive factors
3. **Model building**: Statistical or ML techniques
4. **Validation**: Test on hold-out sample
5. **Implementation**: Integration into systems
6. **Monitoring**: Ongoing performance tracking

**Common variables**:
- Credit bureau score
- Income level
- Employment tenure
- Debt service ratio
- Property ownership
- Previous relationship with institution

### Business Credit Scores

**Dun & Bradstreet PAYDEX**:
- Range: 1-100
- Based on payment history
- 80+ is considered good

**Experian Business Credit Score**:
- Range: 1-100
- Includes payment history, credit utilization, company info

**Factors**:
- Payment history with suppliers
- Credit utilization
- Company age and size
- Industry risk
- Public records (liens, judgments)

## Probability of Default (PD) Models

### Logistic Regression
**Approach**:
- Binary outcome (default/no default)
- Linear combination of features
- Sigmoid function for probability

**Interpretation**:
- Coefficients show impact of each variable
- Odds ratios easily understood
- Transparent and explainable

### Machine Learning Models

**Decision Trees/Random Forests**:
- Handle non-linear relationships
- Feature importance ranking
- Resistant to outliers
- Can capture interactions

**Gradient Boosting (XGBoost, LightGBM)**:
- High predictive accuracy
- Handles missing data
- Feature importance
- Requires careful tuning

**Neural Networks**:
- Complex pattern recognition
- Best with large datasets
- Less interpretable
- Computationally intensive

### Survival Analysis
- Time-to-default prediction
- Incorporates censored data
- Cox proportional hazards model
- Useful for loan vintage analysis

## Loss Given Default (LGD)

### Definition
Percentage of exposure lost when borrower defaults

**Formula**: 
```
LGD = (Exposure at Default - Recovery) / Exposure at Default
```

### Factors Affecting LGD
- **Collateral**: Quality and coverage
- **Seniority**: Position in capital structure
- **Recovery process**: Efficiency and cost
- **Economic conditions**: Asset values during recovery
- **Legal system**: Foreclosure laws and timelines

### LGD Modeling
- Historical recovery data analysis
- Regression models
- Scenario analysis
- Stress testing

## Exposure at Default (EAD)

### Definition
Total value at risk when default occurs

**Components**:
- Outstanding balance
- Accrued interest
- Undrawn commitments (credit cards, lines of credit)

### Credit Conversion Factor (CCF)
Percentage of undrawn limit expected to be drawn at default

**Example**: $10,000 credit limit, $2,000 drawn, CCF 50%
```
EAD = $2,000 + ($8,000 × 50%) = $6,000
```

## Expected Loss (EL)

### Calculation
```
Expected Loss = PD × LGD × EAD
```

**Example**:
- PD = 5%
- LGD = 40%
- EAD = $100,000

```
EL = 5% × 40% × $100,000 = $2,000
```

### Application
- Loan pricing
- Provisioning for losses
- Capital allocation
- Portfolio risk assessment

## Basel Accords and Credit Risk

### Basel III Requirements

**Minimum Capital Ratios**:
- Common Equity Tier 1: 4.5%
- Tier 1 Capital: 6%
- Total Capital: 8%
- Capital Conservation Buffer: 2.5%

**Credit Risk Approaches**:

1. **Standardized Approach**:
   - Prescribed risk weights
   - External credit ratings
   - Simpler calculation

2. **Internal Ratings-Based (IRB)**:
   - Bank develops own PD estimates
   - Foundation IRB: Bank estimates PD, regulators set LGD/EAD
   - Advanced IRB: Bank estimates PD, LGD, and EAD

## Credit Risk Mitigation

### Collateral
**Types**:
- Real estate
- Vehicles
- Equipment
- Securities
- Cash deposits
- Accounts receivable

**Requirements**:
- Legal enforceability
- Valuation procedures
- Regular revaluation
- Insurance
- Documentation

### Guarantees and Credit Insurance
- Third-party payment guarantee
- Credit default swaps
- Export credit insurance
- Mortgage insurance

### Covenants
**Financial covenants**:
- Minimum liquidity ratios
- Maximum leverage ratios
- Minimum profitability
- Debt service coverage

**Operational covenants**:
- Restrictions on additional debt
- Dividend limitations
- Asset sale restrictions
- Change of control provisions

### Loan Structure
- Amortization schedule
- Shorter terms reduce exposure
- Floating vs. fixed rates
- Prepayment options

## Portfolio Management

### Diversification
**Dimensions**:
- Borrower concentration
- Industry diversification
- Geographic spread
- Product type mix
- Maturity distribution

**Limits**:
- Single borrower limits (% of capital)
- Industry concentration limits
- Country exposure limits
- Product concentration monitoring

### Credit Exposure Management
- Regular portfolio reviews
- Watchlist monitoring
- Early warning indicators
- Risk rating migrations
- Stress testing

### Provisioning
**General provisions**: Expected losses on performing loans
**Specific provisions**: Likely losses on problem loans

**CECL (Current Expected Credit Loss)**:
- Lifetime loss estimation
- Day-one provision recognition
- Forward-looking information

## Credit Monitoring

### Performance Metrics

**Portfolio quality**:
- Non-performing loan (NPL) ratio
- Net charge-off rate
- Delinquency rates (30, 60, 90+ days)
- Loan loss reserve coverage

**Risk metrics**:
- Average risk rating
- Risk rating migration
- Concentration metrics
- Expected loss trends

### Early Warning Indicators

**For individuals**:
- Missed payments
- Only minimum payments
- Maximum credit utilization
- Multiple new credit inquiries
- Employment changes
- Address changes

**For businesses**:
- Declining revenues or profits
- Deteriorating liquidity
- Covenant violations
- Management changes
- Adverse news
- Industry problems
- Delayed financial reporting

### Credit Review Process
- Periodic review of all credits
- Risk rating updates
- Documentation review
- Compliance check
- Relationship assessment

## Problem Loan Management

### Classification

**Standard**: Performing as agreed
**Special Mention**: Potential weaknesses
**Substandard**: Well-defined weaknesses
**Doubtful**: Collection in full unlikely
**Loss**: Uncollectible

### Workout Strategies
- Loan modification/restructuring
- Payment plans
- Additional collateral
- Guarantee enhancement
- Asset liquidation
- Legal action

## Technology in Credit Risk

### Automated Underwriting
- Rule-based decisioning
- Instant approvals for low-risk
- Consistent application of criteria
- Faster processing
- Scalability

### Alternative Data
- Utility payment history
- Rent payments
- Bank account transactions
- Mobile phone usage
- Social media (controversial)
- Education and employment

### Machine Learning
- More accurate predictions
- Complex variable interactions
- Continuous learning
- Handling big data
- Multiple model ensemble

### Blockchain
- Credit history portability
- Transparent lending terms
- Smart contract execution
- Fraud reduction
- Cross-border credit

## Regulatory Compliance

### Fair Lending Laws
**Equal Credit Opportunity Act (ECOA)**:
- Prohibits discrimination
- Protected classes
- Adverse action notices

**Fair Credit Reporting Act (FCRA)**:
- Accurate reporting
- Consumer rights
- Permissible purposes
- Adverse action procedures

### Community Reinvestment Act (CRA)
- Encourage lending in all community segments
- Assessment of record
- Public ratings

### Prudential Standards
- Sound underwriting standards
- Portfolio concentration limits
- Appraisal requirements
- Documentation standards
- Qualified mortgage rules

## Best Practices

### Underwriting
1. Consistent application of credit policy
2. Independent credit review
3. Regular policy updates
4. Staff training
5. Documentation standards

### Risk Management
1. Risk-based pricing
2. Diversification targets
3. Stress testing
4. Scenario analysis
5. Model validation

### Monitoring
1. Real-time alerts for deterioration
2. Regular portfolio reviews
3. Industry and economic monitoring
4. Covenant compliance tracking
5. Customer communication

### Technology
1. Invest in modern analytics
2. Integrate alternative data
3. Automate routine decisions
4. Model governance framework
5. Continuous improvement

## Emerging Trends

### Open Banking
- Real-time income verification
- Cash flow underwriting
- Better risk assessment
- Improved fraud detection

### AI and Big Data
- More predictive models
- Automated decisioning
- Personalized pricing
- Real-time monitoring

### ESG Factors
- Environmental risk assessment
- Social responsibility
- Governance quality
- Climate risk integration

### Buy Now, Pay Later (BNPL)
- Alternative credit assessment
- Transaction-level underwriting
- Real-time decisioning
- Lower amounts, higher frequency
