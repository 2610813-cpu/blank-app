import streamlit as st
import pandas as pd
import requests
import pydeck as pdk

# 1. 웹앱 기본 설정 (가로로 넓게 쓰기)
st.set_page_config(page_title="실시간 항공 레이더", layout="wide")
st.title("✈️ 실시간 한반도 비행기 레이더")

# 기존 코드의 2번 데이터 가져오기 함수 부분을 아래 코드로 바꿔치기 하세요.

# 2. 데이터 가져오기 함수 (캐싱 적용: API 차단 방지)
@st.cache_data(ttl=60)
def get_flight_data():
    # 한반도 상공 위경도 범위 설정
    url = "https://opensky-network.org/api/states/all?lamin=33.0&lomin=124.0&lamax=39.0&lomax=132.0"
    
    # [추가된 부분 1] 로봇이 아님을 증명하는 이름표(User-Agent) 달기
    headers = {'User-Agent': 'Python-Streamlit-StudentProject/1.0'}
    
    try:
        # [수정된 부분 2] headers를 포함하고, 기다리는 시간(timeout)을 10초에서 30초로 넉넉하게 늘림
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
            
            df = df[df['on_ground'] == False]
            df = df.dropna(subset=['latitude', 'longitude', 'baro_altitude'])
            df['callsign'] = df['callsign'].apply(
                lambda x: x.strip() if isinstance(x, str) and x.strip() else "알 수 없음"
            )
            return df
            
    except Exception as e:
        st.error(f"데이터를 가져오는 중 오류가 발생했습니다: {e}")
        return None
        
    return pd.DataFrame()

# 3. 데이터 로드 및 안내 문구
with st.spinner("하늘에 있는 비행기들을 찾고 있습니다..."):
    df = get_flight_data()

# 4. 지도 시각화 (데이터가 정상적으로 있을 때만)
if df is not None and not df.empty:
    st.success(f"현재 한반도 상공에 **{len(df)}대**의 비행기가 날고 있습니다!")
    
    # 비행기를 붉은 점으로 표현하는 레이어 설정
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position="[longitude, latitude]", # (경도, 위도) 순서
        get_radius=3000,                      # 점의 크기 (반경 3km)
        get_fill_color="[255, 75, 75, 200]",  # 점의 색상 (붉은색, 약간 투명하게)
        pickable=True,                        # 마우스를 올렸을 때 반응하도록 설정
    )

    # 지도의 초기 중심점 (한반도 중심) 및 카메라 각도 설정
    view_state = pdk.ViewState(
        latitude=36.0, 
        longitude=127.5, 
        zoom=5.5, 
        pitch=45, # 45도로 비스듬히 눕혀서 3D 느낌 내기
    )

    # 화면에 지도 그리기
    st.pydeck_chart(pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/dark-v10", # 다크 모드 지도 배경
        tooltip={"text": "항공편: {callsign}\n국적: {origin_country}\n고도: {baro_altitude}m"} 
    ))
    
    # 수동 새로고침 버튼
    if st.button("🔄 데이터 새로고침"):
        st.cache_data.clear() # 기억해둔 과거 데이터를 지우고
        st.rerun()            # 화면을 새로고침합니다
        
else:
    # 새벽 시간 등 비행기가 하나도 없을 때
    st.warning("현재 표시할 비행기 데이터가 없습니다. 잠시 후 다시 시도해주세요.")
    if st.button("🔄 다시 시도"):
        st.cache_data.clear()
        st.rerun()
