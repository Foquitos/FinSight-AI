# Merchant Risk Management

## Introduction
Merchant risk management involves assessing and mitigating risks associated with accepting merchants as payment processing clients. Financial institutions and payment processors must balance service provision with protection against fraud, chargebacks, and reputational damage.

## Types of Merchant Risk

### Fraud Risk
- **Merchant fraud**: Intentional deceptive practices by merchant
- **Transaction fraud**: Fraudulent purchases through merchant
- **Identity fraud**: Merchant using false information
- **Collusion**: Merchant working with fraudsters

### Credit Risk
- **Chargebacks**: Customer disputes exceeding merchant reserves
- **Business failure**: Merchant unable to honor obligations
- **Insufficient reserves**: Unable to cover chargebacks or refunds

### Operational Risk
- **Poor business practices**: Substandard customer service
- **Fulfillment issues**: Failure to deliver products/services
- **Compliance failures**: Not adhering to card network rules
- **Business model problems**: Unsustainable operations

### Reputational Risk
- **Association with high-risk activities**
- **Excessive customer complaints**
- **Negative publicity**
- **Regulatory actions**

### Legal and Compliance Risk
- **Regulatory violations**: Breaking laws or regulations
- **Prohibited goods/services**: Illegal or restricted products
- **Licensing issues**: Operating without required licenses
- **Data breaches**: PCI DSS compliance failures

## Merchant Risk Categories

### Low-Risk Merchants

**Characteristics**:
- Established business with track record
- Low average transaction values
- Mainstream products/services
- Low chargeback rates (< 0.5%)
- Immediate fulfillment
- Domestic transactions

**Examples**:
- Retail stores
- Restaurants
- Professional services
- Subscription services (established)

**Underwriting**:
- Simplified application
- Faster approval
- Lower reserves or no reserve
- Standard processing rates

### Medium-Risk Merchants

**Characteristics**:
- Moderate transaction values
- Some delayed fulfillment
- International markets
- Moderate chargeback risk (0.5-0.9%)
- Emerging businesses

**Examples**:
- E-commerce apparel
- Home goods online
- Software as a service
- Event tickets
- Electronics

**Underwriting**:
- Detailed application review
- Business verification
- Moderate reserves (5-10%)
- Enhanced monitoring
- Slightly higher rates

### High-Risk Merchants

**Characteristics**:
- High average ticket sizes
- Future delivery of goods/services
- Subscription/recurring billing
- Intangible products
- High chargeback potential (> 0.9%)
- Regulated industries
- Reputational concerns

**Examples**:
- Nutraceuticals and supplements
- Adult entertainment
- Online gambling/gaming
- Travel agencies
- Debt collection
- Multilevel marketing (MLM)
- Cryptocurrency services
- Firearms and ammunition
- CBD products
- Monthly box subscriptions
- Tech support services
- Credit repair

**Underwriting**:
- Extensive documentation required
- Business plan review
- Principal background checks
- High reserves (10-20% or rolling reserve)
- Transaction caps and velocity limits
- Enhanced monitoring
- Higher processing rates
- Longer settlement holds

## Merchant Underwriting Process

### Application Review

**Required information**:
- Business legal name and DBA
- Tax ID (EIN/SSN)
- Business address and contact
- Principals' information and SSN
- Business structure (LLC, Corp, Sole Proprietor)
- Products/services description
- Website URL (for online businesses)
- Processing history
- Bank account information

**Documentation**:
- Business license
- Articles of incorporation
- Bank statements
- Processing statements (if prior history)
- Tax returns
- Financial statements

### Verification Steps

1. **Identity verification**:
   - Principals' identity documents
   - Background checks
   - Credit checks

2. **Business verification**:
   - Secretary of State records
   - Business license verification
   - BBB rating check
   - Website review

3. **Financial verification**:
   - Bank account ownership
   - Financial stability assessment
   - Tax return review

4. **Compliance checks**:
   - MATCH list (terminated merchants)
   - OFAC sanctions screening
   - Regulatory database checks
   - Previous fraud databases

### Risk Assessment

**Scoring factors**:
- Business type and industry
- Processing history (chargebacks, fraud)
- Principal credit history
- Business age and longevity
- Financial strength
- Average ticket size
- Monthly processing volume
- Customer geographic spread
- Fulfillment timeframe

**Risk rating assignment**:
- Aggregate scoring
- Manual review for edge cases
- Final decisioning
- Approval conditions

### Pricing and Terms

**Based on risk**:
- Processing rates (discount rate)
- Transaction fees
- Monthly/annual fees
- Chargeback fees
- Reserve requirements
- Settlement timing
- Transaction limits

## Monitoring and Management

### Transaction Monitoring

**Red flags**:
- Rapid increase in volume
- Large transactions compared to historical average
- Geographic anomalies
- Sudden changes in business model
- High refund rates
- Multiple small transactions followed by large ones
- Unusual hours of operation

**Automated alerts**:
- Volume thresholds exceeded
- Average ticket increase
- Chargeback ratio spikes
- Refund ratio increases
- Velocity anomalies
- Geographic concentration changes

### Chargeback Monitoring

**Key metrics**:
- Chargeback rate (chargebacks/transactions)
- Chargeback-to-sales ratio
- Reason code distribution
- Win rate on representments
- Time from transaction to chargeback

**Thresholds**:
- Warning level: 0.65%
- Intervention level: 0.75%
- Termination consideration: 1.0%+

**Card network programs**:
- Visa Dispute Monitoring Program (VDMP)
- Mastercard Excessive Chargeback Program (ECP)
- Consequences: Higher fees, potential termination

### Financial Monitoring

**Indicators**:
- Reserve balance adequacy
- Settlement timing patterns
- Refund rates
- Net processing trends
- Bank account changes

### Compliance Monitoring

**Checks**:
- PCI DSS compliance status
- Regulatory license maintenance
- Prohibited product/service screening
- Terms of service compliance
- Website/marketing review

## Reserve Management

### Types of Reserves

**Fixed reserve**:
- Set percentage held from each transaction
- Released after holdback period (e.g., 6 months)
- Predictable for merchant

**Rolling reserve**:
- Percentage held from daily sales
- Released on rolling schedule (e.g., after 180 days)
- Adjusts automatically with volume

**Upfront reserve**:
- Lump sum deposited by merchant
- Held throughout relationship
- Returned upon termination (less any liabilities)

**ACH reserve**:
- Merchant authorizes direct debit from bank account
- Used if processing account insufficient

### Reserve Sizing

**Factors**:
- Industry risk level
- Chargeback history/potential
- Business stability
- Average ticket size
- Fulfillment timing
- Principal creditworthiness
- Financial strength

**Calculation examples**:

**Low risk**: 0-5% rolling reserve
**Medium risk**: 5-10% rolling reserve
**High risk**: 10-20% rolling reserve or upfront

**Seasonal business**: 10% + hold settlements during off-season

### Reserve Adjustments

**Increase triggers**:
- Chargeback ratio increase
- Rapid volume growth
- Negative news or complaints
- Business model changes
- Financial deterioration

**Decrease triggers**:
- Consistent low chargeback rates
- Strong financial performance
- Stable operations
- Good processing history

## Problem Merchant Management

### Early Warning Signs

**Operational**:
- Customer complaints increasing
- BBB rating decline
- Negative reviews online
- Shipping delays
- Poor customer service

**Financial**:
- Declining reserves
- Repeated NSFs
- Requesting early funding
- Bank account changes
- Financial distress signals

**Transaction patterns**:
- Processing spikes
- Large batch uploads
- Unusual transaction times
- Geographic shifts
- High refund rates

### Intervention Strategies

**Communication**:
- Contact merchant about concerns
- Request explanation for anomalies
- Confirm business still operating
- Verify contact information current

**Account restrictions**:
- Hold settlements temporarily
- Increase reserves
- Implement transaction limits
- Require pre-approval for large transactions
- Delay settlement timing

**Documentation**:
- Request updated business information
- Verify continued compliance
- Reassess risk rating
- Update underwriting file

### Termination Decisions

**Grounds for termination**:
- Excessive chargebacks
- Fraudulent activity
- Material misrepresentation
- Compliance violations
- Business closure
- Unacceptable risk level

**Process**:
1. Review of all facts
2. Legal consultation if needed
3. Notice to merchant (per agreement)
4. Hold settlements for chargeback exposure period
5. MATCH list reporting if warranted
6. Return remaining reserve (less liabilities)

### MATCH List Reporting

**Reasons for reporting**:
- Excessive chargebacks
- Fraud
- Data compromise
- Identity theft
- Money laundering
- Prohibited business type

**Consequences for merchant**:
- Difficulty obtaining future processing
- Listed for 5 years
- Permanent record in some cases

## Industry-Specific Considerations

### E-commerce
- Card-not-present fraud risk
- Friendly fraud potential
- SEO and marketing verification
- Return policy clarity
- Shipping and tracking

### Subscription Services
- Recurring billing arrangements
- Cancellation process clarity
- Clear billing descriptors
- Trial period management
- Customer retention practices

### Travel and Hospitality
- Advance bookings
- Cancellation policies
- Weather/event risks
- Seasonal variations
- High average tickets

### Digital Goods
- Instant fulfillment
- Difficult to prove delivery
- High fraud risk
- License/keys distribution
- Account access

### Nutraceuticals
- Regulatory compliance
- Recurring billing
- Negative option billing
- Marketing claims
- Free trial abuse

## Technology Solutions

### Underwriting Software
- Automated application processing
- Risk scoring engines
- Document verification
- Background check integration
- Decision management

### Monitoring Platforms
- Real-time transaction analytics
- Chargeback tracking
- Reserve management
- Alert systems
- Dashboard reporting

### Third-Party Data
- Credit bureaus
- MATCH list access
- Fraud databases
- Industry reputation services
- Compliance verification services

### Machine Learning
- Predictive risk modeling
- Anomaly detection
- Chargeback prediction
- Attrition risk assessment
- Fraud pattern recognition

## Regulatory Compliance

### Card Network Rules
- Visa Core Rules and Visa Product and Service Rules
- Mastercard Rules
- American Express merchant operating guide
- Discover Network compliance

### Payment Facilitator Regulations
- Registration requirements
- Compliance obligations
- Sub-merchant oversight
- Reserve requirements
- Reporting obligations

### Anti-Money Laundering (AML)
- Merchant KYC/KYB
- Transaction monitoring
- Suspicious activity reporting
- High-risk merchant enhanced due diligence

## Best Practices

### Underwriting
1. Thorough due diligence
2. Risk-appropriate pricing and terms
3. Documentation standards
4. Consistent decision-making
5. Regular policy review and updates

### Monitoring
1. Automated alerting systems
2. Regular portfolio reviews
3. Chargeback analysis and trends
4. Proactive merchant communication
5. Industry and economic monitoring

### Relationship Management
1. Clear communication of expectations
2. Education on chargeback prevention
3. Support for compliance
4. Fair dispute resolution
5. Partnership approach

### Risk Mitigation
1. Appropriate reserve levels
2. Transaction limits when warranted
3. Settlement timing adjustments
4. Diversification across risk levels
5. Insurance/bonding for high-risk

## Emerging Trends

### Alternative Risk Assessment
- Cash flow underwriting
- Social media reputation analysis
- Real-time business insights
- Alternative credit data

### AI and Machine Learning
- Automated underwriting
- Predictive analytics
- Real-time risk scoring
- Fraud detection improvement

### Blockchain and Cryptocurrency
- New merchant categories
- Unique risk profiles
- Regulatory uncertainty
- Specialized underwriting

### Embedded Payments
- Software platforms as payment facilitators
- Marketplace models
- Increased oversight needs
- Sub-merchant monitoring

## Performance Metrics

### Portfolio Health
- Overall chargeback ratio
- Fraud rate
- Attrition rate
- Reserve adequacy
- Loss ratio

### Operational Efficiency
- Application approval rate
- Time to approval
- Monitoring alert accuracy
- False positive rate
- Merchant satisfaction

### Financial Performance
- Processing volume
- Revenue per merchant
- Cost of risk (losses, reserves)
- Profitability by segment
