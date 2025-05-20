import streamlit as st
import datetime
import random
from itertools import combinations
import math 

# --- Basic Colors Definition ---
BASIC_COLORS_LIMITED = {
    "Blue": "#0000FF", "Yellow": "#FFFF00", "White": "#FFFFFF", 
    "Black": "#000000", "Red": "#FF0000"
}
BASIC_COLOR_HEX_LIST = list(BASIC_COLORS_LIMITED.values())

# --- Color to Emoji Mapping for Poster ---
COLOR_TO_EMOJI_MAP = {
    "#0000FF": "🔵", "#FFFF00": "🟡", "#FFFFFF": "⚪", 
    "#000000": "⚫", "#FF0000": "🔴",
}
DEFAULT_COLOR_EMOJI = "🎨" 

# --- Helper Functions ---
def generate_team_id(index):
    if index < 26: return chr(ord('A') + index)
    return chr(ord('A') + (index // 26) - 1) + chr(ord('A') + (index % 26))

def generate_random_basic_color_hex():
    return random.choice(BASIC_COLOR_HEX_LIST)

def generate_simplified_team_name_and_color(team_id_char):
    team_name_display = f"Team {team_id_char}"
    return team_name_display, generate_random_basic_color_hex()

def parse_player_list_from_raw_text(raw_text):
    player_names = []
    if raw_text:
        raw_lines = raw_text.strip().split('\n')
        for line in raw_lines:
            line = line.strip()
            if not line: continue
            name_part = line
            if '.' in line and line.split('.')[0].strip().isdigit():
                name_part = '.'.join(line.split('.')[1:]).strip()
            elif ')' in line and line.split(')')[0].strip().isdigit():
                 name_part = ')'.join(line.split(')')[1:]).strip()
            if name_part:
                player_names.append(name_part)
    return player_names

def generate_round_robin_fixtures(team_data_for_fixtures, game_duration):
    if len(team_data_for_fixtures) < 2: return []
    teams_for_algo = [(team['id'], team['display_name_with_emoji']) for team in team_data_for_fixtures] 
    original_first_team_id = teams_for_algo[0][0] if teams_for_algo else None
    local_team_ids_with_display = list(teams_for_algo)
    is_odd_teams = len(local_team_ids_with_display) % 2 != 0
    if is_odd_teams: local_team_ids_with_display.append(("BYE", "BYE"))
    n = len(local_team_ids_with_display)
    rounds = n - 1
    fixtures_output_strings = [] 
    game_num = 1
    for r in range(rounds):
        for i in range(n // 2):
            home_team_tuple = local_team_ids_with_display[i]
            away_team_tuple = local_team_ids_with_display[n - 1 - i]
            if home_team_tuple[0] == "BYE" or away_team_tuple[0] == "BYE": continue
            
            current_home_id = home_team_tuple[0]
            current_home_display = home_team_tuple[1] 
            current_away_display = away_team_tuple[1] 
            
            if current_home_id == original_first_team_id and r % 2 != 0 and not is_odd_teams:
                 fixture_str = f"{game_num:02d}. (H) {current_away_display} vs {current_home_display} (A)"
            else:
                 fixture_str = f"{game_num:02d}. (H) {current_home_display} vs {current_away_display} (A)"
            
            fixtures_output_strings.append(fixture_str)
            game_num += 1
        if n > 2:
            last_team_tuple = local_team_ids_with_display.pop()
            local_team_ids_with_display.insert(1, last_team_tuple)
    return fixtures_output_strings

def parse_player_list_from_display_format(raw_text, is_gk=False):
    players = []
    if raw_text:
        raw_lines = raw_text.strip().split('\n')
        for line_num, line in enumerate(raw_lines):
            line = line.strip()
            if not line: continue
            name_part = line
            if '.' in line and line.split('.')[0].strip().isdigit():
                name_part = '.'.join(line.split('.')[1:]).strip()
            elif ')' in line and line.split(')')[0].strip().isdigit():
                 name_part = ')'.join(line.split(')')[1:]).strip()
            if name_part:
                players.append({"name": name_part, "is_gk": is_gk, "original_line_num": line_num + 1})
    return players

# --- Default values for reset ---
DEFAULT_EVENT_TITLE = "MINISOCCER EVENT"
DEFAULT_EVENT_DATE = datetime.date.today() + datetime.timedelta(days=7)
DEFAULT_EVENT_TIME_START = datetime.time(17, 0)
DEFAULT_EVENT_TIME_END = datetime.time(19, 0)
DEFAULT_EVENT_PLACE = "Local Pitch"
DEFAULT_EVENT_PUBLISHER = "Organizer"
DEFAULT_EVENT_ORGANIZER = "You!"
DEFAULT_KICK_OFF_TIME = datetime.time(17, 15)
DEFAULT_PRICE_PLAYER = 50000.0
DEFAULT_PRICE_GK = 25000.0
DEFAULT_NUM_TEAMS = 2
DEFAULT_GAME_DURATION = 10

# --- Initialize Session State ---
def initialize_session_state(force_reset=False):
    defaults = {
        'event_title': DEFAULT_EVENT_TITLE, 'event_date': DEFAULT_EVENT_DATE,
        'event_time_start': DEFAULT_EVENT_TIME_START, 'event_time_end': DEFAULT_EVENT_TIME_END,
        'event_place': DEFAULT_EVENT_PLACE, 'event_publisher': DEFAULT_EVENT_PUBLISHER,
        'event_organizer': DEFAULT_EVENT_ORGANIZER, 'kick_off_time': DEFAULT_KICK_OFF_TIME,
        'price_player': DEFAULT_PRICE_PLAYER, 'price_gk': DEFAULT_PRICE_GK,
        'num_teams': DEFAULT_NUM_TEAMS, 'teams_data': [],
        'game_duration': DEFAULT_GAME_DURATION,
        'form_global_outfield_players': "", 'form_global_goalkeepers': "",
        'players_distributed': False,
        'poster_text_for_copy': ""
    }
    for key, default_value in defaults.items():
        if force_reset or key not in st.session_state:
            st.session_state[key] = default_value
    
    if force_reset:
        st.session_state.teams_data = []
        st.session_state.form_global_outfield_players = ""
        st.session_state.form_global_goalkeepers = ""
        st.session_state.players_distributed = False
        st.session_state.poster_text_for_copy = ""
        if 'parsed_teams_for_output_cache' in st.session_state:
            del st.session_state['parsed_teams_for_output_cache']

initialize_session_state()

# --- App Layout ---
st.set_page_config(layout="wide", page_title="Kentep League Manager")
st.title("⚽ Kentep League Manager")

# --- Sidebar for Event Config & Actions ---
with st.sidebar:
    st.header("⚙️ Konfigurasi Event")
    st.subheader("General Info")
    st.session_state.event_title = st.text_input("Event Title", value=st.session_state.event_title)
    st.session_state.event_date = st.date_input("Tanggal", value=st.session_state.event_date)
    st.session_state.event_time_start = st.time_input("Start Time", value=st.session_state.event_time_start)
    st.session_state.event_time_end = st.time_input("End Time", value=st.session_state.event_time_end)
    st.session_state.event_place = st.text_input("Tempat", value=st.session_state.event_place)
    st.session_state.event_publisher = st.text_input("Video/Photographer", value=st.session_state.event_publisher)
    st.session_state.event_organizer = st.text_input("Wasit", value=st.session_state.event_organizer)
    st.session_state.kick_off_time = st.time_input("Kick Off Time", value=st.session_state.kick_off_time)

    st.subheader("Pricing (HTM)")
    st.session_state.price_player = st.number_input("Price per Player (IDR)", min_value=0.0, value=st.session_state.price_player, step=1000.0, format="%.0f")
    st.session_state.price_gk = st.number_input("Price per Goalkeeper (IDR)", min_value=0.0, value=st.session_state.price_gk, step=1000.0, format="%.0f")
    
    st.markdown("---")
    st.subheader("Actions")
    if st.button("⚠️ Reset All Inputs & Data", key="reset_all_button"):
        initialize_session_state(force_reset=True)
        st.success("All inputs and data have been reset.")
        st.rerun()

# --- Main Interface with Tabs ---
tab1, tab2, tab3 = st.tabs(["👤 Player Pool & Setup Team", "👥 Team Rosters & Edit", "📋 Poster Output"])

with tab1:
    st.header("Enter Player Pool and Define Teams")
    with st.form(key="player_pool_form"):
        st.markdown("Masukin Nama Player Dan Goalkeeper .")
        
        form_num_teams = st.number_input(
            "Jumlah Team", 
            min_value=1, max_value=26,
            value=st.session_state.num_teams,
            step=1, 
            key="form_num_teams_input"
        )
        # MOVED Game Duration here
        form_game_duration = st.number_input(
            "Durasi Per Game", 
            min_value=5, 
            value=st.session_state.game_duration, 
            step=1,
            key="form_game_duration_input"
        )


        cols_form = st.columns(2)
        with cols_form[0]:
            global_outfield_players_input = st.text_area(
                "ALL Players",
                value=st.session_state.form_global_outfield_players,
                height=200,
                key="form_outfield_input",
                help="Example:\n1. John Doe\nPlayer Two\n3) Third Player"
            )
        with cols_form[1]:
            global_goalkeepers_input = st.text_area(
                "ALL Goalkeepers",
                value=st.session_state.form_global_goalkeepers,
                height=200,
                key="form_gk_input",
                help="Example:\nGK Mike\n2. Keeper Sue"
            )
        
        submit_distribute_button = st.form_submit_button(label="🎲 Bagikan Pemain Secara Random")

    if submit_distribute_button:
        st.session_state.num_teams = form_num_teams
        st.session_state.game_duration = form_game_duration # Update game_duration from form
        st.session_state.form_global_outfield_players = global_outfield_players_input
        st.session_state.form_global_goalkeepers = global_goalkeepers_input
        st.session_state.poster_text_for_copy = "" 

        outfield_player_names = parse_player_list_from_raw_text(st.session_state.form_global_outfield_players)
        goalkeeper_names = parse_player_list_from_raw_text(st.session_state.form_global_goalkeepers)
        
        valid_distribution = True
        if st.session_state.num_teams < 1:
            st.error("Number of teams must be at least 1.")
            valid_distribution = False
        elif not outfield_player_names and st.session_state.num_teams > 0 :
            st.error("Please enter outfield players if you want to form teams.")
            valid_distribution = False
        elif len(outfield_player_names) < st.session_state.num_teams and st.session_state.num_teams > 0:
            st.warning(f"There are fewer outfield players ({len(outfield_player_names)}) than teams ({st.session_state.num_teams}). Some teams may have very few or no outfield players initially.")
            
        if valid_distribution:
            random.shuffle(outfield_player_names)
            random.shuffle(goalkeeper_names)

            temp_teams_data = []
            for i in range(st.session_state.num_teams):
                team_id_char = generate_team_id(i)
                team_display_name, team_color = generate_simplified_team_name_and_color(team_id_char)
                temp_teams_data.append({
                    "id": team_id_char, "team_name_display": team_display_name, "team_color_hex": team_color,
                    "outfield_players_raw": "", "goalkeepers_raw": ""
                })

            for idx, player_name in enumerate(outfield_player_names):
                team_index = idx % st.session_state.num_teams
                current_list_str = temp_teams_data[team_index]["outfield_players_raw"]
                if current_list_str:
                    temp_teams_data[team_index]["outfield_players_raw"] += f"\n{len(current_list_str.splitlines()) + 1}. {player_name}"
                else:
                    temp_teams_data[team_index]["outfield_players_raw"] = f"1. {player_name}"

            assigned_gks_count = 0
            for i in range(st.session_state.num_teams):
                if assigned_gks_count < len(goalkeeper_names):
                    gk_name = goalkeeper_names[assigned_gks_count]
                    temp_teams_data[i]["goalkeepers_raw"] = f"1. {gk_name}"
                    assigned_gks_count += 1
                else:
                    temp_teams_data[i]["goalkeepers_raw"] = ""

            st.session_state.teams_data = temp_teams_data
            st.session_state.players_distributed = True
            st.success(f"Players Terdistribusi Ke {st.session_state.num_teams} team! Cek Tab 'Team Rosters & Edits'.")

            if len(goalkeeper_names) > st.session_state.num_teams:
                unassigned_gks = len(goalkeeper_names) - st.session_state.num_teams
                st.warning(f"{unassigned_gks} goalkeeper(s) from the pool were not assigned.")
            elif len(goalkeeper_names) < st.session_state.num_teams and len(goalkeeper_names) > 0:
                teams_without_gks = st.session_state.num_teams - len(goalkeeper_names)
                st.warning(f"{teams_without_gks} team(s) did not receive a goalkeeper.")
            elif len(goalkeeper_names) == 0 and st.session_state.num_teams > 0:
                st.warning("No goalkeepers were available in the pool to assign.")
        else:
            st.session_state.players_distributed = False
    
    if not st.session_state.players_distributed:
         st.info("Enter player details above and click 'Distribute Players' to proceed.")


with tab2:
    st.header("Preview Dan Edit Roster Team")
    if st.session_state.players_distributed and st.session_state.teams_data:
        st.markdown("_Player Dibagi Secara Acak Tapi Masih Bisa Diedit Manual._")
        cols_roster = st.columns(2)
        col_idx_roster = 0
        parsed_teams_for_cache = [] 

        for i in range(len(st.session_state.teams_data)):
            with cols_roster[col_idx_roster % len(cols_roster)]:
                team_data_ref = st.session_state.teams_data[i]
                team_id = team_data_ref['id']
                expander_label = team_data_ref.get('team_name_display', f"Team {team_id}")

                with st.expander(f"{expander_label}", expanded=True):
                    team_data_ref['team_name_display'] = st.text_input(
                        f"Nama Team",
                        value=team_data_ref.get('team_name_display'),
                        key=f"team_name_display_{team_id}"
                    )
                    team_data_ref['team_color_hex'] = st.color_picker(
                        f"Team {team_id} Color",
                        value=team_data_ref.get('team_color_hex'),
                        key=f"team_color_hex_{team_id}"
                    )
                    st.markdown(f"<span style='font-size: 12px; color: {team_data_ref['team_color_hex']}; background-color: {team_data_ref['team_color_hex']}; border-radius: 3px;'>    </span> Selected Color", unsafe_allow_html=True)

                    team_data_ref['outfield_players_raw'] = st.text_area(
                        f"Players for {expander_label}",
                        value=team_data_ref.get('outfield_players_raw', ""),
                        height=120,
                        key=f"team_outfield_players_{team_id}"
                    )
                    team_data_ref['goalkeepers_raw'] = st.text_area(
                        f"Goalkeepers for {expander_label} (max 1)",
                        value=team_data_ref.get('goalkeepers_raw', ""),
                        height=75,
                        key=f"team_gks_{team_id}",
                        help="Initial distribution assigns at most 1 GK. You can edit manually."
                    )
                    
                    outfield_players_parsed = parse_player_list_from_display_format(team_data_ref['outfield_players_raw'], is_gk=False)
                    goalkeepers_parsed = parse_player_list_from_display_format(team_data_ref['goalkeepers_raw'], is_gk=True)
                    all_players_for_team = outfield_players_parsed + goalkeepers_parsed

                    parsed_teams_for_cache.append({
                        "id": team_id, 
                        "display_name": team_data_ref['team_name_display'], 
                        "color_hex": team_data_ref['team_color_hex'].upper(),
                        "players": all_players_for_team,
                        "player_count": len(outfield_players_parsed), 
                        "gk_count": len(goalkeepers_parsed)
                    })
            col_idx_roster += 1
        
        st.session_state.parsed_teams_for_output_cache = parsed_teams_for_cache
        
    else:
        st.info("Players have not been distributed yet. Please go to the 'Player Pool & Team Setup' tab.")


with tab3:
    st.header("Event Poster Output")

    final_teams_for_poster = [] 
    if 'parsed_teams_for_output_cache' in st.session_state and st.session_state.parsed_teams_for_output_cache:
        final_teams_for_poster = st.session_state.parsed_teams_for_output_cache
    elif st.session_state.players_distributed and st.session_state.teams_data: 
        temp_parsed = []
        for team_data_item in st.session_state.teams_data:
            outf = parse_player_list_from_display_format(team_data_item['outfield_players_raw'], is_gk=False)
            gks = parse_player_list_from_display_format(team_data_item['goalkeepers_raw'], is_gk=True)
            temp_parsed.append({
                "id": team_data_item['id'], "display_name": team_data_item['team_name_display'], 
                "color_hex": team_data_item['team_color_hex'].upper(), "players": outf + gks,
                "player_count": len(outf), "gk_count": len(gks)
            })
        final_teams_for_poster = temp_parsed


    if st.button("📝 Prepare Poster Text for Copying", key="prepare_poster_button"):
        if not final_teams_for_poster:
            st.error("No teams have been configured. Please distribute players and review rosters in the previous tabs.")
            st.session_state.poster_text_for_copy = ""
        else:
            output_lines = []
            output_lines.append(f"*{st.session_state.event_title.upper()}*")
            output_lines.append(f"{st.session_state.event_date.strftime('%d/%m/%Y')}")
            output_lines.append(f"Pkl. {st.session_state.event_time_start.strftime('%H.%M')} - {st.session_state.event_time_end.strftime('%H.%M')}")
            output_lines.append("")
            output_lines.append(f"⛳ *{st.session_state.event_place.upper()}*")
            if st.session_state.event_publisher: output_lines.append(f"📽 {st.session_state.event_publisher}")
            if st.session_state.event_organizer: output_lines.append(f"👮 {st.session_state.event_organizer}")
            output_lines.append("")
            output_lines.append(f"*KICK OFF {st.session_state.kick_off_time.strftime('%H.%M')}*")
            output_lines.append("")
            output_lines.append(f"HTM Player : {st.session_state.price_player:,.0f}")
            output_lines.append(f"HTM GK : {st.session_state.price_gk:,.0f}")
            output_lines.append("\n") 

            teams_for_fixtures_generation_with_emoji = [] 

            for team_info in final_teams_for_poster:
                if not team_info['display_name'].strip(): continue
                
                team_color_hex = team_info.get('color_hex', '') 
                color_emoji = COLOR_TO_EMOJI_MAP.get(team_color_hex, DEFAULT_COLOR_EMOJI)
                display_name_with_emoji = f"{team_info['display_name']} {color_emoji}" 
                
                output_lines.append(f"*{display_name_with_emoji}:*") 
                
                teams_for_fixtures_generation_with_emoji.append(
                    {"id": team_info['id'], "display_name_with_emoji": display_name_with_emoji}
                )

                player_display_number = 1
                for player_detail in team_info['players']:
                    gk_marker = " (GK)" if player_detail['is_gk'] else ""
                    output_lines.append(f"{player_display_number}. {player_detail['name']}{gk_marker}")
                    player_display_number += 1
                output_lines.append("")
            
            output_lines.append("*Game Fixtures :*")
            output_lines.append(f"{st.session_state.game_duration} menit/Game") # Use game_duration from session_state
            output_lines.append("Home (H) Kiri")
            output_lines.append("Away (A) Kanan")
            output_lines.append("")
            
            fixture_strings = [] 
            if len(teams_for_fixtures_generation_with_emoji) >=2:
                fixture_strings = generate_round_robin_fixtures(teams_for_fixtures_generation_with_emoji, st.session_state.game_duration)
                if not fixture_strings: 
                    output_lines.append("Not enough teams for fixtures (minimum 2).")
                else:
                    for fixture_item_str in fixture_strings: 
                        output_lines.append(fixture_item_str)

            elif teams_for_fixtures_generation_with_emoji:
                 output_lines.append("Only one team defined, cannot generate fixtures.")
            else:
                output_lines.append("No teams defined to generate fixtures.")
            
            st.session_state.poster_text_for_copy = "\n".join(output_lines)
            st.success("Poster text prepared! See below to copy.")

    if st.session_state.poster_text_for_copy:
        st.subheader("📋 Poster Text (Select All & Copy)")
        st.text_area(
            label="Copy the text below:", 
            value=st.session_state.poster_text_for_copy, 
            height=300, 
            key="poster_copy_area",
            help="Click inside, Ctrl+A (or Cmd+A) to select all, then Ctrl+C (or Cmd+C) to copy."
        )

    elif not (st.session_state.players_distributed and st.session_state.teams_data):
        st.info("Configure event details, input player pool, distribute players, then prepare poster text.")
    else:
        st.info("Review distributed teams or make edits in the 'Team Rosters & Edits' tab, then click 'Prepare Poster Text for Copying'.")


st.markdown("---")
st.caption("Kentep FC Jaya!")