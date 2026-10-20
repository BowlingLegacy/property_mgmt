"""Versioned Painted Lady lease terms shared by the portal and printable PDF."""

from decimal import Decimal

LEASE_VERSION = "painted-lady-2026-10-20"
INITIALS = (
    ("rent_initials", "Rent, deposit, utilities and late fees"),
    ("sobriety_initials", "Sober-living responsibilities"),
    ("testing_initials", "Reasonable testing policy"),
    ("guest_policy_initials", "Guest and occupancy rules"),
    ("cleanliness_initials", "Care of private and shared spaces"),
    ("disclosure_initials", "Property disclosure requirements"),
)

SECTIONS = [
    (
        "Parties, Leased Room and Shared Facilities",
        [
            "{landlord} (the Landlord) rents to {resident} (the Resident) the assigned room or space {room} at {property}, {address}, for residential use. Exclusive occupancy is limited to the assigned room or space; kitchens, bathrooms and other designated common areas are shared. This agreement does not grant exclusive possession of the entire house.",
            "Only the Resident and any additional occupants approved in writing may reside in the assigned space. The Resident may not transfer possession, assign the agreement, sublet, or rent any part of the premises to another person. Enforcement remains subject to applicable law.",
        ],
    ),
    (
        "Month-to-Month Term",
        [
            "The tenancy begins {start} and continues month to month until lawfully terminated or changed by a written agreement. Existing residents retain their original occupancy dates; signing an updated agreement does not restart a tenancy or erase accrued rights."
        ],
    ),
    (
        "Rent, Payment Dates and Late Fees",
        [
            "Monthly base rent is {rent}. Rent is due on the first (1st) of each month; the regular collection date remains the third (3rd). Payment must be received by 11:59 p.m. Pacific time on the fifth (5th) to avoid the agreed late fee. Collection arrangements do not change the rent due date.",
            "If rent remains unpaid when that deadline expires, one $25.00 late fee is assessed automatically on the sixth (6th), provided it is a reasonable flat fee permitted by ORS 90.260(2)(a). The fee is charged once per monthly rental period, including when only part of the rent remains unpaid. There is no daily or recurring late fee and no late fee based solely on unpaid utilities, deposits or earlier fees.",
            "Rent, utilities, deposits and fees remain separate obligations. Payments are applied in the order required by ORS 90.220(9); an unpaid late fee does not become rent and may not itself support a nonpayment-of-rent termination. Pay rent through bowlinglegacy.com, Cash App $Trmf8763, or your bank's online bill pay to our business account. Request verified bank bill-pay instructions privately through the tenant dashboard. Include your name, room and rent month and allow time for receipt. Before the pay-by deadline, report any delay and the promised payment date through the dashboard. Only written landlord approval pauses the fee through that date; a request alone does not. Rent unpaid after an approved date may incur the agreed fee the following day.",
            "A dishonored check may result in a charge of $35 plus actual bank processing charges, only as allowed by ORS 90.302 and ORS 30.701. No key will be issued until the first month's rent is paid and required move-in documents are completed. Nothing in this clause limits statutory tenant rights or makes an existing tenancy disappear.",
        ],
    ),
    (
        "Security Deposit and Condition Reports",
        [
            "The required security deposit is {deposit}. Payment terms: {deposit_plan}. It is due at move-in unless the Landlord approves in writing no more than three installments over 90 days. An approved plan remains part of this agreement and must comply with applicable law.",
            "The Parties will complete, sign and date a move-in condition report and document the room, supplied furnishings and shared facilities as appropriate. Move-out condition will be documented for comparison. Deductions may cover only amounts reasonably necessary and legally chargeable for defaults, damage beyond ordinary wear and tear, or permitted cleaning. Normal wear, the Landlord's maintenance duties and prohibited administrative fees are excluded.",
            "The deposit is not the last month's rent and may not be used as rent without a lawful written arrangement. Within 31 days after termination and delivery of possession, the Landlord will provide an itemized written accounting, any required Eugene photo or video documentation, and the unclaimed deposit as required by ORS 90.300 and local law. The Resident should supply a forwarding address.",
        ],
    ),
    (
        "Shared Utilities",
        [
            "The current monthly contribution for shared electric, gas, water and garbage service is {utilities}. It is shown separately from rent and the security deposit. The Resident should use shared services responsibly and report leaks or unsafe equipment promptly.",
            "Any occupancy-based adjustment must follow the written utility arrangement and applicable law, including required billing disclosures. Management will provide at least 30 days' written notice of an allowed change; this provision does not authorize a change prohibited by law or by the agreement.",
        ],
    ),
    (
        "Periodic Rent Review",
        [
            "Management may review rents for a January 1 adjustment, and Residents may request hardship review. Increases are not automatic: each increase must satisfy ORS 90.323, including any restriction during the first year, applicable amount limits, required written notice and any applicable Eugene requirements."
        ],
    ),
    (
        "Sober-Living Environment",
        [
            "The Painted Lady Inn is a permanent housing community committed to sobriety, self-sufficiency and mutual support. Residents agree to abstain from alcohol, illegal drugs and misuse of prescription medication, and not to be under the influence on the premises. Lawfully prescribed medication used as directed is not misuse.",
            "Participation in recovery programs is encouraged but is not required by this agreement. Residents must not introduce alcohol or illegal drug use into shared spaces or allow guests to violate the written house rules. Management must apply rules consistently and comply with applicable disability and fair housing law.",
        ],
    ),
    (
        "Testing, Safety and House Harmony",
        [
            "The existing reasonable testing policy remains part of the sober-living rules. A refusal to comply with a lawful, reasonable testing request may be reviewed as a lease violation. Testing and the handling of results must comply with applicable law and the disclosed house rules.",
            "Neither a testing result nor a refusal authorizes an immediate lockout, removal of belongings or an automatic eviction. Special statutory drug-and-alcohol-free housing procedures may be used only when all legal qualifications actually apply. The Landlord must use the notices and legal process applicable to the particular facts.",
        ],
    ),
    (
        "Resident Care and Responsibilities",
        [
            "Keep private rooms and common areas clean, sanitary and safe. Avoid excessive trash, clutter, food waste, blocked exits and interference with other residents. Use plumbing, appliances, heating and supplied furnishings reasonably. Residents are responsible for damage caused by their actions or by guests for whom they are legally responsible, beyond ordinary wear and tear.",
            "Promptly report damage, needed repairs, leaks, excess moisture, visible mold, pests and safety hazards. Both Parties will take reasonable steps within their responsibilities to limit moisture and mold. The Landlord remains responsible for habitability and lawful repairs. Residents must respect each other's safety, privacy and quiet enjoyment.",
        ],
    ),
    (
        "Manager Housing and Support",
        [
            "The Painted Lady Inn may provide on-site housing for a manager who supports daily operations, communicates written house rules and models recovery. A manager's role does not expand legal rights of entry or reduce any Resident's tenant protections."
        ],
    ),
    (
        "Guests, Family and Occupancy",
        [
            "Immediate family may visit during normal visiting hours. Non-family guests require manager approval, and guests must be introduced upon arrival. Residents are responsible for guest behavior. No guest may remain after 10:00 p.m. without management approval. First-90-day guest restrictions remain as stated in the written house rules supplied to the Resident.",
            "Approval for a visit is not permission to stay overnight or move in. Overnight stays require prior written management approval. An approved overnight guest may not stay more than five consecutive calendar days without a specific advance written exception. Management will consider reasonable exceptions when circumstances arise; communicate openly and request permission before an exception is needed. Subletting remains prohibited.",
        ],
    ),
    (
        "Smoking, Vaping, Animals and Parking",
        [
            "Smoking and vaping are prohibited inside the residence and shared indoor spaces. Any permitted outdoor smoking area must follow the written smoking policy and applicable law. Do not discard smoking materials where they create a fire or sanitation hazard.",
            "Animals and parking are governed by the written property rules and any separate written authorization. Assistance animals will be accommodated as required by fair housing law and are not treated as ordinary pets. Any parking space must be separately assigned in writing.",
        ],
    ),
    (
        "Property Improvements, Repairs and Entry",
        [
            "The property may undergo phased remodeling. The Landlord may make lawful inspections, repairs and showings at reasonable times, generally after at least 24 hours' actual notice under ORS 90.322. Emergency entry and other statutory exceptions apply only as provided by law. The Landlord may not use access to harass; Residents may not unreasonably withhold lawful access.",
            "Management will take reasonable steps to limit disruption and protect safety during work. Residents should cooperate with lawful access arrangements and promptly report unsafe conditions. This agreement does not waive habitability or other statutory remedies.",
        ],
    ),
    (
        "Alterations, Keys and Locks",
        [
            "Obtain prior written permission before painting, installing fixtures, changing locks, making structural or electrical changes, or otherwise materially altering the premises. Ordinary permitted picture hanging is subject to the written house rules. Do not disable smoke or carbon monoxide alarms or interfere with safety equipment.",
            "Return issued keys and access devices when possession ends. Actual, reasonable costs for lost keys or Resident-caused damage may be charged only as allowed by law. Any lock change required or permitted by law remains subject to those protections.",
        ],
    ),
    (
        "Insurance and Allocation of Responsibility",
        [
            "The Landlord is responsible for building insurance. The Resident is not required to insure the building, its structure or the Landlord's furnishings. The Landlord's policy generally does not insure the Resident's personal belongings; renter's personal-property and liability insurance is encouraged.",
            "Any mandatory renter's liability insurance requirement must be separately documented and comply with ORS 90.222, with required notices, coverage limits, comparable Landlord liability insurance and statutory income or subsidy exceptions. No provision waives liability for negligence, willful misconduct or duties imposed by law.",
        ],
    ),
    (
        "Resident's 30-Day Written Move-Out Notice",
        [
            "For this month-to-month tenancy, the Resident must give the Landlord written notice of intent to move out at least 30 days before the termination date stated in the notice, as required by ORS 90.427(3)(a). The notice must identify the Resident, room or space, property and intended termination date. A termination date need not be the last day of a calendar month when the law permits otherwise.",
            "Serve the notice by a method permitted by ORS 90.155, allowing any additional time required for the selected delivery method. An oral statement, casual text or ordinary portal message alone does not replace statutory written notice unless that delivery method is legally authorized. Keep a copy and evidence of delivery.",
            "A lawful shorter notice period, statutory early-termination right or mutual written release controls when applicable. Rent liability ends as provided by law, including mitigation and re-rental duties; this clause does not authorize double collection, a blanket deposit forfeiture or an automatic penalty for insufficient notice.",
        ],
    ),
    (
        "Landlord Notices, Termination and Casualty",
        [
            "Violations involving rent, utilities, sobriety, safety, guest conduct or repeated cleanliness failures may be grounds for enforcement only under applicable law. Notice length and any opportunity to cure depend on the facts and governing statute. A 24-hour notice is available only when the requirements of ORS 90.396 or another applicable statute are met; ORS 90.392 is not a blanket 10-day termination rule.",
            "There is no self-help eviction, unlawful lock change or disposal of belongings. Possession must be recovered through lawful procedures. If fire or another casualty damages the premises, each Party retains the notices, rent adjustment, termination and other rights provided by the Act; the agreement does not automatically shift rebuilding costs to the Resident.",
        ],
    ),
    (
        "Resident Portal, Records and Optional Text Messages",
        [
            "The tenant dashboard at bowlinglegacy.com is the most effective way to reach the Landlord for maintenance, a 30-day move-out notice, payment arrangements and other written requests. Download the appropriate fillable PDF, complete and save it, and attach it to a dashboard message for the Landlord inbox. Review replies in My Requests. A dated copy remains in the resident file. Use emergency services and direct management contact for emergencies. Management should arrange a lawful alternative when needed.",
            "Routine updates may be sent by email and, with consent, text message. Text participation is optional and is not a condition of renting. Message frequency varies; message and data rates may apply. Reply STOP to opt out or HELP for help. Choosing not to receive texts does not remove responsibility to review communications properly delivered through other lawful methods.",
            "A portal message, email or text does not by itself change statutory notice service requirements. The Parties must use legally authorized delivery methods for termination, rent increases and other formal notices. Keep contact information current and report ledger errors promptly.",
        ],
    ),
    (
        "Disclosures and Notice Information",
        [
            "The Landlord must supply applicable lead-based paint information and records, asbestos information actually known, any required floodplain notice, the Eugene Tenant Education Information flyer and other required disclosures. The Resident must not disturb suspected hazardous materials and should report peeling paint or damaged materials promptly. A signature does not certify an inspection, an absence of hazards, or receipt of a document that was not actually delivered.",
            "The Landlord must provide the name and physical mailing address of the person authorized to receive notices and service, together with management contact details. Complete or attach that notice information before signing; the website alone is not a physical notice address. The Resident may be contacted at the rented premises and the contact details in the resident file.",
        ],
    ),
    (
        "Oregon Law, Disputes and Entire Agreement",
        [
            "Oregon law governs, together with applicable Eugene requirements. The Parties may attempt informal discussion or voluntary mediation with a mutually acceptable mediator. Arbitration requires a separate voluntary agreement after a dispute arises. These options do not delay statutory deadlines or waive access to court. Attorney fees and costs may be awarded as permitted by ORS 90.255.",
            "This agreement, approved written amendments and lawful written house rules form the agreement. Changes must comply with the Act, including required consent or notice. A waiver of one breach does not waive a later breach. Invalid provisions do not invalidate the remainder, and controlling law prevails over conflicting wording. Existing signed agreements remain preserved; an unsigned update does not itself amend a signed lease.",
        ],
    ),
]


def lease_sections(document=None):
    def money(value):
        return f"${Decimal(value or 0):,.2f}"

    values = dict(
        landlord="the Landlord identified in the lease particulars",
        resident="the Resident identified in the lease particulars",
        room="identified in the lease particulars",
        property="The Painted Lady Inn",
        address="address stated in the lease particulars",
        start="on the start date stated in the lease particulars",
        rent="the amount in the lease particulars",
        deposit="the amount in the lease particulars",
        utilities="the amount in the lease particulars",
        deposit_plan="as stated in the lease particulars",
    )
    if document:
        values.update(
            landlord=document.landlord_name,
            resident=document.resident_name,
            room=document.room_space or "as assigned in writing",
            property=document.property_name or "The Painted Lady Inn",
            address=document.property_address
            or "address to be completed before signing",
            start=(
                document.lease_start_date.strftime("%B %d, %Y")
                if document.lease_start_date
                else "as stated in the resident file"
            ),
            rent=money(document.monthly_rent),
            deposit=money(document.security_deposit),
            utilities=money(document.utility_fee),
            deposit_plan=document.get_deposit_payment_plan_display(),
        )
    return [
        dict(number=i, title=title, paragraphs=[p.format(**values) for p in paragraphs])
        for i, (title, paragraphs) in enumerate(SECTIONS, 1)
    ]
