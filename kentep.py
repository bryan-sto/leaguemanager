import streamlit as st
import datetime
import random
import json
import requests
import os
from itertools import combinations
import math
from io import BytesIO

# --- Basic Colors Definition ---
BASIC_COLORS_LIMITED = {
    "Blue": "#0000FF", "Yellow": "#FFFF00", "White": "#FFFFFF",
    "Black": "#000000", "Red": "#FF0000"
}
BASIC_COLOR_HEX_LIST = list(BASIC_COLORS_LIMITED.values())

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

@st.cache_data
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

@st.cache_data
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

# --- Defaults ---
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
        'poster_text_for_copy': "", 'parsed_teams_for_output_cache': []
    }
    for key, default_value in defaults.items():
        if force_reset or key not in st.session_state:
            st.session_state[key] = default_value

initialize_session_state()

# --- Page Config ---
st.set_page_config(layout="wide", page_title="Kentep League Manager")
st.title("⚽ Kentep League Manager")

# --- Sidebar Controls ---
with st.sidebar:
    st.header("⚙️ Konfigurasi Event")

    # --- Cloud Storage ---
    with st.expander("☁️ Cloud Storage & Sync", expanded=True):
        
        # Try to get secrets from Streamlit's secrets manager, then fall back to text input
        api_key = st.secrets.get("JSONBIN_API_KEY")
        bin_id = st.secrets.get("JSONBIN_BIN_ID")

        if not api_key or not bin_id:
            st.info(
                """
                **How to enable Cloud Sync:**
                1. Add `JSONBIN_API_KEY` and `JSONBIN_BIN_ID` to your Streamlit Cloud app secrets.
                
                You can get these keys from [jsonbin.io](https://jsonbin.io) after creating a free account and a new JSON bin.
                """
            )
            api_key_input = st.text_input("JSONBin API Key (Fallback)", type="password", help="Enter if not set in secrets")
            bin_id_input = st.text_input("JSONBin Bin ID (Fallback)", type="password", help="Enter if not set in secrets")
            if not api_key: api_key = api_key_input
            if not bin_id: bin_id = bin_id_input

        cloud_cols = st.columns(2)
        with cloud_cols[0]:
            if st.button("💾 Save to Cloud", key="save_to_cloud"):
                if api_key and bin_id:
                    headers = {
                        'Content-Type': 'application/json',
                        'X-Master-Key': api_key,
                        'X-Bin-Name': f"Kentep Event - {st.session_state.event_date.isoformat()}"
                    }
                    snapshot = {}
                    keys_to_save = ['event_title','event_date','event_time_start','event_time_end','event_place',
                                    'event_publisher','event_organizer','kick_off_time','price_player','price_gk',
                                    'num_teams','game_duration','teams_data','form_global_outfield_players',
                                    'form_global_goalkeepers','players_distributed']
                    for k in keys_to_save:
                        val = st.session_state.get(k)
                        if isinstance(val, (datetime.date, datetime.time)):
                            snapshot[k] = val.isoformat()
                        else:
                            snapshot[k] = val
                    
                    try:
                        response = requests.put(f"https://api.jsonbin.io/v3/b/{bin_id}", json=snapshot, headers=headers)
                        response.raise_for_status()
                        st.success("Successfully saved to cloud!")
                    except requests.exceptions.RequestException as e:
                        st.error(f"Cloud save failed: {e}")
                else:
                    st.warning("API Key and Bin ID are required.")

        with cloud_cols[1]:
            if st.button("🔄 Load from Cloud", key="load_from_cloud"):
                if api_key and bin_id:
                    headers = {'X-Master-Key': api_key}
                    try:
                        response = requests.get(f"https://api.jsonbin.io/v3/b/{bin_id}/latest", headers=headers)
                        response.raise_for_status()
                        loaded_data = response.json().get('record', {})

                        for k, v in loaded_data.items():
                            if k == 'event_date':
                                try: st.session_state['event_date'] = datetime.datetime.strptime(v, "%Y-%m-%d").date()
                                except: pass
                            elif k in ('event_time_start','event_time_end','kick_off_time'):
                                try: st.session_state[k] = datetime.datetime.strptime(v, "%H:%M:%S").time()
                                except: pass
                            else:
                                st.session_state[k] = v
                        
                        st.success("Successfully loaded from cloud!")
                        st.rerun()
                    except requests.exceptions.RequestException as e:
                        st.error(f"Cloud load failed: {e}")
                else:
                    st.warning("API Key and Bin ID are required.")
    st.markdown("---")

    st.subheader("General Info")
    st.text_input("Event Title", key="event_title")
    st.date_input("Tanggal", key="event_date")
    st.time_input("Start Time", key="event_time_start")
    st.time_input("End Time", key="event_time_end")
    st.text_input("Tempat", key="event_place")
    st.text_input("Video/Photographer", key="event_publisher")
    st.text_input("Wasit", key="event_organizer")
    st.time_input("Kick Off Time", key="kick_off_time")

    st.subheader("Pricing (HTM)")
    st.number_input("Price per Player (IDR)", min_value=0.0, key="price_player", step=1000.0, format="%.0f")
    st.number_input("Price per Goalkeeper (IDR)", min_value=0.0, key="price_gk", step=1000.0, format="%.0f")
    st.markdown("---")

    st.subheader("💰 Financial Summary")
    total_players = 0
    total_gks = 0
    paid_players = 0
    paid_gks = 0
    teams_source = st.session_state.get('parsed_teams_for_output_cache', [])
    if not teams_source and st.session_state.get('players_distributed'):
        teams_source = st.session_state.get('teams_data', [])
    if teams_source:
        all_players_list = [p for team in teams_source for p in team.get('players', [])]
        for player in all_players_list:
            if player.get('is_gk'):
                total_gks += 1
                if player.get('paid'): paid_gks += 1
            else:
                total_players += 1
                if player.get('paid'): paid_players += 1
    price_player = st.session_state.get('price_player', 0.0)
    price_gk = st.session_state.get('price_gk', 0.0)
    collected_income = (paid_players * price_player) + (paid_gks * price_gk)
    expected_income = (total_players * price_player) + (total_gks * price_gk)
    st.metric(label="Collected Income", value=f"IDR {collected_income:,.0f}")
    if expected_income > 0:
        try:
            st.progress(collected_income / expected_income)
        except ZeroDivisionError:
            st.progress(0.0)
        st.caption(f"Expected: IDR {expected_income:,.0f}")
    else:
        st.caption("No players to calculate income from.")
    st.markdown("---")

    st.subheader("Actions")
    if st.button("⚠️ Reset All Inputs & Data", key="reset_all_button"):
        initialize_session_state(force_reset=True)
        st.success("All inputs and data have been reset.")
        st.rerun()

# --- Main Tabs ---
tab1, tab2, tab3 = st.tabs(["👤 Player Pool & Setup Team", "👥 Team Rosters & Edit", "📋 Poster Output"])

with tab1:
    st.header("Enter Player Pool and Define Teams")
    with st.form(key="player_pool_form"):
        st.markdown("Masukin Nama Player Dan Goalkeeper .")
        form_num_teams = st.number_input("Jumlah Team", min_value=1, max_value=26, value=st.session_state.num_teams, step=1, key="form_num_teams_input")
        form_game_duration = st.number_input("Durasi Per Game (menit)", min_value=5, value=st.session_state.game_duration, step=1, key="form_game_duration_input")
        cols_form = st.columns(2)
        with cols_form[0]:
            global_outfield_players_input = st.text_area("ALL Players", value=st.session_state.form_global_outfield_players, height=200, key="form_outfield_input", help="Example:\n1. John Doe\nPlayer Two\n3) Third Player")
        with cols_form[1]:
            global_goalkeepers_input = st.text_area("ALL Goalkeepers", value=st.session_state.form_global_goalkeepers, height=200, key="form_gk_input", help="Example:\nGK Mike\n2. Keeper Sue")
        submit_distribute_button = st.form_submit_button(label="🎲 Bagikan Pemain Secara Random")

    if submit_distribute_button:
        st.session_state.num_teams = form_num_teams
        st.session_state.game_duration = form_game_duration
        st.session_state.form_global_outfield_players = global_outfield_players_input
        st.session_state.form_global_goalkeepers = global_goalkeepers_input
        st.session_state.poster_text_for_copy = ""
        st.session_state.parsed_teams_for_output_cache = []
        outfield_player_names = parse_player_list_from_raw_text(st.session_state.form_global_outfield_players)
        goalkeeper_names = parse_player_list_from_raw_text(st.session_state.form_global_goalkeepers)

        if st.session_state.num_teams < 1:
            st.error("Number of teams must be at least 1.")
        elif not outfield_player_names and st.session_state.num_teams > 0:
            st.error("Please enter outfield players if you want to form teams.")
        else:
            if len(outfield_player_names) < st.session_state.num_teams and st.session_state.num_teams > 0:
                st.warning(f"There are fewer outfield players ({len(outfield_player_names)}) than teams ({st.session_state.num_teams}).")
            
            random.shuffle(outfield_player_names)
            random.shuffle(goalkeeper_names)
            temp_teams_data = []
            for i in range(st.session_state.num_teams):
                team_id_char = generate_team_id(i)
                team_display_name, team_color = generate_simplified_team_name_and_color(team_id_char)
                temp_teams_data.append({"id": team_id_char, "team_name_display": team_display_name, "team_color_hex": team_color, "players": []})
            
            for idx, player_name in enumerate(outfield_player_names):
                team_index = idx % st.session_state.num_teams
                player_id = f"player_{team_index}_{len(temp_teams_data[team_index]['players'])}"
                temp_teams_data[team_index]['players'].append({'id': player_id, 'name': player_name, 'is_gk': False, 'paid': False})
            
            assigned_gks_count = 0
            for i in range(st.session_state.num_teams):
                if assigned_gks_count < len(goalkeeper_names):
                    gk_name = goalkeeper_names[assigned_gks_count]
                    player_id = f"player_{i}_{len(temp_teams_data[i]['players'])}"
                    temp_teams_data[i]['players'].append({'id': player_id, 'name': gk_name, 'is_gk': True, 'paid': False})
                    assigned_gks_count += 1
            
            st.session_state.teams_data = temp_teams_data
            st.session_state.players_distributed = True
            st.success(f"Players Terdistribusi Ke {st.session_state.num_teams} team! Cek Tab 'Team Rosters & Edits'.")
            total_players = len(outfield_player_names) + len(goalkeeper_names)
            st.info(f"✅ {total_players} Players | {len(goalkeeper_names)} Goalkeepers | {st.session_state.num_teams} Teams")
            st.rerun()

    if not st.session_state.players_distributed:
         st.info("Masukin Nama Player Diatas Lalu Klik 'Bagikan Pemain Secara Random.'")

with tab2:
    st.header("Preview Dan Edit Roster Team")
    if st.session_state.players_distributed and st.session_state.teams_data:
        st.markdown("_Player Dibagi Secara Acak Tapi Masih Bisa Diedit Manual._")
        num_roster_cols = min(len(st.session_state.teams_data), 2)
        cols_roster = st.columns(num_roster_cols) if num_roster_cols > 0 else [st]
        col_idx_roster = 0
        parsed_teams_for_cache = []
        needs_rerun = False
        for i in range(len(st.session_state.teams_data)):
            with cols_roster[col_idx_roster % num_roster_cols]:
                team_data_ref = st.session_state.teams_data[i]
                team_id = team_data_ref['id']
                with st.expander(f"{team_data_ref.get('team_name_display', f'Team {team_id}')}", expanded=True):
                    team_data_ref['team_name_display'] = st.text_input("Nama Team", value=team_data_ref.get('team_name_display'), key=f"team_name_display_{team_id}")
                    team_data_ref['team_color_hex'] = st.color_picker(f"Team {team_id} Color", value=team_data_ref.get('team_color_hex', generate_random_basic_color_hex()), key=f"team_color_hex_{team_id}")
                    st.markdown(f"<span style='font-size: 12px; color: {team_data_ref['team_color_hex']}; background-color: {team_data_ref['team_color_hex']}; border-radius: 3px;'>    </span> Selected Color", unsafe_allow_html=True)
                    st.markdown("---")
                    st.markdown("**Roster**")
                    header_cols = st.columns([4, 2, 1]); header_cols[0].markdown("_Player Name_"); header_cols[1].markdown("_Paid?_")
                    
                    players_to_remove_indices = []
                    for p_idx, player in enumerate(team_data_ref['players']):
                        p_cols = st.columns([4, 2, 1])
                        with p_cols[0]:
                            display_name, gk_prefix = (player['name'], "🧤 GK: ")
                            if player['is_gk']: display_name = f"{gk_prefix}{display_name}"
                            new_name_input = st.text_input("Player Name", value=display_name, key=f"p_name_{team_id}_{player['id']}", label_visibility="collapsed")
                            cleaned_new_name = new_name_input
                            if player['is_gk'] and cleaned_new_name.startswith(gk_prefix): cleaned_new_name = cleaned_new_name[len(gk_prefix):]
                            if cleaned_new_name != player['name']: player['name'] = cleaned_new_name
                        with p_cols[1]:
                            is_paid = st.checkbox("Paid", value=player.get('paid', False), key=f"p_paid_{team_id}_{player['id']}", label_visibility="collapsed")
                            if is_paid != player.get('paid', False): player['paid'] = is_paid
                        with p_cols[2]:
                            if st.button("x", key=f"p_rem_{team_id}_{player['id']}", help=f"Remove {player['name']}"):
                                players_to_remove_indices.append(p_idx); needs_rerun = True
                    if players_to_remove_indices:
                        for p_idx in sorted(players_to_remove_indices, reverse=True): team_data_ref['players'].pop(p_idx)
                        needs_rerun = True
                    
                    add_player_cols = st.columns(2)
                    with add_player_cols[0]:
                        if st.button("➕ Add Player", key=f"add_player_{team_id}"):
                            team_data_ref['players'].append({'id': f"player_{team_id}_{len(team_data_ref['players'])}_{random.randint(1000,9999)}", 'name': 'New Player', 'is_gk': False, 'paid': False}); needs_rerun = True
                    with add_player_cols[1]:
                        if st.button("🧤 Add GK", key=f"add_gk_{team_id}"):
                            team_data_ref['players'].append({'id': f"player_{team_id}_{len(team_data_ref['players'])}_{random.randint(1000,9999)}", 'name': 'New GK', 'is_gk': True, 'paid': False}); needs_rerun = True
                    
                    outfield_players = [p for p in team_data_ref['players'] if not p['is_gk']]
                    goalkeepers = [p for p in team_data_ref['players'] if p['is_gk']]
                    parsed_teams_for_cache.append({"id": team_id, "display_name": team_data_ref['team_name_display'], "color_hex": team_data_ref['team_color_hex'].upper(), "players": team_data_ref['players'], "player_count": len(outfield_players), "gk_count": len(goalkeepers)})
            col_idx_roster += 1
        
        if needs_rerun: st.rerun()
        st.session_state.parsed_teams_for_output_cache = parsed_teams_for_cache
        if parsed_teams_for_cache:
            all_names = [p['name'] for t in parsed_teams_for_cache for p in t['players']]
            duplicates = {n: all_names.count(n) for n in set(all_names) if all_names.count(n) > 1}
            if duplicates: st.warning(f"Duplicate names detected: {', '.join([f'{k} (x{v})' for k,v in duplicates.items()])}")
    else:
        st.info("Player Belum Dibagiin. Balik ke Player Pool & Setup Team Tab.")

with tab3:
    st.header("Event Poster Output")
    final_teams_for_poster = st.session_state.get('parsed_teams_for_output_cache', [])
    if not final_teams_for_poster:
        st.info("Set Detail Event, Masukin Pemain,Bagikan Pemain,Siapin Poster Lalu Copas Ke WA")
    else:
        summary_cols = st.columns(len(final_teams_for_poster))
        for idx, t in enumerate(final_teams_for_poster):
            with summary_cols[idx]:
                st.markdown(f"**{t['display_name']}**"); st.markdown(f"Players: {t['player_count']} | GK: {t['gk_count']}"); st.markdown(f"<div style='width:18px;height:18px;background:{t['color_hex']};border-radius:4px;'></div>", unsafe_allow_html=True)
        
        if st.button("📝 Prepare Poster Text for Copying", key="prepare_poster_button"):
            output_lines = []
            output_lines.append(f"*{st.session_state.event_title.upper()}*"); output_lines.append(f"{st.session_state.event_date.strftime('%d/%m/%Y')}"); output_lines.append(f"Pkl. {st.session_state.event_time_start.strftime('%H.%M')} - {st.session_state.event_time_end.strftime('%H.%M')}"); output_lines.append("")
            output_lines.append(f"⛳ *{st.session_state.event_place.upper()}*")
            if st.session_state.event_publisher: output_lines.append(f"📽 {st.session_state.event_publisher}")
            if st.session_state.event_organizer: output_lines.append(f"👮 {st.session_state.event_organizer}")
            output_lines.append(""); output_lines.append(f"*KICK OFF {st.session_state.kick_off_time.strftime('%H.%M')}*"); output_lines.append("")
            output_lines.append(f"HTM Player : {st.session_state.price_player:,.0f}"); output_lines.append(f"HTM GK : {st.session_state.price_gk:,.0f}"); output_lines.append("\n")
            
            teams_for_fixtures_generation_with_emoji = []
            for team_info in final_teams_for_poster:
                if not team_info['display_name'].strip(): continue
                color_emoji = COLOR_TO_EMOJI_MAP.get(team_info.get('color_hex', ''), DEFAULT_COLOR_EMOJI)
                display_name_with_emoji = f"{team_info['display_name']} {color_emoji}"
                output_lines.append(f"*{display_name_with_emoji}:*")
                teams_for_fixtures_generation_with_emoji.append({"id": team_info['id'], "display_name_with_emoji": display_name_with_emoji})
                
                player_display_number = 1
                sorted_players = sorted(team_info['players'], key=lambda p: p.get('is_gk', False))
                for player_detail in sorted_players:
                    gk_marker = " (GK)" if player_detail.get('is_gk') else ""
                    paid_marker = " (Paid ✅)" if player_detail.get('paid') else ""
                    output_lines.append(f"{player_display_number}. {player_detail['name']}{gk_marker}{paid_marker}")
                    player_display_number += 1
                output_lines.append("")
            
            output_lines.append("*Game Fixtures :*"); output_lines.append(f"{st.session_state.game_duration} menit/Game"); output_lines.append("Home (H) Kiri"); output_lines.append("Away (A) Kanan"); output_lines.append("")
            if len(teams_for_fixtures_generation_with_emoji) >= 2:
                fixture_strings = generate_round_robin_fixtures(teams_for_fixtures_generation_with_emoji, st.session_state.game_duration)
                output_lines.extend(fixture_strings if fixture_strings else ["Not enough teams for fixtures (minimum 2)."])
            else:
                output_lines.append("Only one or zero teams defined, cannot generate fixtures.")
            
            st.session_state.poster_text_for_copy = "\n".join(output_lines)
            st.success("Poster is ready! You can now copy the text below.")

        if st.session_state.poster_text_for_copy:
            st.subheader("📋 Poster Text (Select All & Copy)")
            st.text_area("Copy the text below:", value=st.session_state.poster_text_for_copy, height=300, key="poster_copy_area", help="Click inside, Ctrl+A (or Cmd+A) to select all, then Ctrl+C to copy.")
            st.markdown("---")
            st.markdown("**Color legend:** " + " | ".join([f"{COLOR_TO_EMOJI_MAP.get(v,DEFAULT_COLOR_EMOJI)} {k}" for k,v in BASIC_COLORS_LIMITED.items()]))
        else:
            st.info("Generate poster first to see the output.")

st.markdown("---")
st.caption("Kentep FC Jaya!")
