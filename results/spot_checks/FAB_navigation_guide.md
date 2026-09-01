# Fabrication-check navigation guide

For each check: the judge claim, then the contract passage(s) to read.
Auto-extracted 26 Aug. Excerpts are whitespace-normalised; ellipses mark truncation.

---

## FAB-01 — claude-sonnet-5 — item F2

**Contract:** `GridironBionutrientsInc_20171206_8-K_EX-10.2_10972556_EX-10.2_Endorsement Agreement.txt`  (529 words)

**Judge claim:** The brief incorrectly attributes the $0.05 per unit donation and the quarterly dispersal of funds to NFLA-NC, whereas the contract states these amounts are payable to and dispersed to the Chapter by the Company.

**Where to look:**

- *match on* `donation of \$0\.05`:

  > ...ts to this Agreement must be signed by all parties to this Agreement. Endorsement Agreement Addendum I Page 1 of 2 Source: GRIDIRON BIONUTRIENTS, INC., 8-K, 12/6/2017 SECTION FOUR. REMUNERATION C. A *donation of $0.05 per Unit sold of Licensed Products within the Contract Territory payable to the **NFL Alumni Northern California Chapter. Donated amounts will be allocated and dispersed to the Northern California Chapter beginning on the first full quarter [three (3) month period] of the Agreement and continue on a quarterly basis thereafter for the term of this Agreement. Where the following per Unit conversion shall apply for the...

- *match on* `payable to`:

  > ...greement Addendum I Page 1 of 2 Source: GRIDIRON BIONUTRIENTS, INC., 8-K, 12/6/2017 SECTION FOUR. REMUNERATION C. A *donation of $0.05 per Unit sold of Licensed Products within the Contract Territory payable to the **NFL Alumni Northern California Chapter. Donated amounts will be allocated and dispersed to the Northern California Chapter beginning on the first full quarter [three (3) month period] of the Agreement and continue on a quarterly basis thereafter for the term of this Agreement. Where the following per Unit conversion shall apply for the term of this Agreement: a. (1) Bottle of BlackMP LivingWater = 1 Unit b. (1...

- *match on* `dispersed`:

  > ...R. REMUNERATION C. A *donation of $0.05 per Unit sold of Licensed Products within the Contract Territory payable to the **NFL Alumni Northern California Chapter. Donated amounts will be allocated and dispersed to the Northern California Chapter beginning on the first full quarter [three (3) month period] of the Agreement and continue on a quarterly basis thereafter for the term of this Agreement. Where the following per Unit conversion shall apply for the term of this Agreement: a. (1) Bottle of BlackMP LivingWater = 1 Unit b. (1) 4oz bottle of BlackMPConcentrate = 30 Units c. (1) Bottle of Zezel ProbioticWater = 1 Unit d...

---

## FAB-02 — claude-sonnet-5 — item F4

**Contract:** `ORBSATCORP_08_17_2007-EX-7.3-STRATEGIC ALLIANCE AGREEMENT.txt`  (2909 words)

**Judge claim:** The brief incorrectly states AVDU cannot assign without UTK's consent, a restriction not present in the contract text.

**ALREADY DONE — verdict: agree**

**Where to look:**

- *match on* `F\. ASSIGNMENTS`:

  > ...d unconditional character and nature of this Agreement shall be in any way invalidated, empowered or affected. There are no representations, warranties or covenants other than those set forth herein. F. ASSIGNMENTS. The benefits of the Agreement shall inure to the respective successors and assignees of the parties and assigns and representatives, and the obligations and liabilities assumed in this Agreement by the parties hereto shall be binding upon their respective successors and assigns; provided that the rights and obligations of UTK under this Agreement may not be assigned or delegated without the prior written consent of...

---

## FAB-03 — deepseek-v4-pro — item F4

**Contract:** `NETGEAR,INC_04_21_2003-EX-10.16-DISTRIBUTOR AGREEMENT.txt`  (6029 words)

**Judge claim:** The contract redacts the exact liability cap amount with an asterisk, so the brief's specific claim about the cap being 'amounts paid' cannot be verified.

**Where to look:**

- *match on* `LIMITATION OF LIABILITY`:

  > ...t as expressly agreed in writing between the parties, no party is liable to the other for any dollar amounts, costs or damages by reason of the expiration or earlier termination of the Agreement. 16. LIMITATION OF LIABILITY A. NETGEAR agrees to indemnify Distributor against any claim arising out of or resulting from the Products or the Agreement, provided that any such claim (i) is attributable to bodily injury, death, or to injury to or destruction of physical property (other than the Products), and (ii) is caused by the negligent act or omission of NETGEAR or a material defect in the Product. This obligation on the part of NETGEAR is...

---

## FAB-04 — deepseek-v4-pro — item F4

**Contract:** `DovaPharmaceuticalsInc_20181108_10-Q_EX-10.2_11414857_EX-10.2_Promotion Agreement.txt`  (26789 words)

**Judge claim:** The brief incorrectly claims Valeant's termination for convenience triggers a tail payment; Section 12.5 explicitly limits the tail payment obligation to terminations initiated by Dova.

**Where to look:**

- *match on* `12\.5`:

  > ...TICLE 12 TERM AND TERMINATION 41 12.1 Term. 41 12.2 Early Termination for Cause. 41 Source: DOVA PHARMACEUTICALS INC., 10-Q, 11/8/2018 12.3 Other Early Termination. 42 12.4 Effects of Termination. 42 12.5 Tail Period. 42 ii CONFIDENTIAL TREATMENT HAS BEEN REQUESTED FOR PORTIONS OF THIS EXHIBIT. THE COPY FILED HEREWITH OMITS THE INFORMATION SUBJECT TO A CONFIDENTIALITY REQUEST. OMISSIONS ARE DESIGNATED [***]. A COMPLETE VERSION OF THIS EXHIBIT HAS BEEN FILED SEPARATELY WITH THE SECURITIES AND EXCHANGE COMMISSION. Source: DOVA PHARMACEUTICALS INC., 10-Q, 11/8/2018 TABLE OF CONTENTS (continued) 12.6 Survival. 43 ARTICLE...

- *match on* `12\.5`:

  > ...e expiration or effective date of termination of this Agreement, (i) all rights and obligations of both Parties hereunder shall immediately terminate, subject to any survival as set forth in Sections 12.5 and 12.6, (ii) Valeant, at Dova's direction, shall immediately return to Dova or destroy in accordance with all Applicable Laws all Product Materials, reports and other tangible items provided by or on behalf of Dova to Valeant or otherwise developed or obtained by Valeant pursuant to the terms of this Agreement (other than Valeant Property) (and at the request of Dova, Valeant shall certify destruction of such mate...

- *match on* `[Tt]ail [Pp]ayment`:

  > ...yments shall be made within [***] following the end of each calendar quarter in the Tail Period. Sections 6.3, 6.4 and 6.5 shall apply, mutatis mutandis, to such Tail Period payments. For clarity, no tail payment shall be due following any expiration or termination of this Agreement except as set forth in this Section 12.5. 12.6 Survival. Termination or expiration of this Agreement shall be without prejudice to any rights that shall have accrued to the benefit of any Party prior to such termination or expiration. Notwithstanding any expiration or termination of this Agreement, such expiration or termination shall not relieve...

---

## FAB-05 — gemini-3.1-pro — item F4

**Contract:** `ReynoldsConsumerProductsInc_20200121_S-1A_EX-10.22_11948918_EX-10.22_Service Agreement.txt`  (17207 words)

**Judge claim:** The brief incorrectly states that RCP must cease using 'Reynolds' names, whereas Section 8.3 explicitly places this restriction on RGHI and its Affiliates.

**Where to look:**

- *match on* `8\.3`:

  > ...ffiliates pursuant to the preceding sentence, neither Party nor its Affiliates shall have any right, title or interest in the intellectual property owned by the other Party or its Affiliates. Section 8.3 Use of RCP Names. By the third anniversary of the Commencement Date, RGHI and its Affiliates will change its corporate names to remove RCP Names and will cease use of RCP Names as trademarks unless such use is pursuant to a separate license agreement with RCP. Source: REYNOLDS CONSUMER PRODUCTS INC., S-1/A, 1/21/2020 ARTICLE IX REMEDIES Section 9.1 Indemnification. Subject to the limitations set forth in this Articl...

- *match on* `8\.3`:

  > ...incurred in providing the service (i.e. external legal firm fees to compile data for RCP) Source: REYNOLDS CONSUMER PRODUCTS INC., S-1/A, 1/21/2020 Service Name Description of Service Term Fee (USD) G8.3 General Services - Corporate Secretarial Provision of corporate secretarial duties and government filing assistance. To the earlier of (i) 24 months from the Commencement Date or (ii) the cessation of current Corporate Governance Paralegal's employment $190 per person / per hour for lawyers, $45 per hour for Corporate Governance Paralegal Plus pass-through of actual third-party costs incurred in providing the servic...

- *match on* `RCP Name`:

  > ...its Affiliates or (ii) agents, accountants, attorneys, independent contractors and other third parties engaged by such Party or its Affiliates. "Provider" has the meaning set forth in the preamble. "RCP Names" means the registered and unregistered trademarks and corporate names used by RCP, RGHI and its respective Affiliates immediately prior to the Commencement Date which include the word "Reynolds" and any derivatives thereof. "Recipient" has the meaning set forth in the preamble "Reverse Transition Services" has the meaning set forth in Section 2.1(b). "RGHI Letters of Credit" means all letters of credit, performance...

- *match on* `RCP Name`:

  > ...ursuant to the preceding sentence, neither Party nor its Affiliates shall have any right, title or interest in the intellectual property owned by the other Party or its Affiliates. Section 8.3 Use of RCP Names. By the third anniversary of the Commencement Date, RGHI and its Affiliates will change its corporate names to remove RCP Names and will cease use of RCP Names as trademarks unless such use is pursuant to a separate license agreement with RCP. Source: REYNOLDS CONSUMER PRODUCTS INC., S-1/A, 1/21/2020 ARTICLE IX REMEDIES Section 9.1 Indemnification. Subject to the limitations set forth in this Article IX, each Party...

- *match on* `cease`:

  > .... "Indemnifying Party" has the meaning set forth in Section 9.1. "Law" means a law, statute, order, ordinance, rule, regulation, judgment, injunction, order, or decree. "Litigation" means any action, cease and desist letter, demand, suit, arbitration proceeding, administrative or regulatory proceeding, citation, summons or subpoena of any nature, civil, criminal, regulatory or otherwise, in law or in equity. "Losses" means any and all damages, liabilities, losses, obligations, claims of any kind, interest and expenses (including reasonable fees and expenses of attorneys). "Migration Plan" has the meaning set forth in...

- *match on* `cease`:

  > ...minating Party. Upon termination of any Service pursuant to this Section 6.2, the Terminating Party's obligation Source: REYNOLDS CONSUMER PRODUCTS INC., S-1/A, 1/21/2020 to pay for such Service will cease except any sums accrued or due as of the date of such early termination for Services rendered (which shall include (i) any amounts contemplated by 6.2(b), plus (ii) a pro rata portion of any fees applicable to the current period in which such Services are being performed if the applicable fee is determined on a period by period basis as set forth on Exhibit A or Exhibit B, as applicable). The provisions of this Sect...

---

## FAB-06 — llama-3.3-70b — item F2

**Contract:** `GridironBionutrientsInc_20171206_8-K_EX-10.2_10972556_EX-10.2_Endorsement Agreement.txt`  (529 words)

**Judge claim:** The brief incorrectly states that the NFLA-NC will pay the $0.05 per unit donation to itself, whereas the contract clearly assigns this payment obligation to the Company.

**Where to look:**

- *match on* `donation of \$0\.05`:

  > ...ts to this Agreement must be signed by all parties to this Agreement. Endorsement Agreement Addendum I Page 1 of 2 Source: GRIDIRON BIONUTRIENTS, INC., 8-K, 12/6/2017 SECTION FOUR. REMUNERATION C. A *donation of $0.05 per Unit sold of Licensed Products within the Contract Territory payable to the **NFL Alumni Northern California Chapter. Donated amounts will be allocated and dispersed to the Northern California Chapter beginning on the first full quarter [three (3) month period] of the Agreement and continue on a quarterly basis thereafter for the term of this Agreement. Where the following per Unit conversion shall apply for the...

- *match on* `payable to`:

  > ...greement Addendum I Page 1 of 2 Source: GRIDIRON BIONUTRIENTS, INC., 8-K, 12/6/2017 SECTION FOUR. REMUNERATION C. A *donation of $0.05 per Unit sold of Licensed Products within the Contract Territory payable to the **NFL Alumni Northern California Chapter. Donated amounts will be allocated and dispersed to the Northern California Chapter beginning on the first full quarter [three (3) month period] of the Agreement and continue on a quarterly basis thereafter for the term of this Agreement. Where the following per Unit conversion shall apply for the term of this Agreement: a. (1) Bottle of BlackMP LivingWater = 1 Unit b. (1...

---

## FAB-07 — llama-3.3-70b — item F2

**Contract:** `CardlyticsInc_20180112_S-1_EX-10.16_11002987_EX-10.16_Maintenance Agreement4.txt`  (756 words)

**Judge claim:** The brief incorrectly states Bank of America must pay for software and maintenance (contract says "no charge") and claims Cardlytics provides installation support (contract says it is handled in a separate agreement).

**Where to look:**

- *match on* `[Nn]o charge`:

  > ...servers and web servers Operating System: Microsoft.net and SQL 2008 Other Required Components Client side ad serving technology PAYMENT TERMS The Software License and Maintenance will be provided at no charge. Proprietary to Bank of America Page A-3 vTIP2010 Source: CARDLYTICS, INC., S-1, 1/12/2018 [***] = CONFIDENTIAL TREATMENT REQUESTED PAYMENT TERMS DELIVERY/INSTALLATION DATES ACCEPTANCE PERIOD MAINTENANCE PERIOD WARRANTY PERIOD DURATION Delivery Date: TBD Installation Date: TBD The period commencing on the Installation Date and continuing for the number of days specified: 120 days Notwithstanding anything set forth e...

- *match on* `[Ii]nstallation [Ss]upport`:

  > ...INING Supplier shall provide the following training classes pursuant to this Agreement in connection with installation of the first copy of the Software. Date: INSTALLATION SUPPORT In addition to the installation support provided pursuant to the Section entitled "Ordering, Delivery and Installation," Supplier shall provide Bank of America the following installation services: Installation Support will be handled in a separate agreement NON-MAINTENANCE SERVICES SUPPORT Support services shall be provided at the Time and Materials rates set forth in the Price List. RELATIONSHIP MANAGERS The following shall be the Relationship Managers f...

- *match on* `[Ii]nstallation [Ss]upport`:

  > ...RT In addition to the installation support provided pursuant to the Section entitled "Ordering, Delivery and Installation," Supplier shall provide Bank of America the following installation services: Installation Support will be handled in a separate agreement NON-MAINTENANCE SERVICES SUPPORT Support services shall be provided at the Time and Materials rates set forth in the Price List. RELATIONSHIP MANAGERS The following shall be the Relationship Managers for the parties: Bank of America: Cardlytics: Brian Woodward Jason Brooks Address: [***] [***] Proprietary to Bank of America Page A-4 vTIP2010 Source: CARDLYTICS, INC., S-1, 1/12...

---

## FAB-08 — llama-3.3-70b — item F3

**Contract:** `CardlyticsInc_20180112_S-1_EX-10.16_11002987_EX-10.16_Maintenance Agreement4.txt`  (756 words)

**Judge claim:** The stated term conflates a source code payment trigger with the agreement's duration, whereas the contract only specifies automatic renewal for the maintenance term.

**Where to look:**

- *match on* `automatically renew`:

  > ...ty Period. The first paid (Initial) Maintenance Term shall commence upon expiration of the Warranty Period and shall continue for twelve (12) months thereafter. Thereafter, the Maintenance Term shall automatically renew for successive period, 12 months, on the terms and conditions of this Agreement unless Bank of America terminates Maintenance Services pursuant to this Agreement. Bank of America may terminate Maintenance Services for convenience at any time in accordance with the Section entitled "Termination" of the Agreement. If Bank of America terminates the Maintenance Services, Bank of America shall have the right to reinstate...

- *match on* `[Rr]enewal`:

  > ...erica terminates the Maintenance Services, Bank of America shall have the right to reinstate the Maintenance Services without paying any reinstatement fee. During the initial Maintenance Term and any renewal term, Maintenance Fees shall be paid in the increments described below under "Payment Terms." Proprietary to Bank of America Page A-2 vTIP2010 Source: CARDLYTICS, INC., S-1, 1/12/2018 PRODUCTS LICENSED PROGRAMS: PROGRAM MATERIALS: PLATFORM: The Software consists of the following: The Program Materials include the following: The Platform consists of the following: Cardlytics OPS (Offer Placement System) Version 3.0 I...

- *match on* `Warranty Period`:

  > ...ng twelve (12) months • At any time if Supplier materially breaches either Agreement $[***] C. Maintenance Services No-charge Maintenance Services shall be provided from the Delivery Date through the Warranty Period. The first paid (Initial) Maintenance Term shall commence upon expiration of the Warranty Period and shall continue for twelve (12) months thereafter. Thereafter, the Maintenance Term shall automatically renew for successive period, 12 months, on the terms and conditions of this Agreement unless Bank of America terminates Maintenance Services pursuant to this Agreement. Bank of America may terminate Maintenance Serv...

- *match on* `Warranty Period`:

  > ...intenance Services No-charge Maintenance Services shall be provided from the Delivery Date through the Warranty Period. The first paid (Initial) Maintenance Term shall commence upon expiration of the Warranty Period and shall continue for twelve (12) months thereafter. Thereafter, the Maintenance Term shall automatically renew for successive period, 12 months, on the terms and conditions of this Agreement unless Bank of America terminates Maintenance Services pursuant to this Agreement. Bank of America may terminate Maintenance Services for convenience at any time in accordance with the Section entitled "Termination" of the Agr...

---

## FAB-09 — llama-3.3-70b — item F2

**Contract:** `NEONSYSTEMSINC_03_01_1999-EX-10.5-DISTRIBUTOR AGREEMENT_Amendment.txt`  (2848 words)

**Judge claim:** The brief incorrectly characterizes the right of first refusal as an obligation when the contract explicitly grants it as a discretionary right.

**Where to look:**

- *match on* `[Ff]irst [Rr]efusal`:

  > ...IGHT OF FIRST REFUSAL. The Distributor Agreement is hereby amended by adding thereto a new Section 15.11 and a new Section 15.12, which shall read in their entirety as follows: Section 15.11 Right of First Refusal. If, at any time or from time to time during the term hereof, Licensor or any stockholder in Licensor shall have received a bona fide offer from any person or entity to sell, transfer or otherwise convey all or any stock in, or assets of, Licensor which Licensor or such stockholder, as the case may be (the "Offeree"), desires to accept, the Offeree shall first give written notice (the "Offering Notice") to Licensee...

- *match on* `[Ff]irst [Rr]efusal`:

  > ...t Amendment to Distributor Agreement dated as of November 19, 1998 by and between PBTC and NEON, such joinder being for purposes of acknowledging and agreeing to be bound by the terms of the Right of First Refusal set forth in Section 15.11 of the Distributor Agreement and the Option to Purchase set forth in Section 15.12 of the Distributor Agreement. Skunkware hereby represents and warrants to NEON that Skunkware is the sole stockholder of PBTC. Skunkware further agrees that its agreements set forth herein shall be binding on its successors and assigns and inure to the benefit of NEON's successors and assigns. Skunkware's ad...

- *match on* `Offering Notice`:

  > ...herwise convey all or any stock in, or assets of, Licensor which Licensor or such stockholder, as the case may be (the "Offeree"), desires to accept, the Offeree shall first give written notice (the "Offering Notice") to Licensee of the financial and other terms and conditions (the "Terms and Conditions") of such offer. Licensee shall have the right and a first opportunity to purchase, lease or otherwise acquire, as the case may be, all or the applicable portion of such stock or assets (as specified in the applicable Offering Notice) on the Terms and Conditions set forth in the Offering Notice, such right to be exercised by not...

- *match on* `Offering Notice`:

  > ...icensee shall have the right and a first opportunity to purchase, lease or otherwise acquire, as the case may be, all or the applicable portion of such stock or assets (as specified in the applicable Offering Notice) on the Terms and Conditions set forth in the Offering Notice, such right to be exercised by notice in writing to the Offeree within ninety (90) days after the giving of the Offering Notice. If Licensee shall have exercised such right, the closing shall be held at the corporate offices of Licensee on the closing date specified in the Offering Notice or the date that is ninety (90) days after the date of Licensee's n...

---

## FAB-10 — llama-3.3-70b — item F4

**Contract:** `ADAMSGOLFINC_03_21_2005-EX-10.17-ENDORSEMENT AGREEMENT.txt`  (3770 words)

**Judge claim:** The brief incorrectly states that the CONSULTANT indemnifies ADAMS GOLF for product defects, whereas Section 21 explicitly assigns this indemnity obligation to ADAMS GOLF.

**Where to look:**

- *match on* `indemnif`:

  > ...either the full performance of CONSULTANT'S obligations hereunder or ADAMS GOLF'S full enjoyment of the rights and privileges granted to it by CONSULTANT. 14. INDEMNITY CONSULTANT agrees to protect, indemnify and hold ADAMS GOLF harmless from any and all liability, claims, causes of action, suits, damages and expenses (including reasonable attorneys' fees and expenses) for which it becomes liable or is compelled to pay by reason of a breach of any covenant or representation by CONSULTANT in this Agreement. 15. ABSENCE OF AGENCY CONSULTANT shall not and will not have the right or authority to bind ADAMS GOLF by any repre...

- *match on* `indemnif`:

  > ...withheld or delayed. If CONSULTANT disapproves, the reasons therefore shall be given to ADAMS GOLF in writing within three (3) business days or shall be deemed approved. ADAMS GOLF agrees to protect, indemnify and hold CONSULTANT harmless from and against any and all expenses, damages, claims, suits, actions, judgments and costs whatsoever, arising out of, or in any way connected with, any advertising material furnished by, or on behalf of, the company. 21. INDEMNITY ADAMS GOLF agrees to defend, indemnify and hold harmless CONSULTANT from any and all liability, claims, causes of action, suits, damages and expenses (inclu...

- *match on* `21\.`:

  > ...y and all expenses, damages, claims, suits, actions, judgments and costs whatsoever, arising out of, or in any way connected with, any advertising material furnished by, or on behalf of, the company. 21. INDEMNITY ADAMS GOLF agrees to defend, indemnify and hold harmless CONSULTANT from any and all liability, claims, causes of action, suits, damages and expenses (including reasonable attorneys' fees and expenses) for which he becomes liable or is compelled to pay by reason of or arising out of any claim or action for personal injury, death or otherwise involving alleged defects in ADAMS GOLF'S PRODUCT, provided that...

---

## FAB-11 — llama-3.3-70b — item F2

**Contract:** `PelicanDeliversInc_20200211_S-1_EX-10.3_11975895_EX-10.3_Development Agreement2.txt`  (4870 words)

**Judge claim:** The brief incorrectly attributes the obligation to provide assistance for acceptance tests to the Developer, whereas Section 3.8 places this duty on the Client.

**Where to look:**

- *match on* `3\.8`:

  > ...fy the Developer of any further failures, objections, changes, or other defects, or bugs of or in the Subject Program via a Change Request, Client will be deemed to have accepted the Subject Program. 3.8 CLIENT ASSISTANCE Client shall provide Developer assistance to complete the Services, and produce the Deliverables, as reasonably requested, including but not limited to providing the necessary information or documentation required from Developer for the development of the Subject Program. Client shall conduct all Acceptance Tests in good faith and shall not delay any acceptance of any Service or Deliverable without...

- *match on* `Acceptance Test`:

  > ...rior to completing a Milestone, Developer will: (a) inform Client of the availability of each portion of a Deliverable otherwise required be delivered by such Milestone date for testing by Client (he Acceptance Test Date); and (b) deliver to Client sue Deliverable (each a Milestone Deliverable) including the source code and object code form compatible with the platform(s) described in the SOW for such Milestone Deliverable. 3.3 ACCEPTANCE AND BETA TESTS Within the time periods designated in the SOW, Client shall perform any tests or evaluation of the Subject Program (collectively, the Acceptance Tests) after the Acceptance Test...

- *match on* `Acceptance Test`:

  > ...SOW for such Milestone Deliverable. 3.3 ACCEPTANCE AND BETA TESTS Within the time periods designated in the SOW, Client shall perform any tests or evaluation of the Subject Program (collectively, the Acceptance Tests) after the Acceptance Test Date, to determine whether each Deliverable: (a) conforms to the SOW; and (b) performs repetitively on an appropriate variety of data and platforms, without failure, as more fully described in the Specifications. Upon completion of II Deliverables, the Acceptance Tests shall be performed on the Subject Program in its entirety in order to determine whether the Subject Program (i) meets the...

- *match on* `assistance`:

  > ...changes, or other defects, or bugs of or in the Subject Program via a Change Request, Client will be deemed to have accepted the Subject Program. 3.8 CLIENT ASSISTANCE Client shall provide Developer assistance to complete the Services, and produce the Deliverables, as reasonably requested, including but not limited to providing the necessary information or documentation required from Developer for the development of the Subject Program. Client shall conduct all Acceptance Tests in good faith and shall not delay any acceptance of any Service or Deliverable without reasonable justification. The evaluation of any Service or...

- *match on* `assistance`:

  > ...the event of a termination or expiration of this Agreement or any SOW for any reason, developer will, as requested by and at additional cost to Client, provide up to three (3) months of Fee billable assistance (collectively, the Termination Assistance Services) in transitioning from Developer to an alternative software service provider including, without limitation, the following: (a) knowledge transfer regarding the operation, use, and support of the subject Program; return of all documentation containing Content, Marks, Procedures a d Confidential Information in a format reasonably specified by Client and assistance wit...

---

## FAB-12 — llama-3.3-70b — item F3

**Contract:** `PelicanDeliversInc_20200211_S-1_EX-10.3_11975895_EX-10.3_Development Agreement2.txt`  (4870 words)

**Judge claim:** The contract explicitly defines the term as commencing on the Effective Date and continuing through project completion or termination, making the 'not specified' claim incorrect.

**Where to look:**

- *match on* `Effective Date`:

  > ...SOFTWARE DEVELOPMENT AGREEMENT THIS SOFTWARE DEVELOPMENT AGREEMENT (Agreement ) is made December 3rd, 2018 (the Effective Date) by and between DOT COM LLC, OBA Seattle Software Developers, a Delaware limited liability company (Developer ), and (Client) Pelican Delivers Inc. for the performance of software design services and software development as detailed herein (Developer and Client are individually referred to herein as a Party, and collectively as the Parties). 1. Term Unless otherwise provided herein, this Agreement will commence on t...

- *match on* `Effective Date`:

  > ...s detailed herein (Developer and Client are individually referred to herein as a Party, and collectively as the Parties). 1. Term Unless otherwise provided herein, this Agreement will commence on the Effective Date and continue through the completion or termination of Developer's services and work product as mutually agreed upon between the Parties (the Project). 2. Statement of Work Developer will design, develop, and deliver, satisfactory to Client, the "Pelican Delivers Application Phase 1" (collectively, the Subject Program), and all elated Project services (collectively, the Services), Project work product (collectively,...

- *match on* `term of this Agreement`:

  > ...TERMINATION SERVICES If elected pursuant to the Agreement, Developer will provide Client Termination Assistance Services at an hourly rate of $[125.00 per hour]. 4. Change Orders Sometimes during the term of this Agreement change order may or may not be requested by Client. However, If Client requests that Developer provide any additional Services or Deliverables or functionalities beyond those detail d in an applicable SOW, or requests a modification or change to any of the Services or Deliverables if possible, client will: (A) Submit to Developer, by means of a written order, all requests r additional services that alter, amend, enh...

- *match on* `term of this Agreement`:

  > ...ny negative posts concerning each other, the names of our companies, and our employees. Both the Client and the Designer both agree and acknowledge that this non-disparagement provision is a material term of this Agreement, the absence of which would have resulted in the Company refusing to enter into this Agreement. Subject to the terms, conditions, express representations and warranties provided in this Agreement, Designer and Client both agree to indemnify, save and hold armless each other from any and all damages, liabilities, costs, losses or expenses arising out of any finding of fact which is inconsistent with Designer's repres...

---

## FAB-13 — llama-3.3-70b — item F4

**Contract:** `CORIOINC_07_20_2000-EX-10.5-LICENSE AND HOSTING AGREEMENT.txt`  (8396 words)

**Judge claim:** The brief incorrectly claims Corio faces exclusivity restrictions on non-ASP sales, whereas Section 2.4 actually restricts Commerce One from soliciting such sales.

**Where to look:**

- *match on* `2\.4`:

  > ...Software shall be made available to Corio's sales personnel and the parties agree to cooperate to make the Commerce One demonstration database available to Corio sales personnel on an ongoing basis. 2.4 Distribution License: Corio shall have the right to resell licenses for Commerce One software, including Hosted BuySite, to any Corio Customer in the Territory, [*]. Subject to the terms and conditions of this Agreement, Commerce One hereby grants to Corio a nonexclusive, nontransferable (except in accordance with Section 14.1 of this Agreement), right and license in the Territory to sell and distribute such softwar...

- *match on* `2\.4`:

  > ...ive, nontransferable (except in accordance with Section 14.1 of this Agreement), right and license in the Territory to sell and distribute such software licenses to Customers pursuant to this Section 2.4. Under no circumstances shall Commerce One contact Corio Customers regarding a non-ASP license sale, unless requested to do so by Corio. Further, if a Corio Customer contacts Commerce One to purchase the Software license independent of the Corio Services, Commerce One shall immediately refer that Customer to Corio. 2.5 Software User License Agreements. Corio shall make the Software and the MarketSite.net Service on...
