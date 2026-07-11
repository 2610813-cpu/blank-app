import streamlit as st
import pandas as pd
import requests
import pydeck as pdk

# 1. 웹앱 기본 설정
st.set_page_config(page_title="실시간 항공 레이더", layout="wide")
st.title("✈️ 실시간 한반도 비행기 레이더")

# 2. 데이터 가져오기 함수 (플랜 B 안전장치 추가!)
@st.cache_data(ttl=60)
def get_flight_data():
    url = "https://opensky-network.org/api/states/all?lamin=33.0&lomin=124.0&lamax=39.0&lomax=132.0"
    headers = {'User-Agent': 'Python-Streamlit-StudentProject/1.0'}
    
    try:
        # 10초만 기다려보고 안 되면 바로 플랜 B로 넘어갑니다.
        response = requests.get(url, headers=headers, timeout=10)
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
        # [플랜 B] API가 차단되었을 때 띄워줄 테스트용 가상 데이터!
        st.warning("⚠️ 현재 OpenSky 서버가 혼잡하여 접속이 차단되었습니다. 임시 테스트용 비행기 데이터를 표시합니다.")
        
        mock_data = {
            'callsign': ['KOR123 (서울)', 'ASI456 (제주)', 'JEJ789 (부산)', 'JIN012 (대전)', 'AIR345 (동해)'],
            'origin_country': ['South Korea'] * 5,
            'latitude': [37.5, 33.5, 35.1, 36.3, 37.0],
            'longitude': [126.9, 126.5, 129.0, 127.3, 131.0],
            'baro_altitude': [8000, 5000, 6500, 7000, 9000],
            'on_ground': [False, False, False, False, False]
        }
        return pd.DataFrame(mock_data)
        
    return pd.DataFrame()

# 3. 데이터 로드
with st.spinner("하늘에 있는 비행기들을 찾고 있습니다..."):
    df = get_flight_data()

# 4. 지도 시각화
if df is not None and not df.empty:
    st.success(f"현재 지도에 **{len(df)}대**의 비행기가 표시되고 있습니다!")
    
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position="[longitude, latitude]",
        get_radius=8000, # 눈에 확 띄게 점 크기를 8km로 키웠습니다
        get_fill_color="[255, 75, 75, 200]",
        pickable=True,
    )

    view_state = pdk.ViewState(
        latitude=36.0, 
        longitude=127.5, 
        zoom=5.5, 
        pitch=45,
    )

    st.pydeck_chart(pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/dark-v10",
        tooltip={"text": "항공편: {callsign}\n국적: {origin_country}\n고도: {baro_altitude}m"} 
    ))
    
    if st.button("🔄 데이터 새로고침"):
        st.cache_data.clear()
        st.rerun()
