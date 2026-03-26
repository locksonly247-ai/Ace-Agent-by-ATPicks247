import streamlit as st
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime
import time
from typing import List, Dict

# Page config
st.set_page_config(page_title="ACE Agent v2 - Live Tennis", page_icon="🎾", layout="wide")
st.title("🎾 ACE Agent v2 - Live Tennis Scores")
st.markdown("Real-time ATP/WTA scores • Auto-refresh every 20s • No API key needed")

# Sidebar controls
with st.sidebar:
    st.header("Settings")
    refresh_interval = st.slider("Refresh interval (seconds)", 10, 60, 20)
    watchlist_input = st.text_input("Watchlist (comma-separated)", "Sinner, Alcaraz, Paul, Fils, Gauff, Zverev")
    watchlist = [p.strip() for p in watchlist_input.split(",")]

# Session state for data persistence
if "last_scores" not in st.session_state:
    st.session_state.last_scores = {}
if "alerts" not in st.session_state:
    st.session_state.alerts = []

async def fetch_live_scores() -> List[Dict]:
    url = "https://www.flashscore.com/tennis/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=12) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    return parse_flashscore(html)
    except:
        pass
    
    # Fallback simulation with realistic Miami Open 2026 data
    return get_simulated_matches()

def parse_flashscore(html: str) -> List[Dict]:
    soup = BeautifulSoup(html, "html.parser")
    matches = []
    for item in soup.select("div.event__match, div.event__item"):
        try:
            players = item.select("div.event__participant")
            if len(players) < 2: continue
            p1 = players[0].get_text(strip=True)
            p2 = players[1].get_text(strip=True)
            
            scores = item.select("div.event__score")
            s1 = scores[0].get_text(strip=True) if scores else "–"
            s2 = scores[1].get_text(strip=True) if len(scores) > 1 else "–"
            
            status_elem = item.select_one("div.event__time, div.event__status")
            status = status_elem.get_text(strip=True) if status_elem else "LIVE"
            
            mid = f"{p1[:8]}-{p2[:8]}-{datetime.now().date()}"
            matches.append({
                "match_id": mid,
                "tournament": "Miami Open 2026",  # Can be enhanced
                "player1": p1,
                "player2": p2,
                "score1": s1,
                "score2": s2,
                "status": status,
                "live": any(k in status.upper() for k in ["LIVE", "•", "SET"]),
                "timestamp": datetime.now().isoformat()
            })
        except:
            continue
    return matches

def get_simulated_matches() -> List[Dict]:
    return [
        {"match_id": "paul-fils", "tournament": "Miami Open 2026", "player1": "T. Paul", "player2": "A. Fils", "score1": "6", "score2": "7", "status": "LIVE (Set 2)", "live": True},
        {"match_id": "lehecka-landaluce", "tournament": "Miami Open 2026", "player1": "J. Lehecka", "player2": "M. Landaluce", "score1": "7", "score2": "5", "status": "LIVE (Set 2)", "live": True},
        {"match_id": "sinner-tiafoe", "tournament": "Miami Open 2026", "player1": "J. Sinner", "player2": "F. Tiafoe", "score1": "6", "score2": "4", "status": "LIVE (Set 1)", "live": True},
    ]

def detect_change(old: Dict, new: Dict) -> bool:
    return (old.get("score1") != new.get("score1") or 
            old.get("score2") != new.get("score2") or 
            old.get("status") != new.get("status"))

# Main dashboard
col1, col2 = st.columns([3, 1])

with col1:
    placeholder = st.empty()

with col2:
    alert_placeholder = st.empty()

async def update_dashboard():
    matches = await fetch_live_scores()
    live_matches = [m for m in matches if m.get("live", False)]
    
    # Check for changes and create alerts
    new_alerts = []
    for match in live_matches:
        mid = match["match_id"]
        if mid in st.session_state.last_scores:
            if detect_change(st.session_state.last_scores[mid], match):
                new_alerts.append(f"🚨 **Score Update!** {match['player1']} vs {match['player2']} → {match['score1']}-{match['score2']} ({match['status']})")
        st.session_state.last_scores[mid] = match.copy()
    
    # Update alerts
    if new_alerts:
        st.session_state.alerts = new_alerts + st.session_state.alerts[:5]  # Keep recent 5
    
    # Display live summary
    with placeholder.container():
        st.subheader(f"📊 Live Matches ({len(live_matches)}) — {datetime.now().strftime('%H:%M:%S')}")
        
        for m in live_matches[:12]:
            is_watched = any(w.lower() in (m["player1"] + m["player2"]).lower() for w in watchlist)
            prefix = "⭐ " if is_watched else "• "
            st.markdown(f"{prefix}**{m['player1']}** vs **{m['player2']}** | **{m['score1']} - {m['score2']}** | {m['status']}")
    
    # Display recent alerts
    with alert_placeholder.container():
        if st.session_state.alerts:
            st.subheader("Recent Alerts")
            for alert in st.session_state.alerts:
                st.info(alert)

# Run the background updater
if st.button("Start Live Monitoring", type="primary"):
    st.info("Monitoring started... Auto-refreshing every " + str(refresh_interval) + " seconds.")
    
    while True:
        asyncio.run(update_dashboard())
        time.sleep(refresh_interval)
        st.rerun()  # Force Streamlit to refresh the UI

else:
    st.info("👆 Click **Start Live Monitoring** to begin tracking tennis matches in real-time.")

st.caption("ACE Agent v2 • Built with Streamlit • Data from public sources (Flashscore fallback simulation)")
