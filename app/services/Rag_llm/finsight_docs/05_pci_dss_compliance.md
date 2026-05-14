# Payment Card Industry Data Security Standard (PCI DSS)

## Overview
The Payment Card Industry Data Security Standard (PCI DSS) is a set of security standards designed to ensure that all companies that accept, process, store, or transmit credit card information maintain a secure environment.

## Who Must Comply?

### Merchant Levels
- **Level 1**: Processes over 6 million transactions annually
- **Level 2**: Processes 1-6 million transactions annually
- **Level 3**: Processes 20,000-1 million e-commerce transactions annually
- **Level 4**: Processes fewer than 20,000 e-commerce transactions or up to 1 million total transactions annually

### Service Providers
- Payment gateways
- Payment processors
- Hosting providers
- Any entity that stores, processes, or transmits cardholder data

## The 12 Requirements

### Build and Maintain a Secure Network
**Requirement 1**: Install and maintain a firewall configuration to protect cardholder data
- Establish firewall and router configuration standards
- Build firewall configurations that restrict connections from untrusted networks
- Prohibit direct public access to cardholder data

**Requirement 2**: Do not use vendor-supplied defaults for system passwords and other security parameters
- Change all vendor defaults before installing system on network
- Remove unnecessary default accounts
- Implement only one primary function per server

### Protect Cardholder Data
**Requirement 3**: Protect stored cardholder data
- Keep cardholder data storage to minimum necessary
- Do not store sensitive authentication data after authorization
- Render Primary Account Number (PAN) unreadable using encryption, truncation, masking, or hashing

**Requirement 4**: Encrypt transmission of cardholder data across open, public networks
- Use strong cryptography and security protocols
- Never send unencrypted PANs by end-user messaging technologies
- Ensure security policies and procedures address use of wireless networks

### Maintain a Vulnerability Management Program
**Requirement 5**: Protect all systems against malware and regularly update anti-virus software
- Deploy anti-virus software on all systems commonly affected by malicious software
- Ensure anti-virus programs are capable of detecting, removing, and protecting
- Ensure logs are enabled and retained according to PCI DSS requirements

**Requirement 6**: Develop and maintain secure systems and applications
- Establish process to identify security vulnerabilities
- Ensure all system components and software are protected from known vulnerabilities
- Develop applications according to PCI DSS and based on industry best practices

### Implement Strong Access Control Measures
**Requirement 7**: Restrict access to cardholder data by business need to know
- Limit access to system components and cardholder data to only those whose job requires access
- Establish access control system for systems components with multiple users
- Ensure proper user authentication management

**Requirement 8**: Identify and authenticate access to system components
- Assign unique ID to each person with computer access
- Employ at least one of: passwords, tokens, biometrics
- Implement multi-factor authentication for all non-console access

**Requirement 9**: Restrict physical access to cardholder data
- Use facility entry controls to limit and monitor physical access
- Develop procedures to easily distinguish between employees and visitors
- Physically secure all media and restrict access

### Regularly Monitor and Test Networks
**Requirement 10**: Track and monitor all access to network resources and cardholder data
- Implement audit trails to link all access to cardholder data
- Implement automated audit trail review for all system components
- Retain audit trail history for at least one year

**Requirement 11**: Regularly test security systems and processes
- Implement processes to test for presence of wireless access points
- Run internal and external network vulnerability scans quarterly
- Implement intrusion-detection and/or intrusion-prevention systems

### Maintain an Information Security Policy
**Requirement 12**: Maintain a policy that addresses information security for all personnel
- Establish, publish, maintain, and disseminate security policy
- Implement risk assessment process
- Develop usage policies for critical technologies
- Ensure security policy and procedures clearly define information security responsibilities

## Cardholder Data Elements

### Primary Account Number (PAN)
- 13 to 19 digit payment card number
- Must be protected wherever stored, processed, or transmitted
- Only authorized personnel should have access

### Sensitive Authentication Data (SAD)
**Never allowed to be stored after authorization**:
- Full magnetic stripe data
- CAV2/CVC2/CVV2/CID security codes
- PIN/PIN blocks

**May be stored if protected**:
- Cardholder name
- Service code
- Expiration date

## Compliance Validation

### Self-Assessment Questionnaires (SAQ)
- **SAQ A**: Card-not-present merchants, all functions outsourced
- **SAQ A-EP**: E-commerce merchants who partially outsource
- **SAQ B**: Imprint-only merchants or standalone dial-out terminal
- **SAQ B-IP**: Merchants using standalone, PTS-approved payment terminals
- **SAQ C**: Merchants with payment application systems connected to internet
- **SAQ C-VT**: Merchants using virtual terminals
- **SAQ D**: All other merchants and service providers
- **SAQ P2PE**: Merchants using validated P2PE solutions

### Attestation of Compliance (AOC)
- Formal documentation that entity has completed PCI DSS assessment
- Must be completed annually
- Includes validation method and compliance status

### Report on Compliance (ROC)
- Detailed report of PCI DSS compliance
- Required for Level 1 merchants
- Must be completed by Qualified Security Assessor (QSA)

## Common Compliance Challenges

### Data Discovery
- Identifying where cardholder data resides
- Finding unexpected data storage locations
- Database and file system searches

### Scope Reduction
- Segmenting payment environment
- Using tokenization to reduce scope
- Outsourcing to reduce direct handling

### Documentation
- Maintaining current network diagrams
- Tracking all data flows
- Documenting security procedures

### Vendor Management
- Ensuring third parties are compliant
- Validating vendor compliance status
- Managing vendor access

## Best Practices

### Network Segmentation
- Isolate cardholder data environment (CDE)
- Use VLANs and firewalls
- Implement strict access controls
- Regular penetration testing of segmentation

### Tokenization
- Replace PAN with non-sensitive token
- Significantly reduces PCI DSS scope
- Tokens mathematically irreversible
- Maintains format for existing systems

### Point-to-Point Encryption (P2PE)
- Encrypt data at point of capture
- Decrypt only in secure environment
- Prevents clear-text data exposure
- PCI-validated solutions available

### Regular Testing
- Quarterly vulnerability scans by Approved Scanning Vendor (ASV)
- Annual penetration testing
- Regular internal vulnerability assessments
- Continuous monitoring

## Penalties for Non-Compliance

### Financial Penalties
- Fines from $5,000 to $100,000 per month
- Card brands can impose penalties
- Increased transaction fees
- Loss of ability to process cards

### Legal Consequences
- Customer lawsuits for data breaches
- Regulatory actions
- Criminal charges in some cases
- Damage to business reputation

## PCI DSS Version Updates

### Version 3.2.1 (Current - 2024)
- Enhanced multi-factor authentication
- Improved risk assessment requirements
- Updated vulnerability management

### Version 4.0 (Effective)
- Customized approach alongside defined approach
- Enhanced continuous monitoring
- More flexible requirements
- Focus on security as a continuous process

## Resources and Support

### PCI Security Standards Council
- Official standards documentation
- Training and certification programs
- Lists of QSAs and ASVs
- Community forums and resources

### Qualified Security Assessors (QSA)
- Certified to perform PCI DSS assessments
- Can provide guidance and consulting
- Required for Level 1 merchant validation

### Approved Scanning Vendors (ASV)
- Authorized to perform quarterly external scans
- Meet PCI SSC qualification requirements
- Provide scan reports for compliance
