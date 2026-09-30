"""Static reference data: Belgian geography, names, merchants, payers, website pages.

Everything here feeds a 100% synthetic dataset. Retail chains and public bodies are
real Belgian names used only as merchant labels so the data looks like a real bank
statement. Employers, landlords, local shops, doctors and all people are fictional.
"""

# ---------------------------------------------------------------------------
# Geography: (city, postcode, province, region, population weight)
# Region codes: FL = Flanders, BR = Brussels, WA = Wallonia
# ---------------------------------------------------------------------------
CITIES = [
    ("Antwerpen", "2000", "Antwerpen", "FL", 53), ("Gent", "9000", "Oost-Vlaanderen", "FL", 27),
    ("Brugge", "8000", "West-Vlaanderen", "FL", 12), ("Leuven", "3000", "Vlaams-Brabant", "FL", 10),
    ("Mechelen", "2800", "Antwerpen", "FL", 9), ("Aalst", "9300", "Oost-Vlaanderen", "FL", 9),
    ("Kortrijk", "8500", "West-Vlaanderen", "FL", 8), ("Hasselt", "3500", "Limburg", "FL", 8),
    ("Sint-Niklaas", "9100", "Oost-Vlaanderen", "FL", 8), ("Oostende", "8400", "West-Vlaanderen", "FL", 7),
    ("Genk", "3600", "Limburg", "FL", 7), ("Roeselare", "8800", "West-Vlaanderen", "FL", 6),
    ("Turnhout", "2300", "Antwerpen", "FL", 5), ("Dendermonde", "9200", "Oost-Vlaanderen", "FL", 5),
    ("Lier", "2500", "Antwerpen", "FL", 4), ("Geel", "2440", "Antwerpen", "FL", 4),
    ("Vilvoorde", "1800", "Vlaams-Brabant", "FL", 4), ("Waregem", "8790", "West-Vlaanderen", "FL", 4),
    ("Ieper", "8900", "West-Vlaanderen", "FL", 3), ("Lokeren", "9160", "Oost-Vlaanderen", "FL", 4),
    ("Beveren", "9120", "Oost-Vlaanderen", "FL", 5), ("Tienen", "3300", "Vlaams-Brabant", "FL", 3),
    ("Halle", "1500", "Vlaams-Brabant", "FL", 4), ("Brasschaat", "2930", "Antwerpen", "FL", 4),
    ("Deinze", "9800", "Oost-Vlaanderen", "FL", 4), ("Tongeren", "3700", "Limburg", "FL", 3),
    ("Lommel", "3920", "Limburg", "FL", 3), ("Mol", "2400", "Antwerpen", "FL", 4),
    ("Sint-Truiden", "3800", "Limburg", "FL", 4), ("Zottegem", "9620", "Oost-Vlaanderen", "FL", 3),
    ("Heist-op-den-Berg", "2220", "Antwerpen", "FL", 4), ("Knokke-Heist", "8300", "West-Vlaanderen", "FL", 3),
    ("Brussel", "1000", "Brussels", "BR", 18), ("Schaerbeek", "1030", "Brussels", "BR", 13),
    ("Etterbeek", "1040", "Brussels", "BR", 5), ("Ixelles", "1050", "Brussels", "BR", 9),
    ("Anderlecht", "1070", "Brussels", "BR", 12), ("Molenbeek-Saint-Jean", "1080", "Brussels", "BR", 10),
    ("Jette", "1090", "Brussels", "BR", 5), ("Uccle", "1180", "Brussels", "BR", 8),
    ("Woluwe-Saint-Lambert", "1200", "Brussels", "BR", 6), ("Forest", "1190", "Brussels", "BR", 6),
    ("Liège", "4000", "Liège", "WA", 20), ("Namur", "5000", "Namur", "WA", 11),
    ("Charleroi", "6000", "Hainaut", "WA", 20), ("Mons", "7000", "Hainaut", "WA", 10),
    ("Wavre", "1300", "Brabant wallon", "WA", 3), ("Ottignies-Louvain-la-Neuve", "1340", "Brabant wallon", "WA", 3),
    ("Tournai", "7500", "Hainaut", "WA", 7), ("Arlon", "6700", "Luxembourg", "WA", 3),
    ("Verviers", "4800", "Liège", "WA", 5), ("Waterloo", "1410", "Brabant wallon", "WA", 3),
    ("Nivelles", "1400", "Brabant wallon", "WA", 3),
]

# Share of customers per region. KBC is strongest in Flanders; in Wallonia the brand is CBC.
REGION_WEIGHTS = {"FL": 0.70, "BR": 0.15, "WA": 0.15}
REGION_LANGUAGES = {"FL": {"nl": 0.96, "fr": 0.02, "en": 0.02},
                    "BR": {"fr": 0.58, "nl": 0.24, "en": 0.18},
                    "WA": {"fr": 0.97, "nl": 0.01, "en": 0.02}}

COUNTRIES_ABROAD = ["ES", "FR", "IT", "NL", "DE", "PT", "GR", "HR", "TR", "MA", "AT", "GB"]

# ---------------------------------------------------------------------------
# Names. Generation buckets: "young" (born 1996+), "mid" (1971-1995), "old" (<1971)
# ---------------------------------------------------------------------------
FIRST_NAMES = {
    ("young", "M"): ["Lucas", "Noah", "Arthur", "Louis", "Liam", "Jules", "Adam", "Victor", "Finn", "Mathis",
                     "Lars", "Wout", "Milan", "Senne", "Robbe", "Hugo", "Nathan", "Théo", "Maxime", "Rayan",
                     "Elias", "Ayoub", "Emre", "Kobe", "Seppe", "Mats", "Gabriel", "Sacha", "Tuur", "Nicolas"],
    ("young", "F"): ["Emma", "Olivia", "Louise", "Mila", "Elena", "Nina", "Lina", "Marie", "Juliette", "Fleur",
                     "Noor", "Lotte", "Febe", "Jana", "Ella", "Chloé", "Manon", "Camille", "Inès", "Yasmine",
                     "Amber", "Hanne", "Lore", "Zoë", "Sara", "Aya", "Elif", "Charlotte", "Axelle", "Margaux"],
    ("mid", "M"): ["Thomas", "Kevin", "Pieter", "Jonas", "Nicolas", "Julien", "Stijn", "Bert", "Tim", "Kristof",
                   "Sven", "Bram", "Wim", "Tom", "Frederik", "Olivier", "Sébastien", "Christophe", "David", "Mehdi",
                   "Mohamed", "Karim", "Marco", "Tomasz", "Jeroen", "Koen", "Joris", "Gert", "Benoît", "Grégory"],
    ("mid", "F"): ["Sofie", "Julie", "Sarah", "Lien", "Elke", "Laura", "Caroline", "Claire", "Charlotte", "Ann",
                   "Katrien", "Nathalie", "Isabelle", "Stéphanie", "Evelien", "Leen", "Tine", "Els", "Hanne", "Céline",
                   "Aurélie", "Fatima", "Nadia", "Giulia", "Anna", "Veerle", "Ilse", "Kim", "Delphine", "Vanessa"],
    ("old", "M"): ["Marc", "Luc", "Jan", "Dirk", "Patrick", "Johan", "Philippe", "Michel", "Jean", "Guy",
                   "Eddy", "Rudi", "Willy", "Jozef", "André", "Paul", "Pierre", "Georges", "Roger", "Frans",
                   "Walter", "Etienne", "Daniel", "Alain", "Hugo", "Ahmed", "Giuseppe", "Rik", "Freddy", "Jacques"],
    ("old", "F"): ["Christine", "Martine", "Annick", "Hilde", "Nadine", "Monique", "Anne", "Marie-Claire", "Rita",
                   "Linda", "Greta", "Maria", "Jeanne", "Godelieve", "Chantal", "Françoise", "Josiane", "Lutgarde",
                   "Brigitte", "Marleen", "Paula", "Mireille", "Simone", "Danielle", "Carine", "Hélène", "Rosa",
                   "Agnes", "Viviane", "Myriam"],
}

LAST_NAMES = {
    "nl": ["Peeters", "Janssens", "Maes", "Jacobs", "Mertens", "Willems", "Claes", "Goossens", "Wouters", "De Smet",
           "Vermeulen", "Van den Bossche", "Pauwels", "Hermans", "Aerts", "Michiels", "Desmet", "De Clercq",
           "Van Damme", "Verhoeven", "Martens", "Coppens", "Van de Velde", "Stevens", "Declercq", "Verstraete",
           "Hendrickx", "Smets", "Leemans", "Vandenberghe", "De Wilde", "Segers", "Lemmens", "Wuyts", "Bogaerts",
           "Cools", "Verbeke", "Deprez", "Geerts", "Van Hecke"],
    "fr": ["Dubois", "Lambert", "Martin", "Dupont", "Leroy", "Simon", "Laurent", "Dumont", "Lejeune", "Renard",
           "Lefebvre", "Mathieu", "Denis", "François", "Collard", "Gilson", "Lemaire", "Hubert", "Masson", "Fontaine",
           "Delvaux", "Noël", "Henrard", "Legrand", "Leclercq", "Thiry", "Marchal", "Pirard", "Charlier", "Bodart"],
    "other": ["El Amrani", "Benali", "Yilmaz", "Demir", "Rossi", "Esposito", "Kowalski", "Nowak", "Mbuyi",
              "Kabasele", "Diallo", "El Idrissi", "Bouzid", "Kaya", "Öztürk", "Russo", "Romano", "Wiśniewski",
              "Popescu", "Ionescu", "Garcia", "Fernandes", "Tshibanda", "Haddad", "Cherif"],
}

# ---------------------------------------------------------------------------
# Fictional employers. Real public bodies are used for civil servants.
# ---------------------------------------------------------------------------
EMPLOYER_PREFIX = ["Vandamme", "Brightwave", "Noordster", "Delta", "Scheldeport", "Arcadia", "Ferrum", "Lumen",
                   "Kempen", "Mosa", "Sonian", "Polder", "Ardenne", "Zenith", "Horizon", "Brabo", "Meridian",
                   "Nova", "Castel", "Leie", "Dijle", "Hainaut", "Aurora", "Orion", "Quadra", "Vektor"]
EMPLOYER_SECTOR = [("Logistics", "logistics"), ("Consulting", "services"), ("Engineering", "industry"),
                   ("Retail Group", "retail"), ("Pharma", "industry"), ("Software", "ict"), ("Construction", "construction"),
                   ("Foods", "industry"), ("Healthcare Services", "health"), ("Chemicals", "industry"),
                   ("Media", "services"), ("Facility Services", "services"), ("Energy Solutions", "industry"),
                   ("Automotive", "industry"), ("Insurance Brokers", "finance"), ("Hospitality", "hospitality")]
EMPLOYER_FORMS = ["NV", "BV", "SA", "SRL"]
PUBLIC_EMPLOYERS = {
    "FL": ["Vlaamse Overheid", "Stad Antwerpen", "Stad Gent", "AgODi Onderwijs Vlaanderen", "UZ Gent", "UZ Leuven",
           "De Lijn", "NMBS", "FOD Financiën", "Politie Zone Antwerpen"],
    "BR": ["Région de Bruxelles-Capitale", "SPF Finances", "STIB-MIVB", "Commission communautaire française",
           "CHU Saint-Pierre", "Ville de Bruxelles", "Actiris", "Défense"],
    "WA": ["Service public de Wallonie", "Fédération Wallonie-Bruxelles", "CHU de Liège", "TEC", "Ville de Namur",
           "SPF Finances", "Forem", "Police Zone Liège"],
}
TEMP_AGENCIES = ["Randstad Belgium", "Start People", "Adecco", "Tempo-Team", "Accent Jobs", "Unique"]

# ---------------------------------------------------------------------------
# Spending categories -> MCC, time of day and weekday profile
# hours: (mean hour, sd); dow: weights Mon..Sun
# ---------------------------------------------------------------------------
CATEGORY_MCC = {
    "groceries": 5411, "bakery": 5462, "drugstore": 5977, "pharmacy": 5912, "restaurant": 5812,
    "cafe_bar": 5813, "fast_food": 5814, "food_delivery": 5814, "clothing": 5651, "electronics": 5732,
    "diy_garden": 5200, "furniture": 5712, "discount_store": 5310, "marketplace": 5999, "books_news": 5942,
    "sports": 5941, "entertainment": 7832, "public_transport": 4111, "taxi_mobility": 4121, "fuel": 5541,
    "parking": 7523, "hair_beauty": 7230, "medical": 8011, "pets": 5995, "baby": 5641, "toys": 5945,
    "gifts_flowers": 5992, "lottery": 7800, "travel_flight": 4511, "travel_lodging": 7011,
    "travel_agency": 4722, "jewelry": 5944, "hospital": 8062, "childcare": 8351, "education": 8220,
    "school": 8211, "legal_notary": 8111, "moving_services": 4214, "car_dealer": 5511, "car_repair": 7538,
    "wedding_services": 7299, "photo_print": 7395, "secondhand": 5931, "vet": 742, "gym": 7997,
    "streaming": 4899, "telecom": 4814, "utilities": 4900, "insurance": 6300, "atm": 6011,
    "funeral": 7261, "dentist": 8021,
}

CATEGORY_TIME = {
    "groceries": ((16, 3.2), [1.0, 0.9, 1.0, 1.0, 1.4, 1.8, 0.4]),
    "bakery": ((9, 2.0), [0.8, 0.8, 0.8, 0.8, 0.9, 1.5, 1.8]),
    "drugstore": ((14, 3.0), [1.0, 1.0, 1.1, 1.0, 1.2, 1.6, 0.1]),
    "pharmacy": ((13, 3.0), [1.2, 1.1, 1.0, 1.0, 1.1, 0.9, 0.1]),
    "restaurant": ((19.5, 1.8), [0.5, 0.6, 0.8, 1.0, 1.7, 2.0, 1.2]),
    "cafe_bar": ((19, 3.5), [0.6, 0.6, 0.8, 1.0, 1.7, 1.9, 1.2]),
    "fast_food": ((17, 4.0), [0.9, 0.9, 1.0, 1.0, 1.3, 1.3, 1.0]),
    "food_delivery": ((19.5, 1.5), [0.7, 0.7, 0.8, 0.9, 1.6, 1.6, 1.4]),
    "clothing": ((15, 2.5), [0.7, 0.8, 1.0, 0.8, 1.0, 2.0, 0.3]),
    "electronics": ((15, 3.0), [0.8, 0.8, 0.9, 0.9, 1.0, 1.7, 0.6]),
    "diy_garden": ((13, 3.0), [0.8, 0.8, 0.9, 0.9, 1.1, 2.2, 0.8]),
    "furniture": ((15, 2.5), [0.6, 0.6, 0.8, 0.8, 1.0, 2.4, 0.8]),
    "discount_store": ((14, 3.0), [1.0, 1.0, 1.1, 1.0, 1.2, 1.7, 0.1]),
    "marketplace": ((20, 3.0), [1.1, 1.1, 1.0, 1.0, 0.9, 0.9, 1.2]),
    "books_news": ((11, 3.5), [1.0, 1.0, 1.0, 1.0, 1.0, 1.4, 1.0]),
    "sports": ((15, 3.0), [0.8, 0.8, 1.0, 0.8, 1.0, 1.9, 0.6]),
    "entertainment": ((19, 3.5), [0.6, 0.6, 1.0, 0.8, 1.4, 1.8, 1.4]),
    "public_transport": ((8.5, 3.0), [1.3, 1.3, 1.2, 1.3, 1.2, 0.6, 0.4]),
    "taxi_mobility": ((20, 4.0), [0.8, 0.8, 0.9, 1.0, 1.5, 1.6, 0.8]),
    "fuel": ((12, 4.0), [1.1, 1.0, 1.0, 1.0, 1.2, 1.2, 0.5]),
    "parking": ((13, 3.5), [1.0, 1.0, 1.0, 1.0, 1.1, 1.4, 0.6]),
    "hair_beauty": ((13, 3.0), [0.3, 1.1, 1.1, 1.2, 1.3, 1.6, 0.0]),
    "medical": ((11, 3.0), [1.3, 1.2, 1.1, 1.2, 1.1, 0.4, 0.0]),
    "dentist": ((11, 3.0), [1.2, 1.2, 1.2, 1.2, 1.1, 0.2, 0.0]),
    "pets": ((14, 3.0), [0.9, 0.9, 1.0, 1.0, 1.1, 1.8, 0.2]),
    "vet": ((14, 3.0), [1.2, 1.2, 1.1, 1.1, 1.1, 0.8, 0.0]),
    "baby": ((14, 3.0), [0.8, 0.8, 1.0, 1.0, 1.1, 2.0, 0.4]),
    "toys": ((14, 3.0), [0.7, 0.7, 1.0, 0.8, 1.0, 2.0, 0.6]),
    "gifts_flowers": ((13, 3.0), [0.8, 0.8, 0.9, 0.9, 1.4, 1.8, 0.6]),
    "lottery": ((15, 4.0), [0.8, 0.8, 1.0, 0.8, 1.4, 1.4, 0.6]),
    "jewelry": ((15, 2.5), [0.6, 0.8, 0.9, 0.9, 1.1, 2.0, 0.2]),
    "secondhand": ((20, 3.0), [1.0, 1.0, 1.0, 1.0, 1.0, 1.2, 1.3]),
    "atm": ((13, 4.0), [1.0, 0.9, 1.0, 1.0, 1.4, 1.5, 0.5]),
}

# ---------------------------------------------------------------------------
# National chains / online merchants: (name, category, online?)
# ---------------------------------------------------------------------------
CHAINS = [
    # groceries
    ("Colruyt", "groceries", False), ("Delhaize", "groceries", False), ("Albert Heijn", "groceries", False),
    ("Aldi", "groceries", False), ("Lidl", "groceries", False), ("Carrefour Hypermarket", "groceries", False),
    ("Carrefour Market", "groceries", False), ("Carrefour Express", "groceries", False), ("Okay", "groceries", False),
    ("Spar", "groceries", False), ("Intermarché", "groceries", False), ("Jumbo", "groceries", False),
    ("Bio-Planet", "groceries", False), ("Collect&Go", "groceries", True), ("Delhaize Online", "groceries", True),
    # bakery chain
    ("Panos", "bakery", False), ("Le Pain Quotidien", "restaurant", False),
    # drugstore / pharmacy
    ("Kruidvat", "drugstore", False), ("DI", "drugstore", False), ("Ici Paris XL", "drugstore", False),
    ("Multipharma", "pharmacy", False), ("Newpharma", "pharmacy", True),
    # restaurants / fast food / delivery / coffee
    ("Exki", "restaurant", False), ("Pizza Hut", "restaurant", False), ("Ellis Gourmet Burger", "restaurant", False),
    ("McDonald's", "fast_food", False), ("Quick", "fast_food", False), ("Burger King", "fast_food", False),
    ("Domino's Pizza", "food_delivery", True), ("Deliveroo", "food_delivery", True), ("Uber Eats", "food_delivery", True),
    ("Takeaway.com", "food_delivery", True), ("Starbucks", "cafe_bar", False), ("Coffee Lab", "cafe_bar", False),
    # clothing
    ("Zara", "clothing", False), ("H&M", "clothing", False), ("C&A", "clothing", False), ("Primark", "clothing", False),
    ("JBC", "clothing", False), ("ZEB", "clothing", False), ("Bel&Bo", "clothing", False), ("Mango", "clothing", False),
    ("WE Fashion", "clothing", False), ("Torfs", "clothing", False), ("Zalando", "clothing", True),
    ("Shein", "clothing", True), ("About You", "clothing", True),
    # electronics
    ("MediaMarkt", "electronics", False), ("Coolblue", "electronics", True), ("Krëfel", "electronics", False),
    ("Vanden Borre", "electronics", False), ("Fnac", "electronics", False), ("Apple.com", "electronics", True),
    # diy / furniture / discount
    ("Brico", "diy_garden", False), ("Gamma", "diy_garden", False), ("Hubo", "diy_garden", False),
    ("Leroy Merlin", "diy_garden", False), ("Aveve", "diy_garden", False), ("IKEA", "furniture", False),
    ("Casa", "furniture", False), ("JYSK", "furniture", False), ("Maisons du Monde", "furniture", False),
    ("Leen Bakker", "furniture", False), ("Kwantum", "furniture", False), ("Action", "discount_store", False),
    ("Hema", "discount_store", False), ("Zeeman", "discount_store", False), ("Flying Tiger", "discount_store", False),
    # marketplaces
    ("bol.com", "marketplace", True), ("Amazon", "marketplace", True), ("AliExpress", "marketplace", True),
    ("Temu", "marketplace", True), ("Vinted", "secondhand", True), ("2dehands.be", "secondhand", True),
    # books / news
    ("Standaard Boekhandel", "books_news", False), ("Club", "books_news", False), ("Press Shop", "books_news", False),
    ("Relay", "books_news", False),
    # sports / entertainment
    ("Decathlon", "sports", False), ("A.S.Adventure", "sports", False), ("Kinepolis", "entertainment", False),
    ("UGC", "entertainment", False), ("Ticketmaster", "entertainment", True), ("Plopsaland", "entertainment", False),
    ("Pairi Daiza", "entertainment", False), ("Walibi", "entertainment", False),
    # mobility
    ("NMBS-SNCB", "public_transport", True), ("De Lijn", "public_transport", True), ("STIB-MIVB", "public_transport", True),
    ("TEC", "public_transport", True), ("Uber", "taxi_mobility", True), ("Poppy", "taxi_mobility", True),
    ("Cambio", "taxi_mobility", True), ("Blue-bike", "taxi_mobility", True),
    ("TotalEnergies", "fuel", False), ("Shell", "fuel", False), ("Q8", "fuel", False), ("Esso", "fuel", False),
    ("DATS 24", "fuel", False), ("Lukoil", "fuel", False),
    ("Interparking", "parking", False), ("Q-Park", "parking", False), ("4411", "parking", True),
    ("EasyPark", "parking", True),
    # pets
    ("Tom&Co", "pets", False), ("Maxi Zoo", "pets", False), ("Zooplus", "pets", True),
    # baby & kids
    ("Dreambaby", "baby", False), ("Baby-Dump", "baby", False), ("Orchestra", "baby", False),
    ("Vertbaudet", "baby", True), ("Babyhuys", "baby", False), ("Dreamland", "toys", False),
    ("Maxi Toys", "toys", False), ("Lego Store", "toys", False),
    # gifts, chocolates (also birth "dragées"), jewelry, lottery
    ("Interflora", "gifts_flowers", True), ("Leonidas", "gifts_flowers", False), ("Neuhaus", "gifts_flowers", False),
    ("Jeff de Bruges", "gifts_flowers", False), ("Pandora", "jewelry", False), ("Nationale Loterij", "lottery", False),
    # travel
    ("Brussels Airlines", "travel_flight", True), ("Ryanair", "travel_flight", True), ("TUI fly", "travel_flight", True),
    ("Transavia", "travel_flight", True), ("Eurostar", "travel_flight", True), ("Booking.com", "travel_lodging", True),
    ("Airbnb", "travel_lodging", True), ("TUI", "travel_agency", True), ("Sunweb", "travel_agency", True),
    ("Center Parcs", "travel_lodging", True),
    # photo prints (birth cards, wedding cards)
    ("Smartphoto", "photo_print", True), ("Hema Foto", "photo_print", True),
]

# Local businesses generated per city. {s} = a surname, {c} = the city.
LOCAL_TEMPLATES = {
    "bakery": {"nl": ["Bakkerij {s}", "Bakkerij De Korenaar", "Bakkerij 't Molentje"],
               "fr": ["Boulangerie {s}", "Boulangerie du Centre", "Au Pain Doré"]},
    "restaurant": {"nl": ["Restaurant De Gouden Leeuw", "Bistro {s}", "Brasserie De Markt", "Trattoria Da Marco",
                          "Sushi Kyo", "Restaurant 't Pleintje"],
                   "fr": ["Brasserie de la Place", "Bistro {s}", "Le Petit Gourmand", "Trattoria Da Marco",
                          "Sushi Kyo", "Restaurant Le Cerf"]},
    "cafe_bar": {"nl": ["Café De Zwaan", "Café 't Hoekje", "Bar {s}", "Koffiebar Bonen"],
                 "fr": ["Café du Commerce", "Le Bar à {s}", "Café Le Central", "Coffee Corner"]},
    "fast_food": {"nl": ["Frituur 't Hoekske", "Frituur {s}", "Kebab Anadolu"],
                  "fr": ["Friterie {s}", "Friterie de la Gare", "Kebab Anadolu"]},
    "pharmacy": {"nl": ["Apotheek {s}", "Apotheek De Linde"], "fr": ["Pharmacie {s}", "Pharmacie du Centre"]},
    "hair_beauty": {"nl": ["Kapsalon {s}", "Beauty Studio Lisa"], "fr": ["Coiffure {s}", "Institut Élégance"]},
    "medical": {"nl": ["Dr. {s} huisarts", "Groepspraktijk {c}"], "fr": ["Dr {s} médecin généraliste", "Maison médicale {c}"]},
    "dentist": {"nl": ["Tandartspraktijk {s}"], "fr": ["Cabinet dentaire {s}"]},
    "vet": {"nl": ["Dierenarts {s}"], "fr": ["Vétérinaire {s}"]},
    "gifts_flowers": {"nl": ["Bloemen {s}", "Bloemenhuis Rosa"], "fr": ["Fleurs {s}", "Au Jardin Fleuri"]},
    "childcare": {"nl": ["Kinderdagverblijf Het Zonnetje", "Kinderopvang De Speelboom"],
                  "fr": ["Crèche Les Petits Loups", "Maison d'enfants Les Lutins"]},
    "school": {"nl": ["Basisschool Sint-Jozef", "GO! Atheneum {c}"], "fr": ["École communale de {c}", "Athénée royal de {c}"]},
    "car_repair": {"nl": ["Garage {s}", "Bandencentrale {c}"], "fr": ["Garage {s}", "Pneus Center {c}"]},
    "car_dealer": {"nl": ["Autohandel {s}", "Garage {s} Automobielen"], "fr": ["Automobiles {s}", "Garage {s} & Fils"]},
    "legal_notary": {"nl": ["Notariskantoor {s}", "Advocatenkantoor {s}"], "fr": ["Étude du notaire {s}", "Cabinet d'avocats {s}"]},
    "moving_services": {"nl": ["Verhuizingen {s}"], "fr": ["Déménagements {s}"]},
    "wedding_services": {"nl": ["Feestzaal Het Kasteel", "Traiteur {s}", "Fotografie {s}"],
                         "fr": ["Salle de réception Le Château", "Traiteur {s}", "Photographe {s}"]},
    "jewelry": {"nl": ["Juwelier {s}"], "fr": ["Bijouterie {s}"]},
}

HOSPITALS = {
    "FL": ["AZ Sint-Jan Brugge", "UZ Gent", "UZ Leuven", "ZNA Middelheim", "AZ Groeninge", "Jessa Ziekenhuis",
           "AZ Delta", "AZ Sint-Lucas Gent", "GZA Ziekenhuizen", "AZ Turnhout"],
    "BR": ["CHU Saint-Pierre", "Cliniques universitaires Saint-Luc", "UZ Brussel", "Hôpital Erasme", "Delta Chirec"],
    "WA": ["CHU de Liège", "CHU UCL Namur", "Grand Hôpital de Charleroi", "CHU Helora Mons", "Clinique Saint-Pierre Ottignies"],
}
UNIVERSITIES = {"FL": ["KU Leuven", "UGent", "UAntwerpen", "VUB", "Hogeschool Gent", "Thomas More", "UHasselt"],
                "BR": ["ULB", "VUB", "UCLouvain Saint-Louis", "EPHEC"],
                "WA": ["UCLouvain", "ULiège", "UNamur", "UMONS", "HELMo"]}

FOREIGN_MERCHANTS = {
    "groceries": ["Mercadona", "Carrefour", "E.Leclerc", "Conad", "Lidl", "Rewe", "Pingo Doce", "Migros",
                  "Tesco", "Spar", "Albert Heijn", "Konzum", "Marjane"],
    "restaurant": ["Restaurante El Puerto", "Trattoria del Sole", "Taverna Mykonos", "Brasserie du Port",
                   "Restaurante Sol y Mar", "Gasthaus zur Linde", "Marisqueira O Farol", "Konoba Adriatic"],
    "cafe_bar": ["Café de la Plage", "Bar Central", "Beach Bar Paradise", "Kafe Istanbul", "Pub The Crown"],
    "entertainment": ["Museo Nacional", "Aquapark Costa", "Boat Tours Ltd", "Musée du Louvre", "Parco Avventura"],
    "fuel": ["Repsol", "TotalEnergies", "Eni", "Aral", "Galp"],
    "travel_lodging": ["Hotel Miramar", "Hôtel du Lac", "Hotel Bellavista", "Camping Les Pins"],
}

# ---------------------------------------------------------------------------
# Payers and recurring counterparties
# ---------------------------------------------------------------------------
PENSION_PAYER = {"FL": "Federale Pensioendienst", "BR": "Service fédéral des Pensions", "WA": "Service fédéral des Pensions"}
CHILD_BENEFIT_PAYERS = {"FL": ["FONS", "Kidslife Vlaanderen", "Infino", "MyFamily", "Parentia"],
                        "BR": ["Famiris", "Infino Brussels", "Kidslife Brussels", "Parentia Brussels"],
                        "WA": ["FAMIWAL", "Camille", "Infino Wallonie", "Kidslife Wallonie", "Parentia Wallonie"]}
UNEMPLOYMENT_PAYERS = {"FL": ["ACV", "ABVV", "ACLVB", "HVW"], "BR": ["CSC", "FGTB", "CGSLB", "CAPAC"],
                       "WA": ["CSC", "FGTB", "CGSLB", "CAPAC"]}
MUTUALITIES = {"FL": ["CM", "Solidaris", "Helan", "Liberale Mutualiteit", "Vlaams & Neutraal Ziekenfonds"],
               "BR": ["Mutualité chrétienne", "Solidaris", "Partenamut", "Helan"],
               "WA": ["Mutualité chrétienne", "Solidaris", "Partenamut", "Mutualité libérale"]}
TAX_AUTHORITY = {"FL": "FOD Financiën", "BR": "SPF Finances", "WA": "SPF Finances"}
REGIONAL_TAX = {"FL": "Vlaamse Belastingdienst", "BR": "Bruxelles Fiscalité", "WA": "SPW Fiscalité"}
ENERGY = ["Engie", "Luminus", "TotalEnergies Power & Gas", "Eneco", "Mega", "Bolt Energie", "Octa+"]
WATER = {"FL": ["De Watergroep", "Farys", "Pidpa", "water-link"], "BR": ["Vivaqua"], "WA": ["SWDE", "CILE", "inBW"]}
TELECOM = {"FL": ["Proximus", "Telenet", "Orange Belgium", "Mobile Vikings", "Scarlet", "BASE"],
           "BR": ["Proximus", "Telenet", "Orange Belgium", "VOO", "Scarlet"],
           "WA": ["Proximus", "VOO", "Orange Belgium", "Scarlet"]}
STREAMING = [("Netflix", 13.99), ("Spotify", 11.99), ("Disney+", 9.99), ("Streamz", 12.95), ("Amazon Prime", 5.99),
             ("YouTube Premium", 13.99), ("Apple iCloud", 2.99), ("GoPlay", 6.99), ("Deezer", 11.99)]
GYMS = [("Basic-Fit", 29.99), ("JIMS", 34.99), ("Anytime Fitness", 44.99)]
EXTERNAL_INSURERS = ["AG Insurance", "Ethias", "P&V", "Baloise", "Allianz Benelux", "Belfius Insurance", "DKV"]
SOCIAL_FUNDS = ["Liantis", "Acerta", "Xerius", "Partena Professional", "Securex"]
CHARITIES = ["Rode Kruis", "Artsen Zonder Grenzen", "11.11.11", "Kom op tegen Kanker", "Unicef Belgium", "Oxfam"]

# ---------------------------------------------------------------------------
# Website / app catalogue (illustrative structure, not the real kbc.be sitemap)
# (page_id, path, section, topic, page_type)
# ---------------------------------------------------------------------------
PAGES = [
    # mobile app / online banking
    ("app_home", "/app/home", "app", "daily_banking", "app_screen"),
    ("app_accounts", "/app/accounts", "app", "daily_banking", "app_screen"),
    ("app_transactions", "/app/accounts/transactions", "app", "daily_banking", "app_screen"),
    ("app_tx_detail", "/app/accounts/transactions/detail", "app", "daily_banking", "app_screen"),
    ("app_transfer", "/app/payments/transfer", "app", "payments", "app_screen"),
    ("app_transfer_confirm", "/app/payments/transfer/confirm", "app", "payments", "app_screen"),
    ("app_payconiq", "/app/payments/scan-qr", "app", "payments", "app_screen"),
    ("app_standing_orders", "/app/payments/standing-orders", "app", "payments", "app_screen"),
    ("app_cards", "/app/cards", "app", "cards", "app_screen"),
    ("app_card_limits", "/app/cards/limits", "app", "cards", "app_screen"),
    ("app_card_block", "/app/cards/block", "app", "cards", "app_screen"),
    ("app_savings", "/app/savings", "app", "savings", "app_screen"),
    ("app_pension", "/app/savings/pension-savings", "app", "pension_savings", "app_screen"),
    ("app_investments", "/app/investments", "app", "investing", "app_screen"),
    ("app_fund_detail", "/app/investments/fund-detail", "app", "investing", "app_screen"),
    ("app_insurance", "/app/insurance", "app", "insurance", "app_screen"),
    ("app_claim", "/app/insurance/report-claim", "app", "insurance", "app_screen"),
    ("app_loans", "/app/loans", "app", "loans", "app_screen"),
    ("app_kate", "/app/kate", "app", "kate", "app_screen"),
    ("app_offers", "/app/offers", "app", "offers", "app_screen"),
    ("app_budget", "/app/insights/budget", "app", "budgeting", "app_screen"),
    ("app_mobility_parking", "/app/mobility/parking", "app", "mobility", "app_screen"),
    ("app_mobility_ticket", "/app/mobility/public-transport", "app", "mobility", "app_screen"),
    ("app_documents", "/app/documents", "app", "documents", "app_screen"),
    ("app_tax_certificates", "/app/documents/tax-certificates", "app", "tax", "app_screen"),
    ("app_settings_consent", "/app/settings/privacy-consent", "app", "settings", "app_screen"),
    ("app_settings_profile", "/app/settings/profile", "app", "settings", "app_screen"),
    ("app_situation", "/app/settings/my-situation", "app", "settings", "app_screen"),
    # public website: products
    ("web_home", "/retail/home", "website", "general", "landing"),
    ("web_current_account", "/retail/products/accounts/current-account", "website", "daily_banking", "product"),
    ("web_youth_account", "/retail/products/accounts/youth-account", "website", "child_savings", "product"),
    ("web_credit_card", "/retail/products/cards/credit-card", "website", "cards", "product"),
    ("web_savings_account", "/retail/products/savings/savings-account", "website", "savings", "product"),
    ("web_pension_savings", "/retail/products/savings/pension-savings", "website", "pension_savings", "product"),
    ("web_long_term_savings", "/retail/products/savings/long-term-savings", "website", "long_term_savings", "product"),
    ("web_child_savings", "/retail/products/savings/saving-for-your-child", "website", "child_savings", "product"),
    ("web_funds", "/retail/products/investing/funds", "website", "investing", "product"),
    ("web_invest_plan", "/retail/products/investing/investment-plan", "website", "investing", "product"),
    ("web_invest_advice", "/retail/products/investing/investment-advice", "website", "investing", "product"),
    ("web_home_loan", "/retail/products/loans/home-loan", "website", "home_loan", "product"),
    ("web_home_loan_sim", "/retail/products/loans/home-loan/simulator", "website", "home_loan", "simulator"),
    ("web_renovation_loan", "/retail/products/loans/renovation-loan", "website", "renovation", "product"),
    ("web_car_loan", "/retail/products/loans/car-loan", "website", "car_loan", "product"),
    ("web_car_loan_sim", "/retail/products/loans/car-loan/simulator", "website", "car_loan", "simulator"),
    ("web_personal_loan", "/retail/products/loans/personal-loan", "website", "personal_loan", "product"),
    ("web_home_insurance", "/retail/products/insurance/home-insurance", "website", "home_insurance", "product"),
    ("web_car_insurance", "/retail/products/insurance/car-insurance", "website", "car_insurance", "product"),
    ("web_hospitalisation", "/retail/products/insurance/hospitalisation-insurance", "website", "hospitalisation", "product"),
    ("web_family_liability", "/retail/products/insurance/family-liability", "website", "family_liability", "product"),
    ("web_life_insurance", "/retail/products/insurance/life-insurance", "website", "life_insurance", "product"),
    ("web_travel_insurance", "/retail/products/insurance/travel-insurance", "website", "travel", "product"),
    # public website: life moments
    ("life_baby", "/retail/life/having-a-baby", "website", "baby_family", "life_moment"),
    ("life_baby_checklist", "/retail/life/having-a-baby/checklist", "website", "baby_family", "life_moment"),
    ("life_home", "/retail/life/buying-a-home", "website", "home_loan", "life_moment"),
    ("life_home_costs", "/retail/life/buying-a-home/costs-and-taxes", "website", "home_loan", "life_moment"),
    ("life_first_job", "/retail/life/your-first-job", "website", "first_job", "life_moment"),
    ("life_moving", "/retail/life/moving-out", "website", "moving", "life_moment"),
    ("life_together", "/retail/life/living-together", "website", "living_together", "life_moment"),
    ("life_wedding", "/retail/life/getting-married", "website", "wedding", "life_moment"),
    ("life_retirement", "/retail/life/preparing-your-retirement", "website", "retirement", "life_moment"),
    ("life_studying", "/retail/life/children-going-to-university", "website", "studying", "life_moment"),
    ("life_job_loss", "/retail/life/losing-your-job", "website", "job_loss", "life_moment"),
    ("life_separation", "/retail/life/separating", "website", "separation", "life_moment"),
    ("life_inheritance", "/retail/life/receiving-an-inheritance", "website", "inheritance", "life_moment"),
    ("life_car", "/retail/life/buying-a-car", "website", "car_loan", "life_moment"),
    # tools and help
    ("tool_budget", "/retail/tools/budget-planner", "website", "budgeting", "tool"),
    ("tool_pension_calc", "/retail/tools/pension-calculator", "website", "pension_savings", "tool"),
    ("tool_savings_goal", "/retail/tools/savings-goal-calculator", "website", "savings", "tool"),
    ("help_faq", "/retail/help/faq", "website", "help", "help"),
    ("help_contact", "/retail/help/contact", "website", "help", "help"),
    ("help_card_blocked", "/retail/help/card-lost-or-stolen", "website", "cards", "help"),
    ("help_phishing", "/retail/help/fraud-and-phishing", "website", "help", "help"),
    ("help_payment_difficulties", "/retail/help/payment-difficulties", "website", "job_loss", "help"),
    ("branch_finder", "/retail/branches/find-a-branch", "website", "help", "help"),
    ("appointment_book", "/retail/appointments/book", "website", "appointment", "form"),
    ("appointment_confirm", "/retail/appointments/confirmation", "website", "appointment", "form"),
    ("apply_start", "/retail/apply/start", "website", "application", "form"),
    ("apply_done", "/retail/apply/confirmation", "website", "application", "form"),
    ("news_rates", "/retail/news/interest-rates", "website", "savings", "article"),
    ("news_markets", "/retail/news/markets-update", "website", "investing", "article"),
    ("news_tax", "/retail/news/tax-return-tips", "website", "tax", "article"),
    ("news_travel", "/retail/news/paying-abroad", "website", "travel", "article"),
]

# Topic -> pages visited when a customer explores that topic (ordered funnel)
TOPIC_FUNNELS = {
    "baby_family": ["life_baby", "life_baby_checklist", "web_hospitalisation", "web_child_savings", "web_family_liability"],
    "child_savings": ["web_child_savings", "web_youth_account", "web_long_term_savings", "tool_savings_goal"],
    "home_loan": ["life_home", "life_home_costs", "web_home_loan", "web_home_loan_sim"],
    "home_insurance": ["web_home_insurance", "web_family_liability"],
    "renovation": ["web_renovation_loan", "web_home_insurance"],
    "car_loan": ["life_car", "web_car_loan", "web_car_loan_sim", "web_car_insurance"],
    "car_insurance": ["web_car_insurance"],
    "pension_savings": ["web_pension_savings", "tool_pension_calc", "app_pension"],
    "long_term_savings": ["web_long_term_savings", "tool_savings_goal"],
    "savings": ["web_savings_account", "news_rates", "tool_savings_goal", "app_savings"],
    "investing": ["web_funds", "news_markets", "web_invest_plan", "web_invest_advice", "app_investments"],
    "first_job": ["life_first_job", "web_pension_savings", "web_credit_card", "web_savings_account"],
    "moving": ["life_moving", "web_home_insurance", "web_family_liability"],
    "living_together": ["life_together", "web_current_account", "web_home_insurance"],
    "wedding": ["life_wedding", "web_personal_loan", "web_life_insurance"],
    "retirement": ["life_retirement", "tool_pension_calc", "web_invest_advice", "web_funds"],
    "studying": ["life_studying", "web_youth_account", "tool_budget"],
    "job_loss": ["life_job_loss", "help_payment_difficulties", "tool_budget", "app_budget"],
    "separation": ["life_separation", "web_current_account", "tool_budget"],
    "inheritance": ["life_inheritance", "web_invest_advice", "web_funds"],
    "travel": ["news_travel", "web_travel_insurance", "app_card_limits"],
    "hospitalisation": ["web_hospitalisation"],
    "family_liability": ["web_family_liability"],
    "life_insurance": ["web_life_insurance"],
    "personal_loan": ["web_personal_loan"],
    "budgeting": ["app_budget", "tool_budget"],
    "tax": ["news_tax", "app_tax_certificates"],
    "cards": ["web_credit_card", "app_cards"],
    "help": ["help_faq", "help_contact", "branch_finder"],
}
TOPIC_SIMULATOR = {"home_loan": "web_home_loan_sim", "car_loan": "web_car_loan_sim",
                   "pension_savings": "tool_pension_calc", "savings": "tool_savings_goal",
                   "child_savings": "tool_savings_goal", "retirement": "tool_pension_calc",
                   "budgeting": "tool_budget", "job_loss": "tool_budget"}

SEARCH_QUERIES = {
    "baby_family": {"nl": ["groeipakket startbedrag", "kraampremie", "hospitalisatieverzekering baby", "zwanger wat regelen",
                           "kind bijschrijven ziekenfonds", "geboortepremie"],
                    "fr": ["allocation de naissance", "prime de naissance", "assurance hospitalisation bébé",
                           "enceinte démarches banque", "ajouter enfant mutuelle"],
                    "en": ["birth allowance belgium", "having a baby checklist", "add baby to insurance"]},
    "child_savings": {"nl": ["spaarrekening kind", "sparen voor kinderen", "rekening op naam van kind"],
                      "fr": ["compte épargne enfant", "épargner pour son enfant"], "en": ["savings account for my child"]},
    "home_loan": {"nl": ["woonkrediet simulatie", "hoeveel kan ik lenen", "registratierechten", "woonlening rente",
                         "eigen inbreng huis"],
                  "fr": ["crédit hypothécaire simulation", "combien puis-je emprunter", "droits d'enregistrement",
                         "taux prêt immobilier"],
                  "en": ["mortgage simulator", "how much can I borrow", "home loan rate"]},
    "car_loan": {"nl": ["autolening", "lening nieuwe auto", "autokrediet simulatie"],
                 "fr": ["prêt auto", "crédit voiture simulation"], "en": ["car loan"]},
    "pension_savings": {"nl": ["pensioensparen", "pensioensparen belastingvoordeel", "pensioenspaarfonds"],
                        "fr": ["épargne pension", "épargne pension avantage fiscal"], "en": ["pension savings belgium"]},
    "investing": {"nl": ["beleggen", "beleggingsfonds", "beleggingsplan", "beleggen met spaargeld"],
                  "fr": ["investir", "fonds de placement", "plan d'investissement"], "en": ["investment funds", "invest savings"]},
    "retirement": {"nl": ["pensioen berekenen", "met pensioen gaan", "groepsverzekering uitbetaling"],
                   "fr": ["calcul pension", "partir à la retraite", "assurance groupe capital"], "en": ["retirement planning"]},
    "job_loss": {"nl": ["werkloosheidsuitkering", "afbetaling uitstellen", "betalingsmoeilijkheden"],
                 "fr": ["allocations de chômage", "report de paiement", "difficultés de paiement"], "en": ["lost my job loan"]},
    "wedding": {"nl": ["huwelijk bankrekening", "trouwen samenlevingscontract"], "fr": ["mariage compte commun"],
                "en": ["joint account marriage"]},
    "moving": {"nl": ["huurwaarborg", "brandverzekering huurder"], "fr": ["garantie locative", "assurance incendie locataire"],
               "en": ["rental deposit"]},
    "first_job": {"nl": ["eerste job", "eerste loon", "kredietkaart aanvragen"], "fr": ["premier emploi", "carte de crédit"],
                  "en": ["first job bank account"]},
    "savings": {"nl": ["spaarrente", "beste spaarrekening"], "fr": ["taux d'épargne", "compte d'épargne"], "en": ["savings rate"]},
    "travel": {"nl": ["betalen in het buitenland", "reisverzekering"], "fr": ["payer à l'étranger", "assurance voyage"],
               "en": ["paying abroad card"]},
    "tax": {"nl": ["fiscaal attest", "belastingaangifte"], "fr": ["attestation fiscale", "déclaration d'impôts"],
            "en": ["tax certificate"]},
    "inheritance": {"nl": ["erfenis", "successierechten"], "fr": ["héritage", "droits de succession"], "en": ["inheritance tax"]},
    "separation": {"nl": ["scheiding rekening", "gezamenlijke rekening splitsen"], "fr": ["séparation compte joint"],
                   "en": ["separation joint account"]},
    "studying": {"nl": ["studentenkot", "inschrijvingsgeld universiteit"], "fr": ["kot étudiant", "minerval"],
                 "en": ["student room"]},
    "cards": {"nl": ["kaart geblokkeerd", "limiet verhogen"], "fr": ["carte bloquée", "augmenter limite"], "en": ["card limit"]},
    "help": {"nl": ["contact kantoor", "phishing melden"], "fr": ["contacter agence", "signaler phishing"], "en": ["contact branch"]},
}

KATE_INTENTS = {
    "daily_banking": ["check_balance", "spending_this_month", "find_transaction"],
    "payments": ["make_transfer", "pay_bill", "schedule_payment"],
    "cards": ["block_card", "change_card_limit", "card_pin"],
    "baby_family": ["child_benefit_info", "add_child_to_insurance"],
    "home_loan": ["how_much_can_i_borrow", "home_loan_rate"],
    "pension_savings": ["pension_savings_info", "tax_benefit_pension"],
    "investing": ["investment_advice", "market_update"],
    "savings": ["savings_rate", "open_savings_account"],
    "car_loan": ["car_loan_info"],
    "travel": ["card_abroad", "travel_insurance_info"],
    "job_loss": ["payment_holiday", "budget_help"],
    "retirement": ["retirement_income", "pension_date"],
    "budgeting": ["spending_insights", "budget_help"],
}

# Generic in-app banners shown today to everyone (the "BEFORE" state of KBC Fit)
GENERIC_BANNERS = [("banner_personal_loan", "personal_loan"), ("banner_car_insurance", "car_insurance"),
                   ("banner_savings", "savings"), ("banner_credit_card", "cards"), ("banner_home_insurance", "home_insurance"),
                   ("banner_investing", "investing")]
