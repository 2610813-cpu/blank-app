%%writefile app.py
import streamlit as st
import pandas as pd
import requests
import pydeck as pdk

# 1. 웹앱 기본 설정 (가로로 넓게 쓰기)
st.set_page_config(page_title="실시간 항공 레이더", layout="wide")
st.title("✈️ 실시간 한반도 비행기 레이더")

# 2. 데이터 가져오기 함수 (캐싱 적용: 너무 자주 새로고침되어 차단당하는 것 방지)
@st.cache_data(ttl=60) # 60초 동안은 기존 데이터를 기억해둡니다.
def get_flight_data():
    url = "https://opensky-network.org/api/states/all?lamin=33.0&lomin=124.0&lamax=39.0&lomax=132.0"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data and data.get('states'):
            columns = ['icao24', 'callsign', 'origin_country', 'time_position', 'last_contact', 
                       'longitude', 'latitude', 'baro_altitude', 'on_ground', 'velocity', 
                       'true_track', 'vertical_rate', 'sensors', 'geo_altitude', 'squawk', 'spi', 'position_source']
            df = pd.DataFrame(data['states'], columns=columns)
            
            # [전처리] 지상 비행기 제외 및 결측치 제거
            df = df[df['on_ground'] == False]
            df = df.dropna(subset=['latitude', 'longitude', 'baro_altitude'])
            
            # callsign(항공편명)이 비어있는 경우 'Unknown'으로 처리
            df['callsign'] = df['callsign'].apply(lambda x: x.strip() if isinstance(x, str) and x.strip() else "Unknown")
            return df
    except Exception as e:
        st.error(f"데이터를 가져오는 중 오류가 발생했습니다: {e}")
        return None
    return pd.DataFrame() # 데이터가 없을 경우 빈 데이터프레임 반환

# 3. 데이터 로드 및 화면 표시
with st.spinner("하늘에 있는 비행기들을 찾고 있습니다..."):
    df = get_flight_data()

if df is not None and not df.empty:
    st.success(f"현재 한반도 상공에 **{len(df)}대**의 비행기가 날고 있습니다!")
    
    # 4. Pydeck 3D 지도 그리기
    # 비행기를 점(Scatterplot)으로 표시
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position="[longitude, latitude]", # 위치 (경도, 위도 순서주의!)
        get_radius=3000,                      # 점의 크기 (반경 3km)
        get_fill_color="[255, 75, 75, 200]",  # 점의 색상 (빨간색, 투명도)
        pickable=True,                        # 마우스를 올렸을 때 반응하도록 설정
    )

    # 지도의 초기 중심점과 시야각 설정 (한반도 중심)
    view_state = pdk.ViewState(
        latitude=36.0, 
        longitude=127.5, 
        zoom=5.5, 
        pitch=45, # 45도 기울여서 3D 느낌 내기
    )

    # 지도 출력
    st.pydeck_chart(pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/dark-v10", # 멋진 다크 모드 지도
        tooltip={"text": "항공편: {callsign}\n고도: {baro_altitude}m\n국적: {origin_country}"} # 마우스 오버 시 정보
    ))
    
    # 새로고침 버튼
    if st.button("🔄 데이터 새로고침"):
        st.cache_data.clear()
        st.rerun()
else:
    st.warning("현재 표시할 비행기 데이터가 없습니다. 잠시 후 다시 시도해주세요.")
