"""Static names and tables used by the Panchang engine."""

TITHI_NAMES = [
    "Shukla Pratipada",
    "Shukla Dwitiya",
    "Shukla Tritiya",
    "Shukla Chaturthi",
    "Shukla Panchami",
    "Shukla Shashthi",
    "Shukla Saptami",
    "Shukla Ashtami",
    "Shukla Navami",
    "Shukla Dashami",
    "Shukla Ekadashi",
    "Shukla Dwadashi",
    "Shukla Trayodashi",
    "Shukla Chaturdashi",
    "Purnima",
    "Krishna Pratipada",
    "Krishna Dwitiya",
    "Krishna Tritiya",
    "Krishna Chaturthi",
    "Krishna Panchami",
    "Krishna Shashthi",
    "Krishna Saptami",
    "Krishna Ashtami",
    "Krishna Navami",
    "Krishna Dashami",
    "Krishna Ekadashi",
    "Krishna Dwadashi",
    "Krishna Trayodashi",
    "Krishna Chaturdashi",
    "Amavasya",
]

NAKSHATRA_NAMES = [
    "Ashwini",
    "Bharani",
    "Krittika",
    "Rohini",
    "Mrigashira",
    "Ardra",
    "Punarvasu",
    "Pushya",
    "Ashlesha",
    "Magha",
    "Purva Phalguni",
    "Uttara Phalguni",
    "Hasta",
    "Chitra",
    "Swati",
    "Vishakha",
    "Anuradha",
    "Jyeshtha",
    "Mula",
    "Purva Ashadha",
    "Uttara Ashadha",
    "Shravana",
    "Dhanishta",
    "Shatabhisha",
    "Purva Bhadrapada",
    "Uttara Bhadrapada",
    "Revati",
]

YOGA_NAMES = [
    "Vishkambha",
    "Priti",
    "Ayushman",
    "Saubhagya",
    "Shobhana",
    "Atiganda",
    "Sukarma",
    "Dhriti",
    "Shula",
    "Ganda",
    "Vriddhi",
    "Dhruva",
    "Vyaghata",
    "Harshana",
    "Vajra",
    "Siddhi",
    "Vyatipata",
    "Variyana",
    "Parigha",
    "Shiva",
    "Siddha",
    "Sadhya",
    "Shubha",
    "Shukla",
    "Brahma",
    "Indra",
    "Vaidhriti",
]

KARANA_NAMES_MOVABLE = ["Bava", "Balava", "Kaulava", "Taitila", "Gara", "Vanija", "Vishti"]
KARANA_NAMES_FIXED = ["Shakuni", "Chatushpada", "Naga", "Kintughna"]

VARA_NAMES = [
    "Ravivara",
    "Somavara",
    "Mangalavara",
    "Budhavara",
    "Guruvara",
    "Shukravara",
    "Shanivara",
]

RASHI_NAMES = [
    "Mesha",
    "Vrishabha",
    "Mithuna",
    "Karka",
    "Simha",
    "Kanya",
    "Tula",
    "Vrishchika",
    "Dhanu",
    "Makara",
    "Kumbha",
    "Meena",
]

RITU_NAMES = ["Vasanta", "Grishma", "Varsha", "Sharad", "Hemanta", "Shishira"]

LUNAR_MONTH_NAMES_AMANTA = [
    "Chaitra",
    "Vaishakha",
    "Jyeshtha",
    "Ashadha",
    "Shravana",
    "Bhadrapada",
    "Ashwina",
    "Kartika",
    "Margashirsha",
    "Pausha",
    "Magha",
    "Phalguna",
]

SAMVATSARA_NAMES = [
    "Prabhava",
    "Vibhava",
    "Shukla",
    "Pramoda",
    "Prajapati",
    "Angirasa",
    "Shrimukha",
    "Bhava",
    "Yuva",
    "Dhata",
    "Ishvara",
    "Bahudhanya",
    "Pramathi",
    "Vikrama",
    "Vrisha",
    "Chitrabhanu",
    "Subhanu",
    "Tarana",
    "Parthiva",
    "Vyaya",
    "Sarvajit",
    "Sarvadhari",
    "Virodhi",
    "Vikriti",
    "Khara",
    "Nandana",
    "Vijaya",
    "Jaya",
    "Manmatha",
    "Durmukhi",
    "Hemalamba",
    "Vilamba",
    "Vikari",
    "Sharvari",
    "Plava",
    "Shubhakritu",
    "Shobhakritu",
    "Krodhi",
    "Vishvavasu",
    "Parabhava",
    "Plavanga",
    "Kilaka",
    "Saumya",
    "Sadharana",
    "Virodhikritu",
    "Paridhavi",
    "Pramadi",
    "Ananda",
    "Rakshasa",
    "Anala",
    "Pingala",
    "Kalayukti",
    "Siddharthi",
    "Raudra",
    "Durmati",
    "Dundubhi",
    "Rudhirodgari",
    "Raktakshi",
    "Krodhana",
    "Akshaya",
]

CHOGHADIYA_DAY_SEQUENCE = {
    # Vara index (0=Sunday) -> ordered list of the 8 day choghadiya names
    0: ["Udvega", "Amrita", "Roga", "Kala", "Shubha", "Udvega", "Chara", "Labha"],
    1: ["Amrita", "Kala", "Shubha", "Roga", "Udvega", "Chara", "Labha", "Amrita"],
    2: ["Roga", "Udvega", "Chara", "Labha", "Amrita", "Kala", "Shubha", "Roga"],
    3: ["Labha", "Amrita", "Kala", "Shubha", "Roga", "Udvega", "Chara", "Labha"],
    4: ["Shubha", "Roga", "Udvega", "Chara", "Labha", "Amrita", "Kala", "Shubha"],
    5: ["Chara", "Labha", "Amrita", "Kala", "Shubha", "Roga", "Udvega", "Chara"],
    6: ["Kala", "Shubha", "Roga", "Udvega", "Chara", "Labha", "Amrita", "Kala"],
}

CHOGHADIYA_NIGHT_SEQUENCE = {
    0: ["Shubha", "Amrita", "Chara", "Roga", "Kala", "Labha", "Udvega", "Shubha"],
    1: ["Chara", "Roga", "Kala", "Labha", "Udvega", "Shubha", "Amrita", "Chara"],
    2: ["Kala", "Labha", "Udvega", "Shubha", "Amrita", "Chara", "Roga", "Kala"],
    3: ["Udvega", "Shubha", "Amrita", "Chara", "Roga", "Kala", "Labha", "Udvega"],
    4: ["Amrita", "Chara", "Roga", "Kala", "Labha", "Udvega", "Shubha", "Amrita"],
    5: ["Roga", "Kala", "Labha", "Udvega", "Shubha", "Amrita", "Chara", "Roga"],
    6: ["Labha", "Udvega", "Shubha", "Amrita", "Chara", "Roga", "Kala", "Labha"],
}

CHOGHADIYA_AUSPICIOUS = {"Amrita", "Shubha", "Labha", "Chara"}

# Hora lord sequence starting from the Sun, cycled by Vara (Chaldean order)
HORA_LORDS = ["Surya", "Shukra", "Budha", "Chandra", "Shani", "Guru", "Mangala"]

# Index into HORA_LORDS for the first hora of each weekday (0=Sunday)
HORA_START_INDEX = {0: 0, 1: 3, 2: 6, 3: 2, 4: 5, 5: 1, 6: 4}

# Rahu Kalam / Yamaganda / Gulika segment-of-the-day index (0-7), by weekday (0=Sunday)
RAHU_KALAM_SEGMENT = {0: 7, 1: 1, 2: 6, 3: 4, 4: 5, 5: 3, 6: 2}
YAMAGANDA_SEGMENT = {0: 4, 1: 3, 2: 2, 3: 1, 4: 0, 5: 6, 6: 5}
GULIKA_SEGMENT = {0: 6, 1: 5, 2: 4, 3: 3, 4: 2, 5: 1, 6: 0}
