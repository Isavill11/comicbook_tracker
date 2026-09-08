



from bs4 import BeautifulSoup
import requests
import time
import json
import os




STUDIOS = ['DC', 'Marvel']

### i will never EVER (probably) pick up these comics, so why have em in my database
EXCLUDE = [
    'GO!', '100 BULLETS', 'KEV', 'ADAM STRANGE', 'AMERICAN CARNAGE', 'AMERICAN VAMPIRE', 'AMERICAN SPLENDOR', 'AMETHYST', 'ANARKY', 'ANIMA', 'ANIMAL MAN', 'ARION', 'ART OPS', 'AZRAEL', 'AZTEK', 'BACKLASH', 'BARDA', 'BLACK ADAM', 'BLACK MAGIC', 'BLACK ORCHID', 'BLACKHAWK', 'BLOOD & SHADOWS', 'BLOOD SYNDICATE', 'BLOODLINES', 'BOOKS OF MAGIC', 'CINDER & ASHE', 'CITY BOY','CLEAN ROOM', 'CHUCK', 'CHASE',' COFFIN HILL', 'COLLAPSER', 'DMZ', 'DUO', 'DV8', 'DAMAGE', 'DANGER STREET', 'DAPHNE DYRNE', 'DEADENDERS', 'DEADMAN', 'DEMON KNIGHTS', 'DESTINY', 'DIAL H', 'DOG MOON', 'VOODOO CHILD', 'ETERNITY GIRL', 'EL DIABLO', 'ELECTRIC WARRIORS', 'EVENT LEVIATHAN', 'EVERAFTER', 'EX MACHINA', 'EXIT STAGE LEFT', 'FBP', 'FABLES', 'FAULT LINES', 'FURIES', 'FIRE', 'FIRE & ICE', 'FLINCH', 'FOREVER PEOPLE', 'FREEDOM FIGHTERS', 'FRINGE', 'FROSTBITE', 'GI COMBAT', 'GALAXY', 'GANGLAND', 'GEN13', 'GET JIRO!', 'GHOSTDANCING', 'GHOSTS', 'GODDESS', 'GODZILLA', 'GLOBAL FREQUENCY', 'HARDWARE', 'HARLEEN', 'HBO MAX', 'H-E-R-O', 'HEART THROBS', 'HELLBLAZER', 'HEX', 'HITMAN', 'HOURMAN', 'HOUSE OF', 'HUMAN BOMB', 'HUMAN DEFENSE CORPS', 'HUMAN TARGET', 'I AM NOT STARFIRE', 'I, VAMPIRE', 'ICON', 'INFERNO', 'INFERIOR FIVE', 'INVASION!', 'JINNY HEX', 'JEW GANGSTER', 'JIMMY OLSEN', 'JINX', 'JOE KUBERT PRESENTS', 'JOE' 'JONAH HEX', 'JONNI THUNDER', 'JONNY DOUBLE', 'JUNK CULTURE', 'JUST IMAGINE', 'JUSTICE LEAGUE:DREAM GIRLS', 'KATANA', 'KID ETERNITY', 'KAMANDI:', 'KLARION', 'KNIGHT & SQUIRE', 'LEGION', 'LOBO', 'MAD', 'LUCIFER', 'MERA', 'METAL MEN', 'MILK WARS', 'NATHANIEL DUSK', "NEIL GAIMAN'S", 'NEIL GAIMAN', 'NEMESIS', 'NEW GODS', 'NEW CHALLENGERS', 'NIGHT FORCE', 'NORTH 40', 'NUBIA:', 'OMAC', 'NUMBER OF THE BEAST', 'ORBITER', 'ORION', 'PHANTOM LADY', 'PLASTIC MAN', 'POWER GIRL', 'PREZ', 'PREACHER', 'PRIMER', 'PROMETHEA', 'QUARANTINE ZONE', 'REBELS', 'RAGMAN', 'RANN-THANAGAR', 'RED THORN', 'RED TORNADO', 'REIGN IN HELL', 'RICHARD DRAGON', 'REVOLVER', 'RONIN', 'ROGUES', 'RORSCHACH', 'SALVATION RUN', 'SASQUATCH', 'SCALPED', 'SAVAGE THINGS', 'SCARAB', 'SCOOBY', 'SEVEN SOLDIERS', 'SHADE,', 'SHADOWPACT', 'SHERIFF OF BABYLON', 'SHOWCASE', 'SIX DAYS', 'SKIN GRAFT', 'SLEEPER', 'SLASH & BURN', 'SOLO', 'STRANGE ADVENTURES', 'SUN DEVILS', 'SURVIVORS CLUB', 'THUNDER AGENTS', 'SWEET TOOTH', 'SWORD OF AZRAEL', 'SWORD OF SORCERY', 'TANGENT COMICS', 'TEAM 7', 'TATTERED BANNERS', 'TEAM ONE WILDC.A.T.S', 'TEAM ZERO', 'TERRA OBSCURA', 'THE AUTHORITY', 'THE DEADMAN', 'THE DARKSTARS', 'THE DARK AND BLOODY', 'THE DEAD BOY DETECTIVES', 'THE DEMON', 'THE DREAMING', 'THE DOLLHOUSE', 'THE EZRA CAIN MYSTERIES', 'THE FILTH', 'THE GIRL WHO WOULD BE DEATH', 'THE GREAT TEN', 'THE KITCHEN', 'THE KAMANDI CHALLENGE', 'THE LEGION', 'THE LITERALS', 'THE LITTLE ENDLESS STORYBOOK', 'THE LOSERS', 'THE LOST BOYS', 'THE MOVEMENT', 'THE MULTIVERSITY', 'THE NAMES OF MAGIC', 'THE NEW DEADWARDIANS','THE NEW GODS', 'THE OMAC PROJECT', 'THE OMEGA MEN', 'THE ORACLE CODE', 'THE RAY', 'THE TRENCHCOAT BRIGADE', 'THE TWILIGHT CHILDREN', 'THE UN-MEN', 'THE UNEXPECTED', 'THE UNWRITTEN', 'THE VIGIL', 'THE WAKE', 'THE WANDERERS', 'THE WILD STORM', 'THE WITCHING', 'TIME WARP', 'TIME MASTERS', 'TIMBER WOLF', 'TOM STRONG', 'TOP 10', 'TORSO', 'TRANSMETROPOLITAN', 'TRILLIUM', 'TRIGGER', 'TRINITY OF SIN', 'TRUTH AND JUSTICE', 'TWO STEP', 'UNCLE SAM', 'UNEARTHED', 'UNDERWORLD UNLEASHED', 'V FOR VENDETTA', 'VALOR', 'VAMPS', 'VERTIGO', 'VICTOR AND NORA', 'VICTORIAN UNDEAD', 'VIXEN', 'VOODOO', 'WACKY RACELAND', 'WALLER VS. WILDSTORM', 'WARRIORS AND A WEE WONDER', 'WEIRD WESTERN TALES', 'WEIRD WAR TALES', 'WEIRD MYSTERY TALES', 'HOUSE OF MYSTERY', 'WELCOME TO TRANQUILITY', 'WETWORKS', 'WHISTLE', 'WHIZ COMICS', "WHO'S WHO", 'WILD DOG', 'WILDC.A.T.S', 'WILDCORE', 'WILDSTORM', 'WITCHCRAFT']









'''FIRST STEP: DC'''


def scrape_dc():
    url = "https://www.dcuniverseinfinite.com/api/search_proxy/1/search"
    headers = {
        "content-type": "application/json;charset=UTF-8",
        "x-consumer-key": "DA59dtVXYLxajktV",
        "referer": "https://www.dcuniverseinfinite.com/browse/comics",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "cookie": "PASTE_YOUR_COOKIE_HERE",
    }

    dc_all_series = []
    page = 1
    per_page = 100

    while True:
        payload = {
            "page": page,
            "per_page": per_page,
            "document_types": ["comicseries"],
            "filters": {},
            "apply_transform": True,
            "sort_direction": {"comicseries": "asc"},
            "sort_field": {"comicseries": "title"},
        }

        resp = requests.post(url, json=payload, headers=headers)
        resp.raise_for_status()  # fail loudly instead of silently parsing bad JSON
        data = resp.json()

        records = data.get("records", {}).get("comicseries", [])
        if not records:
            break  # no more pages

        dc_all_series.extend(records)
        print(f"page {page}: got {len(records)} series (running total: {len(dc_all_series)})")

        page += 1
        time.sleep(0.5)  # dont be a dick

    return dc_all_series


'''SECOND STEP: MARVEL'''

def scrape_marvel():
    # placeholder until Marvel scraping is implemented
    return []




def filter_series(series_list, exclude_terms):
    '''removes any series you will probably never pick up anyways so why have them in your database?'''
    kept = []
    excluded = []

    for record in series_list:
        name = record.get('title')  ## this can be anything you want i think
        if not name:
            continue
        if any(term in name.upper() for term in exclude_terms):
            excluded.append(name)
            continue
        kept.append(name)

    print(f"Kept: {len(kept)}  |  Excluded: {len(excluded)}")
    return sorted(kept), sorted(excluded)


def parse_creator_filter_html(html_path):

    with open(html_path, encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    names = []
    for li in soup.select('li.browse-menu__filter'):
        name = li.get('aria-label')
        if name:
            names.append(name.strip())
    return names


def build_creator_database(artists_html, writers_html, output_path):
    artists = parse_creator_filter_html(artists_html)
    writers = parse_creator_filter_html(writers_html)

    db = {
        "artists": sorted(set(artists)),
        "writers": sorted(set(writers)),
        "all_creators": sorted(set(artists) | set(writers)),
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=2)

    print(f"Artists: {len(artists)}")
    print(f"Writers: {len(writers)}")
    print(f"Total unique creators: {len(db['all_creators'])}")

    return db




def main():
    dc_all_series = scrape_dc()
    marvel_all_series = scrape_marvel()

    all_series_raw = {
        "DC": dc_all_series,
        "Marvel": marvel_all_series,
    }

    preprocess_dir = "backend/preprocesses"
    db_dir = "comics_db"
    os.makedirs(preprocess_dir, exist_ok=True)
    os.makedirs(db_dir, exist_ok=True)

    # RAW dc comics database will stay saved. 
    with open(os.path.join(preprocess_dir, "dc_series_raw.json"), "w") as f:
        json.dump(dc_all_series, f, indent=2)

    with open(os.path.join(preprocess_dir, "all_comic_series_raw.json"), "w") as f:
        json.dump(all_series_raw, f, indent=2)

    # filtered dc comics database for actual use
    dc_filtered, dc_excluded = filter_series(dc_all_series, EXCLUDE)

    print(f"\nDC unique series (filtered): {len(dc_filtered)}")

    with open(os.path.join(db_dir, "all_comic_series.json"), "w") as f:
        json.dump({"DC": dc_filtered}, f, indent=2)

    with open(os.path.join(preprocess_dir, "dc_excluded_series.json"), "w") as f:
        json.dump(dc_excluded, f, indent=2)


    database_dir = 'comics_db'
    build_creator_database(
        artists_html= r"backend\preprocesses\artist_filter.html",
        writers_html= r"backend\preprocesses\writers_filter.html",
        output_path=os.path.join(database_dir, "all_comic_creators.json"),
    )




if __name__ == "__main__":
    main()