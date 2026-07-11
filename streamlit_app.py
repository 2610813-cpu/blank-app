import streamlit as st
import pandas as pd
import requests
import pydeck as pdk

# 1. 웹앱 기본 설정
st.set_page_config(page_title="실시간 항공 레이더", layout="wide")
st.title("✈️ 실시간 한반도 비행기 레이더")

# 2. 데이터 가져오기 및 전처리 함수 
@st.cache_data(ttl=60)
def get_flight_data():
    url = "https://opensky-network.org/api/states/all?lamin=33.0&lomin=124.0&lamax=39.0&lomax=132.0"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    # OpenSky 가입 후 아이디/비밀번호를 넣으면 호출 제한이 크게 완화됩니다.
    username = ""  
    password = ""  
    
    try:
        if username and password:
            response = requests.get(url, headers=headers, auth=(username, password), timeout=30)
        else:
            response = requests.get(url, headers=headers, timeout=30)
            
        response.raise_for_status()
        data = response.json()
        
        if data and data.get('states'):
            columns = [
                'icao24', 'callsign', 'origin_country', 'time_position', 'last_contact', 
                'longitude', 'latitude', 'baro_altitude', 'on_ground', 'velocity', 
                'true_track', 'vertical_rate', 'sensors', 'geo_altitude', 'squawk', 'spi', 'position_source'
            ]
            df = pd.DataFrame(data['states'], columns=columns)
            
            # --- [전처리 로직] ---
            # 1. 지상에 있는 비행기 제외
            df = df[df['on_ground'] == False]
            
            # 2. 필수 데이터 결측치 행 제거 
            df = df.dropna(subset=['latitude', 'longitude', 'vertical_rate', 'baro_altitude'])
            
            # 3. 빈 콜사인(호출부호) 문자열 처리
            df['callsign'] = df['callsign'].apply(
                lambda x: x.strip() if isinstance(x, str) and x.strip() else "알 수 없음"
            )

            # 4. Z-스코어 기반 이상치(Outlier) 제거 
            if len(df) > 1: 
                std_val = df['baro_altitude'].std()
                # 표준편차가 0인 경우(모든 고도가 같음) 나누기 오류 방지
                if std_val > 0: 
                    z_scores = (df['baro_altitude'] - df['baro_altitude'].mean()) / std_val
                    df = df[z_scores.abs() <= 3]
            
            return df
            
    except requests.exceptions.HTTPError as e:
        if response.status_code == 429:
            st.error("API 호출 횟수 초과 (Too Many Requests). 잠시 후 다시 시도해주세요.")
        elif response.status_code == 403:
            st.error("API 서버에서 접근을 차단했습니다. 계정 정보를 확인하거나 나중에 시도하세요.")
        else:
            st.error(f"HTTP 에러 발생: {e}")
        return pd.DataFrame()
        
    except Exception as e:
        st.error(f"API 서버 접속 지연 또는 기타 에러 발생: {e}")
        return pd.DataFrame()
        
    return pd.DataFrame()

# 3. 데이터 로드
with st.spinner("비행기 데이터를 불러오는 중... (서버 상황에 따라 최대 30초 소요)"):
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
    st.success(f"현재 한반도 상공에서 비행 중인 정상 데이터는 **{len(df)}대**입니다!")
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

# Pydeck 차트 렌더링
st.pydeck_chart(pdk.Deck(
    layers=layers,
    initial_view_state=view_state,
    map_style="dark", 
    tooltip={"text": "항공편: {callsign}\n국적: {origin_country}\n고도: {baro_altitude}m\n수직속도: {vertical_rate}m/s"} if not df.empty else None
))

# 새로고침 버튼 작동 방식 수정 (최신 Streamlit 방식)
if st.button("🔄 데이터 새로고침"):
    st.cache_data.clear()
    st.rerun()
