# voteiq/data.py

preloaded_qa = {
    "what is nota?": "NOTA stands for 'None of the Above'. It is an option on the EVM allowing a voter to officially reject all candidates. Note that even if NOTA gets the highest votes, the candidate with the next highest votes is declared the winner.",
    "how does voting work?": "To vote, you must be a registered voter and have a Voter ID card (EPIC). You go to your designated polling booth, verify your identity with the polling officer, proceed to the voting compartment, and press the blue button on the Electronic Voting Machine (EVM) against the candidate of your choice.",
    "who won 2024?": "I am an educational assistant focused on explaining the election process. I do not provide election results, party performance, or winner claims. Please check the official Election Commission of India website for results.",
}


myths = [
    {
        "myth": "My vote does not matter",
        "reality": "Every single vote contributes to the final outcome. Many elections are decided by narrow margins.",
        "source": "Civic Education Principle"
    },
    {
        "myth": "EVMs can be casually manipulated",
        "reality": "EVMs are standalone machines not connected to any network (no Wi-Fi, Bluetooth, or Internet). They are protected by strict administrative and security protocols.",
        "source": "Election Commission of India Guidelines"
    },
    {
        "myth": "NOTA cancels all votes",
        "reality": "NOTA allows you to register your dissatisfaction, but it does not invalidate the election or force a re-election even if it receives the most votes.",
        "source": "EVM Regulations"
    },
    {
        "myth": "First-time voters need special approval",
        "reality": "First-time voters only need to register and obtain their Voter ID (EPIC) just like any other voter. No special approval is required to cast your vote.",
        "source": "Voter Registration Guidelines"
    },
    {
        "myth": "If I skip one election, I lose my right permanently",
        "reality": "Skipping an election does not remove you from the electoral roll. As long as your name remains on the current electoral roll, you can vote in subsequent elections.",
        "source": "Electoral Roll Rules"
    }
]


journey_steps = [
    {
        "step": 1,
        "title": "Check Voter Registration",
        "description": "Verify that your name appears on the electoral roll for your constituency. You can check online at the National Voters' Service Portal (NVSP) using your name, date of birth, or EPIC number.",
        "tip": "Registration closes several weeks before election day. Check early!",
        "stat": "Over 960 million registered voters in India (2024)",
        "yt_title": "How to Apply for Voter ID Card Online",
        "yt_url": "https://www.youtube.com/watch?v=-ucLifzB3HM",
        "yt_id": "-ucLifzB3HM",
        "yt_channel": "How To Finally",
        "link": "https://voters.eci.gov.in/",
        "link_label": "Check on Voter Portal",
        "icon": "bi-person-check"
    },
    {
        "step": 2,
        "title": "Register or Update Your Voter ID",
        "description": "If you are a first-time voter (18+) or have changed your address, apply for a new Voter ID card (EPIC) or update your existing details via Form 6 / Form 8 on the Voter Portal.",
        "tip": "You can now register online — no need to visit a government office.",
        "stat": "18 million new voters added to the roll before the 2024 General Election",
        "yt_title": "New Voter ID Card Apply Online 2025 — Step-by-Step",
        "yt_url": "https://www.youtube.com/watch?v=CYCb_yA_9ig",
        "yt_id": "CYCb_yA_9ig",
        "yt_channel": "Technical Sagar",
        "link": "https://voters.eci.gov.in/",
        "link_label": "Register on Voter Portal",
        "icon": "bi-card-text"
    },
    {
        "step": 3,
        "title": "Find Your Polling Booth",
        "description": "Every voter is assigned a specific polling booth based on their registered address. You must vote only at your designated booth. Find it on the Voter Information Slip (VIS) or the ECI Electoral Search portal.",
        "tip": "The ECI releases a Voter Slip closer to election day — it shows your booth number and serial number.",
        "stat": "Over 1 million polling stations set up across India for general elections",
        "yt_title": "Polling Booth Location Kaise Check Kare | How To Find Polling Station",
        "yt_url": "https://www.youtube.com/watch?v=ZJReQ8ao0SU",
        "yt_id": "ZJReQ8ao0SU",
        "yt_channel": "Online Point",
        "link": "https://electoralsearch.eci.gov.in/",
        "link_label": "Find Your Booth — ECI Electoral Search",
        "icon": "bi-geo-alt"
    },
    {
        "step": 4,
        "title": "Know Which Documents to Carry",
        "description": "You must carry your Voter ID (EPIC) to the polling booth. If you do not have your EPIC, the ECI accepts 12 alternative documents including Aadhaar, Passport, PAN card, Driving License, and MNREGA job card.",
        "tip": "Take a photo of your Voter Information Slip before going — it contains your serial number which helps polling staff locate you faster.",
        "stat": "12 alternative photo IDs accepted at polling stations (ECI Notification, Oct 2025)",
        "yt_title": "How To Get Voter ID Card Online — Documents & Process",
        "yt_url": "https://www.youtube.com/watch?v=Vz4wgt6vPBI",
        "yt_id": "Vz4wgt6vPBI",
        "yt_channel": "NDTV India",
        "link": "https://eci.gov.in/",
        "link_label": "ECI Official Site",
        "icon": "bi-file-earmark-text"
    },
    {
        "step": 5,
        "title": "Understand How to Use the EVM",
        "description": "At the polling station, after identity verification, you enter the voting compartment. Press the blue button on the EVM next to your chosen candidate's name and symbol. You will hear a beep confirming your vote.",
        "tip": "The VVPAT machine next to the EVM prints a paper slip showing your vote — it is visible for 7 seconds before dropping into a sealed box.",
        "stat": "5.5 million EVMs and 2.3 million VVPATs used in 2024",
        "yt_title": "How to Check Voter Registration Online",
        "yt_url": "https://www.youtube.com/watch?v=ehqXZs9hauc",
        "yt_id": "ehqXZs9hauc",
        "yt_channel": "Election Commission of India",
        "link": "https://eci.gov.in/",
        "link_label": "Learn About EVM — ECI",
        "icon": "bi-hand-index-thumb"
    },
    {
        "step": 6,
        "title": "After Voting — The Counting Process",
        "description": "After polling ends, EVMs are sealed and stored in secure strongrooms under continuous CCTV surveillance and security forces. On counting day, EVMs are retrieved and votes are tallied by the Returning Officer.",
        "tip": "Results are usually declared on the same day as counting, which can take 4–8 hours.",
        "stat": "Counting for 543 Lok Sabha seats happens simultaneously across the country",
        "yt_title": "Documents Required for Voting in India",
        "yt_url": "https://www.youtube.com/watch?v=NGpW-i54K-c",
        "yt_id": "NGpW-i54K-c",
        "yt_channel": "India TV News",
        "link": "https://results.eci.gov.in/",
        "link_label": "ECI Results Portal",
        "icon": "bi-clipboard-data"
    },
]


journey_templates = {
    "default": [
        {"step": "Check voter registration", "description": "Ensure your name is on the electoral roll.", "link": "https://voters.eci.gov.in/"},
        {"step": "Verify polling booth", "description": "Find your designated polling station before election day.", "link": "https://electoralsearch.eci.gov.in/"},
        {"step": "Know documents to carry", "description": "Carry your Voter ID (EPIC) or an approved alternative ID.", "link": "https://eci.gov.in/"},
        {"step": "Understand EVM + VVPAT", "description": "Learn how to use the Electronic Voting Machine and verify your vote via VVPAT.", "link": "https://eci.gov.in/"},
        {"step": "What happens after vote is cast", "description": "EVMs are sealed and stored securely until counting day.", "link": "https://results.eci.gov.in/"}
    ]
}


official_links = {
    "eci_home": "https://eci.gov.in/",
    "voter_portal": "https://voters.eci.gov.in/",
    "electoral_search": "https://electoralsearch.eci.gov.in/",
    "results_portal": "https://results.eci.gov.in/",
    "voter_helpline": "https://www.nvsp.in/",
    "ceo_tamilnadu": "https://www.elections.tn.gov.in/",
}

quiz_data = [
    {
        "question": "What is the minimum voting age in India?",
        "options": ["16", "18", "21", "25"],
        "answer": 1
    },
    {
        "question": "What does EPIC stand for in the context of Indian elections?",
        "options": ["Electoral Photo Identity Card", "Election Processing and Information Center", "Electronic Polling Interface Controller", "Electoral Polling Identification Card"],
        "answer": 0
    },
    {
        "question": "What is the purpose of VVPAT?",
        "options": ["To verify the voter's identity", "To allow the voter to verify their cast vote", "To count the votes electronically", "To display the list of candidates"],
        "answer": 1
    },
    {
        "question": "Which body is responsible for conducting free and fair elections in India?",
        "options": ["Supreme Court of India", "Parliament of India", "Election Commission of India", "President of India"],
        "answer": 2
    }
]
