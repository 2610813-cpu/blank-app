import streamlit as st
import pandas as pd
import requests
import pydeck as pdk

# 1. 웹앱 기본 설정
st.set_page_config(page_title="실시간 항공 레이더", layout="wide")
st.title("✈️ 실시간 한반도 비행기 레이더")

# 2. 데이터 가져오기 함수 
@st.cache_data(ttl=60)
def get_flight_data():
    url = "https://opensky-network.org/api/states/all?lamin=33.0&lomin=124.0&lamax=39.0&lomax=132.0"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        if data and data.get('states'):
            columns = [
                'icao24', 'callsign', 'origin_country', 'time_position', 'last_contact', 
                'longitude', 'latitude', 'baro_altitude', 'on_ground', 'velocity', 
                'true_track', 'vertical_rate', 'sensors', 'geo_altitude', 'squawk', 'spi', 'position_source'
            ]
            df = pd.DataFrame(data['states'], columns=columns)
            
            df = df[df['on_ground'] == False]
            df = df.dropna(subset=['latitude', 'longitude', 'baro_altitude'])
            df['callsign'] = df['callsign'].apply(
                lambda x: x.strip() if isinstance(x, str) and x.strip() else "알 수 없음"
            )
            return df
            
    except Exception as e:
        st.error(f"API 서버 접속 지연 또는 차단됨: {e}")
        return pd.DataFrame()
        
    return pd.DataFrame()

# 3. 데이터 로드
with st.spinner("비행기 데이터를 불러오는 중..."):
    df = get_flight_data()

# 4. 지도 시각화
view_state = pdk.ViewState(
    latitude=36.0, 
    longitude=127.5, 
    zoom=5.5, 
    pitch=45,
)

layers = []

if not df.empty:
    st.success(f"현재 한반도 상공에 **{len(df)}대**의 비행기가 있습니다!")
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position="[longitude, latitude]",
        get_radius=3000,
        get_fill_color="[255, 75, 75, 200]",
        pickable=True,
    )
    layers.append(layer)
else:
    st.warning("현재 수신된 실시간 비행기 데이터가 없습니다. (API 서버 지연 또는 비행기 없음)")

# [수정됨] map_style을 스트림릿 기본 제공인 "dark"로 변경했습니다.
st.pydeck_chart(pdk.Deck(
    layers=layers,
    initial_view_state=view_state,
    map_style="dark", 
    tooltip={"text": "항공편: {callsign}\n국적: {origin_country}\n고도: {baro_altitude}m"} if not df.empty else None
))

if st.button("🔄 데이터 새로고침"):
    st.cache_data.clear()
    st.rerun()
